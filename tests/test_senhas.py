import os
import unittest
from html.parser import HTMLParser
from unittest.mock import patch

from psycopg import Error
from werkzeug.datastructures import MultiDict

from safeclick import create_app
from safeclick.pwned_api import ServicoSenhasIndisponivel
from safeclick.sessoes import Usuario

PAGINA = "/verificar-senha/"
CONSULTA = "/verificar-senha/consultar"
TEXTO = "A" * 35 + ":3\r\n" + "B" * 35 + ":0"


class CamposHTML(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.campos = {}
        self.feed(html)

    def handle_starttag(self, tag, atributos):
        if tag in {"input", "button"}:
            atributos = dict(atributos)
            self.campos[atributos.get("id")] = atributos


class SenhasTeste(unittest.TestCase):
    def substituir(self, substituicao):
        resultado = substituicao.start()
        self.addCleanup(substituicao.stop)
        return resultado

    def setUp(self):
        self.substituir(patch.dict(os.environ, {
            "SECRET_KEY": "chave-ficticia-dos-testes",
            "DATABASE_URL": "postgresql://nao-usado",
            "FLASK_SKIP_DOTENV": "1",
        }, clear=True))
        for alvo in (
            "psycopg.connect", "socket.socket.connect",
            "socket.create_connection", "requests.sessions.Session.request",
        ):
            self.substituir(patch(
                alvo, side_effect=AssertionError("Acesso externo proibido no teste")
            ))

        self.app = create_app()
        self.app.config.update(TESTING=True, WTF_CSRF_ENABLED=True)
        self.cliente = self.app.test_client()
        self.usuario = Usuario({
            "id": 7, "nome": "Pessoa Teste",
            "email": "pessoa@example.com", "perfil": "usuario",
        })
        self.substituir(patch.object(
            self.app.login_manager, "_user_callback", return_value=self.usuario
        ))
        self.aceitou = self.substituir(patch(
            "safeclick.aceite_termos.usuario_aceitou_termos_atuais",
            return_value=True,
        ))
        self.permitir = self.substituir(patch(
            "safeclick.senhas.permitir_tentativa", return_value=True
        ))
        self.consultar = self.substituir(patch(
            "safeclick.senhas.consultar_prefixo_senha", return_value=TEXTO
        ))
        self.registrar = self.substituir(patch("safeclick.senhas.registrar_evento"))
        self.substituir(patch("safeclick.sessoes.registrar_evento"))

        with self.cliente.session_transaction() as sessao:
            sessao["_user_id"] = "7"
            sessao["_fresh"] = True

        self.pagina = self.cliente.get(PAGINA)
        self.assertEqual(self.pagina.status_code, 200)
        self.campos = CamposHTML(self.pagina.get_data(as_text=True)).campos
        self.token = self.campos["csrf-consulta-senha"]["value"]

    def enviar(self, **dados):
        corpo = {"prefixo": "AB123", "csrf_token": self.token}
        corpo.update(dados)
        return self.cliente.post(CONSULTA, data=corpo)

    def conferir_headers(self, resposta):
        self.assertEqual(resposta.headers["Cache-Control"], "no-store")
        self.assertEqual(resposta.headers["Referrer-Policy"], "no-referrer")
        self.assertEqual(resposta.headers["X-Content-Type-Options"], "nosniff")

    def test_pagina_prepara_consulta_sem_enviar_senha(self):
        campo = self.campos["senha-consulta"]
        self.assertEqual(campo["type"], "password")
        self.assertNotIn("name", campo)
        self.assertIn("disabled", campo)
        self.assertIn("disabled", self.campos["consultar-senha"])
        self.assertEqual(self.campos["csrf-consulta-senha"]["name"], "csrf_token")
        self.conferir_headers(self.pagina)
        self.consultar.assert_not_called()
        self.permitir.assert_not_called()

    def test_consulta_valida_preserva_padding_e_audita_so_metadados(self):
        resposta = self.enviar()
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.mimetype, "text/plain")
        self.assertEqual(resposta.get_data(as_text=True), TEXTO)
        self.conferir_headers(resposta)
        self.permitir.assert_called_once_with("consulta_senha", "7", 5)
        self.consultar.assert_called_once_with("AB123")
        self.registrar.assert_called_once_with(
            usuario_id=7, evento="api.consultada", resultado="sucesso",
            recurso_tipo="api",
            detalhes={"servico": "pwned_passwords", "operacao": "consultar_prefixo"},
        )
        with self.cliente.session_transaction() as sessao:
            self.assertNotIn("AB123", repr(dict(sessao)))
            self.assertNotIn(TEXTO, repr(dict(sessao)))

    def test_exige_login_completo(self):
        for pendente in (False, True):
            with self.subTest(login_pendente=pendente):
                with self.cliente.session_transaction() as sessao:
                    sessao.clear()
                    if pendente:
                        sessao["login_pendente"] = "x" * 43
                for resposta in (self.cliente.get(PAGINA), self.enviar()):
                    self.assertEqual(resposta.status_code, 302)
                    self.assertTrue(resposta.location.startswith("/login"))
        self.consultar.assert_not_called()
        self.permitir.assert_not_called()

    def test_exige_aceite_atual_dos_termos(self):
        self.aceitou.return_value = False
        for resposta in (self.cliente.get(PAGINA), self.enviar()):
            self.assertEqual(resposta.status_code, 303)
            self.assertEqual(resposta.location, "/aceitar-termos")
        self.consultar.assert_not_called()
        self.permitir.assert_not_called()

    def test_rejeita_perfil_nao_permitido(self):
        self.usuario.perfil = "outro"
        self.assertEqual(self.cliente.get(PAGINA).status_code, 403)
        self.assertEqual(self.enviar().status_code, 403)
        self.consultar.assert_not_called()

    def test_administrador_pode_consultar(self):
        self.usuario.perfil = "administrador"
        self.assertEqual(self.enviar().status_code, 200)
        self.consultar.assert_called_once_with("AB123")

    def test_rejeita_csrf_ausente_forjado_ou_de_outra_sessao(self):
        resposta = self.cliente.post(CONSULTA, data={"prefixo": "AB123"})
        self.assertEqual(resposta.status_code, 400)
        self.assertEqual(self.enviar(csrf_token="token-forjado").status_code, 400)
        with self.cliente.session_transaction() as sessao:
            sessao.pop("csrf_token", None)
        self.assertEqual(self.enviar().status_code, 400)
        self.consultar.assert_not_called()
        self.permitir.assert_not_called()

    def test_rejeita_prefixos_invalidos(self):
        for valor in ("", "ABC", "A" * 40, "senha-ficticia", "ZZZZZ", "ABCDE\n"):
            with self.subTest(prefixo=valor):
                self.assertEqual(self.enviar(prefixo=valor).status_code, 400)
        self.consultar.assert_not_called()
        self.permitir.assert_not_called()

    def test_rejeita_campo_senha_sem_refletir_o_conteudo(self):
        resposta = self.enviar(senha="SEGREDO-FICTICIO")
        self.assertEqual(resposta.status_code, 400)
        self.assertNotIn("SEGREDO-FICTICIO", resposta.get_data(as_text=True))
        self.consultar.assert_not_called()
        self.registrar.assert_not_called()

    def test_rejeita_campos_duplicados(self):
        for campo in ("prefixo", "csrf_token"):
            with self.subTest(campo=campo):
                dados = MultiDict([
                    ("prefixo", "AB123"), ("csrf_token", self.token), (campo, "AB123")
                ])
                resposta = self.cliente.post(CONSULTA, data=dados)
                self.assertEqual(resposta.status_code, 400)
        self.consultar.assert_not_called()

    def test_rejeita_json_querystring_e_consulta_por_get(self):
        dados = {"prefixo": "AB123", "csrf_token": self.token}
        resposta = self.cliente.post(CONSULTA, json=dados)
        self.assertEqual(resposta.status_code, 400)
        resposta = self.cliente.post(CONSULTA + "?prefixo=AB123", data=dados)
        self.assertEqual(resposta.status_code, 400)
        self.assertEqual(self.cliente.get(CONSULTA).status_code, 405)
        self.consultar.assert_not_called()

    def test_rejeita_corpo_grande(self):
        resposta = self.enviar(prefixo="A" * 5000)
        self.assertEqual(resposta.status_code, 413)
        self.conferir_headers(resposta)
        self.consultar.assert_not_called()

    def test_limite_atingido_impede_consulta(self):
        self.permitir.return_value = False
        resposta = self.enviar()
        self.assertEqual(resposta.status_code, 429)
        self.assertEqual(resposta.headers["Retry-After"], "300")
        self.conferir_headers(resposta)
        self.consultar.assert_not_called()
        self.registrar.assert_not_called()

    def test_falha_no_controle_de_limite_impede_consulta(self):
        self.permitir.side_effect = Error("detalhe-interno")
        resposta = self.enviar()
        self.assertEqual(resposta.status_code, 503)
        self.assertNotIn("detalhe-interno", resposta.get_data(as_text=True))
        self.consultar.assert_not_called()

    def test_falha_ao_verificar_termos_impede_acesso(self):
        self.aceitou.side_effect = Error("detalhe-interno")
        for resposta in (self.cliente.get(PAGINA), self.enviar()):
            self.assertEqual(resposta.status_code, 503)
            self.assertNotIn("detalhe-interno", resposta.get_data(as_text=True))
        self.consultar.assert_not_called()
        self.permitir.assert_not_called()

    def test_api_indisponivel_retorna_erro(self):
        self.consultar.side_effect = ServicoSenhasIndisponivel("detalhe-interno")
        resposta = self.enviar()
        self.assertEqual(resposta.status_code, 503)
        self.assertEqual(resposta.mimetype, "application/json")
        self.assertIn("erro", resposta.get_json())
        self.assertNotIn("detalhe-interno", resposta.get_data(as_text=True))
        self.assertEqual(self.registrar.call_args.kwargs["resultado"], "falha")
        self.conferir_headers(resposta)

    def test_falha_auditoria_nao_expoe_dados_no_log(self):
        self.registrar.side_effect = Error("AB123-detalhe-interno")
        with self.assertLogs(self.app.logger.name, level="WARNING") as mensagens:
            resposta = self.enviar()
        self.assertEqual(resposta.status_code, 200)
        self.assertNotIn("AB123", repr(mensagens.output))
        self.assertNotIn("detalhe-interno", repr(mensagens.output))