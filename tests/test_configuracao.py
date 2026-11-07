import os
import unittest
from pathlib import Path
from unittest.mock import patch

from safeclick.config import carregar_configuracao

BASICO = {"SECRET_KEY": "chave-de-teste", "DATABASE_URL": "postgresql://nao-usado"}
PRODUCAO = {
    "APP_ENV": "producao",
    "SECRET_KEY": "x" * 40,
    "DATABASE_URL": "postgresql://nao-usado",
    "APP_BASE_URL": "https://safeclick.example/",
    "TWILIO_ACCOUNT_SID": "AC123",
    "TWILIO_AUTH_TOKEN": "token",
    "TWILIO_VERIFY_SERVICE_SID": "VA123",
    "SMTP_USER": "projeto@example.test",
    "SMTP_PASSWORD": "senha-de-app",
}


def carregar(variaveis):
    with patch.dict(os.environ, variaveis, clear=True):
        return carregar_configuracao()


class ConfiguracaoTeste(unittest.TestCase):
    def test_valores_padrao_em_desenvolvimento(self):
        config = carregar(BASICO)
        self.assertEqual(config["APP_ENV"], "desenvolvimento")
        self.assertEqual(config["SMTP_PORT"], 587)
        self.assertEqual(config["APP_BASE_URL"], "http://127.0.0.1:5000")
        self.assertFalse(config["SESSION_COOKIE_SECURE"])
        self.assertTrue(config["SESSION_COOKIE_HTTPONLY"])

    def test_lista_todas_as_obrigatorias_que_faltam(self):
        with self.assertRaisesRegex(RuntimeError, "SECRET_KEY"):
            carregar({})
        with self.assertRaisesRegex(RuntimeError, "SECRET_KEY, DATABASE_URL, TWILIO_ACCOUNT_SID"):
            carregar({"APP_ENV": "producao"})

    def test_valor_so_com_espacos_conta_como_vazio(self):
        with self.assertRaisesRegex(RuntimeError, "SECRET_KEY"):
            carregar({**BASICO, "SECRET_KEY": "   "})

    def test_producao_exige_integracoes_e_https(self):
        config = carregar(PRODUCAO)
        self.assertTrue(config["SESSION_COOKIE_SECURE"])
        self.assertEqual(config["APP_BASE_URL"], "https://safeclick.example")

        sem_twilio = {chave: valor for chave, valor in PRODUCAO.items() if chave != "TWILIO_AUTH_TOKEN"}
        with self.assertRaisesRegex(RuntimeError, "TWILIO_AUTH_TOKEN"):
            carregar(sem_twilio)
        with self.assertRaisesRegex(RuntimeError, "https://"):
            carregar({**PRODUCAO, "APP_BASE_URL": "http://safeclick.example"})
        with self.assertRaisesRegex(RuntimeError, "32 caracteres"):
            carregar({**PRODUCAO, "SECRET_KEY": "curta"})

    def test_producao_recusa_valores_de_exemplo(self):
        casos = {
            "SECRET_KEY": "troque-por-uma-chave-aleatoria-com-pelo-menos-32-caracteres",
            "TWILIO_ACCOUNT_SID": "ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
            "DATABASE_URL": "postgresql://USUARIO:SENHA@ep-exemplo-123456.neon.tech/neondb",
        }
        for nome, valor in casos.items():
            with self.subTest(nome=nome), self.assertRaisesRegex(RuntimeError, f"valores de exemplo.*{nome}"):
                carregar({**PRODUCAO, nome: valor})

    def test_desenvolvimento_aceita_o_exemplo_copiado(self):
        exemplo = Path(__file__).resolve().parents[1] / ".env.example"
        variaveis = dict(
            linha.split("=", 1)
            for linha in exemplo.read_text(encoding="utf-8").splitlines()
            if "=" in linha and not linha.lstrip().startswith("#")
        )
        self.assertEqual(carregar(variaveis)["APP_ENV"], "desenvolvimento")
        with self.assertRaisesRegex(RuntimeError, "valores de exemplo"):
            carregar({**variaveis, "APP_ENV": "producao", "APP_BASE_URL": "https://safeclick.example"})

    def test_valores_invalidos(self):
        casos = {
            "APP_ENV": ("teste", "APP_ENV"),
            "SMTP_PORT": ("porta", "SMTP_PORT"),
            "SESSION_COOKIE_SECURE": ("sim", "SESSION_COOKIE_SECURE"),
        }
        for nome, (valor, mensagem) in casos.items():
            with self.subTest(nome=nome), self.assertRaisesRegex(RuntimeError, mensagem):
                carregar({**BASICO, nome: valor})

    def test_exemplo_documenta_todas_as_variaveis(self):
        exemplo = Path(__file__).resolve().parents[1] / ".env.example"
        nomes = {
            linha.split("=", 1)[0]
            for linha in exemplo.read_text(encoding="utf-8").splitlines()
            if "=" in linha and not linha.lstrip().startswith("#")
        }
        lidas = set(carregar(BASICO)) - {"SESSION_COOKIE_HTTPONLY", "SESSION_COOKIE_SAMESITE"}
        self.assertEqual(nomes, lidas)


if __name__ == "__main__":
    unittest.main()