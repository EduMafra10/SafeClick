import unittest
from unittest.mock import patch

from flask import Flask

from safeclick.db import conectar_banco


class ConexaoBancoTeste(unittest.TestCase):
    def conectar(self, ambiente, endereco):
        app = Flask(__name__)
        app.config.update(APP_ENV=ambiente, DATABASE_URL=endereco)
        with app.app_context(), patch("safeclick.db.psycopg.connect") as conectar:
            conectar_banco()
        return conectar.call_args.kwargs

    def test_producao_exige_tls_quando_o_endereco_nao_exige(self):
        for endereco in ("postgresql://u:s@banco/safeclick", "postgresql://u:s@banco/safeclick?sslmode=prefer"):
            with self.subTest(endereco=endereco):
                self.assertEqual(self.conectar("producao", endereco)["sslmode"], "require")

    def test_producao_mantem_modo_mais_forte_do_endereco(self):
        opcoes = self.conectar("producao", "postgresql://u:s@banco/safeclick?sslmode=verify-full")
        self.assertNotIn("sslmode", opcoes)

    def test_desenvolvimento_nao_altera_a_conexao(self):
        self.assertNotIn("sslmode", self.conectar("desenvolvimento", "postgresql://u:s@localhost/safeclick"))
