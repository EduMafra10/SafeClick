"""Toda página do SafeClick mostra os links da Política de Privacidade e dos Termos de Uso."""
import os
from pathlib import Path
from unittest.mock import patch

from flask import render_template

from safeclick import create_app


TEMPLATES = Path(__file__).resolve().parents[1] / "safeclick" / "templates"
LINKS = ('href="/politica-de-privacidade"', 'href="/termos-de-uso"')
AMBIENTE = {"SECRET_KEY": "chave-exclusiva-dos-testes", "DATABASE_URL": "postgresql://nao-usado"}


def _app():
    with patch.dict(os.environ, AMBIENTE):
        app = create_app()
    app.config.update(TESTING=True)
    return app


def test_toda_pagina_completa_tem_os_links_legais():
    faltando = []
    for arquivo in sorted(TEMPLATES.rglob("*.html")):
        texto = arquivo.read_text(encoding="utf-8")
        if "<html" not in texto or "conteudos/_rodape.html" in texto:
            continue
        if "privacidade.politica" in texto and "privacidade.termos" in texto:
            continue
        faltando.append(str(arquivo.relative_to(TEMPLATES)))
    assert faltando == []


def test_rodape_comum_tem_os_links_e_o_texto_extra():
    app = _app()
    with app.test_request_context():
        rodape = render_template("conteudos/_rodape.html")
        laboratorio = render_template("conteudos/_rodape.html", rodape_extra="Dados do desafio: Pwned Passwords.")
    for link in LINKS:
        assert link in rodape
    assert "Dados do desafio" not in rodape
    assert "Dados do desafio: Pwned Passwords." in laboratorio


def test_login_e_cadastro_mostram_os_links():
    app = _app()
    with patch("psycopg.connect", side_effect=AssertionError("Banco real proibido")):
        html = app.test_client().get("/login").get_data(as_text=True)
    assert 'class="autenticacao-legal"' in html
    for link in LINKS:
        assert link in html