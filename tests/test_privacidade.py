# Testes das páginas de LGPD. Não acessam o banco de dados.
# Executar: .\.venv\Scripts\python.exe -m pytest tests
import os

import pytest

from safeclick import create_app
from safeclick.privacidade import DOCUMENTOS


@pytest.fixture
def cliente():
    os.environ.setdefault("SECRET_KEY", "chave-somente-para-testes")
    app = create_app()
    app.config["TESTING"] = True
    return app.test_client()


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
