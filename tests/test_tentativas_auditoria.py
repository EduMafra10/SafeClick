import unittest
from unittest.mock import MagicMock, patch

from safeclick.db import salvar_tentativa_simulacao
from safeclick.quizzes import salvar_tentativa


class TentativasAuditoriaTeste(unittest.TestCase):
    def setUp(self):
        self.conexao = MagicMock()
        self.contexto = MagicMock()
        self.contexto.__enter__.return_value = self.conexao

    def test_simulacao_vincula_usuario_e_log_na_mesma_transacao(self):
        self.conexao.execute.return_value.fetchone.return_value = {"id": 21}

        with patch("safeclick.db.conectar_banco", return_value=self.contexto), \
             patch("safeclick.auditoria_db.registrar_evento") as registrar:
            tentativa_id = salvar_tentativa_simulacao(7, "conta_bloqueada", "clicar_link")

        self.assertEqual(tentativa_id, 21)
        sql, parametros = self.conexao.execute.call_args.args
        self.assertIn("usuario_id", sql)
        self.assertEqual(parametros, (7, "conta_bloqueada", "clicar_link"))
        self.assertEqual(registrar.call_args.kwargs["usuario_id"], 7)
        self.assertEqual(registrar.call_args.kwargs["evento"], "simulacao.concluida")
        self.assertIs(registrar.call_args.kwargs["conexao"], self.conexao)

    def test_quiz_grava_respostas_e_log_para_o_mesmo_usuario(self):
        self.conexao.execute.return_value.fetchone.return_value = {"id": 34}
        resultado = {"pontuacao": 1, "total_questoes": 2}

        with patch("safeclick.quizzes.conectar_banco", return_value=self.contexto), \
             patch("safeclick.quizzes.registrar_evento") as registrar:
            tentativa_id = salvar_tentativa(7, 3, {11: 41, 12: 45}, resultado, "token")

        self.assertEqual(tentativa_id, 34)
        sql, parametros = self.conexao.execute.call_args_list[0].args
        self.assertIn("usuario_id", sql)
        self.assertEqual(parametros[:2], (7, 3))
        self.assertEqual(self.conexao.execute.call_count, 3)
        self.assertEqual(registrar.call_args.kwargs["usuario_id"], 7)
        self.assertEqual(registrar.call_args.kwargs["evento"], "quiz.concluido")
        self.assertIs(registrar.call_args.kwargs["conexao"], self.conexao)


if __name__ == "__main__":
    unittest.main()
