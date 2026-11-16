import unittest

from safeclick.pistas_simulacao import separar_pistas


class PistasSimulacaoTeste(unittest.TestCase):
    def test_marcacoes_reconhecidas(self):
        textos, marcas = separar_pistas([
            "[remetente] Número desconhecido.",
            "[Parágrafo 2] Pressão para pagar.",
            "[botão] Link enviado na mensagem.",
            "[paragrafo 2] Valor pequeno.",
        ])
        self.assertEqual(textos, ["Número desconhecido.", "Pressão para pagar.", "Link enviado na mensagem.", "Valor pequeno."])
        self.assertEqual(marcas, {"origem": [1], "paragrafo-2": [2, 4], "chamada": [3]})

    def test_sem_marcacao_ou_marcacao_desconhecida_fica_como_texto(self):
        textos, marcas = separar_pistas(["Urgência.", "[rodapé] Texto pequeno.", "[assunto]"])
        self.assertEqual(textos, ["Urgência.", "[rodapé] Texto pequeno.", "[assunto]"])
        self.assertEqual(marcas, {})

    def test_aceita_texto_com_quebras_de_linha(self):
        textos, marcas = separar_pistas("[assunto] Ameaça.\n\nPrazo curto.")
        self.assertEqual(textos, ["Ameaça.", "Prazo curto."])
        self.assertEqual(marcas, {"assunto": [1]})


if __name__ == "__main__":
    unittest.main()
