import os
import unittest
from datetime import date
from html.parser import HTMLParser
from unittest.mock import MagicMock, patch

from psycopg import Error
from safeclick import create_app
from safeclick.sessoes import Usuario
from safeclick.termos_db import registrar_aceite_termos


class CamposHTML(HTMLParser):
    def __init__(self, resposta):
        super().__init__()
        self.campos = {}
        self.feed(resposta.get_data(as_text=True))

    def handle_starttag(self, tag, atributos):
        atributos = dict(atributos)
        if tag == "input":
            self.campos[atributos.get("name")] = atributos


class ReaceiteTermosTeste(unittest.TestCase):
    def substituir(self, substituicao):
        resultado = substituicao.start()
        self.addCleanup(substituicao.stop)
        return resultado

    def setUp(self):
        self.substituir(patch.dict(os.environ, {
            "SECRET_KEY": "chave-exclusiva-dos-testes",
            "DATABASE_URL": "postgresql://nao-usado",
        }, clear=True))
        for alvo in ("psycopg.connect", "socket.socket.connect"):
            self.substituir(patch(
                alvo, side_effect=AssertionError("Acesso externo nos testes")
            ))
        self.substituir(patch("safeclick.privacidade.VERSAO_TERMOS", "1.0"))
        self.app = create_app()
        self.app.config.update(TESTING=True, WTF_CSRF_ENABLED=True)
        self.client = self.app.test_client()
        usuario = Usuario({
            "id": 7, "nome": "Pessoa Teste",
            "email": "pessoa@example.com", "perfil": "usuario",
        })
        self.substituir(patch.object(
            self.app.login_manager, "_user_callback", return_value=usuario
        ))
        self.conexao = MagicMock()
        banco = self.substituir(patch("safeclick.termos_db.conectar_banco"))
        banco.return_value.__enter__.return_value = self.conexao
        self.resultado = self.conexao.execute.return_value.fetchone
        self.resultado.return_value = {"aceitou": False}
        self.registrar = self.substituir(patch(
            "safeclick.aceite_termos.registrar_aceite_termos", return_value=True
        ))
        with self.client.session_transaction() as sessao:
            sessao["_user_id"] = "7"
            sessao["_fresh"] = True

    def dados(self):
        resposta = self.client.get("/aceitar-termos")
        self.assertEqual(resposta.status_code, 200)
        campos = CamposHTML(resposta).campos
        self.assertNotIn("checked", campos["aceitou_termos"])
        return {
            "csrf_token": campos["csrf_token"]["value"],
            "versao_termos": campos["versao_termos"]["value"],
            "aceitou_termos": "y",
        }

    def test_sem_aceite_redireciona_areas_protegidas(self):
        for caminho in ("/", "/simulacoes/conta-bloqueada", "/conteudos/",
                        "/conteudos/golpes", "/quizzes/", "/quizzes/1",
                        "/quizzes/resultado", "/auditoria/"):
            with self.subTest(caminho=caminho):
                resposta = self.client.get(caminho)
                self.assertEqual(resposta.status_code, 303)
                self.assertEqual(resposta.location, "/aceitar-termos")
                self.assertEqual(resposta.headers["Cache-Control"], "no-store")
        self.registrar.assert_not_called()

    def test_post_protegido_redireciona_para_get_sem_gravar(self):
        with patch("safeclick.simulacoes.salvar_tentativa_simulacao") as salvar:
            resposta = self.client.post(
                "/simulacoes/conta-bloqueada", follow_redirects=True
            )
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.history[0].status_code, 303)
        self.assertEqual(resposta.request.method, "GET")
        self.assertEqual(resposta.request.path, "/aceitar-termos")
        salvar.assert_not_called()
        self.registrar.assert_not_called()

    def test_sem_login_completo_nao_registra_aceite(self):
        with self.client.session_transaction() as sessao:
            sessao.clear()
            sessao["login_pendente"] = "x" * 43
        resposta = self.client.post("/aceitar-termos")
        self.assertEqual(resposta.status_code, 302)
        self.assertTrue(resposta.location.startswith("/login"))
        self.conexao.execute.assert_not_called()
        self.registrar.assert_not_called()

    def test_aceite_atual_nao_pede_novamente(self):
        self.resultado.return_value = {"aceitou": True}
        resposta = self.client.get("/aceitar-termos")
        self.assertEqual(resposta.status_code, 303)
        self.assertEqual(resposta.location, "/")
        self.assertEqual(self.client.get("/simulacoes/conta-bloqueada").status_code, 200)
        self.registrar.assert_not_called()

    def test_aceite_valido_libera_apenas_usuario_da_sessao(self):
        dados = self.dados()
        dados.update(usuario_id="999", next="https://example.com")

        def registrar(*args, **kwargs):
            self.resultado.return_value = {"aceitou": True}
            return True

        self.registrar.side_effect = registrar
        resposta = self.client.post("/aceitar-termos", data=dados, follow_redirects=True)
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.request.path, "/simulacoes/conta-bloqueada")
        self.registrar.assert_called_once_with(7, "1.0", aceitou=True)

    def test_formulario_invalido_nao_registra(self):
        for campo, valor in (("csrf_token", None), ("csrf_token", "invalido"),
                             ("aceitou_termos", None), ("aceitou_termos", "false"),
                             ("versao_termos", None), ("versao_termos", "0.9")):
            with self.subTest(campo=campo, valor=valor):
                dados = self.dados()
                if valor is None:
                    dados.pop(campo)
                else:
                    dados[campo] = valor
                resposta = self.client.post("/aceitar-termos", data=dados)
                self.assertEqual(resposta.status_code, 400)
        self.registrar.assert_not_called()

    def test_versao_mudou_com_formulario_aberto(self):
        dados = self.dados()
        with patch("safeclick.privacidade.VERSAO_TERMOS", "1.1"):
            resposta = self.client.post("/aceitar-termos", data=dados)
        self.assertEqual(resposta.status_code, 400)
        campos = CamposHTML(resposta).campos
        self.assertEqual(campos["versao_termos"]["value"], "1.1")
        self.assertNotIn("checked", campos["aceitou_termos"])
        self.registrar.assert_not_called()

    def test_nova_versao_exige_aceite_na_sessao_aberta(self):
        self.resultado.return_value = {"aceitou": True}
        self.assertEqual(self.client.get("/simulacoes/conta-bloqueada").status_code, 200)
        with patch("safeclick.privacidade.VERSAO_TERMOS", "1.1"):
            self.resultado.return_value = {"aceitou": False}
            resposta = self.client.get("/simulacoes/conta-bloqueada")
            self.assertEqual(resposta.status_code, 303)
            self.assertEqual(resposta.location, "/aceitar-termos")
            self.assertEqual(self.conexao.execute.call_args.args[1], (7, "1.1"))
            self.assertEqual(self.dados()["versao_termos"], "1.1")
        with self.client.session_transaction() as sessao:
            self.assertEqual(sessao["_user_id"], "7")
        self.registrar.assert_not_called()

    def test_falha_consulta_ou_versao_ausente_bloqueia_acesso(self):
        for erro in (None, Error("detalhe-interno")):
            self.resultado.return_value = None
            self.resultado.side_effect = erro
            for caminho in ("/simulacoes/conta-bloqueada", "/aceitar-termos"):
                with self.subTest(erro=erro, caminho=caminho):
                    resposta = self.client.get(caminho)
                    self.assertEqual(resposta.status_code, 503)
                    self.assertNotIn("detalhe-interno", resposta.get_data(as_text=True))
        self.registrar.assert_not_called()

    def test_falha_registro_nao_anuncia_sucesso(self):
        dados = self.dados()
        self.registrar.side_effect = Error("detalhe-interno")
        resposta = self.client.post("/aceitar-termos", data=dados)
        self.assertEqual(resposta.status_code, 503)
        with self.client.session_transaction() as sessao:
            self.assertNotIn(
                ("sucesso", "Aceite dos Termos de Uso confirmado."),
                sessao.get("_flashes", []),
            )

    def test_documentos_e_saida_disponiveis_sem_aceite(self):
        dados = self.dados()
        self.conexao.execute.reset_mock()
        documento = {"versao": "1.0", "vigente_desde": date(2026, 9, 28),
                     "conteudo_html": "<p>Termos fictícios.</p>"}
        with patch("safeclick.privacidade.buscar_termos", return_value=documento), \
             patch("safeclick.privacidade.buscar_politica", return_value=documento), \
             patch("safeclick.privacidade.buscar_referencias", return_value=[]):
            self.assertEqual(self.client.get("/termos-de-uso").status_code, 200)
            self.assertEqual(self.client.get("/politica-de-privacidade").status_code, 200)
        with patch("safeclick.autenticacao.revogar_sessao") as revogar:
            resposta = self.client.post("/sair", data={"csrf_token": dados["csrf_token"]})
        self.assertEqual(resposta.status_code, 303)
        self.assertEqual(resposta.location, "/login")
        revogar.assert_called_once_with()
        self.conexao.execute.assert_not_called()
        self.registrar.assert_not_called()

    def test_aceite_nao_concede_permissao_de_administrador(self):
        self.resultado.return_value = {"aceitou": True}
        with patch("safeclick.auditoria.registrar_evento"):
            self.assertEqual(self.client.get("/auditoria/").status_code, 403)

    def test_registro_e_auditoria_usam_mesma_transacao(self):
        self.resultado.side_effect = [{"versao": "1.0"}, {"id": 50}]
        with patch("safeclick.auditoria_db.registrar_evento") as auditar:
            self.assertTrue(registrar_aceite_termos(7, "1.0", aceitou=True))
        self.assertEqual(self.conexao.execute.call_args.args[1], (7, "1.0"))
        auditar.assert_called_once_with(
            usuario_id=7, evento="termo.aceito", resultado="sucesso",
            recurso_tipo="aceite_termos", recurso_id=50,
            detalhes={"versao": "1.0"}, conexao=self.conexao,
        )

    def test_registro_repetido_nao_duplica_auditoria(self):
        self.resultado.side_effect = [{"versao": "1.0"}, None]
        with patch("safeclick.auditoria_db.registrar_evento") as auditar:
            self.assertFalse(registrar_aceite_termos(7, "1.0", aceitou=True))
        auditar.assert_not_called()