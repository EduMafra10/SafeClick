import html
import importlib
import os
import re
import unittest
from contextlib import ExitStack
from unittest.mock import MagicMock, patch

from safeclick import create_app

MODULO = importlib.import_module("safeclick.recuperacao")
TOKEN = "t" * 43
SENHA = "Senha!Teste2026#Nova"


def criar_app_teste(caso):
    for alvo in ("socket.create_connection", "psycopg.connect"):
        bloqueio = patch(alvo, side_effect=AssertionError("Acesso externo proibido no teste"))
        bloqueio.start()
        caso.addCleanup(bloqueio.stop)
    with patch.dict(os.environ, {
        "SECRET_KEY": "chave-ficticia-de-teste",
        "DATABASE_URL": "postgresql://nao-usado",
        "SMTP_PORT": "587",
        "FLASK_SKIP_DOTENV": "1",
    }):
        return create_app()


class FluxoRecuperacaoTeste(unittest.TestCase):
    def setUp(self):
        self.app = criar_app_teste(self)
        self.app.config.update(TESTING=True, WTF_CSRF_ENABLED=True,
                               APP_BASE_URL="http://127.0.0.1:5000")
        self.cliente = self.app.test_client()
        self.patches = ExitStack()
        self.addCleanup(self.patches.close)
        self.permitir = self.patches.enter_context(patch.object(MODULO, "permitir_tentativa", return_value=True))
        self.agendar = self.patches.enter_context(patch.object(MODULO, "_agendar", return_value=True))
        self.buscar = self.patches.enter_context(patch.object(MODULO, "buscar_recuperacao", return_value={"usuario_id": 7}))
        self.redefinir = self.patches.enter_context(patch.object(MODULO, "redefinir_senha", return_value={"id": 7, "email": "aluno@example.com"}))

    def csrf(self, rota, **kwargs):
        resposta = self.cliente.get(rota, **kwargs)
        self.assertEqual(resposta.status_code, 200)
        return html.unescape(re.search(r'name="csrf_token"[^>]*value="([^"]+)"', resposta.get_data(as_text=True)).group(1))

    def solicitar(self, email="aluno@example.com", **kwargs):
        return self.cliente.post("/recuperar-senha", data={
            "csrf_token": self.csrf("/recuperar-senha", headers=kwargs.get("headers")), "email": email,
        }, **kwargs)

    def salvar(self, **dados):
        formulario = {"csrf_token": self.csrf("/redefinir-senha"),
                      "token_recuperacao": TOKEN, "senha": SENHA, "confirmar_senha": SENHA}
        formulario.update(dados)
        return self.cliente.post("/redefinir-senha", data=formulario)

    def test_paginas_renderizam_sem_consultar_token_no_get(self):
        for rota in ("/login", "/recuperar-senha", "/redefinir-senha"):
            resposta = self.cliente.get(rota)
            self.assertEqual(resposta.status_code, 200)
            self.assertEqual(resposta.headers["Cache-Control"], "no-store")
        self.buscar.assert_not_called()
        self.redefinir.assert_not_called()
        self.assertIn(b'Esqueci minha senha', self.cliente.get("/login").data)
        resposta = self.cliente.get("/redefinir-senha")
        self.assertEqual(resposta.headers["Referrer-Policy"], "no-referrer")
        self.assertIn(b'recuperacao.js', resposta.data)
        self.assertEqual(self.cliente.get("/static/js/recuperacao.js").status_code, 200)

    def test_solicitacao_normaliza_email_e_agenda_sem_consultar_conta(self):
        resposta = self.solicitar("  ALUNO@example.com  ")
        self.assertEqual(resposta.status_code, 303)
        self.agendar.assert_called_once_with(MODULO._enviar_recuperacao,
                                            "aluno@example.com", "http://127.0.0.1:5000/redefinir-senha")
        self.permitir.assert_any_call("recuperacao_email", "aluno@example.com", 3)
        self.permitir.assert_any_call("recuperacao_ip", "127.0.0.1", 5)
        self.buscar.assert_not_called()

    def test_email_inexistente_e_limite_usam_mesma_resposta(self):
        respostas = []
        for permitido, email in ((True, "aluno@example.com"),
                                  (True, "inexistente@example.com"),
                                  (False, "aluno@example.com")):
            self.permitir.return_value = permitido
            resposta = self.solicitar(email)
            self.assertEqual(resposta.status_code, 303)
            with self.cliente.session_transaction() as sessao:
                respostas.append(sessao["_flashes"][-1][1])
        self.assertEqual(len(set(respostas)), 1)
        self.assertEqual(self.agendar.call_count, 2)

    def test_fila_cheia_informa_indisponibilidade(self):
        self.agendar.return_value = False
        self.assertEqual(self.solicitar().status_code, 503)

    def test_configuracao_invalida_nao_agenda(self):
        self.app.config["APP_BASE_URL"] = "http://site-publico.example"
        self.assertEqual(self.solicitar().status_code, 503)
        self.agendar.assert_not_called()

    def test_host_da_requisicao_nao_entra_no_link(self):
        resposta = self.solicitar(headers={"Host": "atacante.example", "X-Forwarded-Host": "outro.example"})
        self.assertEqual(resposta.status_code, 303)
        self.assertEqual(self.agendar.call_args.args[2], "http://127.0.0.1:5000/redefinir-senha")

    def test_ip_encaminhado_nao_e_confiado_sem_proxy_configurado(self):
        self.solicitar(headers={"X-Forwarded-For": "1.2.3.4"})
        self.permitir.assert_any_call("recuperacao_ip", "127.0.0.1", 5)

    def test_email_invalido_e_csrf_ausente_nao_disparam_envio(self):
        self.assertEqual(self.solicitar("invalido").status_code, 400)
        resposta = self.cliente.post("/recuperar-senha", data={"email": "aluno@example.com"})
        self.assertEqual(resposta.status_code, 400)
        self.agendar.assert_not_called()
        self.permitir.assert_not_called()

    def test_formulario_grande_e_rejeitado(self):
        resposta = self.cliente.post("/recuperar-senha", data={"email": "x" * 17000})
        self.assertEqual(resposta.status_code, 413)
        self.agendar.assert_not_called()

    def test_reset_valido_limpa_cookie_avisa_e_redireciona_sem_autologin(self):
        with self.cliente.session_transaction() as sessao:
            sessao["login_pendente"] = "p" * 43
            sessao["sessao_token"] = "s" * 43
        resposta = self.salvar()
        self.assertEqual(resposta.status_code, 303)
        self.assertTrue(resposta.location.endswith("/login"))
        self.redefinir.assert_called_once_with(TOKEN, SENHA)
        self.agendar.assert_called_once_with(MODULO._avisar_redefinicao, "aluno@example.com")
        with self.cliente.session_transaction() as sessao:
            self.assertNotIn("_user_id", sessao)
            self.assertNotIn("sessao_token", sessao)
            self.assertNotIn("login_pendente", sessao)
            self.assertIn("Senha alterada", sessao["_flashes"][0][1])

    def test_token_invalido_ou_expirado_nao_altera_senha(self):
        self.buscar.return_value = None
        resposta = self.salvar()
        self.assertEqual(resposta.status_code, 400)
        self.assertNotIn(TOKEN.encode(), resposta.data)
        self.redefinir.assert_not_called()
        self.agendar.assert_not_called()

    def test_token_revogado_entre_consulta_e_reset_nao_indica_sucesso(self):
        self.redefinir.return_value = None
        self.assertEqual(self.salvar().status_code, 400)
        self.agendar.assert_not_called()

    def test_repeticao_do_link_nao_altera_senha_ou_notifica_duas_vezes(self):
        self.buscar.side_effect = [{"usuario_id": 7}, None]
        self.assertEqual(self.salvar().status_code, 303)
        self.assertEqual(self.salvar().status_code, 400)
        self.assertEqual(self.redefinir.call_count, 1)
        self.assertEqual(self.agendar.call_count, 1)

    def test_confirmacao_errada_preserva_token_no_formulario_sem_expor_senha(self):
        resposta = self.salvar(confirmar_senha="Outra!Senha2026#Teste")
        self.assertEqual(resposta.status_code, 400)
        self.assertIn(TOKEN.encode(), resposta.data)
        self.assertNotIn(SENHA.encode(), resposta.data)
        self.redefinir.assert_not_called()

    def test_csrf_ausente_bloqueia_troca(self):
        self.assertEqual(self.salvar(csrf_token="").status_code, 400)
        self.buscar.assert_not_called()
        self.redefinir.assert_not_called()

    def test_limite_ip_bloqueia_reset_sem_consumir_token(self):
        self.permitir.return_value = False
        self.assertEqual(self.salvar().status_code, 429)
        self.buscar.assert_not_called()
        self.redefinir.assert_not_called()

    def test_falha_no_banco_nao_indica_sucesso(self):
        self.redefinir.side_effect = RuntimeError("falha")
        self.assertEqual(self.salvar().status_code, 503)
        self.agendar.assert_not_called()

    def test_aviso_nao_agendado_nao_desfaz_troca_concluida(self):
        self.agendar.return_value = False
        with patch.object(self.app.logger, "error") as log:
            self.assertEqual(self.salvar().status_code, 303)
        log.assert_called_once()


class ProcessamentoEmailTeste(unittest.TestCase):
    def setUp(self):
        self.app = criar_app_teste(self)
        self.dados = {"email": "aluno@example.com", "token": TOKEN, "usuario_id": 7}

    def test_envio_contem_link_confiavel_e_prazo_sem_mudar_senha(self):
        with patch.object(MODULO, "criar_recuperacao", return_value=self.dados), \
             patch.object(MODULO, "enviar_email") as enviar, \
             patch.object(MODULO, "redefinir_senha") as redefinir:
            MODULO._enviar_recuperacao("aluno@example.com", "https://safeclick.example/redefinir-senha")
        self.assertEqual(enviar.call_args.args[0], self.dados["email"])
        self.assertIn("https://safeclick.example/redefinir-senha#token=" + TOKEN, enviar.call_args.args[2])
        self.assertIn("30 minutos", enviar.call_args.args[2])
        redefinir.assert_not_called()

    def test_conta_inexistente_nao_recebe_email(self):
        with patch.object(MODULO, "criar_recuperacao", return_value=None), \
             patch.object(MODULO, "enviar_email") as enviar:
            MODULO._enviar_recuperacao("inexistente@example.com", "https://safeclick.example/redefinir-senha")
        enviar.assert_not_called()

    def test_falha_smtp_cancela_apenas_token_desse_envio(self):
        with patch.object(MODULO, "criar_recuperacao", return_value=self.dados), \
             patch.object(MODULO, "enviar_email", side_effect=RuntimeError("falha smtp")), \
             patch.object(MODULO, "cancelar_recuperacao") as cancelar:
            with self.assertRaises(RuntimeError):
                MODULO._enviar_recuperacao("aluno@example.com", "https://safeclick.example/redefinir-senha")
        cancelar.assert_called_once_with(TOKEN)

    def test_log_de_falha_nao_contem_segredos_e_libera_vaga(self):
        funcao = MagicMock(side_effect=RuntimeError(TOKEN + " segredo smtp aluno@example.com"))
        with patch.object(MODULO, "_VAGAS") as vagas, patch.object(self.app.logger, "error") as log:
            MODULO._executar(self.app, funcao, ("aluno@example.com",))
        vagas.release.assert_called_once()
        self.assertNotIn(TOKEN, str(log.call_args))
        self.assertNotIn("aluno@example.com", str(log.call_args))
        self.assertNotIn("exc_info", log.call_args.kwargs)

    def test_trabalho_tem_contexto_da_app_sem_contexto_da_requisicao(self):
        from flask import current_app, has_request_context
        def executar():
            self.assertIs(current_app._get_current_object(), self.app)
            self.assertFalse(has_request_context())
        with patch.object(MODULO, "_VAGAS") as vagas:
            MODULO._executar(self.app, executar, ())
        vagas.release.assert_called_once()

    def test_fila_cheia_nao_submete_e_falha_submit_libera_vaga(self):
        with self.app.app_context(), patch.object(MODULO, "_VAGAS") as vagas, \
             patch.object(MODULO, "_EXECUTOR") as executor:
            vagas.acquire.return_value = False
            self.assertFalse(MODULO._agendar(MODULO._avisar_redefinicao, "aluno@example.com"))
            executor.submit.assert_not_called()
            vagas.release.assert_not_called()
            vagas.acquire.return_value = True
            executor.submit.side_effect = RuntimeError("executor encerrado")
            self.assertFalse(MODULO._agendar(MODULO._avisar_redefinicao, "aluno@example.com"))
            vagas.release.assert_called_once()

    def test_agendamento_nao_espera_execucao_do_trabalho(self):
        with self.app.app_context(), patch.object(MODULO, "_VAGAS") as vagas, \
             patch.object(MODULO, "_EXECUTOR") as executor:
            vagas.acquire.return_value = True
            self.assertTrue(MODULO._agendar(MODULO._avisar_redefinicao, "aluno@example.com"))
            executor.submit.return_value.result.assert_not_called()
            executor.submit.assert_called_once_with(MODULO._executar, self.app,
                MODULO._avisar_redefinicao, ("aluno@example.com",))

    def test_aviso_de_troca_nao_contem_senha_ou_token(self):
        with patch.object(MODULO, "enviar_email") as enviar:
            MODULO._avisar_redefinicao("aluno@example.com")
        self.assertNotIn(TOKEN, str(enviar.call_args))
        self.assertNotIn(SENHA, str(enviar.call_args))
        self.assertIn("autenticador", enviar.call_args.args[2])

    def test_base_publica_exige_https_exceto_loopback_e_recusa_componentes_extras(self):
        invalidas = ("", "http://exemplo.com", "https://usuario:senha@exemplo.com",
                     "https://exemplo.com/caminho", "https://exemplo.com?x=1",
                     "https://exemplo.com#x", "https://exemplo.com:invalido", "https://exemplo .com")
        with self.app.app_context():
            for base in invalidas:
                with self.subTest(base=base):
                    self.app.config["APP_BASE_URL"] = base
                    with self.assertRaises(RuntimeError):
                        MODULO._base_publica()
            for base in ("https://exemplo.com", "http://127.0.0.1:5000", "http://localhost:5000"):
                self.app.config["APP_BASE_URL"] = base
                self.assertEqual(MODULO._base_publica(), base)


if __name__ == "__main__":
    unittest.main()
