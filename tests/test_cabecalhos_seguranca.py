import os
import unittest
from unittest.mock import patch

from safeclick import create_app


class CabecalhosSegurancaTeste(unittest.TestCase):
    def setUp(self):
        ambiente = patch.dict(os.environ, {"SECRET_KEY": "chave-teste-cabecalhos", "DATABASE_URL": "postgresql://nao-usado"}, clear=True)
        ambiente.start()
        self.addCleanup(ambiente.stop)
        self.client = create_app().test_client()

    def test_paginas_html_recebem_politica_de_conteudo(self):
        resposta = self.client.get("/login")
        politica = resposta.headers.get("Content-Security-Policy", "")
        for trecho in ("default-src 'self'", "script-src 'self'", "object-src 'none'", "frame-ancestors 'self'", "form-action 'self'"):
            with self.subTest(trecho=trecho):
                self.assertIn(trecho, politica)
        self.assertNotIn("unsafe-eval", politica)
        self.assertEqual(resposta.headers["X-Content-Type-Options"], "nosniff")

    def test_arquivos_que_nao_sao_html_ficam_sem_politica(self):
        resposta = self.client.get("/favicon.ico")
        self.assertNotIn("Content-Security-Policy", resposta.headers)
