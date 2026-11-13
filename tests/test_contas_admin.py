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
        "ultimo_acesso": datetime(2026, 11, 10, 22, 15, tzinfo=timezone.utc),
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

    def test_filtro_do_autenticador_junto_com_a_busca(self):
        self.conexao.execute.return_value.fetchone.return_value = {"total": 0}
        contas_db.listar_contas(busca="ana", autenticador="pendente")
        consulta = self.conexao.execute.call_args_list[1].args[0]
        self.assertIn("(nome ILIKE %(padrao)s OR email ILIKE %(padrao)s) AND mfa_fator_sid IS NOT NULL AND mfa_confirmado_em IS NULL", consulta)
        self.assertIn("evento = 'login.sucesso'", consulta)
        with self.assertRaises(ValueError):
            contas_db.listar_contas(autenticador="qualquer")

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

    def preparar_perfil(self, perfil="usuario", autenticador_ativo=True, administradores=2):
        self.conexao.execute.return_value.fetchall.return_value = [{"id": n} for n in range(administradores)]
        self.conexao.execute.return_value.fetchone.return_value = {
            "id": 12, "perfil": perfil, "autenticador_ativo": autenticador_ativo}
        self.conexao.execute.return_value.rowcount = 3

    def test_promover_encerra_sessoes_e_registra(self):
        self.preparar_perfil()
        contas_db.alterar_perfil(7, 12, "administrador")
        comandos = [chamada.args for chamada in self.conexao.execute.call_args_list]
        self.assertIn("perfil = 'administrador' FOR NO KEY UPDATE", comandos[0][0])
        self.assertIn("FOR NO KEY UPDATE", comandos[1][0])
        self.assertEqual(comandos[2], ("UPDATE public.usuarios SET perfil = %s WHERE id = %s", ("administrador", 12)))
        self.assertIn("DELETE FROM public.sessoes_autenticadas", comandos[3][0])
        dados = self.registrar.call_args.kwargs
        self.assertEqual(dados["usuario_id"], 7)
        self.assertEqual(dados["evento"], "usuario.perfil_alterado")
        self.assertEqual(dados["recurso_id"], 12)
        self.assertEqual(dados["detalhes"], {"perfil_anterior": "usuario", "perfil_novo": "administrador",
                                             "sessoes_encerradas": 3})
        self.assertIs(dados["conexao"], self.conexao)

    def test_rebaixar_quando_ha_outro_administrador(self):
        self.preparar_perfil(perfil="administrador", administradores=2)
        contas_db.alterar_perfil(7, 12, "usuario")
        self.assertEqual(self.registrar.call_args.kwargs["detalhes"]["perfil_novo"], "usuario")

    def test_alteracoes_de_perfil_recusadas(self):
        casos = (
            ("propria conta", {}, (7, 7, "usuario"), "próprio perfil"),
            ("mesmo perfil", {"perfil": "administrador"}, (7, 12, "administrador"), "já tem"),
            ("sem autenticador", {"autenticador_ativo": False}, (7, 12, "administrador"), "autenticador ativo"),
            ("ultimo administrador", {"perfil": "administrador", "administradores": 1}, (7, 12, "usuario"), "pelo menos um"),
        )
        for nome, conta_banco, argumentos, mensagem in casos:
            with self.subTest(nome):
                self.preparar_perfil(**conta_banco)
                with self.assertRaisesRegex(contas_db.AlteracaoDePerfilRecusada, mensagem):
                    contas_db.alterar_perfil(*argumentos)
        comandos = " ".join(chamada.args[0] for chamada in self.conexao.execute.call_args_list)
        self.assertNotIn("SET perfil", comandos)
        self.registrar.assert_not_called()

    def test_perfil_invalido_e_conta_inexistente(self):
        with self.assertRaises(ValueError):
            contas_db.alterar_perfil(7, 12, "suporte")
        self.preparar_perfil()
        self.conexao.execute.return_value.fetchone.return_value = None
        with self.assertRaises(contas_db.ContaNaoEncontrada):
            contas_db.alterar_perfil(7, 99, "administrador")


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
        self.alterar = self.substituir("safeclick.administracao.contas_db.alterar_perfil")

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
        self.listar.assert_called_once_with(busca="jo", autenticador=None, pagina=1, por_pagina=20)
        self.assertIn("Último acesso em 10/11/2026 às 19:15", html)
    def test_situacoes_do_autenticador(self):
        self.listar.return_value = ([conta(autenticador_ativo=False), conta(id=13, tem_autenticador=False,
                                                                            autenticador_ativo=False)], 2)
        html = self.client.get("/administracao/contas").get_data(as_text=True)
        self.assertIn("QR Code gerado, ainda não ativado", html)
        self.assertIn("Não configurado", html)
        self.assertNotIn('href="/administracao/contas/13/redefinir-autenticador"', html)

    def test_filtra_pela_situacao_do_autenticador(self):
        self.listar.return_value = ([conta(id=13, ultimo_acesso=None)], 1)
        html = self.client.get("/administracao/contas?autenticador=pendente").get_data(as_text=True)
        self.listar.assert_called_once_with(busca="", autenticador="pendente", pagina=1, por_pagina=20)
        self.assertIn('<option value="pendente" selected>', html)
        self.assertIn("Nenhum acesso registrado", html)

    def test_filtros_invalidos(self):
        for url in ("/administracao/contas?pagina=0", "/administracao/contas?pagina=abc",
                    "/administracao/contas?outro=1", "/administracao/contas?autenticador=bloqueado"):
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

    def test_lista_oferece_promover_e_remover_acesso(self):
        self.listar.return_value = ([conta(), conta(id=13, perfil="administrador"),
                                     conta(id=14, autenticador_ativo=False),
                                     conta(id=7, nome="Admin", perfil="administrador")], 4)
        html = self.client.get("/administracao/contas").get_data(as_text=True)
        self.assertIn('href="/administracao/contas/12/perfil">Tornar administrador', html)
        self.assertIn('href="/administracao/contas/13/perfil">Remover acesso de administrador', html)
        self.assertNotIn('href="/administracao/contas/14/perfil"', html)
        self.assertNotIn('href="/administracao/contas/7/perfil"', html)

    def test_confirmacao_de_promocao(self):
        resposta = self.client.get("/administracao/contas/12/perfil")
        html = resposta.get_data(as_text=True)
        self.assertEqual(resposta.status_code, 200)
        self.assertIn("Confirmar promoção", html)
        self.assertIn("próximo login", html)
        self.alterar.assert_not_called()

    def test_promover_volta_para_a_lista(self):
        resposta = self.postar("/administracao/contas/12/perfil")
        self.assertEqual(resposta.status_code, 303)
        self.assertIn("/administracao/contas?busca=joao@example.test", resposta.location)
        self.alterar.assert_called_once_with(7, 12, "administrador")
        html = self.client.get(resposta.location).get_data(as_text=True)
        self.assertIn("João Teste agora é administrador(a).", html)

    def test_remover_acesso_de_administrador(self):
        self.obter.return_value = conta(perfil="administrador")
        self.assertIn("Confirmar remoção", self.client.get("/administracao/contas/12/perfil").get_data(as_text=True))
        resposta = self.postar("/administracao/contas/12/perfil")
        self.assertEqual(resposta.status_code, 303)
        self.alterar.assert_called_once_with(7, 12, "usuario")

    def test_bloqueios_da_alteracao_de_perfil(self):
        for dados in (conta(id=7, perfil="administrador"), conta(autenticador_ativo=False)):
            with self.subTest(dados=dados):
                self.obter.return_value = dados
                resposta = self.postar(f"/administracao/contas/{dados['id']}/perfil")
                self.assertEqual(resposta.status_code, 409)
                self.assertNotIn("Confirmar", resposta.get_data(as_text=True))
        self.alterar.assert_not_called()

    def test_recusa_do_banco_aparece_na_tela(self):
        self.obter.return_value = conta(perfil="administrador")
        self.alterar.side_effect = contas_db.AlteracaoDePerfilRecusada("O sistema precisa ter pelo menos um administrador.")
        resposta = self.postar("/administracao/contas/12/perfil")
        self.assertEqual(resposta.status_code, 409)
        self.assertIn("pelo menos um administrador", resposta.get_data(as_text=True))

    def test_falha_no_banco_ao_alterar_perfil(self):
        self.alterar.side_effect = RuntimeError("banco")
        resposta = self.postar("/administracao/contas/12/perfil")
        self.assertEqual(resposta.status_code, 503)
        self.assertIn("Nada foi alterado", resposta.get_data(as_text=True))

    def test_alterar_perfil_exige_csrf_e_administrador(self):
        self.assertEqual(self.client.post("/administracao/contas/12/perfil").status_code, 400)
        self.obter.return_value = None
        self.assertEqual(self.client.get("/administracao/contas/99/perfil").status_code, 404)
        self.usuario.perfil = "usuario"
        self.assertEqual(self.client.post("/administracao/contas/12/perfil").status_code, 403)
        self.alterar.assert_not_called()


    

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