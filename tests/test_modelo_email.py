import email
import unittest
from unittest.mock import MagicMock, patch

from safeclick.emails import enviar_email
from safeclick.modelo_email import montar_email
from tests.test_recuperacao import criar_app_teste


class ModeloEmailTeste(unittest.TestCase):
    def setUp(self):
        self.app = criar_app_teste(self)
        self.app.config["SUPORTE_EMAIL"] = "suporte@example.com"
        contexto = self.app.app_context()
        contexto.push()
        self.addCleanup(contexto.pop)

    def test_texto_e_html_trazem_o_mesmo_conteudo(self):
        texto, html = montar_email(
            "Segurança da conta", "Título do aviso", ["Primeiro parágrafo."],
            botao=("Abrir", "https://safeclick.example/pagina#token=abc"),
            aviso=("Não foi você?", "Ignore."),
        )
        for parte in ("Primeiro parágrafo.", "https://safeclick.example/pagina#token=abc",
                      "Não foi você? Ignore.", "suporte@example.com"):
            self.assertIn(parte, texto)
        self.assertIn('href="https://safeclick.example/pagina#token=abc"', html)
        self.assertIn("Título do aviso", html)
        self.assertIn("suporte@example.com", html)

    def test_html_escapa_o_conteudo(self):
        _, html = montar_email("Conta", "<b>t</b>", ['<script>alert("x")</script>'],
                               botao=("Abrir", 'https://a.example/"><script>'))
        self.assertNotIn("<script>", html)
        self.assertNotIn("<b>t</b>", html)
        self.assertIn("&lt;script&gt;", html)

    def test_sem_botao_nao_mostra_link_direto(self):
        _, html = montar_email("Conta", "Título", ["Texto."])
        self.assertNotIn("Link direto", html)
        self.assertNotIn("<a ", html)

    def test_envio_leva_texto_puro_e_html(self):
        self.app.config.update(SMTP_USER="remetente@example.com")
        conexao = MagicMock()
        with patch("safeclick.emails.conectar_smtp") as conectar:
            conectar.return_value.__enter__.return_value = conexao
            enviar_email("pessoa@example.com", "Assunto", "Texto puro", html="<p>HTML</p>")
        mensagem = email.message_from_bytes(conexao.send_message.call_args.args[0].as_bytes())
        tipos = [parte.get_content_type() for parte in mensagem.walk()]
        self.assertEqual(tipos, ["multipart/alternative", "text/plain", "text/html"])

    def test_envio_sem_html_continua_texto_puro(self):
        self.app.config.update(SMTP_USER="remetente@example.com")
        conexao = MagicMock()
        with patch("safeclick.emails.conectar_smtp") as conectar:
            conectar.return_value.__enter__.return_value = conexao
            enviar_email("pessoa@example.com", "Assunto", "Texto puro")
        self.assertEqual(conexao.send_message.call_args.args[0].get_content_type(), "text/plain")


if __name__ == "__main__":
    unittest.main()
