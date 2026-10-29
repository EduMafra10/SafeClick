import unittest
from unittest.mock import MagicMock, patch

from requests.exceptions import ConnectionError, Timeout

from safeclick.pwned_api import (
    ServicoSenhasIndisponivel,
    consultar_prefixo_senha,
)


class PwnedApiTeste(unittest.TestCase):
    def setUp(self):
        bloqueio = patch(
            "requests.sessions.Session.request",
            side_effect=AssertionError("Acesso real à API proibido no teste"),
        )
        bloqueio.start()
        self.addCleanup(bloqueio.stop)

        consulta = patch("safeclick.pwned_api.requests.get")
        self.get = consulta.start()
        self.addCleanup(consulta.stop)

        self.resposta = MagicMock()
        self.resposta.status_code = 200
        self.resposta.text = "A" * 35 + ":12\r\n" + "B" * 35 + ":0\r\n"
        self.get.return_value.__enter__.return_value = self.resposta

    def test_envia_apenas_prefixo_e_preserva_padding(self):
        texto = consultar_prefixo_senha("aB123")

        self.assertEqual(texto, "A" * 35 + ":12\r\n" + "B" * 35 + ":0")
        self.get.assert_called_once_with(
            "https://api.pwnedpasswords.com/range/AB123",
            headers={
                "User-Agent": "SafeClick-Verificador-Senhas/1.0",
                "Add-Padding": "true",
            },
            timeout=(3.05, 10),
            allow_redirects=False,
        )

    def test_rejeita_entrada_invalida_sem_consultar(self):
        entradas = (
            None, 12345, "", "1234", "123456", "ABCDE\n",
            "ABCG1", "../ab", "A" * 40, "senha-ficticia",
        )
        for entrada in entradas:
            with self.subTest(entrada=entrada):
                with self.assertRaises(ValueError):
                    consultar_prefixo_senha(entrada)

        self.get.assert_not_called()

    def test_erro_http_ou_redirecionamento_gera_indisponibilidade(self):
        for status in (204, 301, 302, 400, 403, 404, 429, 500, 503):
            with self.subTest(status=status):
                self.resposta.status_code = status
                with self.assertRaises(ServicoSenhasIndisponivel):
                    consultar_prefixo_senha("ABCDE")

    def test_falha_de_rede_nao_expoe_detalhes(self):
        for tipo in (Timeout, ConnectionError):
            with self.subTest(tipo=tipo.__name__):
                self.get.side_effect = tipo("detalhe-interno-da-requisicao")
                with self.assertRaises(ServicoSenhasIndisponivel) as erro:
                    consultar_prefixo_senha("ABCDE")

                self.assertNotIn("detalhe-interno", str(erro.exception))
                self.assertTrue(erro.exception.__suppress_context__)

    def test_resposta_vazia_ou_invalida_gera_indisponibilidade(self):
        respostas = (
            "", "\n", "<html>Erro</html>",
            "A" * 34 + ":2",
            "G" * 35 + ":2",
            "A" * 35 + ":-1",
            "A" * 35 + ":abc",
            "A" * 35 + ":2\nlinha-invalida",
        )
        for resposta in respostas:
            with self.subTest(resposta=resposta):
                self.resposta.text = resposta
                with self.assertRaises(ServicoSenhasIndisponivel):
                    consultar_prefixo_senha("ABCDE")

    def test_normaliza_sufixos_e_mantem_contagem_zero(self):
        self.resposta.text = "c" * 35 + ":0\n" + "d" * 35 + ":9001\n"

        self.assertEqual(
            consultar_prefixo_senha("ABCDE"),
            "C" * 35 + ":0\r\n" + "D" * 35 + ":9001",
        )