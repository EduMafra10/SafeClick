import os
import re
import unittest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from safeclick import create_app
from safeclick import contas_db
from safeclick.sessoes import Usuario


def conta(**alteracoes):
    dados = {
        "id": 12, "nome": "João Teste", "email": "joao@example.test", "perfil": "usuario",
        "criado_em": datetime(2026, 11, 1, 2, 30, tzinfo=timezone.utc),
        "tem_autenticador": True, "autenticador_ativo": True,
    }
    dados.update(alteracoes)
    return dados


class ContasBancoTeste(unittest.TestCase):
    def setUp(self):
        self.conexao = MagicMock()
        contexto = MagicMock()
        contexto.__enter__.return_value = self.conexao
        abrir = patch("safeclick.contas_db.conectar_banco", return_value=contexto)
        abrir.start()
        self.addCleanup(abrir.stop)
        self.registrar = patch("safeclick.contas_db.registrar_evento").start()
        self.addCleanup(patch.stopall)

    def test_busca_por_texto_escapa_curingas(self):
        self.conexao.execute.return_value.fetchone.return_value = {"total": 0}
        self.conexao.execute.return_value.fetchall.return_value = []
        contas_db.listar_contas(busca="50%_a")
        contagem, consulta = self.conexao.execute.call_args_list
        self.assertIn("ILIKE", consulta.args[0])
        self.assertEqual(consulta.args[1]["padrao"], "%50\\%\\_a%")
        self.assertNotIn("senha_hash", consulta.args[0])

    def test_busca_por_numero_da_conta(self):
        self.conexao.execute.return_value.fetchone.return_value = {"total": 1}
        contas_db.listar_contas(busca="12")
        consulta = self.conexao.execute.call_args_list[1]
        self.assertIn("WHERE id = %(id)s", consulta.args[0])
        self.assertEqual(consulta.args[1]["id"], 12)

    def test_redefinir_desvincula_encerra_sessoes_e_registra(self):
        self.conexao.execute.return_value.fetchone.return_value = {
            "id": 12, "mfa_identidade": "identidade", "mfa_fator_sid": "YF123"}
        self.conexao.execute.return_value.rowcount = 2

        antigo = contas_db.redefinir_autenticador(7, 12)

        self.assertEqual(antigo, {"identidade": "identidade", "fator_sid": "YF123"})
        comandos = " ".join(chamada.args[0] for chamada in self.conexao.execute.call_args_list)
        self.assertIn("FOR NO KEY UPDATE", comandos)
        self.assertIn("SET mfa_fator_sid = NULL, mfa_confirmado_em = NULL", comandos)
        self.assertIn("DELETE FROM public.sessoes_autenticadas", comandos)
        self.assertIn("DELETE FROM public.logins_pendentes", comandos)
        dados = self.registrar.call_args.kwargs
        self.assertEqual(dados["usuario_id"], 7)
        self.assertEqual(dados["evento"], "mfa.reconfiguracao_administrativa")
        self.assertEqual(dados["recurso_id"], 12)
        self.assertEqual(dados["detalhes"], {"sessoes_encerradas": 2})
        self.assertIs(dados["conexao"], self.conexao)

    def test_conta_sem_autenticador_nao_e_alterada(self):
        self.conexao.execute.return_value.fetchone.return_value = {
            "id": 12, "mfa_identidade": "identidade", "mfa_fator_sid": None}
        with self.assertRaises(contas_db.SemAutenticador):
            contas_db.redefinir_autenticador(7, 12)
        self.assertEqual(self.conexao.execute.call_count, 1)
        self.registrar.assert_not_called()

    def test_conta_inexistente(self):
        self.conexao.execute.return_value.fetchone.return_value = None
        with self.assertRaises(contas_db.ContaNaoEncontrada):
            contas_db.redefinir_autenticador(7, 99)


class ContasRotasTeste(unittest.TestCase):
    def substituir(self, alvo, **argumentos):
        substituicao = patch(alvo, **argumentos)
        valor = substituicao.start()
        self.addCleanup(substituicao.stop)
        return valor

    def setUp(self):
        with patch.dict(os.environ, {"SECRET_KEY": "chave-de-teste", "DATABASE_URL": "postgresql://nao-usado"}):
            self.app = create_app()
        self.app.config.update(TESTING=True, WTF_CSRF_ENABLED=True)
        self.client = self.app.test_client()
        self.substituir("psycopg.connect", side_effect=AssertionError("Banco real proibido"))
        self.usuario = Usuario({"id": 7, "nome": "Admin", "email": "admin@example.test", "perfil": "administrador"})
        self.substituir("safeclick.aceite_termos.usuario_aceitou_termos_atuais", return_value=True)
        self.substituir("safeclick.sessoes.registrar_evento")
        usuario = patch.object(self.app.login_manager, "_user_callback", return_value=self.usuario)
        usuario.start()
        self.addCleanup(usuario.stop)
        with self.client.session_transaction() as sessao:
            sessao["_user_id"] = "7"
            sessao["_fresh"] = True
        self.listar = self.substituir("safeclick.administracao.contas_db.listar_contas",
                                      return_value=([conta(), conta(id=7, nome="Admin", perfil="administrador")], 2))
        self.obter = self.substituir("safeclick.administracao.contas_db.obter_conta", return_value=conta())
        self.redefinir = self.substituir("safeclick.administracao.contas_db.redefinir_autenticador",
                                         return_value={"identidade": "identidade", "fator_sid": "YF123"})
        self.remover = self.substituir("safeclick.administracao.remover_fator_totp")

    def postar(self, url):
        pagina = self.client.get("/administracao/contas").get_data(as_text=True)
        token = re.search(r'name="csrf_token" type="hidden" value="([^"]+)"', pagina).group(1)
        return self.client.post(url, data={"csrf_token": token})

    def test_lista_mostra_situacao_e_nao_oferece_redefinir_a_propria_conta(self):
        resposta = self.client.get("/administracao/contas?busca=jo")
        html = resposta.get_data(as_text=True)
        self.assertEqual(resposta.status_code, 200)
        self.assertIn("Autenticador: Ativo", html)
        self.assertIn("joao@example.test", html)
        self.assertIn('href="/administracao/contas/12/redefinir-autenticador"', html)
        self.assertNotIn('href="/administracao/contas/7/redefinir-autenticador"', html)
        self.listar.assert_called_once_with(busca="jo", pagina=1, por_pagina=20)

    def test_situacoes_do_autenticador(self):
        self.listar.return_value = ([conta(autenticador_ativo=False), conta(id=13, tem_autenticador=False,
                                                                            autenticador_ativo=False)], 2)
        html = self.client.get("/administracao/contas").get_data(as_text=True)
        self.assertIn("QR Code gerado, ainda não ativado", html)
        self.assertIn("Não configurado", html)
        self.assertNotIn('href="/administracao/contas/13/redefinir-autenticador"', html)

    def test_filtros_invalidos(self):
        for url in ("/administracao/contas?pagina=0", "/administracao/contas?pagina=abc",
                    "/administracao/contas?outro=1"):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 400)

    def test_usuario_comum_nao_acessa(self):
        self.usuario.perfil = "usuario"
        self.assertEqual(self.client.get("/administracao/contas").status_code, 403)
        self.assertEqual(self.client.post("/administracao/contas/12/redefinir-autenticador").status_code, 403)
        self.redefinir.assert_not_called()

    def test_confirmacao_explica_o_que_acontece(self):
        resposta = self.client.get("/administracao/contas/12/redefinir-autenticador")
        html = resposta.get_data(as_text=True)
        self.assertEqual(resposta.status_code, 200)
        self.assertIn("Confirmar redefinição", html)
        self.assertIn("continua obrigatória", html)
        self.redefinir.assert_not_called()

    def test_redefinir_remove_na_twilio_e_volta_para_a_lista(self):
        resposta = self.postar("/administracao/contas/12/redefinir-autenticador")
        self.assertEqual(resposta.status_code, 303)
        self.assertIn("/administracao/contas?busca=joao@example.test", resposta.location)
        self.redefinir.assert_called_once_with(7, 12)
        self.remover.assert_called_once_with("identidade", "YF123", usuario_id=12)
        html = self.client.get(resposta.location).get_data(as_text=True)
        self.assertIn("Autenticador de João Teste redefinido", html)

    def test_falha_na_twilio_nao_desfaz_a_redefinicao(self):
        self.remover.side_effect = RuntimeError("Twilio fora do ar")
        resposta = self.postar("/administracao/contas/12/redefinir-autenticador")
        self.assertEqual(resposta.status_code, 303)
        self.redefinir.assert_called_once()

    def test_falha_no_banco_nao_chama_a_twilio(self):
        self.redefinir.side_effect = RuntimeError("banco")
        resposta = self.postar("/administracao/contas/12/redefinir-autenticador")
        self.assertEqual(resposta.status_code, 503)
        self.assertIn("Nada foi alterado", resposta.get_data(as_text=True))
        self.remover.assert_not_called()

    def test_nao_redefine_a_propria_conta_nem_conta_sem_autenticador(self):
        for dados in (conta(id=7), conta(tem_autenticador=False, autenticador_ativo=False)):
            with self.subTest(dados=dados):
                self.obter.return_value = dados
                resposta = self.postar(f"/administracao/contas/{dados['id']}/redefinir-autenticador")
                self.assertEqual(resposta.status_code, 409)
                self.assertNotIn("Confirmar redefinição", resposta.get_data(as_text=True))
        self.redefinir.assert_not_called()

    def test_conta_inexistente(self):
        self.obter.return_value = None
        self.assertEqual(self.client.get("/administracao/contas/99/redefinir-autenticador").status_code, 404)

    def test_exige_token_csrf(self):
        resposta = self.client.post("/administracao/contas/12/redefinir-autenticador")
        self.assertEqual(resposta.status_code, 400)
        self.redefinir.assert_not_called()


    

class AjudaAutenticadorTeste(unittest.TestCase):
    def setUp(self):
        with patch.dict(os.environ, {"SECRET_KEY": "chave-de-teste", "DATABASE_URL": "postgresql://nao-usado",
                                     "SUPORTE_EMAIL": "suporte@example.test"}):
            self.app = create_app()
        self.app.config.update(TESTING=True)
        self.client = self.app.test_client()
        with self.client.session_transaction() as sessao:
            sessao["login_pendente"] = "x" * 43

    def tela(self, confirmado):
        usuario = {"id": 12, "mfa_fator_sid": "YF123", "mfa_confirmado_em": confirmado}
        with patch("safeclick.autenticacao.buscar_login_pendente", return_value={"usuario_id": 12, "tentativas": 0}), \
             patch("safeclick.autenticacao.buscar_mfa_por_usuario", return_value=usuario):
            return self.client.get("/login/autenticador").get_data(as_text=True)

    def test_mostra_como_pedir_ajuda_quando_o_autenticador_esta_ativo(self):
        html = self.tela(datetime(2026, 11, 1, tzinfo=timezone.utc))
        self.assertIn("Perdi acesso ao meu autenticador", html)
        self.assertIn('href="mailto:suporte@example.test?subject=Perdi%20acesso', html)

    def test_nao_mostra_durante_a_primeira_configuracao(self):
        self.assertNotIn("Perdi acesso ao meu autenticador", self.tela(None))


if __name__ == "__main__":
    unittest.main()