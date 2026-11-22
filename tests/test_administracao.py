import os
import unittest
from io import BytesIO
from unittest.mock import patch


from safeclick import create_app
from safeclick.sessoes import Usuario
from test_visao_geral import dados_visao_geral


class AdministracaoAcessoTeste(unittest.TestCase):
    def substituir(self, alvo, **argumentos):
        substituicao = patch(alvo, **argumentos)
        valor = substituicao.start()
        self.addCleanup(substituicao.stop)
        return valor

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
        self.usuario = Usuario({
            "id": 7, "nome": "Pessoa Teste", "email": "pessoa@example.test",
            "perfil": "administrador",
        })
        usuario = patch.object(self.app.login_manager, "_user_callback", return_value=self.usuario)
        usuario.start()
        self.addCleanup(usuario.stop)
        with self.client.session_transaction() as sessao:
            sessao["_user_id"] = "7"
            sessao["_fresh"] = True
        self.aceite = self.substituir(
            "safeclick.aceite_termos.usuario_aceitou_termos_atuais", return_value=True
        )
        self.auditar = self.substituir("safeclick.sessoes.registrar_evento")
        self.visao = self.substituir(
            "safeclick.administracao.buscar_visao_geral", return_value=dados_visao_geral()
        )

    def test_conta_comum_nao_abre_previa_nem_grava_catalogo(self):
        self.usuario.perfil = "usuario"
        with patch("safeclick.catalogo_admin.db.obter_item") as obter, \
             patch("safeclick.catalogo_admin.db.salvar_rascunho") as salvar:
            for caminho, metodo in (
                ("/administracao/catalogo/quizzes/2/previa", "GET"),
                ("/administracao/catalogo/quizzes/novo", "POST"),
                ("/administracao/catalogo/conteudos/1/remover", "POST"),
                ("/administracao/catalogo/simulacoes/1/publicar", "POST"),
                ("/administracao/catalogo/paginas/1/restaurar", "POST"),
            ):
                self.assertEqual(self.client.open(caminho, method=metodo).status_code, 403)
            obter.assert_not_called()
            salvar.assert_not_called()

    def test_admin_sem_csrf_nao_cria_rascunho(self):
        with patch("safeclick.catalogo_admin.db.salvar_rascunho") as salvar:
            resposta = self.client.post("/administracao/catalogo/quizzes/novo",
                                        data={"titulo": "Quiz", "formato": "perguntas", "estrutura": "[]"})
        self.assertEqual(resposta.status_code, 400)
        salvar.assert_not_called()

    def test_catalogo_oferece_editor_e_rota_de_importacao_foi_removida(self):
        with patch("safeclick.catalogo_admin.db.listar_itens", return_value=([], 0)):
            pagina = self.client.get("/administracao/catalogo/quizzes")
        self.assertEqual(pagina.status_code, 200)
        self.assertIn('href="/administracao/catalogo/quizzes/novo"', pagina.text)
        self.assertNotIn("Importar", pagina.text)
        rota = "/administracao/catalogo/quizzes/importar"
        self.assertEqual(self.client.get(rota).status_code, 404)
        self.assertEqual(self.client.post(rota, data={"lote": (BytesIO(b"[]"), "quizzes.json")}).status_code, 404)

    def test_visitante_precisa_login(self):
        with self.client.session_transaction() as sessao:
            sessao.clear()
        for caminho in ["/administracao/", "/administracao/contas"]:
            with self.subTest(caminho=caminho):
                resposta = self.client.get(caminho)
                self.assertEqual(resposta.status_code, 302)
                self.assertTrue(resposta.location.startswith("/login"))
        self.visao.assert_not_called()

    def test_usuario_comum_nao_acessa_nem_por_url(self):
        self.usuario.perfil = "usuario"
        for caminho in ["/administracao/", "/administracao/contas"]:
            with self.subTest(caminho=caminho):
                self.assertEqual(self.client.get(caminho).status_code, 403)
        self.visao.assert_not_called()
        self.assertEqual(self.auditar.call_count, 2)
        self.assertEqual(self.auditar.call_args.kwargs["evento"], "acesso.negado")
        self.assertEqual(self.auditar.call_args.kwargs["detalhes"], {"area": "administracao"})

    def test_perfil_invalido_e_parametro_nao_concedem_acesso(self):
        for perfil in ["admin", "moderador", None, "usuario"]:
            with self.subTest(perfil=perfil):
                self.usuario.perfil = perfil
                resposta = self.client.get("/administracao/?perfil=administrador")
                self.assertEqual(resposta.status_code, 403)
        self.visao.assert_not_called()

    def test_permissao_e_reavaliada_na_proxima_requisicao(self):
        self.assertEqual(self.client.get("/administracao/").status_code, 200)
        self.visao.reset_mock()
        self.usuario.perfil = "usuario"
        self.assertEqual(self.client.get("/administracao/").status_code, 403)
        self.visao.assert_not_called()

    def test_aceite_dos_termos_continua_obrigatorio(self):
        self.aceite.return_value = False
        resposta = self.client.get("/administracao/")
        self.assertEqual(resposta.status_code, 303)
        self.assertEqual(resposta.location, "/aceitar-termos")
        self.visao.assert_not_called()


if __name__ == "__main__":
    unittest.main()
