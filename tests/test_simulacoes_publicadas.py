import json
import os
import re
import unittest
from copy import deepcopy
from html.parser import HTMLParser
from unittest.mock import MagicMock, patch

from flask_login import AnonymousUserMixin, UserMixin
from psycopg import Error
from werkzeug.datastructures import MultiDict

from safeclick import create_app
from safeclick.cenarios_simulacao import CENARIOS
from safeclick.simulacoes_db import (
    SimulacaoAlterada,
    _preparar_cenario_publicado,
    buscar_resultado_simulacao,
    salvar_tentativa_publicada,
)


def versoes_no_html(html):
    """Lê o campo oculto de versão, independentemente de espaços ou quebras de linha."""
    class LeitorVersoes(HTMLParser):
        def __init__(self):
            super().__init__()
            self.valores = []

        def handle_starttag(self, tag, atributos):
            atributos = dict(atributos)
            if tag == 'input' and atributos.get('name') == 'versao_id':
                self.valores.append((atributos.get('type'), atributos.get('value')))

    leitor = LeitorVersoes()
    leitor.feed(html)
    leitor.close()
    return leitor.valores


def registro_cenario(chave='conta_bloqueada', versao_id=101, versao=1):
    conteudo = deepcopy(CENARIOS[chave])
    conteudo['ordem_opcoes'] = list(conteudo['opcoes'])
    conteudo['tipo'] = {
        'conta_bloqueada': 'email', 'entrega_sms': 'sms',
        'falso_conhecido': 'conversa', 'loja_falsa': 'loja',
    }[chave]
    conteudo = json.loads(json.dumps(conteudo, sort_keys=True))
    return {
        'simulacao_id': 1, 'identificador': chave, 'slug': conteudo['slug'],
        'versao_id': versao_id, 'versao': versao, 'conteudo': conteudo,
        'estado': 'publicada', 'opcao': list(CENARIOS[chave]['opcoes'])[0],
    }


def cursor_com(valor):
    cursor = MagicMock()
    cursor.fetchone.return_value = valor
    return cursor


class PersistenciaSimulacaoTeste(unittest.TestCase):
    def setUp(self):
        self.conexao = MagicMock()
        self.contexto = MagicMock()
        self.contexto.__enter__.return_value = self.conexao
        for alvo, atributo, argumentos in [
            ('psycopg.connect', 'bloqueio', {'side_effect': AssertionError('Banco real proibido')}),
            ('safeclick.simulacoes_db.conectar_banco', 'abrir', {'return_value': self.contexto}),
            ('safeclick.auditoria_db.registrar_evento', 'auditar', {}),
        ]:
            patcher = patch(alvo, **argumentos)
            setattr(self, atributo, patcher.start())
            self.addCleanup(patcher.stop)

    def test_grava_usuario_opcao_versao_e_auditoria_juntos(self):
        self.conexao.execute.side_effect = [cursor_com(registro_cenario()), cursor_com({'id': 21})]
        self.assertEqual(salvar_tentativa_publicada(7, 'conta-bloqueada', 101, 'clicar_link'), 21)
        leitura, gravacao = self.conexao.execute.call_args_list
        self.assertIn("s.estado = 'publicada'", leitura.args[0])
        self.assertIn('v.id = s.versao_publicada_id', leitura.args[0])
        self.assertIn('FOR SHARE OF s, v', leitura.args[0])
        self.assertIn('versao_simulacao_id', gravacao.args[0])
        self.assertEqual(gravacao.args[1], (7, 'conta_bloqueada', 'clicar_link', 101))
        evento = self.auditar.call_args.kwargs
        self.assertIs(evento['conexao'], self.conexao)
        self.assertEqual(evento['usuario_id'], 7)
        self.assertEqual(evento['recurso_id'], 21)
        self.assertEqual(evento['evento'], 'simulacao.concluida')
        self.assertEqual(evento['detalhes']['versao_id'], 101)
        self.contexto.__exit__.assert_called_once_with(None, None, None)

    def test_publicacao_trocada_nao_grava(self):
        self.conexao.execute.return_value = cursor_com(registro_cenario(versao_id=102))
        with self.assertRaises(SimulacaoAlterada):
            salvar_tentativa_publicada(7, 'conta-bloqueada', 101, 'clicar_link')
        self.assertEqual(self.conexao.execute.call_count, 1)
        self.auditar.assert_not_called()
        self.assertIs(self.contexto.__exit__.call_args.args[0], SimulacaoAlterada)

    def test_cenario_retirado_nao_grava(self):
        self.conexao.execute.return_value = cursor_com(None)
        with self.assertRaises(SimulacaoAlterada):
            salvar_tentativa_publicada(7, 'conta-bloqueada', 101, 'clicar_link')
        self.assertEqual(self.conexao.execute.call_count, 1)
        self.auditar.assert_not_called()

    def test_opcao_invalida_nao_grava(self):
        self.conexao.execute.return_value = cursor_com(registro_cenario())
        with self.assertRaises(ValueError):
            salvar_tentativa_publicada(7, 'conta-bloqueada', 101, 'inexistente')
        self.assertEqual(self.conexao.execute.call_count, 1)
        self.auditar.assert_not_called()

    def test_falha_auditoria_aborta_a_transacao(self):
        self.conexao.execute.side_effect = [cursor_com(registro_cenario()), cursor_com({'id': 21})]
        self.auditar.side_effect = Error('falha simulada')
        with self.assertRaises(Error):
            salvar_tentativa_publicada(7, 'conta-bloqueada', 101, 'clicar_link')
        self.assertIs(self.contexto.__exit__.call_args.args[0], Error)

    def test_resultado_usa_versao_da_tentativa_e_filtra_proprietario(self):
        registro = registro_cenario()
        registro['estado'] = 'arquivada'
        registro['conteudo']['titulo'] = 'Título respondido anteriormente'
        self.conexao.execute.return_value = cursor_com(registro)
        retorno = buscar_resultado_simulacao(7, 'conta-bloqueada', 21)
        sql, parametros = self.conexao.execute.call_args.args
        self.assertEqual(parametros, (21, 7, 'conta-bloqueada'))
        self.assertIn('t.usuario_id = %s', sql)
        self.assertIn('s.slug = %s', sql)
        self.assertIn('s.identificador = t.simulacao', sql)
        self.assertIn('v.id = t.versao_simulacao_id', sql)
        self.assertNotIn('s.versao_publicada_id', sql)
        self.assertEqual(retorno['cenario']['titulo'], 'Título respondido anteriormente')
        self.assertEqual(retorno['cenario']['versao_id'], 101)
        self.assertFalse(retorno['pode_repetir'])
        self.auditar.assert_not_called()

    def test_tentativa_nao_encontrada(self):
        self.conexao.execute.return_value = cursor_com(None)
        self.assertIsNone(buscar_resultado_simulacao(8, 'conta-bloqueada', 21))

    def test_resultado_inconsistente_nao_e_exibido(self):
        registro = registro_cenario()
        registro['opcao'] = 'nao_existe'
        self.conexao.execute.return_value = cursor_com(registro)
        with self.assertRaises(RuntimeError):
            buscar_resultado_simulacao(7, 'conta-bloqueada', 21)


class UsuarioTeste(UserMixin):
    id = 7
    nome = 'Pessoa de teste'
    email = 'pessoa@example.test'
    perfil = 'usuario'


class RotasSimulacoesPublicadasTeste(unittest.TestCase):
    def setUp(self):
        with patch.dict(os.environ, {'SECRET_KEY': 'chave-de-teste', 'DATABASE_URL': 'postgresql://nao-usado'}):
            self.app = create_app()
        self.app.config.update(TESTING=True, WTF_CSRF_ENABLED=True, SESSION_COOKIE_SECURE=False)
        self.client = self.app.test_client()
        with self.client.session_transaction() as sessao:
            sessao['_user_id'] = '7'
        self.usuario = UsuarioTeste()
        self.cenario = _preparar_cenario_publicado(registro_cenario())
        self.catalogo = {
            chave: _preparar_cenario_publicado(registro_cenario(chave)) for chave in CENARIOS
        }
        self.resultado = {
            'cenario': deepcopy(self.cenario),
            'resultado': deepcopy(self.cenario['opcoes']['clicar_link']),
            'pode_repetir': True,
        }
        patches = [
            ('psycopg.connect', 'bloqueio', {'side_effect': AssertionError('Banco real proibido')}),
            ('requests.sessions.Session.request', 'rede', {'side_effect': AssertionError('API real proibida')}),
            ('flask_login.utils._get_user', 'usuario_atual', {'side_effect': lambda: self.usuario}),
            ('safeclick.aceite_termos.usuario_aceitou_termos_atuais', 'aceite', {'return_value': True}),
            ('safeclick.sessoes.registrar_evento', 'acesso_negado', {}),
            ('safeclick.simulacoes.listar_simulacoes_publicadas', 'listar', {'return_value': self.catalogo}),
            ('safeclick.simulacoes.buscar_simulacao_publicada', 'buscar', {'return_value': self.cenario}),
            ('safeclick.simulacoes.salvar_tentativa_publicada', 'salvar', {'return_value': 21}),
            ('safeclick.simulacoes.buscar_resultado_simulacao', 'resultado_salvo', {'return_value': self.resultado}),
        ]
        for alvo, atributo, argumentos in patches:
            patcher = patch(alvo, **argumentos)
            setattr(self, atributo, patcher.start())
            self.addCleanup(patcher.stop)

    def formulario(self):
        resposta = self.client.get('/simulacoes/conta-bloqueada')
        self.assertEqual(resposta.status_code, 200)
        token = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', resposta.get_data(as_text=True)).group(1)
        return {'csrf_token': token, 'opcao': 'clicar_link', 'versao_id': '101'}

    def test_catalogo_exibe_publicadas(self):
        resposta = self.client.get('/simulacoes/')
        self.assertEqual(resposta.status_code, 200)
        for cenario in self.catalogo.values():
            self.assertIn(cenario['titulo'], resposta.get_data(as_text=True))
        self.listar.assert_called_once_with()

    def test_quatro_modelos_preservam_visual_e_ordem(self):
        estilos = ['conta-bloqueada', 'entrega-sms', 'falso-conhecido', 'loja-falsa']
        for (chave, cenario), estilo in zip(self.catalogo.items(), estilos):
            with self.subTest(chave=chave):
                self.buscar.return_value = cenario
                resposta = self.client.get('/simulacoes/' + cenario['slug'])
                self.assertEqual(resposta.status_code, 200)
                html = resposta.get_data(as_text=True)
                self.assertIn('mensagem--' + estilo, html)
                self.assertEqual(versoes_no_html(html), [('hidden', '101')])
                indices = [html.index(f'value="{opcao}"') for opcao in CENARIOS[chave]['opcoes']]
                self.assertEqual(indices, sorted(indices))

    def test_modelo_visual_nao_depende_do_slug(self):
        cenario = deepcopy(self.catalogo['falso_conhecido'])
        cenario['slug'] = 'nova-conversa'
        self.buscar.return_value = cenario
        resposta = self.client.get('/simulacoes/nova-conversa')
        self.assertIn('mensagem--falso-conhecido', resposta.get_data(as_text=True))
        self.assertNotIn('class="mensagem-chamada"', resposta.get_data(as_text=True))

    def test_visitante_precisa_login(self):
        self.usuario = AnonymousUserMixin()
        resposta = self.client.get('/simulacoes/')
        self.assertEqual(resposta.status_code, 302)
        self.assertIn('/login', resposta.location)
        self.listar.assert_not_called()

    def test_perfil_sem_permissao_e_bloqueado(self):
        self.usuario.perfil = 'sem_permissao'
        self.assertEqual(self.client.get('/simulacoes/').status_code, 403)
        self.listar.assert_not_called()

    def test_administrador_pode_responder(self):
        self.usuario.perfil = 'administrador'
        self.assertEqual(self.client.get('/simulacoes/conta-bloqueada').status_code, 200)

    def test_aceite_continua_obrigatorio(self):
        self.aceite.return_value = False
        resposta = self.client.get('/simulacoes/')
        self.assertEqual(resposta.status_code, 303)
        self.assertIn('/aceitar-termos', resposta.location)
        self.listar.assert_not_called()

    def test_cenario_nao_publicado_retorna_404(self):
        self.buscar.return_value = None
        self.assertEqual(self.client.get('/simulacoes/conta-bloqueada').status_code, 404)

    def test_banco_indisponivel_retorna_503_generico(self):
        self.listar.side_effect = Error('detalhe-interno')
        self.buscar.side_effect = RuntimeError('detalhe-interno')
        for url in ['/simulacoes/', '/simulacoes/conta-bloqueada']:
            with self.subTest(url=url):
                resposta = self.client.get(url)
                self.assertEqual(resposta.status_code, 503)
                self.assertNotIn('detalhe-interno', resposta.get_data(as_text=True))

    def test_envio_redireciona_para_tentativa_salva(self):
        resposta = self.client.post('/simulacoes/conta-bloqueada', data=self.formulario())
        self.assertEqual(resposta.status_code, 303)
        self.assertEqual(resposta.location, '/simulacoes/conta-bloqueada?tentativa=21#titulo-resultado')
        self.salvar.assert_called_once_with(7, 'conta-bloqueada', 101, 'clicar_link')
        self.assertEqual(resposta.headers['Cache-Control'], 'no-store')

    def test_csrf_ausente_ou_invalido_nao_grava(self):
        dados = self.formulario()
        for token in [None, 'invalido']:
            with self.subTest(token=token):
                envio = dict(dados)
                if token is None:
                    envio.pop('csrf_token')
                else:
                    envio['csrf_token'] = token
                self.assertEqual(self.client.post('/simulacoes/conta-bloqueada', data=envio).status_code, 400)
        self.salvar.assert_not_called()

    def test_formato_ou_opcao_invalida_nao_grava(self):
        base = self.formulario()
        envios = [
            {**base, 'opcao': 'inexistente'},
            {**base, 'usuario_id': '8'},
            {k: v for k, v in base.items() if k != 'versao_id'},
            MultiDict([*base.items(), ('opcao', 'responder_email')]),
            MultiDict([*base.items(), ('versao_id', '102')]),
        ]
        for envio in envios:
            with self.subTest(envio=envio):
                self.assertEqual(self.client.post('/simulacoes/conta-bloqueada', data=envio).status_code, 400)
        self.salvar.assert_not_called()

    def test_versao_antiga_retorna_409(self):
        dados = self.formulario()
        dados['versao_id'] = '100'
        resposta = self.client.post('/simulacoes/conta-bloqueada', data=dados)
        self.assertEqual(resposta.status_code, 409)
        self.assertEqual(versoes_no_html(resposta.get_data(as_text=True)), [('hidden', '101')])
        self.salvar.assert_not_called()

    def test_publicacao_muda_durante_gravacao(self):
        dados = self.formulario()
        novo = deepcopy(self.cenario)
        novo.update({'versao_id': 102, 'versao': 2, 'titulo': 'Nova versão'})
        self.buscar.side_effect = [self.cenario, novo]
        self.salvar.side_effect = SimulacaoAlterada()
        resposta = self.client.post('/simulacoes/conta-bloqueada', data=dados)
        self.assertEqual(resposta.status_code, 409)
        self.assertEqual(versoes_no_html(resposta.get_data(as_text=True)), [('hidden', '102')])
        self.assertIn('Nova versão', resposta.get_data(as_text=True))

    def test_arquivamento_durante_gravacao(self):
        dados = self.formulario()
        self.buscar.side_effect = [self.cenario, None]
        self.salvar.side_effect = SimulacaoAlterada()
        self.assertEqual(self.client.post('/simulacoes/conta-bloqueada', data=dados).status_code, 404)

    def test_falha_na_gravacao_nao_mostra_resultado(self):
        dados = self.formulario()
        self.salvar.side_effect = Error('detalhe-interno')
        resposta = self.client.post('/simulacoes/conta-bloqueada', data=dados)
        self.assertEqual(resposta.status_code, 503)
        self.assertNotIn('detalhe-interno', resposta.get_data(as_text=True))
        self.assertNotIn('id="titulo-resultado"', resposta.get_data(as_text=True))

    def test_get_resultado_preserva_versao_e_nao_grava_de_novo(self):
        self.resultado['cenario']['titulo'] = 'Título da versão respondida'
        for _ in range(2):
            resposta = self.client.get('/simulacoes/conta-bloqueada?tentativa=21')
            self.assertEqual(resposta.status_code, 200)
            self.assertIn('Título da versão respondida', resposta.get_data(as_text=True))
            self.assertIn('id="titulo-resultado"', resposta.get_data(as_text=True))
        self.resultado_salvo.assert_called_with(7, 'conta-bloqueada', 21)
        self.buscar.assert_not_called()
        self.salvar.assert_not_called()

    def test_resultado_nao_localizado_retorna_404(self):
        self.resultado_salvo.return_value = None
        self.assertEqual(self.client.get('/simulacoes/conta-bloqueada?tentativa=999').status_code, 404)
        self.resultado_salvo.assert_called_once_with(7, 'conta-bloqueada', 999)

    def test_tentativa_invalida_nao_consulta(self):
        for valor in ['', '0', '-1', '1.5', 'abc', '2147483648', '1' * 100, '1&tentativa=2']:
            with self.subTest(valor=valor):
                resposta = self.client.get('/simulacoes/conta-bloqueada?tentativa=' + valor)
                self.assertEqual(resposta.status_code, 400)
        self.resultado_salvo.assert_not_called()

    def test_resultado_arquivado_sem_botao_repetir(self):
        self.resultado['pode_repetir'] = False
        resposta = self.client.get('/simulacoes/conta-bloqueada?tentativa=21')
        self.assertEqual(resposta.status_code, 200)
        self.assertNotIn('Tentar novamente', resposta.get_data(as_text=True))
        self.assertIn('foi arquivado', resposta.get_data(as_text=True))

    def test_link_antigo_nao_fabrica_tentativa(self):
        resposta = self.client.get('/simulacoes/conta-bloqueada?resultado=acessar_canal_oficial')
        self.assertEqual(resposta.status_code, 200)
        self.assertNotIn('id="titulo-resultado"', resposta.get_data(as_text=True))
        self.salvar.assert_not_called()

    def test_falha_consulta_resultado_retorna_503(self):
        self.resultado_salvo.side_effect = Error('detalhe-interno')
        resposta = self.client.get('/simulacoes/conta-bloqueada?tentativa=21')
        self.assertEqual(resposta.status_code, 503)
        self.assertNotIn('detalhe-interno', resposta.get_data(as_text=True))

    def test_requisicao_grande_retorna_413(self):
        resposta = self.client.post('/simulacoes/conta-bloqueada', data={'opcao': 'x' * 5000})
        self.assertEqual(resposta.status_code, 413)
        self.salvar.assert_not_called()


if __name__ == '__main__':
    unittest.main()
