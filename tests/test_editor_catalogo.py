import json
import os
import re
import unittest
from unittest.mock import patch

from psycopg import OperationalError

from safeclick import create_app
from safeclick.catalogo_admin_db import EdicaoConflitante, salvar_rascunho
from safeclick.sessoes import Usuario
from safeclick.texto_formatado import html_do_texto, texto_do_html


CONTEUDO_PUBLICADO = """<h3>Como identificar</h3>
<p>O golpe chega por <em>SMS</em> ou e-mail.</p>
<ul>
<li><strong>Urgência:</strong> "sua conta será bloqueada".</li>
<li>Link estranho.</li>
</ul>
<p class="conteudos-pratique"><strong>Pratique:</strong> <a href="/simulacoes/entrega-sms">simulação da entrega</a></p>
<p class="conteudos-fonte">Fontes: Cartilha de Segurança para Internet (CERT.br).</p>"""


def sem_espacos(html):
    return re.sub(r">\s+<", "><", html).strip()


class TextoFormatadoTeste(unittest.TestCase):
    def test_marcacoes_viram_o_html_dos_conteudos(self):
        html = html_do_texto(
            "Primeiro parágrafo\ncom quebra.\n\n## Como se proteger\n- **Confira** o remetente\n- Não clique\n\n"
            "> **Pratique:** [simulação](/simulacoes/loja-falsa)\n\nFontes: CERT.br."
        )
        self.assertEqual(sem_espacos(html), sem_espacos(
            "<p>Primeiro parágrafo<br>\ncom quebra.</p>\n<h3>Como se proteger</h3>\n"
            "<ul>\n<li><strong>Confira</strong> o remetente</li>\n<li>Não clique</li>\n</ul>\n"
            '<p class="conteudos-pratique"><strong>Pratique:</strong> <a href="/simulacoes/loja-falsa">simulação</a></p>\n'
            '<p class="conteudos-fonte">Fontes: CERT.br.</p>'
        ))

    def test_conteudo_publicado_volta_igual_depois_de_editado(self):
        texto = texto_do_html(CONTEUDO_PUBLICADO)
        self.assertIn("## Como identificar", texto)
        self.assertIn("- **Urgência:** \"sua conta será bloqueada\".", texto)
        self.assertIn("> **Pratique:** [simulação da entrega](/simulacoes/entrega-sms)", texto)
        self.assertIn("*SMS*", texto)
        self.assertEqual(sem_espacos(html_do_texto(texto)), sem_espacos(CONTEUDO_PUBLICADO))

    def test_html_digitado_e_links_perigosos_nao_viram_tags(self):
        html = html_do_texto('<script>alert(1)</script>\n\n[a](javascript:alert(1)) [b](//fora.example) [c](/ok" onclick="x)')
        self.assertNotIn("<script", html)
        self.assertNotIn("<a ", html)
        self.assertIn("&lt;script&gt;", html)
        self.assertEqual(html_do_texto("[site](https://cert.br/?a=1&b=2)"),
                         '<p><a href="https://cert.br/?a=1&amp;b=2">site</a></p>')
        self.assertEqual(texto_do_html('<p><a href="javascript:x">aqui</a></p>'), "aqui")

    def test_texto_simples_continua_em_paragrafos(self):
        self.assertEqual(html_do_texto("Um.\n\n\nDois -- três * quatro"), "<p>Um.</p>\n<p>Dois -- três * quatro</p>")


class EditorCatalogoTeste(unittest.TestCase):
    def substituir(self, alvo, **argumentos):
        substituicao = patch(alvo, **argumentos)
        valor = substituicao.start()
        self.addCleanup(substituicao.stop)
        return valor

    def setUp(self):
        with patch.dict(os.environ, {"SECRET_KEY": "chave-de-teste", "DATABASE_URL": "postgresql://nao-usado"}):
            self.app = create_app()
        self.app.config.update(TESTING=True, WTF_CSRF_ENABLED=True)
        self.client = self.app.test_client()
        self.substituir("psycopg.connect", side_effect=AssertionError("Banco real proibido"))
        usuario = Usuario({"id": 7, "nome": "Admin", "email": "admin@example.test", "perfil": "administrador"})
        self.substituir("safeclick.aceite_termos.usuario_aceitou_termos_atuais", return_value=True)
        self.substituir("safeclick.sessoes.registrar_evento")
        carregar = patch.object(self.app.login_manager, "_user_callback", return_value=usuario)
        carregar.start()
        self.addCleanup(carregar.stop)
        with self.client.session_transaction() as sessao:
            sessao["_user_id"] = "7"
            sessao["_fresh"] = True
        self.obter = self.substituir("safeclick.catalogo_admin.db.obter_item")
        self.salvar = self.substituir("safeclick.catalogo_admin.db.salvar_rascunho", return_value=30)

    def item(self, dados, **alteracoes):
        item = {"id": 30, "revisao": 2, "estado": "rascunho", "slug": "golpe-qr", "versao": None,
                "rascunho": dados, "dados": dados, "texto": "", "titulo_publicado": None}
        item.update(alteracoes)
        return item

    def test_novo_item_tem_lateral_e_blocos_em_todas_as_secoes(self):
        marcas = {
            "conteudos": ('data-formato="subtitulo"', 'name="slug"', "/conteudos/"),
            "paginas": ('data-formato="lista"', 'name="slug"', "/paginas/"),
            "quizzes": ('name="formato" value="oficina"', 'data-lista="questao"', "Uma resposta correta em cada pergunta"),
            "simulacoes": ('name="tipo" value="sms"', "Onde o golpe chega", "Uma escolha segura e uma de risco"),
        }
        for secao, textos in marcas.items():
            with self.subTest(secao=secao):
                resposta = self.client.get(f"/administracao/catalogo/{secao}/novo")
                html = resposta.get_data(as_text=True)
                self.assertEqual(resposta.status_code, 200)
                for texto in ("Antes de publicar", 'form="editor-catalogo"', "Salve o rascunho para ver a prévia", *textos):
                    self.assertIn(texto, html)
                self.assertNotIn("Ver como o usuário vai ver", html)

    def test_item_salvo_mostra_previa_e_publicacao(self):
        self.obter.return_value = self.item({"titulo": "Golpe do QR", "corpo": "## Cuidado"})
        html = self.client.get("/administracao/catalogo/conteudos/30/editar").get_data(as_text=True)
        self.assertIn('href="/administracao/catalogo/conteudos/30/previa">Ver como o usuário vai ver', html)
        self.assertIn('href="/administracao/catalogo/conteudos/30/publicar">Publicar', html)
        self.assertIn("/conteudos/<b>golpe-qr</b>", html)
        self.assertIn("## Cuidado", html)

    def formulario_quiz(self, rota="/administracao/catalogo/quizzes/novo", **campos):
        html = self.client.get(rota).text
        token = re.search(r'name="csrf_token" type="hidden" value="([^"]+)"', html)[1]
        return dict(csrf_token=token, titulo="Oficina de contas", formato="oficina", estrutura="[]") | campos

    def test_editor_preserva_titulo_e_formato_quando_a_estrutura_e_invalida(self):
        rota = "/administracao/catalogo/quizzes/novo"
        for estrutura in ("", "{}", "JSON incompleto"):
            with self.subTest(estrutura=estrutura):
                resposta = self.client.post(rota, data=self.formulario_quiz(estrutura=estrutura))
                self.assertEqual(resposta.status_code, 400)
                self.assertIn('value="Oficina de contas"', resposta.text)
                self.assertRegex(resposta.text, r'name="formato" value="oficina"\s+checked')
        self.salvar.assert_not_called()

    def test_dados_invalidos_impedem_gravacao_antes_de_abrir_conexao(self):
        self.salvar.side_effect = salvar_rascunho
        rota = "/administracao/catalogo/quizzes/novo"
        for campos, mensagem in (
            ({"titulo": "   "}, "Título"),
            ({"formato": "desconhecido"}, "formato de quiz"),
            ({"estrutura": json.dumps([{}] * 21)}, "máximo 20"),
            ({"estrutura": json.dumps([{"alternativas": [{}] * 9}])}, "máximo 8"),
            ({"estrutura": "[null]"}, "item"),
        ):
            with self.subTest(campos=campos):
                resposta = self.client.post(rota, data=self.formulario_quiz(**campos))
                self.assertEqual(resposta.status_code, 400)
                self.assertIn(mensagem, resposta.text)

    def test_erro_de_conexao_permite_recuperar_o_rascunho_digitado(self):
        self.salvar.side_effect = OperationalError("detalhes internos")
        campos = self.formulario_quiz(estrutura=json.dumps([{"enunciado": "Trecho digitado"}]))
        resposta = self.client.post("/administracao/catalogo/quizzes/novo", data=campos)
        self.assertEqual(resposta.status_code, 503)
        self.assertIn("Confira a lista", resposta.text)
        self.assertIn("Trecho digitado", resposta.text)
        self.assertNotIn("detalhes internos", resposta.text)

    def test_conflito_de_publicacao_exige_revisar_o_item_antes_de_reconfirmar(self):
        dados = {"titulo": "Quiz de contas", "questoes": []}
        self.obter.return_value = self.item(dados)
        rota = "/administracao/catalogo/quizzes/30/publicar"
        campos = self.formulario_quiz(rota)
        with patch("safeclick.catalogo_admin.db.alterar_publicacao", side_effect=EdicaoConflitante("O item mudou.")):
            resposta = self.client.post(rota, data={"csrf_token": campos["csrf_token"], "revisao": "1"})
        self.assertEqual(resposta.status_code, 409)
        self.assertRegex(resposta.text, r'<button class="admin-botao" type="submit"\s+disabled')
        self.assertIn("/administracao/catalogo/quizzes/30/editar", resposta.text)

    def test_simulacao_salva_com_o_formato_escolhido_no_cartao(self):
        pagina = self.client.get("/administracao/catalogo/simulacoes/novo").get_data(as_text=True)
        token = re.search(r'name="csrf_token" type="hidden" value="([^"]+)"', pagina).group(1)
        campos = {nome: "" for nome in ("titulo", "resumo", "assunto", "origem", "mensagem", "chamada", "sinais",
                                        "produto_nome", "produto_preco_anterior", "produto_preco_atual")}
        campos.update(csrf_token=token, titulo="Falsa entrega", slug="falsa-entrega", tipo="sms", estrutura="[]")
        resposta = self.client.post("/administracao/catalogo/simulacoes/novo", data=campos)
        self.assertEqual(resposta.status_code, 303)
        self.assertEqual(self.salvar.call_args.args[2]["tipo"], "sms")
        self.assertEqual(self.salvar.call_args.kwargs["slug"], "falsa-entrega")

    def test_previa_do_conteudo_usa_o_layout_do_site(self):
        self.obter.return_value = self.item({"titulo": "Golpe do QR", "corpo": "## Como se proteger\n- Confira o nome"})
        html = self.client.get("/administracao/catalogo/conteudos/30/previa").get_data(as_text=True)
        self.assertIn("css/conteudos_visual.css", html)
        self.assertIn('class="ct-artigo"', html)
        self.assertIn("<h2>Como se proteger</h2>", html)
        self.assertIn("<li>Confira o nome</li>", html)

    def test_previa_da_simulacao_mostra_mensagem_e_resultados(self):
        dados = {
            "titulo": "Falsa entrega", "tipo": "sms", "canal": "SMS fictício", "assunto": "Encomenda retida",
            "origem": "+55 11 0000-0000", "mensagem": ["Pague a taxa."], "chamada": "", "sinais": ["Urgência"],
            "opcoes": {"opcao_1": {"texto": "Pagar", "consequencia": "Perdeu.", "explicacao": "É golpe.", "segura": False},
                       "opcao_2": {"texto": "Conferir", "consequencia": "Evitou.", "explicacao": "Canal oficial.", "segura": True}},
            "ordem_opcoes": ["opcao_1", "opcao_2"],
        }
        self.obter.return_value = self.item(dados, slug="falsa-entrega")
        html = self.client.get("/administracao/catalogo/simulacoes/30/previa").get_data(as_text=True)
        for texto in ("css/simulacao.css", "simulacao-mensagem mensagem--entrega-sms", "Encomenda retida",
                      "Depois da escolha", "Escolha de risco", "Escolha segura", "Urgência"):
            self.assertIn(texto, html)
        self.assertNotIn('class="mensagem-chamada"', html)

    def test_previa_do_quiz_destaca_a_resposta_correta(self):
        dados = {"titulo": "Senhas", "formato": "perguntas", "questoes": [{
            "enunciado": "Qual senha é melhor?", "explicacao": "Longa e única.",
            "alternativas": [{"texto": "123456", "correta": False}, {"texto": "Frase longa", "correta": True}],
        }]}
        self.obter.return_value = self.item(dados)
        html = self.client.get("/administracao/catalogo/quizzes/30/previa").get_data(as_text=True)
        self.assertIn("css/quizzes_visual.css", html)
        self.assertIn("Pergunta 1 de 1", html)
        self.assertRegex(html, r'admin-previa-correta">\s*<input type="radio">\s*'
                               r'<span class="qz-letra" aria-hidden="true">B</span>\s*<span>Frase longa')

    def test_oficina_tem_regra_ajuda_e_previa_propria(self):
        html = self.client.get("/administracao/catalogo/quizzes/novo").get_data(as_text=True)
        self.assertIn('data-regra="oficina" hidden', html)
        self.assertIn("data-repetir-cartoes", html)
        cartoes = [{"texto": "Frase longa", "correta": True}, {"texto": "Duas etapas", "correta": False}]
        dados = {"titulo": "Guia", "formato": "oficina", "questoes": [
            {"enunciado": "Trecho A", "explicacao": "", "alternativas": cartoes},
            {"enunciado": "Trecho B", "explicacao": "", "alternativas": [dict(c, correta=not c["correta"]) for c in cartoes]},
        ]}
        self.obter.return_value = self.item(dados)
        html = self.client.get("/administracao/catalogo/quizzes/30/previa").get_data(as_text=True)
        self.assertIn("Cartões do guia", html)
        self.assertIn("Trecho 2 de 2", html)
        self.assertIn("<strong>Cartão correto:</strong> Duas etapas", html)


if __name__ == "__main__":
    unittest.main()
