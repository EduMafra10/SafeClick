"""Permissões, consentimento e renderização sem conectar ao banco do site."""
import re
from contextlib import nullcontext
from decimal import Decimal
from importlib import import_module
from unittest.mock import Mock

import pytest
from psycopg import Error

from safeclick import create_app, avaliacoes_db
from safeclick.avaliacoes_config import VERSAO_AVISO
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


def test_avaliacoes_e_aviso_sao_consultaveis_sem_login(site, monkeypatch):
    _, cliente, _ = site
    monkeypatch.setattr(avaliacoes_db, 'listar_publicas', Mock(return_value=([], 0)))
    for rota in ('/avaliacoes/publicas', '/avaliacoes/privacidade'):
        resposta = cliente.get(rota)
        assert resposta.status_code == 200
        assert resposta.headers['Cache-Control'] == 'no-store'
        assert resposta.headers['X-Robots-Tag'] == 'noindex, nofollow'


@pytest.mark.parametrize('rota', ['/ranking/', '/ranking/participacao', '/ranking/privacidade'])
def test_ranking_foi_removido_inclusive_das_rotas(site, rota):
    assert not any(regra.rule.startswith('/ranking') for regra in site[0].url_map.iter_rules())
    assert site[1].get(rota).status_code == 404
    entrar(site, 'administrador')
    assert site[1].get(rota).status_code == 404


def test_aviso_de_avaliacoes_continua_acessivel_com_coleta_desligada(site):
    site[0].config['AVALIACOES_ATIVAS'] = False
    resposta = site[1].get('/avaliacoes/privacidade')
    assert resposta.status_code == 200
    assert 'ranking' not in resposta.text.lower()


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


def test_barras_publicas_tem_contagens_e_rotulos_acessiveis(site, monkeypatch):
    dados = ({'id': 11, 'titulo': 'Senhas', 'slug': 'senhas'},
             {'total': 3, 'media': Decimal('4.7'), 'comentarios': 0, 'distribuicao': [0, 0, 0, 1, 2]}, [])
    monkeypatch.setattr(avaliacoes_db, 'detalhar_publicas', Mock(return_value=dados))
    html = site[1].get('/avaliacoes/publicas/conteudo/11').text
    assert html.count('<meter ') == 5
    assert 'Nota 5 de 5, 2 de 3 avaliações' in html
    assert 'Nota 4 de 5, 1 de 3 avaliações' in html


def test_pendencias_usam_icone_e_marcador_no_atalho_de_moderacao(site, monkeypatch):
    entrar(site, 'administrador')
    monkeypatch.setattr(avaliacoes_db, 'listar_gestao', Mock(return_value=([], 0)))
    html = site[1].get('/administracao/avaliacoes/comentarios').text
    aviso = re.search(r'<a class="admin-menu-pendencias".*?</a>', html, re.S)[0]
    assert '<svg ' in aviso and 'aria-label="Comentários aguardando aprovação"' in aviso
    assert 'para aprovar</span>' not in aviso and '<strong' not in aviso
    assert 'data-avaliacoes-moderacao' in html and 'data-avaliacoes-sinal hidden' in html
    assert 'evento=cat:avaliacoes' in html


def test_consulta_publica_retorna_404_para_atividade_nao_publicada(site, monkeypatch):
    monkeypatch.setattr(avaliacoes_db, 'detalhar_publicas', Mock(return_value=None))
    assert site[1].get('/avaliacoes/publicas/quiz/21').status_code == 404


@pytest.mark.parametrize('consulta', ['pagina=0', 'pagina=-1', 'pagina=10001', 'pagina=a', 'pagina=1&pagina=2'])
def test_paginacao_invalida_nao_consulta_o_banco(site, monkeypatch, consulta):
    buscar = Mock()
    monkeypatch.setattr(avaliacoes_db, 'listar_publicas', buscar)
    assert site[1].get('/avaliacoes/publicas?' + consulta).status_code == 400
    buscar.assert_not_called()


@pytest.mark.parametrize('modulo,metodo,rota', [
    (avaliacoes_db, 'listar_publicas', '/avaliacoes/publicas'),
])
def test_indisponibilidade_publica_nao_revela_erro_do_banco(site, monkeypatch, modulo, metodo, rota):
    monkeypatch.setattr(modulo, metodo, Mock(side_effect=Error('segredo-do-banco')))
    resposta = site[1].get(rota)
    assert resposta.status_code == 503
    assert 'Tentar novamente' in resposta.text
    assert 'segredo-do-banco' not in resposta.text


@pytest.mark.parametrize('rota', ['/avaliacoes/minhas', '/administracao/avaliacoes/comentarios'])
def test_controles_privados_exigem_login(site, rota):
    assert site[1].get(rota).status_code == 302


@pytest.mark.parametrize('publicada,publica', [(True, True), (True, False), (False, True)])
def test_minhas_preserva_edicao_privacidade_exclusao_e_escape_dos_comentarios(site, monkeypatch, publicada, publica):
    entrar(site)
    buscar = Mock(return_value=[{
        'tipo': 'quiz', 'formato': 'oficina', 'item_id': 21, 'titulo': 'Guia de senhas',
        'nota': 4, 'comentario': '<script>texto não confiável</script>', 'publicar_nota': publica,
        'publicar_comentario': publica, 'moderacao': 'pendente' if publica else 'nao_solicitada',
        'publicada': publicada, 'ultimo_resultado': 31,
    }])
    monkeypatch.setattr(avaliacoes_db, 'listar_minhas', buscar)
    resposta = site[1].get('/avaliacoes/minhas')
    assert resposta.status_code == 200
    buscar.assert_called_once_with(7)
    assert '&lt;script&gt;texto não confiável&lt;/script&gt;' in resposta.text
    assert '<script>texto não confiável</script>' not in resposta.text
    assert ('href="/avaliacoes/quizzes/31"' in resposta.text) == publicada
    assert ('action="/avaliacoes/minhas/quiz/21/retirar"' in resposta.text) == publica
    assert ('Nota pública' if publica else 'Nota privada') in resposta.text
    assert 'action="/avaliacoes/minhas/quiz/21/excluir"' in resposta.text
    assert 'data-confirmar="Excluir esta avaliação?' in resposta.text
    principal = re.search(r'<main\b[^>]*>(.*?)</main>', resposta.text, re.S)[1]
    assert principal.count('name="csrf_token"') == (2 if publica else 1)


def test_minhas_sem_avaliacoes_oferece_destinos_para_atividades(site, monkeypatch):
    entrar(site)
    monkeypatch.setattr(avaliacoes_db, 'listar_minhas', Mock(return_value=[]))
    html = site[1].get('/avaliacoes/minhas').text
    assert 'Você ainda não enviou avaliações.' in html
    assert 'aria-label="Atividades para avaliar"' in html
    assert 'href="/conteudos/"' in html and 'href="/quizzes/"' in html
    assert 'Como seus dados são utilizados' in html


def test_usuario_nao_pode_moderar_nem_por_post_direto(site, monkeypatch):
    entrar(site)
    moderar = Mock()
    monkeypatch.setattr(avaliacoes_db, 'moderar_comentario', moderar)
    for metodo, rota in [('get', '/administracao/avaliacoes/comentarios'),
                         ('post', '/administracao/avaliacoes/comentarios/conteudo/11/7/aprovar')]:
        assert getattr(site[1], metodo)(rota).status_code == 403
    moderar.assert_not_called()


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
             'aviso_versao': VERSAO_AVISO, 'publicar_nota': '1', 'publicar_comentario': '1', 'maior_de_idade': '1'}
    for remover in ('maior_de_idade', 'aviso_versao', 'publicar_nota'):
        assert site[1].post(rota, data={k: v for k, v in dados.items() if k != remover}).status_code == 400
    salvar.assert_not_called()
    assert site[1].post(rota, data=dados).status_code == 303
    assert salvar.call_args.kwargs == {'publicar_nota': True, 'publicar_comentario': True,
                                       'maior_de_idade': True, 'aviso_versao': VERSAO_AVISO}


def test_administrador_confirma_moderacao_com_revisao_e_csrf(site, monkeypatch):
    entrar(site, 'administrador')
    item = {'tipo': 'conteudo', 'item_id': 11, 'titulo': 'Senhas', 'usuario_id': 7,
            'comentario': '<script>exemplo</script>', 'revisao': 4, 'publicar_comentario': True,
            'aviso_versao': VERSAO_AVISO, 'nota': 5, 'data': '17/11/2026'}
    conexao = Mock()
    conexao.execute.return_value.fetchone.return_value = item
    monkeypatch.setattr(avaliacoes_db, 'conectar_banco', lambda: nullcontext(conexao))
    auditoria = Mock()
    monkeypatch.setattr(avaliacoes_db, 'registrar_evento', auditoria)
    moderar = Mock()
    monkeypatch.setattr(avaliacoes_db, 'moderar_comentario', moderar)
    rota = '/administracao/avaliacoes/comentarios/conteudo/11/7/aprovar'
    html = site[1].get(rota).text
    assert '&lt;script&gt;exemplo' in html and '<script>exemplo' not in html
    previa = re.search(r'<div class="avaliacoes-admin-previa-cartao">(.*?)</div>', html, re.S)[1]
    assert 'Participante sem identificação' in previa and '5 de 5' in previa
    assert '17/11/2026' in previa
    assert 'Nome privado' not in previa and 'privado@example.test' not in previa and 'Conta #' not in previa
    auditoria.assert_called_once_with(
        7, 'avaliacao.previa_consultada', 'sucesso', recurso_tipo='avaliacao_conteudo', recurso_id=11,
        detalhes={'formato': 'conteudo', 'acao': 'aprovar', 'autor_id': 7, 'revisao': 4}, conexao=conexao,
    )
    csrf = token(site[1], rota)
    base = {'csrf_token': csrf, 'revisao': '4', 'confirmar': '1'}
    assert site[1].post(rota, data=base | {'confirmar': '0'}).status_code == 400
    moderar.assert_not_called()
    assert site[1].post(rota, data=base).status_code == 303
    moderar.assert_called_once_with(7, 'conteudo', 11, 7, 4, 'aprovar')
    moderar.side_effect = ValueError('A avaliação mudou. Reabra a lista antes de moderar.')
    assert site[1].post(rota, data=base).status_code == 409


@pytest.mark.parametrize('situacao,publico', [('pendente', True), ('aprovada', True), ('rejeitada', True), ('nao_solicitada', False)])
def test_painel_de_comentarios_respeita_estado_e_autorizacao(site, monkeypatch, situacao, publico):
    entrar(site, 'administrador')
    item = {'tipo': 'conteudo', 'item_id': 11, 'titulo': 'Senhas', 'usuario_id': 7, 'nota': 5,
            'comentario': '<script>exemplo</script>', 'moderacao': situacao, 'publicar_comentario': publico,
            'publicar_nota': publico, 'publicada': True}
    monkeypatch.setattr(avaliacoes_db, 'listar_gestao', Mock(return_value=([item], 1)))
    resposta = site[1].get('/administracao/avaliacoes/comentarios')
    assert resposta.status_code == 200
    assert '&lt;script&gt;exemplo' in resposta.text and '<script>exemplo' not in resposta.text
    assert 'ranking' not in resposta.text.lower()
    assert ('/conteudo/11/7/aprovar' in resposta.text) == (publico and situacao != 'aprovada')
    assert ('/conteudo/11/7/ocultar' in resposta.text) == (publico and situacao != 'rejeitada')


@pytest.mark.parametrize('rota,metodo', [
    ('/avaliacoes/publicas', 'listar_publicas'),
    ('/avaliacoes/publicas/quiz/21', 'detalhar_publicas'),
    ('/administracao/avaliacoes/comentarios', 'listar_gestao'),
])
@pytest.mark.parametrize('consulta', ['ordem=invalida', 'ordem=DESC', 'ordem=antigas&ordem=recentes'])
def test_ordenacao_invalida_nao_consulta_o_banco(site, monkeypatch, rota, metodo, consulta):
    entrar(site, 'administrador')
    buscar = Mock()
    monkeypatch.setattr(avaliacoes_db, metodo, buscar)
    assert site[1].get(rota + '?' + consulta).status_code == 400
    buscar.assert_not_called()


def test_filtros_e_ordem_continuam_ativos_na_paginacao_publica(site, monkeypatch):
    buscar = Mock(return_value=([], 45))
    monkeypatch.setattr(avaliacoes_db, 'listar_publicas', buscar)
    resposta = site[1].get('/avaliacoes/publicas?pagina=2&tipo=oficina&busca=senhas&ordem=antigas')
    assert resposta.status_code == 200
    buscar.assert_called_once_with(tipo='oficina', busca='senhas', pagina=2, ordem='antigas')
    assert resposta.text.count('ordem=antigas') == 2
    assert resposta.text.count('tipo=oficina') == 2
    assert '<option value="antigas" selected>' in resposta.text


def test_filtros_e_ordem_continuam_ativos_na_paginacao_da_moderacao(site, monkeypatch):
    entrar(site, 'administrador')
    buscar = Mock(return_value=([], 45))
    monkeypatch.setattr(avaliacoes_db, 'listar_gestao', buscar)
    resposta = site[1].get('/administracao/avaliacoes/comentarios?pagina=2&estado=pendente&ordem=antigas')
    assert resposta.status_code == 200
    buscar.assert_called_once_with(2, 'pendente', 'antigas')
    assert resposta.text.count('ordem=antigas') == 2
    assert resposta.text.count('estado=pendente') >= 2


def test_media_geral_continua_visivel_em_pagina_com_atividades_sem_notas(site, monkeypatch):
    item = {'tipo': 'conteudo', 'id': 42, 'titulo': 'Outra leitura', 'total': 0,
            'atividades_avaliadas': 3, 'media_geral': 4.5, 'notas_filtradas': 6}
    monkeypatch.setattr(avaliacoes_db, 'listar_publicas', Mock(return_value=([item], 21)))
    resposta = site[1].get('/avaliacoes/publicas?pagina=2')
    assert resposta.status_code == 200
    assert '6 notas compartilhadas' in resposta.text and '4,5' in resposta.text
    assert 'Nenhuma atividade avaliada nesta página.' in resposta.text


@pytest.mark.parametrize('formato,rotulo', [('perguntas', 'Quiz'), ('oficina', 'Oficina')])
def test_avaliacoes_identificam_o_formato_da_atividade(site, monkeypatch, formato, rotulo):
    entrar(site, 'administrador')
    item = {'tipo': 'quiz', 'formato': formato, 'id': 21, 'item_id': 21, 'titulo': 'Atividade de senhas',
            'usuario_id': 7, 'nota': 5, 'total': 1, 'media': 5, 'comentario': 'Explicações úteis.',
            'atividades_avaliadas': 1, 'notas_filtradas': 1, 'media_geral': 5,
            'moderacao': 'pendente', 'publicar_comentario': True, 'publicar_nota': True,
            'publicada': True, 'ultimo_resultado': 31}
    monkeypatch.setattr(avaliacoes_db, 'listar_publicas', Mock(return_value=([item], 1)))
    monkeypatch.setattr(avaliacoes_db, 'listar_minhas', Mock(return_value=[item]))
    monkeypatch.setattr(avaliacoes_db, 'listar_gestao', Mock(return_value=([item], 1)))
    monkeypatch.setattr(avaliacoes_db, 'detalhar_publicas', Mock(return_value=(
        item, {'total': 1, 'media': 5, 'comentarios': 0}, [])))
    for rota in ('/avaliacoes/publicas', '/avaliacoes/minhas', '/avaliacoes/publicas/quiz/21',
                 '/administracao/avaliacoes/comentarios'):
        resposta = site[1].get(rota)
        assert resposta.status_code == 200
        assert rotulo in resposta.text
        assert 'Quiz ou oficina' not in resposta.text
    modulo = import_module('safeclick.avaliacoes')
    monkeypatch.setattr(modulo, 'conectar_banco', lambda: nullcontext(object()))
    monkeypatch.setattr(modulo, 'buscar_atividade', Mock(return_value=item | {'proxima_referencia': None}))
    assert f'Avaliar {rotulo.lower()}' in site[1].get('/avaliacoes/quizzes/31').text


def test_contador_de_pendencias_exige_administrador_e_retorna_somente_quantidade(site, monkeypatch):
    buscar = Mock(return_value=3)
    monkeypatch.setattr(import_module('safeclick.administracao'), 'contar_pendentes', buscar)
    rota = '/administracao/avaliacoes/pendentes'
    assert site[1].get(rota).status_code == 302
    entrar(site)
    assert site[1].get(rota).status_code == 403
    buscar.assert_not_called()
    entrar(site, 'administrador')
    resposta = site[1].get(rota)
    assert resposta.status_code == 200
    assert resposta.json == {'total': 3}
    assert resposta.headers['Cache-Control'] == 'no-store'
    site[0].config['AVALIACOES_ATIVAS'] = False
    assert site[1].get(rota).status_code == 404
    buscar.assert_called_once_with()


def test_falha_ao_consultar_pendencias_nao_publica_detalhes_internos(site, monkeypatch):
    entrar(site, 'administrador')
    monkeypatch.setattr(import_module('safeclick.administracao'), 'contar_pendentes',
                        Mock(side_effect=Error('credencial-ficticia-nao-deve-aparecer')))
    resposta = site[1].get('/administracao/avaliacoes/pendentes')
    assert resposta.status_code == 503
    assert 'credencial-ficticia' not in resposta.text
    assert 'total' not in resposta.json
