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


SEM_RODAPE = {"erro.html", "emails/modelo.html"}
RODAPES = ("componentes/_rodape.html", "conteudos/_rodape.html")


def test_toda_pagina_completa_tem_os_links_legais():

    faltando = []
    for arquivo in sorted(TEMPLATES.rglob("*.html")):
        texto = arquivo.read_text(encoding="utf-8")
        nome = str(arquivo.relative_to(TEMPLATES)).replace("\\", "/")
        if "<html" not in texto or nome in SEM_RODAPE or any(r in texto for r in RODAPES):
            continue
        if "privacidade.politica" in texto and "privacidade.termos" in texto:
            continue
        faltando.append(nome)
    assert faltando == []


def test_rodape_comum_tem_os_links_e_a_fonte():
    app = _app()
    with app.test_request_context():
        rodape = render_template("componentes/_rodape.html")
        laboratorio = render_template("componentes/_rodape.html", rodape_fonte="Dados do desafio: Pwned Passwords.")
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
