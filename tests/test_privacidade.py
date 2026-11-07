# Testes das páginas de LGPD. Não acessam o banco de dados.
# Executar: .\.venv\Scripts\python.exe -m pytest tests
import os
from datetime import date
from pathlib import Path
from unittest.mock import patch

import psycopg
import pytest

from safeclick import create_app
from safeclick.privacidade import DOCUMENTOS, VERSAO_POLITICA


LEI_EXEMPLO = {
    "norma": "Lei nº 13.709/2018 (LGPD)",
    "dispositivo": "art. 14",
    "assunto": "Tratamento de dados de crianças e adolescentes",
    "url": "https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709.htm",
}


def _documento(app, template):
    with app.test_request_context():
        from flask import render_template
        pagina = render_template(template, **DOCUMENTOS)
    artigo = pagina.split('<article class="privacidade-documento">', 1)[1].split('</article>', 1)[0].strip()
    return {"versao": DOCUMENTOS["versao"], "vigente_desde": date(2026, 9, 28), "conteudo_html": artigo}


@pytest.fixture
def cliente():
    os.environ.setdefault("SECRET_KEY", "chave-somente-para-testes")
    app = create_app()
    app.config["TESTING"] = True
    # As paginas usam os documentos arquivados; o teste continua sem banco real.
    termos = _documento(app, "privacidade/termos.html")
    politica = _documento(app, "privacidade/politica.html")
    with patch("safeclick.privacidade.buscar_termos", return_value=termos), \
         patch("safeclick.privacidade.buscar_politica", return_value=politica), \
         patch("safeclick.privacidade.buscar_referencias", return_value=[LEI_EXEMPLO]):
        yield app.test_client()


@pytest.mark.parametrize("rota", ["/politica-de-privacidade", "/termos-de-uso"])
def test_paginas_abrem_com_versao_e_contato(cliente, rota):
    resposta = cliente.get(rota)
    html = resposta.get_data(as_text=True)

    assert resposta.status_code == 200
    assert f"Versão {DOCUMENTOS['versao']}" in html
    assert DOCUMENTOS["email_privacidade"] in html
    assert f"{DOCUMENTOS['idade_minima_conta']} anos" in html


def test_politica_cobre_os_itens_exigidos(cliente):
    html = cliente.get("/politica-de-privacidade").get_data(as_text=True)

    for trecho in ["Base legal", "Adolescentes", "Cookies", "Com quem compartilhamos",
                   "Transferência internacional", "Por quanto tempo guardamos",
                   "Seus direitos", "três dias úteis"]:
        assert trecho in html


def test_termos_apontam_para_a_politica(cliente):
    html = cliente.get("/termos-de-uso").get_data(as_text=True)
    assert 'href="/politica-de-privacidade"' in html


def test_canal_de_privacidade_foi_preenchido():
    # o canal precisa funcionar de verdade: troque os valores PREENCHER em privacidade.py
    assert "PREENCHER" not in DOCUMENTOS["email_privacidade"]
    assert "PREENCHER" not in DOCUMENTOS["encarregado"]


@pytest.mark.parametrize("rota", ["/politica-de-privacidade", "/termos-de-uso"])
def test_paginas_mostram_legislacao_citada_do_banco(cliente, rota):
    html = cliente.get(rota).get_data(as_text=True)
    assert "Legislação citada" in html
    assert "Lei nº 13.709/2018 (LGPD)</a>, art. 14" in html


def test_politica_inexistente_404_e_banco_indisponivel_503(cliente):
    with patch("safeclick.privacidade.buscar_politica", return_value=None):
        assert cliente.get("/politica-de-privacidade?versao=9.9").status_code == 404
    with patch("safeclick.privacidade.buscar_politica", side_effect=psycopg.Error):
        assert cliente.get("/politica-de-privacidade").status_code == 503


def test_versao_da_politica_esta_no_script_do_banco():
    # a versao exibida por padrao precisa existir em registrar_politica_e_leis.sql
    script = (Path(__file__).resolve().parents[1] / "sql" / "registrar_politica_e_leis.sql").read_text(encoding="utf-8")
    assert f"VALUES ('{VERSAO_POLITICA}', DATE" in script
    assert f"Versão {VERSAO_POLITICA} · vigente desde" in script
