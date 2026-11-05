

import os
import unittest
from html.parser import HTMLParser
from pathlib import Path
from unittest.mock import patch

from psycopg import Error

from safeclick import create_app
from safeclick.sessoes import Usuario

PAGINA = "/laboratorio-senhas/"


class ElementosHTML(HTMLParser):
    

    def __init__(self, html):
        super().__init__()
        self.por_id = {}
        self.todos = []
        self.feed(html)

    def handle_starttag(self, tag, atributos):
        atributos = dict(atributos, tag=tag)
        self.todos.append(atributos)
        if atributos.get("id"):
            self.por_id[atributos["id"]] = atributos


class LaboratorioSenhasTeste(unittest.TestCase):
    def substituir(self, substituicao):
        resultado = substituicao.start()
        self.addCleanup(substituicao.stop)
        return resultado

    def setUp(self):
        self.substituir(patch.dict(os.environ, {
            "SECRET_KEY": "chave-ficticia-dos-testes",
            "DATABASE_URL": "postgresql://nao-usado",
            "FLASK_SKIP_DOTENV": "1",
        }, clear=True))
        for alvo in (
            "psycopg.connect", "socket.socket.connect",
            "socket.create_connection", "requests.sessions.Session.request",
        ):
            self.substituir(patch(
                alvo, side_effect=AssertionError("Acesso externo proibido no teste")
            ))

        self.app = create_app()
        self.app.config.update(TESTING=True, WTF_CSRF_ENABLED=True)
        self.cliente = self.app.test_client()
        self.usuario = Usuario({
            "id": 7, "nome": "Pessoa Teste",
            "email": "pessoa@example.com", "perfil": "usuario",
        })
        self.substituir(patch.object(
            self.app.login_manager, "_user_callback", return_value=self.usuario
        ))
        self.aceitou = self.substituir(patch(
            "safeclick.aceite_termos.usuario_aceitou_termos_atuais",
            return_value=True,
        ))
        self.contar = self.substituir(patch("safeclick.senhas.contar_vazamentos"))
        self.substituir(patch("safeclick.sessoes.registrar_evento"))

        with self.cliente.session_transaction() as sessao:
            sessao["_user_id"] = "7"
            sessao["_fresh"] = True

    def abrir(self):
        resposta = self.cliente.get(PAGINA)
        self.assertEqual(resposta.status_code, 200)
        html = resposta.get_data(as_text=True)
        return resposta, html, ElementosHTML(html)

    def test_pagina_tem_as_tres_ferramentas(self):
        _, html, elementos = self.abrir()
        for painel in ("painel-analisador", "painel-gerador", "painel-desafio"):
            with self.subTest(painel=painel):
                self.assertEqual(elementos.por_id[painel]["role"], "tabpanel")
        for texto in ("Analisador", "Gerador", "Qual vazou mais?", "laboratorio.js",
                      "palavras_senha.js", "gerador_senhas.js", "desafio_senhas.js"):
            with self.subTest(texto=texto):
                self.assertIn(texto, html)

    def test_sem_javascript_abas_ocultas_e_paineis_visiveis(self):
        # Sem JavaScript, a pessoa vê os três painéis em sequência (nada some).
        _, _, elementos = self.abrir()
        [lista_abas] = [e for e in elementos.todos if e.get("role") == "tablist"]
        self.assertIn("hidden", lista_abas)
        for painel in ("painel-analisador", "painel-gerador", "painel-desafio"):
            with self.subTest(painel=painel):
                self.assertNotIn("hidden", elementos.por_id[painel])

    def test_campo_do_analisador_nunca_e_enviado_ao_servidor(self):
        _, html, elementos = self.abrir()
        campo = elementos.por_id["senha-analise"]
        # Sem "name" e fora de <form>: o navegador não tem como enviar o campo.
        self.assertNotIn("name", campo)
        self.assertEqual(campo["type"], "password")
        self.assertEqual(campo["autocomplete"], "off")
        # O único <form> da página é o "Sair" do cabeçalho; o laboratório não tem nenhum.
        conteudo = html[html.index("<main"):html.index("</main>")]
        self.assertNotIn("<form", conteudo)
        self.assertIn("forca_senha_worker.js", html)

    def test_pagina_entrega_token_csrf_do_desafio(self):
        _, _, elementos = self.abrir()
        token = elementos.por_id["csrf-desafio"]
        self.assertEqual(token["name"], "csrf_token")
        self.assertTrue(token["value"])
        self.assertEqual(
            elementos.por_id["painel-desafio"]["data-iniciar-url"],
            "/laboratorio-senhas/desafio/iniciar",
        )

    def test_abrir_a_pagina_nao_consulta_a_api(self):
        self.abrir()
        self.contar.assert_not_called()

    def test_cabecalhos_de_protecao(self):
        resposta, _, _ = self.abrir()
        self.assertEqual(resposta.headers["Cache-Control"], "no-store")
        self.assertEqual(resposta.headers["Referrer-Policy"], "no-referrer")
        self.assertEqual(resposta.headers["X-Content-Type-Options"], "nosniff")

    def test_menu_mostra_laboratorio(self):
        _, html, _ = self.abrir()
        self.assertIn(f'href="{PAGINA}"', html)
        self.assertIn("Laboratório", html)

    def test_enderecos_antigos_nao_existem_mais(self):
        for endereco in ("/verificar-senha/", "/laboratorio-senhas/consultar"):
            with self.subTest(endereco=endereco):
                self.assertEqual(self.cliente.get(endereco).status_code, 404)
        self.assertEqual(
            self.cliente.post("/laboratorio-senhas/consultar").status_code, 404
        )

    def test_exige_login_completo(self):
        for pendente in (False, True):
            with self.subTest(login_pendente=pendente):
                with self.cliente.session_transaction() as sessao:
                    sessao.clear()
                    if pendente:
                        sessao["login_pendente"] = "x" * 43
                resposta = self.cliente.get(PAGINA)
                self.assertEqual(resposta.status_code, 302)
                self.assertTrue(resposta.location.startswith("/login"))

    def test_exige_aceite_atual_dos_termos(self):
        self.aceitou.return_value = False
        resposta = self.cliente.get(PAGINA)
        self.assertEqual(resposta.status_code, 303)
        self.assertEqual(resposta.location, "/aceitar-termos")

    def test_falha_ao_verificar_termos_impede_acesso(self):
        self.aceitou.side_effect = Error("detalhe-interno")
        resposta = self.cliente.get(PAGINA)
        self.assertEqual(resposta.status_code, 503)
        self.assertNotIn("detalhe-interno", resposta.get_data(as_text=True))

    def test_rejeita_perfil_nao_permitido(self):
        self.usuario.perfil = "outro"
        self.assertEqual(self.cliente.get(PAGINA).status_code, 403)

    def test_administrador_tambem_acessa(self):
        self.usuario.perfil = "administrador"
        self.assertEqual(self.cliente.get(PAGINA).status_code, 200)


class ListaPalavrasTeste(unittest.TestCase):
    """Confere a lista usada pelo gerador de frase-senha."""

    def test_lista_tem_palavras_suficientes_e_simples(self):
        caminho = Path(__file__).resolve().parents[1] / "safeclick/static/js/palavras_senha.js"
        texto = caminho.read_text(encoding="utf-8")
        bloco = texto[texto.index("`") + 1:texto.rindex("`")]
        palavras = bloco.split()

        # Sem repetidas: repetir palavras diminuiria as combinações possíveis.
        self.assertEqual(len(palavras), len(set(palavras)))
        # Cada palavra sorteada soma log2(700) ≈ 9,5 bits de aleatoriedade.
        self.assertGreaterEqual(len(palavras), 700)
        # Só letras minúsculas sem acento: digitável em qualquer teclado.
        for palavra in palavras:
            with self.subTest(palavra=palavra):
                self.assertRegex(palavra, r"\A[a-z]{3,11}\Z")


if __name__ == "__main__":
    unittest.main()