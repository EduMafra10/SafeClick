import unittest
from unittest.mock import MagicMock, patch

import psycopg

from safeclick.usuarios_db import criar_usuario


class CadastroAuditoriaTeste(unittest.TestCase):
    def setUp(self):
        self.conexao = MagicMock()
        self.conexao.execute.return_value.fetchone.return_value = {"id": 11}
        self.contexto = MagicMock()
        self.contexto.__enter__.return_value = self.conexao

    def test_conta_e_log_usam_a_mesma_conexao(self):
        with patch("safeclick.usuarios_db.conectar_banco", return_value=self.contexto), \
             patch("safeclick.usuarios_db.generate_password_hash", return_value="hash-teste"), \
             patch("safeclick.usuarios_db.registrar_evento") as registrar:
            usuario_id = criar_usuario("Pessoa", "PESSOA@example.com", "senha-teste")

        self.assertEqual(usuario_id, 11)
        self.assertEqual(registrar.call_args.kwargs["evento"], "usuario.cadastrado")
        self.assertEqual(registrar.call_args.kwargs["usuario_id"], 11)
        self.assertIs(registrar.call_args.kwargs["conexao"], self.conexao)

    def test_falha_no_log_impede_confirmar_cadastro(self):
        with patch("safeclick.usuarios_db.conectar_banco", return_value=self.contexto), \
             patch("safeclick.usuarios_db.generate_password_hash", return_value="hash-teste"), \
             patch("safeclick.usuarios_db.registrar_evento", side_effect=psycopg.Error):
            with self.assertRaises(psycopg.Error):
                criar_usuario("Pessoa", "pessoa@example.com", "senha-teste")

        self.assertIs(self.contexto.__exit__.call_args.args[0], psycopg.Error)


if __name__ == "__main__":
    unittest.main()
