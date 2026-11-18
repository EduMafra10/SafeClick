"""Página inicial pública e favicon (o redirecionamento de quem já entrou fica em test_painel e test_visao_geral)."""
import os
import re
import unittest
from pathlib import Path
from unittest.mock import patch

from safeclick import create_app


AMBIENTE = {"SECRET_KEY": "chave-exclusiva-dos-testes", "DATABASE_URL": "postgresql://nao-usado"}
TEMPLATES = Path(__file__).resolve().parents[1] / "safeclick" / "templates"


class PaginaInicialTest(unittest.TestCase):
    def setUp(self):
        with patch.dict(os.environ, AMBIENTE):
            self.app = create_app()
        self.app.config.update(TESTING=True)
        self.client = self.app.test_client()
        banco = patch("psycopg.connect", side_effect=AssertionError("Banco real proibido"))
        banco.start()
        self.addCleanup(banco.stop)

    def test_visitante_ve_a_pagina_inicial_sem_consultar_o_banco(self):
        resposta = self.client.get("/")
        html = resposta.get_data(as_text=True)

        self.assertEqual(resposta.status_code, 200)
        self.assertIn("Aprenda antes de clicar", html)
        self.assertIn('id="como"', html)
        self.assertIn('id="senhas"', html)
        self.assertIn('id="protecao"', html)
        self.assertIn('id="sobre"', html)

    def test_pagina_inicial_leva_para_cadastro_login_e_documentos(self):
        html = self.client.get("/").get_data(as_text=True)

        for destino in (
            'href="/cadastro"', 'href="/login"', 'href="/recuperar-senha"',
            'href="/politica-de-privacidade"', 'href="/termos-de-uso"',
            'href="https://github.com/EduMafra10/SafeClick"',
        ):
            self.assertIn(destino, html)

    def test_atalhos_do_menu_apontam_para_secoes_existentes(self):
        html = self.client.get("/").get_data(as_text=True)
        menu = re.search(r'<nav class="menu".*?</nav>', html, re.S).group(0)

        ancoras = re.findall(r'href="#([\w-]+)"', menu)
        self.assertEqual(ancoras, ["como", "senhas", "protecao", "sobre"])
        for ancora in ancoras:
            self.assertIn(f'id="{ancora}"', html)

    def test_links_externos_abrem_sem_acesso_a_janela_de_origem(self):
        html = self.client.get("/").get_data(as_text=True)

        for link in re.findall(r'<a [^>]*target="_blank"[^>]*>', html):
            self.assertIn('rel="noopener"', link)

    def test_favicon_na_raiz_do_site(self):
        resposta = self.client.get("/favicon.ico")

        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.mimetype, "image/vnd.microsoft.icon")
        self.assertTrue(resposta.get_data().startswith(b"\x00\x00\x01\x00"))
        resposta.close()

    def test_arquivos_do_favicon_existem(self):
        for arquivo in ("favicon.ico", "favicon.svg", "apple-touch-icon.png"):
            resposta = self.client.get(f"/static/img/{arquivo}")
            self.assertEqual(resposta.status_code, 200, arquivo)
            resposta.close()


class FaviconNasPaginasTest(unittest.TestCase):
    def test_toda_pagina_completa_inclui_o_favicon(self):
        faltando = []
        for arquivo in sorted(TEMPLATES.rglob("*.html")):
            texto = arquivo.read_text(encoding="utf-8")
            nome = str(arquivo.relative_to(TEMPLATES)).replace("\\", "/")
            if "<head>" not in texto or nome == "emails/modelo.html":
                continue
            if 'componentes/_favicon.html' not in texto:
                faltando.append(nome)
        self.assertEqual(faltando, [])

    def test_login_mostra_o_favicon_e_volta_para_o_inicio(self):
        with patch.dict(os.environ, AMBIENTE):
            app = create_app()
        app.config.update(TESTING=True)
        with patch("psycopg.connect", side_effect=AssertionError("Banco real proibido")):
            html = app.test_client().get("/login").get_data(as_text=True)

        self.assertIn('href="/static/img/favicon.ico"', html)
        self.assertIn('<a class="autenticacao-marca" href="/">', html)


if __name__ == "__main__":
    unittest.main()
