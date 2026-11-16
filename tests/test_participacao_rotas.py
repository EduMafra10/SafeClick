"""Permissões, consentimento e renderização sem conectar ao banco do site."""
import re
from contextlib import nullcontext
from decimal import Decimal
from importlib import import_module
from unittest.mock import Mock

import pytest
from psycopg import Error
from werkzeug.datastructures import MultiDict

from safeclick import create_app, avaliacoes_db, ranking_db
from safeclick.sessoes import Usuario


@pytest.fixture
def site(monkeypatch):
    monkeypatch.setenv('SECRET_KEY', 'chave-exclusiva-destes-testes')
    monkeypatch.setattr('psycopg.connect', Mock(side_effect=AssertionError('Banco real proibido')))
    monkeypatch.setattr(import_module('safeclick.aceite_termos'), 'usuario_aceitou_termos_atuais', lambda *_: True)
    monkeypatch.setattr('safeclick.sessoes.registrar_evento', Mock())
    app = create_app()
    app.config.update(TESTING=True, AVALIACOES_ATIVAS=True)
    cliente = app.test_client()
    pessoa = Usuario({'id': 7, 'nome': 'Nome privado', 'email': 'privado@example.test', 'perfil': 'usuario'})
    monkeypatch.setattr(app.login_manager, '_user_callback', lambda _: pessoa)
    return app, cliente, pessoa


def entrar(site, perfil='usuario'):
    _, cliente, pessoa = site
    pessoa.perfil = perfil
    with cliente.session_transaction() as sessao:
        sessao['_user_id'] = '7'
        sessao['_fresh'] = True


def token(cliente, rota):
    resposta = cliente.get(rota)
    assert resposta.status_code == 200
    return re.search(r'name="csrf_token"[^>]+value="([^"]+)"', resposta.text)[1]


def test_avaliacoes_e_ranking_sao_consultaveis_sem_login(site, monkeypatch):
    _, cliente, _ = site
    monkeypatch.setattr(avaliacoes_db, 'listar_publicas', Mock(return_value=([], 0)))
    monkeypatch.setattr(ranking_db, 'buscar_ranking', Mock(return_value=([], 0)))
    for rota in ('/avaliacoes/publicas', '/ranking/', '/ranking/privacidade'):
        resposta = cliente.get(rota)
        assert resposta.status_code == 200
        assert resposta.headers['Cache-Control'] == 'no-store'
        assert resposta.headers['X-Robots-Tag'] == 'noindex, nofollow'


def test_comentarios_publicos_escapam_html_e_nao_expoem_identificadores(site, monkeypatch):
    _, cliente, _ = site
    dados = ({'id': 11, 'titulo': 'Senhas', 'slug': 'senhas'},
             {'total': 1, 'media': Decimal('4.0'), 'comentarios': 1},
             [{'nota': 4, 'data': '15/11/2026', 'comentario': '<img src=x onerror=alert(1)>',
               'email': 'segredo@example.test', 'usuario_id': 999}])
    monkeypatch.setattr(avaliacoes_db, 'detalhar_publicas', Mock(return_value=dados))
    for final in ('', '/resumo'):
        resposta = cliente.get('/avaliacoes/publicas/conteudo/11' + final)
        assert resposta.status_code == 200
        assert '&lt;img' in resposta.text
        assert '<img src=x' not in resposta.text
        assert 'segredo@example.test' not in resposta.text
        assert '999' not in resposta.text
        assert '4,0 de 5' in resposta.text


def test_consulta_publica_retorna_404_para_atividade_nao_publicada(site, monkeypatch):
    monkeypatch.setattr(avaliacoes_db, 'detalhar_publicas', Mock(return_value=None))
    assert site[1].get('/avaliacoes/publicas/quiz/21').status_code == 404


@pytest.mark.parametrize('consulta', ['pagina=0', 'pagina=-1', 'pagina=10001', 'pagina=a', 'pagina=1&pagina=2'])
def test_paginacao_invalida_nao_consulta_o_banco(site, monkeypatch, consulta):
    buscar = Mock()
    monkeypatch.setattr(ranking_db, 'buscar_ranking', buscar)
    assert site[1].get('/ranking/?' + consulta).status_code == 400
    buscar.assert_not_called()


@pytest.mark.parametrize('modulo,metodo,rota', [
    (avaliacoes_db, 'listar_publicas', '/avaliacoes/publicas'),
    (ranking_db, 'buscar_ranking', '/ranking/'),
])
def test_indisponibilidade_publica_nao_revela_erro_do_banco(site, monkeypatch, modulo, metodo, rota):
    monkeypatch.setattr(modulo, metodo, Mock(side_effect=Error('segredo-do-banco')))
    resposta = site[1].get(rota)
    assert resposta.status_code == 503
    assert 'Tentar novamente' in resposta.text
    assert 'segredo-do-banco' not in resposta.text


def test_ranking_publica_somente_pseudonimo_e_pontuacao(site, monkeypatch):
    linha = {'apelido': 'Participante ABCD-1234-5678', 'posicao': 1, 'pontos': Decimal('280'),
             'atividades': 3, 'nome': 'Nome secreto', 'email': 'secreto@example.test', 'usuario_id': 4567}
    monkeypatch.setattr(ranking_db, 'buscar_ranking', Mock(return_value=([linha], 1)))
    html = site[1].get('/ranking/').text
    assert linha['apelido'] in html and '280,00' in html
    for privado in ('Nome secreto', 'secreto@example.test', '4567'):
        assert privado not in html


@pytest.mark.parametrize('rota', ['/avaliacoes/minhas', '/ranking/participacao', '/administracao/avaliacoes/comentarios'])
def test_controles_privados_exigem_login(site, rota):
    assert site[1].get(rota).status_code == 302


def test_usuario_nao_pode_moderar_nem_por_post_direto(site, monkeypatch):
    entrar(site)
    moderar = Mock()
    monkeypatch.setattr(avaliacoes_db, 'moderar_comentario', moderar)
    for metodo, rota in [('get', '/administracao/avaliacoes/comentarios'),
                         ('post', '/administracao/avaliacoes/comentarios/conteudo/11/7/aprovar')]:
        assert getattr(site[1], metodo)(rota).status_code == 403
    moderar.assert_not_called()


def test_participacao_requer_csrf_aviso_atual_e_autodeclaracao(site, monkeypatch):
    entrar(site)
    monkeypatch.setattr(ranking_db, 'buscar_preferencia', Mock(return_value=None))
    salvar = Mock()
    monkeypatch.setattr(ranking_db, 'alterar_participacao', salvar)
    csrf = token(site[1], '/ranking/participacao')
    base = {'csrf_token': csrf, 'aviso_versao': ranking_db.VERSAO_AVISO, 'participar': '1', 'maior_de_idade': '1'}
    invalidos = [base | {'csrf_token': ''}, base | {'aviso_versao': 'antigo'},
                 base | {'maior_de_idade': '0'}, base | {'participar': 'sim'},
                 base | {'usuario_id': '99'}, {k: v for k, v in base.items() if k != 'maior_de_idade'},
                 MultiDict(list(base.items()) + [('participar', '1')])]
    for dados in invalidos:
        assert site[1].post('/ranking/participacao', data=dados).status_code == 400
    salvar.assert_not_called()


def test_adesao_e_saida_atuam_apenas_na_conta_da_sessao(site, monkeypatch):
    entrar(site)
    monkeypatch.setattr(ranking_db, 'buscar_preferencia', Mock(return_value=None))
    monkeypatch.setattr(import_module('safeclick.ranking'), 'permitir_tentativa', Mock(return_value=True))
    salvar = Mock()
    monkeypatch.setattr(ranking_db, 'alterar_participacao', salvar)
    base = {'csrf_token': token(site[1], '/ranking/participacao'), 'aviso_versao': ranking_db.VERSAO_AVISO}
    assert site[1].post('/ranking/participacao', data=base | {'participar': '1', 'maior_de_idade': '1'}).status_code == 303
    salvar.assert_called_with(7, True, True)
    assert site[1].post('/ranking/participacao', data=base).status_code == 303
    salvar.assert_called_with(7, False, False)


def test_limite_de_escritas_impede_abuso(site, monkeypatch):
    entrar(site)
    monkeypatch.setattr(ranking_db, 'buscar_preferencia', Mock(return_value=None))
    monkeypatch.setattr(import_module('safeclick.ranking'), 'permitir_tentativa', Mock(return_value=False))
    salvar = Mock()
    monkeypatch.setattr(ranking_db, 'alterar_participacao', salvar)
    dados = {'csrf_token': token(site[1], '/ranking/participacao'), 'aviso_versao': ranking_db.VERSAO_AVISO}
    assert site[1].post('/ranking/participacao', data=dados).status_code == 429
    salvar.assert_not_called()


def test_retirada_e_exclusao_proprias_continuam_disponiveis_com_recurso_desligado(site, monkeypatch):
    entrar(site)
    site[0].config['AVALIACOES_ATIVAS'] = False
    monkeypatch.setattr(avaliacoes_db, 'listar_minhas', Mock(return_value=[]))
    csrf = token(site[1], '/avaliacoes/minhas')
    for acao, metodo in [('retirar', 'retirar_publicacao'), ('excluir', 'excluir_avaliacao')]:
        salvar = Mock(return_value=True)
        monkeypatch.setattr(avaliacoes_db, metodo, salvar)
        rota = '/avaliacoes/minhas/conteudo/11/' + acao
        assert site[1].post(rota, data={}).status_code == 400
        assert site[1].post(rota, data={'csrf_token': csrf, 'usuario_id': '8'}).status_code == 400
        assert site[1].post(rota, data={'csrf_token': [csrf, csrf]}).status_code == 400
        salvar.assert_not_called()
        assert site[1].post(rota, data={'csrf_token': csrf}).status_code == 303
        salvar.assert_called_once_with(7, 'conteudo', 11)
    assert site[1].get('/avaliacoes/publicas').status_code == 404


def test_nova_avaliacao_publica_exige_escolhas_explicitas(site, monkeypatch):
    entrar(site)
    modulo = import_module('safeclick.avaliacoes')
    monkeypatch.setattr(modulo, 'conectar_banco', lambda: nullcontext(object()))
    monkeypatch.setattr(modulo, 'buscar_atividade', Mock(return_value={
        'id': 11, 'titulo': 'Senhas', 'nota': None, 'comentario': None, 'proxima_referencia': None}))
    monkeypatch.setattr(modulo, 'permitir_tentativa', Mock(return_value=True))
    salvar = Mock()
    monkeypatch.setattr(modulo, 'salvar_avaliacao', salvar)
    rota = '/avaliacoes/conteudos/senhas'
    dados = {'csrf_token': token(site[1], rota), 'nota': '5', 'comentario': 'Entendi melhor.',
             'aviso_versao': ranking_db.VERSAO_AVISO, 'publicar_nota': '1', 'publicar_comentario': '1', 'maior_de_idade': '1'}
    for remover in ('maior_de_idade', 'aviso_versao', 'publicar_nota'):
        assert site[1].post(rota, data={k: v for k, v in dados.items() if k != remover}).status_code == 400
    salvar.assert_not_called()
    assert site[1].post(rota, data=dados).status_code == 303
    assert salvar.call_args.kwargs == {'publicar_nota': True, 'publicar_comentario': True,
                                     'maior_de_idade': True, 'aviso_versao': ranking_db.VERSAO_AVISO}


def test_administrador_confirma_moderacao_com_revisao_e_csrf(site, monkeypatch):
    entrar(site, 'administrador')
    item = {'tipo': 'conteudo', 'item_id': 11, 'titulo': 'Senhas', 'usuario_id': 7,
            'comentario': '<script>exemplo</script>', 'revisao': 4, 'publicar_comentario': True,
            'aviso_versao': ranking_db.VERSAO_AVISO}
    conexao = Mock()
    conexao.execute.return_value.fetchone.return_value = item
    monkeypatch.setattr(avaliacoes_db, 'conectar_banco', lambda: nullcontext(conexao))
    moderar = Mock()
    monkeypatch.setattr(avaliacoes_db, 'moderar_comentario', moderar)
    rota = '/administracao/avaliacoes/comentarios/conteudo/11/7/aprovar'
    html = site[1].get(rota).text
    assert '&lt;script&gt;exemplo' in html and '<script>exemplo' not in html
    csrf = token(site[1], rota)
    base = {'csrf_token': csrf, 'revisao': '4', 'confirmar': '1'}
    assert site[1].post(rota, data=base | {'confirmar': '0'}).status_code == 400
    moderar.assert_not_called()
    assert site[1].post(rota, data=base).status_code == 303
    moderar.assert_called_once_with(7, 'conteudo', 11, 7, 4, 'aprovar')
    moderar.side_effect = ValueError('A avaliação mudou. Reabra a lista antes de moderar.')
    assert site[1].post(rota, data=base).status_code == 409
