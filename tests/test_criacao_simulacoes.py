import os
import unittest
from html.parser import HTMLParser
from unittest.mock import MagicMock, patch

from psycopg import Error
from werkzeug.datastructures import MultiDict

from safeclick import create_app
from safeclick.sessoes import Usuario
from safeclick.simulacoes_db import SimulacaoDuplicada, criar_rascunho_simulacao


EXEMPLO = {
    "titulo": "Falso suporte técnico",
    "slug": "falso-suporte-tecnico",
    "tipo": "conversa",
    "resumo": "Um contato desconhecido pede acesso ao computador para corrigir um problema.",
}


class EntradasHTML(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.entradas = {}
        self.feed(html)

    def handle_starttag(self, tag, atributos):
        atributos = dict(atributos)
        if tag in {"input", "textarea", "select"} and atributos.get("name"):
            self.entradas[atributos["name"]] = atributos


class CriacaoRascunhoBancoTeste(unittest.TestCase):
    def setUp(self):
        self.conexao = MagicMock()
        self.buscar = self.conexao.execute.return_value.fetchone
        self.buscar.side_effect = [{"id": 7}, {"id": 5}, {"id": 99}]
        self.contexto = MagicMock()
        self.contexto.__enter__.return_value = self.conexao
        abrir = patch("safeclick.simulacoes_db.conectar_banco", return_value=self.contexto)
        self.abrir = abrir.start()
        self.addCleanup(abrir.stop)
        bloqueio = patch("psycopg.connect", side_effect=AssertionError("Banco real proibido"))
        bloqueio.start()
        self.addCleanup(bloqueio.stop)

    def test_cria_somente_rascunho_e_audita_na_mesma_conexao(self):
        self.assertEqual(criar_rascunho_simulacao(7, **EXEMPLO), 5)
        permissao, gravacao, auditoria = self.conexao.execute.call_args_list
        self.assertIn("perfil = 'administrador' FOR SHARE", permissao.args[0])
        self.assertEqual(permissao.args[1], (7,))
        self.assertIn("'rascunho'", gravacao.args[0])
        self.assertNotIn("versoes_simulacao", gravacao.args[0])
        parametros = gravacao.args[1]
        self.assertEqual(parametros[:2], ("falso_suporte_tecnico", "falso-suporte-tecnico"))
        self.assertEqual(parametros[3], 7)
        self.assertEqual(parametros[2].obj["tipo"], "conversa")
        self.assertEqual(parametros[2].obj["canal"], "Conversa fictícia")
        self.assertEqual(parametros[2].obj["titulo"], EXEMPLO["titulo"])
        self.assertIn("INSERT INTO public.logs_auditoria", auditoria.args[0])
        self.assertEqual(auditoria.args[1][:5], (7, "simulacao.criada", "sucesso", "simulacao", "5"))
        self.assertEqual(auditoria.args[1][5].obj, {"identificador": "falso_suporte_tecnico", "estado": "rascunho"})
        self.abrir.assert_called_once_with()
        self.contexto.__exit__.assert_called_once_with(None, None, None)

    def test_permissao_revogada_impede_gravacao(self):
        self.buscar.side_effect = [None]
        with self.assertRaises(PermissionError):
            criar_rascunho_simulacao(7, **EXEMPLO)
        self.assertEqual(self.conexao.execute.call_count, 1)

    def test_endereco_duplicado_nao_sobrescreve_nem_audita_criacao(self):
        self.buscar.side_effect = [{"id": 7}, None]
        with self.assertRaises(SimulacaoDuplicada):
            criar_rascunho_simulacao(7, **EXEMPLO)
        self.assertEqual(self.conexao.execute.call_count, 2)
        self.assertIn("ON CONFLICT DO NOTHING", self.conexao.execute.call_args.args[0])
        self.assertIs(self.contexto.__exit__.call_args.args[0], SimulacaoDuplicada)

    def test_falha_auditoria_aborta_transacao(self):
        self.buscar.side_effect = [{"id": 7}, {"id": 5}, Error("falha simulada")]
        with self.assertRaises(Error):
            criar_rascunho_simulacao(7, **EXEMPLO)
        self.assertIs(self.contexto.__exit__.call_args.args[0], Error)

    def test_dados_invalidos_nao_abrem_banco(self):
        for campo, valor in [
            ("titulo", " "), ("titulo", "a" * 121), ("titulo", "ab\x00cd"),
            ("resumo", "a" * 301), ("tipo", "html"), ("tipo", None),
            ("slug", "1-inicio"), ("slug", "UPPER"), ("slug", "falso--suporte"),
            ("slug", "a" * 81), ("slug", "teste'; DELETE FROM usuarios;--"),
        ]:
            with self.subTest(campo=campo, valor=valor), self.assertRaises(ValueError):
                criar_rascunho_simulacao(7, **{**EXEMPLO, campo: valor})
        self.abrir.assert_not_called()


class CriacaoRascunhoRotaTeste(unittest.TestCase):
    def substituir(self, alvo, **argumentos):
        substituicao = patch(alvo, **argumentos)
        retorno = substituicao.start()
        self.addCleanup(substituicao.stop)
        return retorno

    def setUp(self):
        ambiente = patch.dict(os.environ, {
            "SECRET_KEY": "chave-exclusiva-dos-testes",
            "DATABASE_URL": "postgresql://nao-usado",
        }, clear=True)
        ambiente.start()
        self.addCleanup(ambiente.stop)
        self.substituir("psycopg.connect", side_effect=AssertionError("Banco real proibido"))
        self.substituir("socket.socket.connect", side_effect=AssertionError("Rede real proibida"))
        self.app = create_app()
        self.app.config.update(TESTING=True, WTF_CSRF_ENABLED=True)
        self.client = self.app.test_client()
        self.usuario = Usuario({"id": 7, "nome": "Pessoa Teste", "email": "pessoa@example.test", "perfil": "administrador"})
        usuario = patch.object(self.app.login_manager, "_user_callback", return_value=self.usuario)
        usuario.start()
        self.addCleanup(usuario.stop)
        with self.client.session_transaction() as sessao:
            sessao["_user_id"] = "7"
            sessao["_fresh"] = True
        self.aceite = self.substituir("safeclick.aceite_termos.usuario_aceitou_termos_atuais", return_value=True)
        self.auditar = self.substituir("safeclick.sessoes.registrar_evento")
        self.criar = self.substituir("safeclick.administracao.criar_rascunho_simulacao", return_value=5)
        self.listar = self.substituir("safeclick.administracao.listar_simulacoes_administrativas", return_value=([], 0))

    def dados(self):
        resposta = self.client.get("/administracao/simulacoes/novo")
        self.assertEqual(resposta.status_code, 200)
        campos = EntradasHTML(resposta.get_data(as_text=True)).entradas
        self.assertIn("csrf_token", campos)
        return {**EXEMPLO, "csrf_token": campos["csrf_token"]["value"]}

    def test_formulario_abre_com_campos_e_csrf_sem_gravar(self):
        resposta = self.client.get("/administracao/simulacoes/novo")
        self.assertEqual(resposta.status_code, 200)
        html = resposta.get_data(as_text=True)
        entradas = EntradasHTML(html).entradas
        self.assertTrue({"titulo", "slug", "tipo", "resumo", "csrf_token"}.issubset(entradas))
        self.assertEqual(entradas["slug"]["aria-describedby"], "ajuda-slug erro-slug")
        self.assertEqual(entradas["titulo"]["maxlength"], "120")
        self.assertIn("Salvar rascunho", html)
        self.assertEqual(resposta.headers["Cache-Control"], "no-store")
        self.criar.assert_not_called()

    def test_envio_valido_grava_com_usuario_da_sessao_e_redireciona(self):
        resposta = self.client.post("/administracao/simulacoes/novo", data=self.dados())
        self.assertEqual(resposta.status_code, 303)
        self.assertEqual(resposta.location, "/administracao/simulacoes?estado=rascunho")
        self.criar.assert_called_once_with(7, **EXEMPLO)
        for _ in range(2):
            pagina = self.client.get(resposta.location)
            self.assertEqual(pagina.status_code, 200)
        self.criar.assert_called_once()

    def test_confirmacao_aparece_na_listagem(self):
        resposta = self.client.post("/administracao/simulacoes/novo", data=self.dados(), follow_redirects=True)
        self.assertEqual(resposta.status_code, 200)
        self.assertIn("Cenário salvo como rascunho", resposta.get_data(as_text=True))
        self.assertIn('href="/administracao/simulacoes/novo"', resposta.get_data(as_text=True))

    def test_usuario_comum_nao_abre_nem_cadastra(self):
        self.usuario.perfil = "usuario"
        for metodo in ["GET", "POST"]:
            with self.subTest(metodo=metodo):
                self.assertEqual(self.client.open("/administracao/simulacoes/novo", method=metodo).status_code, 403)
        self.criar.assert_not_called()
        self.assertEqual(self.auditar.call_count, 2)

    def test_visitante_nao_abre_nem_cadastra(self):
        with self.client.session_transaction() as sessao:
            sessao.clear()
        for metodo in ["GET", "POST"]:
            with self.subTest(metodo=metodo):
                resposta = self.client.open("/administracao/simulacoes/novo", method=metodo)
                self.assertEqual(resposta.status_code, 302)
                self.assertTrue(resposta.location.startswith("/login"))
        self.criar.assert_not_called()

    def test_aceite_pendente_impede_cadastro(self):
        dados = self.dados()
        self.aceite.return_value = False
        resposta = self.client.post("/administracao/simulacoes/novo", data=dados)
        self.assertEqual(resposta.status_code, 303)
        self.assertEqual(resposta.location, "/aceitar-termos")
        self.criar.assert_not_called()

    def test_csrf_ausente_ou_invalido_nao_grava(self):
        dados = self.dados()
        for valor in [None, "invalido"]:
            with self.subTest(valor=valor):
                envio = dict(dados)
                if valor is None:
                    envio.pop("csrf_token")
                else:
                    envio["csrf_token"] = valor
                self.assertEqual(self.client.post("/administracao/simulacoes/novo", data=envio).status_code, 400)
        self.criar.assert_not_called()

    def test_validacao_de_campos_no_servidor(self):
        dados = self.dados()
        for campo, valor in [
            ("titulo", " "), ("titulo", "a" * 121), ("titulo", "ab\x00cd"),
            ("resumo", ""), ("resumo", "a" * 301), ("tipo", ""), ("tipo", "html"),
            ("slug", "1-inicio"), ("slug", "UPPER"), ("slug", "falso--suporte"),
        ]:
            with self.subTest(campo=campo, valor=valor):
                resposta = self.client.post("/administracao/simulacoes/novo", data={**dados, campo: valor})
                self.assertEqual(resposta.status_code, 400)
                self.assertEqual(EntradasHTML(resposta.get_data(as_text=True)).entradas[campo]["aria-invalid"], "true")
        self.criar.assert_not_called()

    def test_campos_administrativos_extras_ou_repetidos_sao_rejeitados(self):
        dados = self.dados()
        for envio in [
            {**dados, "estado": "publicada"}, {**dados, "criado_por": "999"},
            {**dados, "versao_publicada_id": "1"},
            MultiDict([*dados.items(), ("slug", "outro-endereco")]),
        ]:
            with self.subTest(envio=envio):
                self.assertEqual(self.client.post("/administracao/simulacoes/novo", data=envio).status_code, 400)
        self.criar.assert_not_called()

    def test_duplicidade_preserva_formulario(self):
        dados = self.dados()
        self.criar.side_effect = SimulacaoDuplicada()
        resposta = self.client.post("/administracao/simulacoes/novo", data=dados)
        self.assertEqual(resposta.status_code, 409)
        entradas = EntradasHTML(resposta.get_data(as_text=True)).entradas
        self.assertEqual(entradas["slug"]["value"], EXEMPLO["slug"])
        self.assertEqual(entradas["titulo"]["value"], EXEMPLO["titulo"])
        self.assertIn("Já existe um cenário", resposta.get_data(as_text=True))

    def test_revogacao_entre_acesso_e_gravacao_retorna_403(self):
        dados = self.dados()
        self.criar.side_effect = PermissionError("detalhe-interno")
        resposta = self.client.post("/administracao/simulacoes/novo", data=dados)
        self.assertEqual(resposta.status_code, 403)
        self.assertNotIn("detalhe-interno", resposta.get_data(as_text=True))

    def test_falha_no_banco_nao_expoe_detalhes_nem_confirma(self):
        dados = self.dados()
        self.criar.side_effect = Error("detalhe-interno")
        resposta = self.client.post("/administracao/simulacoes/novo", data=dados)
        self.assertEqual(resposta.status_code, 503)
        self.assertNotIn("detalhe-interno", resposta.get_data(as_text=True))
        with self.client.session_transaction() as sessao:
            self.assertNotIn("_flashes", sessao)

    def test_reexibicao_de_texto_nao_executa_html(self):
        dados = {**self.dados(), "titulo": '<script>alert("teste")</script>', "tipo": "invalido"}
        resposta = self.client.post("/administracao/simulacoes/novo", data=dados)
        self.assertEqual(resposta.status_code, 400)
        self.assertNotIn('<script>alert(', resposta.get_data(as_text=True))
        self.assertIn("&lt;script&gt;", resposta.get_data(as_text=True))

    def test_tamanho_da_requisicao_limitado(self):
        resposta = self.client.post("/administracao/simulacoes/novo", data={"resumo": "a" * 17000})
        self.assertEqual(resposta.status_code, 413)
        self.criar.assert_not_called()


if __name__ == "__main__":
    unittest.main()
