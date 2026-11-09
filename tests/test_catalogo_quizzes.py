import json
import unittest

from safeclick.catalogo_validacao import DadosInvalidos, validar, validar_lote_quizzes


def pergunta(cartao_correto):
    return {
        "enunciado": "Escolha a melhor orientação.",
        "explicacao": "A orientação depende do risco apresentado.",
        "alternativas": [
            {"texto": cartao, "correta": cartao == cartao_correto}
            for cartao in ("Use senhas únicas", "Ative dois fatores")
        ],
    }


class CatalogoQuizzesTeste(unittest.TestCase):
    def setUp(self):
        self.quiz = {"titulo": "Proteção de contas", "questoes": [pergunta("Use senhas únicas")]}
        self.oficina = {
            "titulo": "Revisão de contas", "formato": "oficina",
            "questoes": [pergunta("Use senhas únicas"), pergunta("Ative dois fatores")],
        }

    def test_rascunho_incompleto_pode_ser_salvo_mas_nao_publicado(self):
        rascunho = {"titulo": "Nova atividade", "questoes": []}
        self.assertEqual(validar("quizzes", rascunho)["questoes"], [])
        with self.assertRaisesRegex(DadosInvalidos, "pelo menos uma pergunta"):
            validar("quizzes", rascunho, publicar=True)

    def test_publicacao_exige_uma_unica_alternativa_correta(self):
        alternativas = self.quiz["questoes"][0]["alternativas"]
        for correta in (False, True):
            with self.subTest(ambas_corretas=correta):
                for alternativa in alternativas:
                    alternativa["correta"] = correta
                with self.assertRaisesRegex(DadosInvalidos, "exatamente uma correta"):
                    validar("quizzes", self.quiz, publicar=True)

    def test_publicacao_aceita_explicacoes_completas_e_recusa_parciais(self):
        alternativas = self.quiz["questoes"][0]["alternativas"]
        alternativas[0]["explicacao"] = "Senha única limita o impacto de um vazamento."
        with self.assertRaisesRegex(DadosInvalidos, "explique cada alternativa"):
            validar("quizzes", self.quiz, publicar=True)

        alternativas[1]["explicacao"] = "Dois fatores protegem o login, mas não tornam as senhas diferentes."
        publicado = validar("quizzes", self.quiz, publicar=True)
        self.assertEqual(publicado["questoes"][0]["alternativas"], alternativas)

    def test_oficina_exige_mesmo_banco_de_cartoes_em_todos_os_trechos(self):
        self.oficina["questoes"][1]["alternativas"][1]["texto"] = "Use um gerenciador"
        with self.assertRaisesRegex(DadosInvalidos, "use os mesmos cartões do primeiro trecho"):
            validar("quizzes", self.oficina, publicar=True)

    def test_oficina_exige_um_cartao_correto_diferente_por_trecho(self):
        self.oficina["questoes"][1] = pergunta("Use senhas únicas")
        with self.assertRaisesRegex(DadosInvalidos, "cartão correto diferente"):
            validar("quizzes", self.oficina, publicar=True)

    def test_importacao_valida_os_dois_formatos_e_normaliza_o_titulo(self):
        self.quiz["titulo"] = "  Proteção de contas  "
        lote = validar_lote_quizzes(json.dumps([self.quiz, self.oficina]))

        self.assertEqual([item["titulo"] for item in lote], ["Proteção de contas", "Revisão de contas"])
        self.assertEqual([item["formato"] for item in lote], ["perguntas", "oficina"])
        self.assertEqual(len(lote[1]["questoes"]), 2)

    def test_importacao_recusa_titulo_repetido_e_identifica_item_invalido(self):
        repetido = self.quiz | {"titulo": "  PROTEÇÃO DE CONTAS  "}
        with self.assertRaisesRegex(DadosInvalidos, "mais de um item com o título"):
            validar_lote_quizzes(json.dumps([self.quiz, repetido]))

        self.oficina["questoes"].pop()
        with self.assertRaisesRegex(DadosInvalidos, "Item 2 do lote.*pelo menos dois trechos"):
            validar_lote_quizzes(json.dumps([self.quiz, self.oficina]))
