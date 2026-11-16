import os
import unittest
from unittest.mock import patch

from werkzeug.datastructures import MultiDict

from safeclick import create_app
from safeclick.formularios import FormularioCadastro, FormularioRedefinirSenha
from safeclick.politica_senha import MENSAGEM_PESSOAL, MENSAGEM_TRIVIAL, problema_senha


class PoliticaSenhaTeste(unittest.TestCase):
    def test_recusa_senhas_triviais(self):
        for senha in ("aaaaaaaaaaaaaaa", "123456789012345", "abcdefghijklmnop", "senhasenhasenha",
                      "senha12345678910", "Senha@123Senha@123", "qwertyuiopasdfgh", "abcabcabcabcabc",
                      "9876543210987654", "a a a a a a a a "):
            with self.subTest(senha=senha):
                self.assertEqual(problema_senha(senha), MENSAGEM_TRIVIAL)

    def test_aceita_frases_e_senhas_longas(self):
        for senha in ("cafe com pao de queijo", "Ipe-amarelo-no-quintal-2026", "correct horse battery",
                      "minha senha muito forte 2026", "1qaz2wsx3edc4rfv", "pão de queijo na varanda"):
            with self.subTest(senha=senha):
                self.assertIsNone(problema_senha(senha))

    def test_recusa_nome_e_email(self):
        self.assertEqual(problema_senha("eduardo-gosta-de-cafe-2026", "Eduardo Mafra", "x@exemplo.com"), MENSAGEM_PESSOAL)
        self.assertEqual(problema_senha("viagem com mafra10 em 2026", "Ana", "Mafra10@exemplo.com"), MENSAGEM_PESSOAL)
        self.assertIsNone(problema_senha("viagem com a ana em 2026", "Ana Lima", "al@exemplo.com"))

    def test_tamanho_fica_com_o_formulario(self):
        self.assertIsNone(problema_senha("aaaa"))
        self.assertIsNone(problema_senha("a" * 129))


class FormulariosSenhaTeste(unittest.TestCase):
    def setUp(self):
        with patch.dict(os.environ, {"SECRET_KEY": "chave-de-teste", "DATABASE_URL": "postgresql://nao-usado"}):
            self.app = create_app()
        self.app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)

    def erros(self, classe, **dados):
        with self.app.test_request_context(method="POST"):
            formulario = classe(formdata=MultiDict(dados))
            formulario.validate()
            return formulario.senha.errors

    def test_cadastro_recusa_trivial_e_dados_pessoais(self):
        base = {"nome": "Bruno Souza", "email": "bruno@exemplo.com", "confirmar_email": "bruno@exemplo.com"}
        self.assertIn(MENSAGEM_TRIVIAL, self.erros(FormularioCadastro, **base, senha="aaaaaaaaaaaaaaa", confirmar_senha="aaaaaaaaaaaaaaa"))
        self.assertIn(MENSAGEM_PESSOAL, self.erros(FormularioCadastro, **base, senha="bruno gosta de cafe", confirmar_senha="bruno gosta de cafe"))
        self.assertEqual(self.erros(FormularioCadastro, **base, senha="cafe com pao de queijo", confirmar_senha="cafe com pao de queijo"), [])
        self.assertEqual(self.erros(FormularioCadastro, **base, senha="curta", confirmar_senha="curta"), ["Use uma senha com 15 a 128 caracteres"])

    def test_redefinicao_recusa_trivial(self):
        self.assertIn(MENSAGEM_TRIVIAL, self.erros(FormularioRedefinirSenha, senha="123456789012345", confirmar_senha="123456789012345"))
        self.assertEqual(self.erros(FormularioRedefinirSenha, senha="cafe com pao de queijo", confirmar_senha="cafe com pao de queijo"), [])


if __name__ == "__main__":
    unittest.main()
