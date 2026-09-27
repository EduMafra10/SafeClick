import os
import unittest
from unittest.mock import MagicMock, patch

from flask_login import UserMixin, login_user

from safeclick import create_app
from safeclick.mfa import ErroMFA
from safeclick.sessoes import criar_sessao, revogar_sessao, login_manager
from safeclick.twilio_api import validar_codigo_totp


class UsuarioTeste(UserMixin):
    id = 7
    perfil = "leitor"


class AutenticacaoAuditoriaTeste(unittest.TestCase):
    def setUp(self):
        with patch.dict(os.environ, {"SECRET_KEY": "chave-de-teste", "DATABASE_URL": "postgresql://nao-usado"}):
            self.app = create_app()
        self.app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
        self.client = self.app.test_client()
        self.conexao = MagicMock()
        self.contexto = MagicMock()
        self.contexto.__enter__.return_value = self.conexao

    def test_sessao_e_login_sucesso_usam_a_mesma_transacao(self):
        self.conexao.execute.return_value.fetchone.return_value = {"usuario_id": 7}

        with self.app.app_context(), \
             patch("safeclick.sessoes.conectar_banco", return_value=self.contexto), \
             patch("safeclick.sessoes.registrar_evento") as registrar:
            token = criar_sessao(7)

        self.assertEqual(len(token), 43)
        self.assertEqual(registrar.call_args.kwargs["evento"], "login.sucesso")
        self.assertEqual(registrar.call_args.kwargs["usuario_id"], 7)
        self.assertIs(registrar.call_args.kwargs["conexao"], self.conexao)

    def test_logout_revoga_sessao_e_registra_usuario(self):
        with self.app.test_request_context("/"):
            login_user(UsuarioTeste())
            from flask import session
            session["sessao_token"] = "x" * 43

            with patch("safeclick.sessoes.conectar_banco", return_value=self.contexto), \
                 patch("safeclick.sessoes.registrar_evento") as registrar:
                revogar_sessao()

        self.assertEqual(registrar.call_args.kwargs["evento"], "logout.realizado")
        self.assertEqual(registrar.call_args.kwargs["usuario_id"], 7)
        self.assertIs(registrar.call_args.kwargs["conexao"], self.conexao)

    def test_senha_invalida_nao_registra_email_ou_senha(self):
        with patch("safeclick.autenticacao.permitir_tentativa", return_value=True), \
             patch("safeclick.autenticacao.buscar_usuario_por_email", return_value=None), \
             patch("safeclick.autenticacao.render_template", return_value="Login"), \
             patch("safeclick.autenticacao.registrar_evento") as registrar:
            resposta = self.client.post("/login", data={"email": "pessoa@example.com", "senha": "segredo"})

        self.assertEqual(resposta.status_code, 401)
        dados = registrar.call_args.kwargs
        self.assertIsNone(dados["usuario_id"])
        self.assertEqual(dados["evento"], "login.falha")
        self.assertNotIn("pessoa@example.com", str(dados))
        self.assertNotIn("segredo", str(dados))

    def test_codigo_rejeitado_identifica_conta_ja_verificada_por_senha(self):
        with self.client.session_transaction() as sessao:
            sessao["login_pendente"] = "x" * 43

        with patch("safeclick.autenticacao.buscar_login_pendente", return_value={"usuario_id": 7}), \
             patch("safeclick.autenticacao.confirmar_autenticador", side_effect=ErroMFA("Código inválido.")), \
             patch("safeclick.autenticacao._tela_autenticador", return_value=("Código inválido.", 400)), \
             patch("safeclick.autenticacao.registrar_evento") as registrar:
            resposta = self.client.post("/login/autenticador", data={"codigo": "123456"})

        self.assertEqual(resposta.status_code, 400)
        self.assertEqual(registrar.call_args.kwargs["usuario_id"], 7)
        self.assertEqual(registrar.call_args.kwargs["evento"], "login.falha")
        self.assertNotIn("123456", str(registrar.call_args.kwargs))

    def test_perfil_invalido_registra_acesso_negado(self):
        with self.client.session_transaction() as sessao:
            sessao["_user_id"] = "7"
            sessao["_fresh"] = True

        with patch.object(login_manager, "_user_callback", return_value=UsuarioTeste()), \
             patch("safeclick.sessoes.registrar_evento") as registrar:
            resposta = self.client.get("/quizzes/")

        self.assertEqual(resposta.status_code, 403)
        self.assertEqual(registrar.call_args.kwargs["evento"], "acesso.negado")
        self.assertEqual(registrar.call_args.kwargs["detalhes"], {"area": "quizzes"})

    def test_consulta_twilio_registra_somente_operacao_e_resultado(self):
        servico = MagicMock()
        servico.entities.return_value.challenges.create.return_value.status = "approved"

        with self.app.app_context(), \
             patch("safeclick.twilio_api.obter_servico_twilio", return_value=servico), \
             patch("safeclick.twilio_api.registrar_evento") as registrar:
            aprovado = validar_codigo_totp("identidade-secreta", "fator-secreto", "123456")

        self.assertTrue(aprovado)
        dados = registrar.call_args.kwargs
        self.assertEqual(dados["evento"], "api.consultada")
        self.assertEqual(dados["resultado"], "sucesso")
        self.assertEqual(dados["detalhes"], {
            "servico": "twilio_verify", "operacao": "validar_codigo_totp"
        })
        self.assertNotIn("123456", str(dados))
        self.assertNotIn("identidade-secreta", str(dados))

    def test_falha_twilio_tambem_fica_registrada(self):
        with self.app.app_context(), \
             patch("safeclick.twilio_api.obter_servico_twilio", side_effect=RuntimeError("indisponível")), \
             patch("safeclick.twilio_api.registrar_evento") as registrar:
            with self.assertRaises(RuntimeError):
                validar_codigo_totp("identidade-secreta", "fator-secreto", "123456")

        self.assertEqual(registrar.call_args.kwargs["resultado"], "falha")

    def test_codigo_malformado_nao_e_registrado_como_consulta_api(self):
        with self.app.app_context(), \
             patch("safeclick.twilio_api.obter_servico_twilio") as obter_servico, \
             patch("safeclick.twilio_api.registrar_evento") as registrar:
            aprovado = validar_codigo_totp("identidade", "fator", "invalido")

        self.assertFalse(aprovado)
        obter_servico.assert_not_called()
        registrar.assert_not_called()


if __name__ == "__main__":
    unittest.main()
