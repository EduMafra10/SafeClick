import os
import unittest
from unittest.mock import patch

from safeclick import create_app


AMBIENTE = {"SECRET_KEY": "chave-exclusiva-dos-testes", "DATABASE_URL": "postgresql://nao-usado"}


class PainelDeAcessoTest(unittest.TestCase):
    def setUp(self):
        with patch.dict(os.environ, AMBIENTE):
            self.app = create_app()
        self.app.config.update(TESTING=True)
        self.client = self.app.test_client()
        banco = patch("psycopg.connect", side_effect=AssertionError("Banco real proibido"))
        banco.start()
        self.addCleanup(banco.stop)

    def test_login_mostra_a_simulacao_e_o_caminho_de_volta(self):
        html = self.client.get("/login").get_data(as_text=True)

        self.assertIn("autenticacao-apresentacao-simulacao", html)
        self.assertIn('class="autenticacao-cena" aria-hidden="true"', html)
        self.assertIn('<a class="autenticacao-voltar" href="/">Voltar para o início</a>', html)
        self.assertIn('<h1 class="autenticacao-serif" id="titulo-pagina">Entre na sua conta</h1>', html)

    def test_cadastro_mostra_os_tres_passos_reais(self):
        with patch("safeclick.autenticacao.buscar_termos", return_value={"versao": "1.1"}):
            html = self.client.get("/cadastro").get_data(as_text=True)

        self.assertIn("autenticacao-apresentacao-passos", html)
        for passo in ("Crie sua conta", "Entre com e-mail e senha", "Ative o autenticador"):
            self.assertIn(f"<b>{passo}</b>", html)

    def test_demais_telas_usam_o_painel_padrao(self):
        html = self.client.get("/recuperar-senha").get_data(as_text=True)

        self.assertIn('class="autenticacao-anzol"', html)
        self.assertNotIn("autenticacao-cena", html)
        self.assertNotIn("autenticacao-passos", html)

    def test_painel_vem_antes_do_formulario_sem_titulo_concorrente(self):
        html = self.client.get("/login").get_data(as_text=True)

        self.assertLess(html.index("autenticacao-apresentacao"), html.index('id="titulo-pagina"'))
        self.assertEqual(html.count("<h1"), 1)
        self.assertNotIn("<h2", html)


if __name__ == "__main__":
    unittest.main()
