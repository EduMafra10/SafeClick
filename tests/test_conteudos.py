import os
import unittest
from html.parser import HTMLParser
from unittest.mock import MagicMock, patch

from psycopg import Error

from safeclick import create_app
from safeclick.auditoria_db import EVENTOS_PERMITIDOS
from safeclick.conteudos_db import concluir_conteudo
from safeclick.sessoes import Usuario


CONTEUDO = {
    "id": 1, "slug": "phishing", "titulo": "Phishing",
    "texto": "<p>Texto do conteúdo.</p>", "concluido_em": None,
}


class CamposHTML(HTMLParser):
    def __init__(self, resposta):
        super().__init__()
        self.campos = {}
        self.feed(resposta.get_data(as_text=True))

    def handle_starttag(self, tag, atributos):
        atributos = dict(atributos)
        if tag == "input":
            self.campos[atributos.get("name")] = atributos


class ConcluirConteudoBancoTeste(unittest.TestCase):
    """Testa a gravação da conclusão sem acessar o banco real."""

    def setUp(self):
        self.conexao = MagicMock()
        contexto = MagicMock()
        contexto.__enter__.return_value = self.conexao
        abrir = patch("safeclick.conteudos_db.conectar_banco", return_value=contexto)
        abrir.start()
        self.addCleanup(abrir.stop)
        registrar = patch("safeclick.conteudos_db.registrar_evento")
        self.registrar = registrar.start()
        self.addCleanup(registrar.stop)

    def responder(self, conteudo, insercao=None):
        busca = MagicMock()
        busca.fetchone.return_value = conteudo
        gravacao = MagicMock()
        gravacao.fetchone.return_value = insercao
        self.conexao.execute.side_effect = [busca, gravacao]

    def test_primeira_conclusao_grava_e_audita(self):
        self.responder({"id": 1}, {"conteudo_id": 1})

        self.assertIs(concluir_conteudo(7, "phishing"), True)

        insercao = self.conexao.execute.call_args_list[1]
        self.assertIn("ON CONFLICT (usuario_id, conteudo_id) DO NOTHING", insercao.args[0])
        self.assertEqual(insercao.args[1], (7, 1))
        self.registrar.assert_called_once_with(
            usuario_id=7, evento="conteudo.concluido", resultado="sucesso",
            recurso_tipo="conteudo", recurso_id=1, conexao=self.conexao,
        )

    def test_concluir_de_novo_nao_duplica_nem_audita(self):
        self.responder({"id": 1}, None)

        self.assertIs(concluir_conteudo(7, "phishing"), False)
        self.registrar.assert_not_called()

    def test_conteudo_inexistente(self):
        self.responder(None)

        self.assertIsNone(concluir_conteudo(7, "nao-existe"))
        self.assertEqual(self.conexao.execute.call_count, 1)
        self.registrar.assert_not_called()

    def test_evento_esta_liberado_na_auditoria(self):
        self.assertIn("conteudo.concluido", EVENTOS_PERMITIDOS)


class RotasConteudosTeste(unittest.TestCase):
    """Testa as páginas de conteúdo e o botão de conclusão."""

    def substituir(self, substituicao):
        resultado = substituicao.start()
        self.addCleanup(substituicao.stop)
        return resultado

    def setUp(self):
        self.substituir(patch.dict(os.environ, {
            "SECRET_KEY": "chave-exclusiva-dos-testes",
            "DATABASE_URL": "postgresql://nao-usado",
        }, clear=True))
        for alvo in ("psycopg.connect", "socket.socket.connect"):
            self.substituir(patch(alvo, side_effect=AssertionError("Acesso externo nos testes")))
        self.app = create_app()
        self.app.config.update(TESTING=True, WTF_CSRF_ENABLED=True)
        self.client = self.app.test_client()
        self.substituir(patch(
            "safeclick.aceite_termos.usuario_aceitou_termos_atuais", return_value=True
        ))
        self.buscar = self.substituir(patch(
            "safeclick.conteudos_db.buscar_conteudos", return_value=dict(CONTEUDO)
        ))
        self.listar = self.substituir(patch(
            "safeclick.conteudos_db.listar_conteudos",
            return_value=[
                {"id": 1, "slug": "phishing", "titulo": "Phishing", "concluido": True},
                {"id": 2, "slug": "senhas", "titulo": "Proteção de Senhas", "concluido": False},
            ],
        ))
        self.concluir = self.substituir(patch(
            "safeclick.conteudos_db.concluir_conteudo", return_value=True
        ))
        usuario = Usuario({
            "id": 7, "nome": "Pessoa Teste",
            "email": "pessoa@example.com", "perfil": "usuario",
        })
        self.substituir(patch.object(
            self.app.login_manager, "_user_callback", return_value=usuario
        ))
        with self.client.session_transaction() as sessao:
            sessao["_user_id"] = "7"
            sessao["_fresh"] = True

    def token(self):
        resposta = self.client.get("/conteudos/phishing")
        self.assertEqual(resposta.status_code, 200)
        return CamposHTML(resposta).campos["csrf_token"]["value"]

    def test_conteudo_nao_concluido_mostra_o_botao(self):
        html = self.client.get("/conteudos/phishing").get_data(as_text=True)
        self.assertIn("Marcar como concluído", html)
        self.assertIn('action="/conteudos/phishing/concluir"', html)

    def test_navegacao_da_leitura_independe_da_conclusao(self):
        self.buscar.return_value = dict(CONTEUDO, proxima_referencia="senhas")
        html = self.client.get("/conteudos/phishing").text
        self.assertIn('href="/conteudos/senhas">Próximo conteúdo', html)
        self.assertIn('href="/conteudos/">Ver todos os conteúdos', html)
        self.concluir.assert_not_called()

        html_editorial = self.client.get("/paginas/phishing").text
        self.assertNotIn("Próximo conteúdo", html_editorial)

    def test_conteudo_concluido_mostra_a_data(self):
        self.buscar.return_value = dict(CONTEUDO, concluido_em="04/11/2026")
        html = self.client.get("/conteudos/phishing").get_data(as_text=True)
        self.assertIn("Você concluiu este conteúdo em 04/11/2026.", html)
        self.assertNotIn("Marcar como concluído", html)

    def test_lista_indica_conteudos_concluidos(self):
        html = self.client.get("/conteudos/").get_data(as_text=True)
        self.assertEqual(html.count("✓ Concluído"), 1)
        self.assertIn("Ler novamente →", html)

    def test_concluir_registra_para_o_usuario_da_sessao(self):
        resposta = self.client.post(
            "/conteudos/phishing/concluir",
            data={"csrf_token": self.token(), "usuario_id": "999"},
        )
        self.assertEqual(resposta.status_code, 303)
        self.assertEqual(resposta.location, "/conteudos/phishing")
        self.concluir.assert_called_once_with(7, "phishing")

    def test_concluir_sem_csrf_e_recusado(self):
        resposta = self.client.post("/conteudos/phishing/concluir")
        self.assertEqual(resposta.status_code, 400)
        self.concluir.assert_not_called()

    def test_concluir_por_get_nao_e_permitido(self):
        self.assertEqual(self.client.get("/conteudos/phishing/concluir").status_code, 405)
        self.concluir.assert_not_called()

    def test_concluir_conteudo_inexistente(self):
        self.concluir.return_value = None
        resposta = self.client.post(
            "/conteudos/nao-existe/concluir", data={"csrf_token": self.token()}
        )
        self.assertEqual(resposta.status_code, 404)

    def test_falha_no_banco_ao_concluir(self):
        self.concluir.side_effect = Error("falha simulada")
        resposta = self.client.post(
            "/conteudos/phishing/concluir", data={"csrf_token": self.token()}
        )
        self.assertEqual(resposta.status_code, 503)

    def test_concluir_exige_login(self):
        with self.client.session_transaction() as sessao:
            sessao.clear()
        resposta = self.client.post("/conteudos/phishing/concluir")
        self.assertEqual(resposta.status_code, 302)
        self.assertTrue(resposta.location.startswith("/login"))
        self.concluir.assert_not_called()


if __name__ == "__main__":
    unittest.main()
