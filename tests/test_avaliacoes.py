import os
import re
import unittest
from contextlib import nullcontext
from decimal import Decimal
from unittest.mock import patch

from psycopg import Error

from safeclick import create_app
from safeclick.sessoes import Usuario


class AvaliacoesTeste(unittest.TestCase):
    def setUp(self):
        ambiente = patch.dict(os.environ, {"SECRET_KEY": "chave-exclusiva-dos-testes"}, clear=True)
        ambiente.start()
        self.addCleanup(ambiente.stop)
        self.substituir("psycopg.connect", side_effect=AssertionError("Banco real proibido"))
        self.app = create_app()
        self.app.config.update(TESTING=True, AVALIACOES_ATIVAS=True)
        self.cliente = self.app.test_client()
        self.usuario = Usuario({"id": 7, "nome": "Pessoa", "email": "pessoa@example.test", "perfil": "usuario"})
        self.substituir(self.app.login_manager, self.usuario, atributo="_user_callback")
        self.substituir("safeclick.aceite_termos.usuario_aceitou_termos_atuais", return_value=True)
        self.substituir("safeclick.sessoes.registrar_evento")
        with self.cliente.session_transaction() as sessao:
            sessao["_user_id"] = "7"
            sessao["_fresh"] = True
        self.conexao = object()
        self.abrir = self.substituir("safeclick.avaliacoes.conectar_banco", return_value=nullcontext(self.conexao))
        self.buscar = self.substituir(
            "safeclick.avaliacoes.buscar_atividade",
            return_value={
                "id": 42, "titulo": "Aprender", "nota": None,
                "comentario": None, "proxima_referencia": None,
            },
        )
        self.salvar = self.substituir("safeclick.avaliacoes.salvar_avaliacao")
        self.rota = "/avaliacoes/conteudos/aprender"

    def substituir(self, alvo, valor=None, *, atributo=None, **kwargs):
        if atributo:
            ajuste = patch.object(alvo, atributo, return_value=valor)
        else:
            ajuste = patch(alvo, **kwargs)
        resultado = ajuste.start()
        self.addCleanup(ajuste.stop)
        return resultado

    def csrf(self):
        html = self.cliente.get(self.rota).text
        return re.search(r'name="csrf_token"[^>]+value="([^"]+)"', html)[1]

    def test_salva_para_a_conta_da_sessao_e_aceita_ausencia_de_comentario(self):
        resposta = self.cliente.post(self.rota, data={"nota": "4", "csrf_token": self.csrf()})
        self.assertEqual(resposta.status_code, 303)
        self.buscar.assert_called_with(self.conexao, "conteudo", 7, "aprender", bloquear=True)
        self.salvar.assert_called_once_with(self.conexao, "conteudo", 7, 42, 4, None)

    def test_aceita_500_caracteres(self):
        resposta = self.cliente.post(self.rota, data={
            "nota": "5", "comentario": "á" * 500, "csrf_token": self.csrf(),
        })
        self.assertEqual(resposta.status_code, 303)
        self.salvar.assert_called_once_with(self.conexao, "conteudo", 7, 42, 5, "á" * 500)

    def test_navegacao_entre_atividades_sem_enviar_avaliacao(self):
        for rota, referencia, destino, lista, rotulo, rotulo_lista in (
            (self.rota, "revisar", "/conteudos/revisar", "/conteudos/", "Próximo conteúdo", "Ver todos os conteúdos"),
            ("/avaliacoes/quizzes/19", 43, "/quizzes/43", "/quizzes/", "Próximo quiz", "Ver todos os quizzes"),
        ):
            with self.subTest(rota=rota):
                self.buscar.return_value["proxima_referencia"] = referencia
                resposta = self.cliente.get(rota)
                self.assertEqual(resposta.status_code, 200)
                navegacao = re.search(
                    r'</form>\s*<nav[^>]+aria-label="Próximas atividades"[^>]*>(.*?)</nav>',
                    resposta.text, re.DOTALL,
                )
                self.assertIsNotNone(navegacao)
                navegacao = navegacao[1]
                self.assertIn(f'href="{destino}">{rotulo}', navegacao)
                self.assertIn(f'href="{lista}">{rotulo_lista}', navegacao)

                self.buscar.return_value["proxima_referencia"] = None
                ultima = self.cliente.get(rota)
                self.assertNotIn(rotulo, ultima.text)
                self.assertIn(f'href="{lista}">{rotulo_lista}', ultima.text)
        self.salvar.assert_not_called()

    def test_entradas_invalidas_e_adulteradas_nao_gravam(self):
        token = self.csrf()
        for dados in (
            {"nota": "0"}, {"nota": "6"}, {"nota": "2.5"}, {"nota": ""},
            {"nota": ["1", "2"]}, {"nota": "5", "comentario": "x" * 501},
            {"nota": "5", "comentario": "\x00"}, {"nota": "5", "usuario_id": "8"},
        ):
            with self.subTest(dados=dados):
                resposta = self.cliente.post(self.rota, data=dados | {"csrf_token": token})
                self.assertEqual(resposta.status_code, 400)
        self.assertEqual(self.cliente.post(self.rota, data={"nota": "5"}).status_code, 400)
        self.salvar.assert_not_called()

    def test_sem_conclusao_da_propria_conta(self):
        token = self.csrf()
        self.buscar.return_value = None
        for rota in (self.rota, "/avaliacoes/quizzes/19"):
            self.assertEqual(self.cliente.post(rota, data={"nota": "5", "csrf_token": token}).status_code, 404)
        self.salvar.assert_not_called()

    def test_edita_avaliacao_do_quiz_por_item_do_catalogo_e_limpa_comentario(self):
        self.rota = "/avaliacoes/quizzes/19"
        self.buscar.return_value.update(nota=4, comentario="<script>privado</script>")
        pagina = self.cliente.get(self.rota)
        self.assertEqual(pagina.status_code, 200)
        self.assertIn('href="/quizzes/resultado/19"', pagina.text)
        self.assertIn("Atualizar avaliação", pagina.text)
        self.assertIn("&lt;script&gt;privado&lt;/script&gt;", pagina.text)
        self.assertNotIn("<script>privado</script>", pagina.text)

        resposta = self.cliente.post(self.rota, data={
            "nota": "5", "comentario": "  ", "csrf_token": self.csrf(),
        })

        self.assertEqual(resposta.status_code, 303)
        self.assertEqual(resposta.location, self.rota)
        self.buscar.assert_called_with(self.conexao, "quiz", 7, 19, bloquear=True)
        self.salvar.assert_called_once_with(self.conexao, "quiz", 7, 42, 5, None)
        self.assertIn("Avaliação salva", self.cliente.get(resposta.location).text)

    def test_erro_no_banco_retorna_mensagem_sem_detalhes_privados(self):
        self.salvar.side_effect = Error("detalhe privado do banco")
        resposta = self.cliente.post(self.rota, data={"nota": "4", "csrf_token": self.csrf()})

        self.assertEqual(resposta.status_code, 503)
        self.assertIn("Não foi possível acessar a avaliação agora", resposta.text)
        self.assertNotIn("detalhe privado do banco", resposta.text)

    def test_painel_mostra_apenas_resumo_e_sinaliza_dados_insuficientes(self):
        self.usuario.perfil = "administrador"
        resumo = self.substituir("safeclick.administracao.listar_resumo_avaliacoes", return_value=[
            {"tipo": "Conteúdo", "titulo": "Aprender", "total": None, "media": None,
             "comentario": "Comentário privado", "usuario_id": 7},
            {"tipo": "Quiz", "titulo": "Revisar", "total": 5, "media": Decimal("4.6")},
        ])
        resposta = self.cliente.get("/administracao/avaliacoes")

        self.assertEqual(resposta.status_code, 200)
        for texto in ("Aprender", "Dados insuficientes", "Revisar", "4,6 de 5", "5 avaliações"):
            self.assertIn(texto, resposta.text)
        self.assertNotIn("Comentário privado", resposta.text)
        resumo.assert_called_once_with()

    def test_agregados_restritos_e_desativacao_fecha_as_rotas(self):
        resumo = self.substituir("safeclick.administracao.listar_resumo_avaliacoes", return_value=[])
        self.assertEqual(self.cliente.get("/administracao/avaliacoes").status_code, 403)
        resumo.assert_not_called()
        self.usuario.perfil = "administrador"
        self.assertEqual(self.cliente.get("/administracao/avaliacoes").status_code, 200)
        self.app.config["AVALIACOES_ATIVAS"] = False
        self.assertEqual(self.cliente.get("/administracao/avaliacoes").status_code, 404)
        self.assertEqual(self.cliente.get(self.rota).status_code, 404)
        self.abrir.assert_not_called()
