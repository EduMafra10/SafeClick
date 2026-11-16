import os
import re
import unittest
from contextlib import ExitStack, nullcontext
from unittest.mock import Mock, patch

from psycopg import Error

from safeclick import create_app
from safeclick.sessoes import Usuario


class QuizzesTeste(unittest.TestCase):
    def setUp(self):
        ajustes = ExitStack()
        self.addCleanup(ajustes.close)
        ajustes.enter_context(patch.dict(os.environ, {"SECRET_KEY": "chave-dos-testes"}, clear=True))
        ajustes.enter_context(patch("psycopg.connect", side_effect=AssertionError("Banco real proibido")))
        self.app = create_app()
        self.app.config.update(TESTING=True, AVALIACOES_ATIVAS=True)
        usuario = Usuario({"id": 7, "nome": "Pessoa", "email": "pessoa@example.test", "perfil": "usuario"})
        ajustes.enter_context(patch.object(self.app.login_manager, "_user_callback", return_value=usuario))
        ajustes.enter_context(patch("safeclick.aceite_termos.usuario_aceitou_termos_atuais", return_value=True))
        self.cliente = self.app.test_client()
        with self.cliente.session_transaction() as sessao:
            sessao["_user_id"] = "7"
            sessao["_fresh"] = True

        self.conexao = Mock()
        ajustes.enter_context(patch("safeclick.quizzes.conectar_banco", return_value=nullcontext(self.conexao)))
        self.auditar = ajustes.enter_context(patch("safeclick.quizzes.registrar_evento"))
        self.rota = "/quizzes/4"
        self.quiz = {
            "id": 4, "versao_id": 19, "titulo": "Proteção de contas",
            "formato": "perguntas", "proxima_referencia": 5,
        }
        self.questoes = [
            {"id": 11, "enunciado": "Como evitar reutilização?", "ordem": 1},
            {"id": 12, "enunciado": "Como reforçar o login?", "ordem": 2},
        ]
        self.alternativas = [
            {"id": 41, "questao_id": 11, "texto": "Use senhas únicas", "ordem": 1},
            {"id": 42, "questao_id": 11, "texto": "Ative dois fatores", "ordem": 2},
            {"id": 43, "questao_id": 12, "texto": "Use senhas únicas", "ordem": 1},
            {"id": 44, "questao_id": 12, "texto": "Ative dois fatores", "ordem": 2},
        ]

    def preparar_formulario(self, *consultas_adicionais):
        self.conexao.execute.reset_mock()
        self.conexao.execute.side_effect = [
            Mock(fetchone=Mock(return_value=self.quiz)),
            Mock(fetchall=Mock(return_value=self.questoes)),
            Mock(fetchall=Mock(return_value=self.alternativas)),
            *consultas_adicionais,
        ]

    def preparar_envio_valido(self, *consultas_de_gravacao):
        gabarito = [
            {"questao_id": 11, "alternativa_id": 41, "texto_correto": "Use senhas únicas",
             "explicacao": "Uma senha diferente protege as outras contas."},
            {"questao_id": 12, "alternativa_id": 44, "texto_correto": "Ative dois fatores",
             "explicacao": "O segundo fator reforça a verificação de identidade."},
        ]
        self.preparar_formulario(Mock(fetchall=Mock(return_value=gabarito)), *consultas_de_gravacao)

    def abrir_quiz(self):
        self.preparar_formulario()
        resposta = self.cliente.get(self.rota)
        self.assertEqual(resposta.status_code, 200)
        token = re.search(r'name="token_envio" value="([^"]+)"', resposta.text)
        self.assertIsNotNone(token)
        return resposta.text, token[1]

    def test_visitante_precisa_entrar_para_acessar_quiz_e_resultado(self):
        visitante = self.app.test_client()
        for rota in (self.rota, "/quizzes/resultado/31", "/quizzes/guia"):
            with self.subTest(rota=rota):
                self.assertEqual(visitante.get(rota).status_code, 302)
        self.conexao.execute.assert_not_called()

    def test_catalogo_exibe_quizzes_e_oficinas_com_seus_destinos(self):
        self.conexao.execute.return_value.fetchall.return_value = [
            {"id": 4, "titulo": "Proteção de contas", "formato": "perguntas", "total_questoes": 2},
            {"id": 5, "titulo": "Revisão de golpes", "formato": "oficina", "total_questoes": 3},
        ]
        resposta = self.cliente.get("/quizzes/")

        self.assertEqual(resposta.status_code, 200)
        self.assertIn('aria-label="Começar quiz: Proteção de contas"', resposta.text)
        self.assertIn('aria-label="Abrir oficina: Revisão de golpes"', resposta.text)
        for destino in ("/quizzes/4", "/quizzes/5", "/quizzes/guia"):
            self.assertIn(f'href="{destino}"', resposta.text)

    def test_envio_corrige_grava_e_audita_quiz_e_oficina(self):
        for formato, rotulo, ultima_escolha, pontos in (
            ("perguntas", "Finalizar quiz", "43", 1),
            ("oficina", "Conferir guia", "44", 2),
        ):
            with self.subTest(formato=formato):
                self.quiz["formato"] = formato
                html, token = self.abrir_quiz()
                self.assertIn(rotulo, html)
                self.assertIn('href="/quizzes/5">Próximo quiz', html)
                self.assertIn('href="/quizzes/">Ver todos os quizzes', html)
                self.auditar.reset_mock()
                self.preparar_envio_valido(Mock(fetchone=Mock(return_value={"id": 31, "catalogo_id": 4})), Mock(), Mock())

                resposta = self.cliente.post(self.rota, data={
                    "token_envio": token, "questao_11": "41", "questao_12": ultima_escolha,
                })

                self.assertEqual(resposta.status_code, 303)
                self.assertEqual(resposta.location, "/quizzes/resultado")
                gravacoes = self.conexao.execute.call_args_list[4:]
                self.assertEqual([consulta.args[1] for consulta in gravacoes], [
                    (7, 19, pontos, 2, token, 19), (31, 11, 41), (31, 12, int(ultima_escolha)),
                ])
                self.auditar.assert_called_once_with(
                    usuario_id=7, evento="quiz.concluido", resultado="sucesso", recurso_tipo="tentativa_quiz",
                    recurso_id=31, detalhes={"quiz_id": 4, "pontuacao": pontos, "total_questoes": 2},
                    conexao=self.conexao,
                )

    def test_respostas_incompletas_ou_adulteradas_sao_recusadas(self):
        _, token = self.abrir_quiz()
        for dados in (
            {"questao_11": "41"},
            {"questao_11": "44", "questao_12": "44"},
            {"questao_11": ["41", "42"], "questao_12": "44"},
            {"questao_11": "41", "questao_12": "44", "usuario_id": "8"},
        ):
            with self.subTest(dados=dados):
                self.preparar_formulario()
                resposta = self.cliente.post(self.rota, data=dados | {"token_envio": token})
                self.assertEqual(resposta.status_code, 400)
                self.assertEqual(self.conexao.execute.call_count, 3)
        self.auditar.assert_not_called()

    def test_oficina_recusa_reuso_do_cartao_mesmo_com_ids_distintos(self):
        self.quiz["formato"] = "oficina"
        _, token = self.abrir_quiz()
        self.preparar_formulario()
        resposta = self.cliente.post(self.rota, data={
            "token_envio": token, "questao_11": "41", "questao_12": "43",
        })

        self.assertEqual(resposta.status_code, 400)
        self.assertIn("Encaixe cada cartão em um único trecho", resposta.text)
        self.auditar.assert_not_called()

    def test_token_invalido_e_formulario_de_versao_antiga_sao_recusados(self):
        _, token = self.abrir_quiz()
        dados = {"questao_11": "41", "questao_12": "44"}
        self.preparar_formulario()
        resposta = self.cliente.post(self.rota, data=dados | {"token_envio": "token-invalido"})
        self.assertEqual(resposta.status_code, 400)

        self.quiz["versao_id"] = 20
        self.preparar_formulario()
        resposta = self.cliente.post(self.rota, data=dados | {"token_envio": token})
        self.assertEqual(resposta.status_code, 409)
        self.assertIn("Este quiz foi atualizado", resposta.text)
        self.auditar.assert_not_called()

    def test_falha_ao_salvar_mantem_formulario_sem_expor_erro_do_banco(self):
        _, token = self.abrir_quiz()
        self.preparar_envio_valido(Error("detalhe privado do banco"))
        resposta = self.cliente.post(self.rota, data={
            "token_envio": token, "questao_11": "41", "questao_12": "44",
        })

        self.assertEqual(resposta.status_code, 503)
        self.assertIn("Não foi possível salvar sua tentativa", resposta.text)
        self.assertIn('name="questao_11"', resposta.text)
        self.assertNotIn("detalhe privado do banco", resposta.text)
        self.auditar.assert_not_called()

    def test_resultado_preserva_explicacoes_e_exibe_acoes_conforme_publicacao(self):
        for publicado in (True, False):
            with self.subTest(publicado=publicado):
                tentativa = {
                    "id": 31, "quiz_id": 19, "pontuacao": 0, "total_questoes": 1,
                    "titulo": self.quiz["titulo"], "formato": "perguntas", "catalogo_id": 4,
                    "pode_repetir": publicado, "proxima_referencia": 5 if publicado else None,
                }
                detalhes = [{
                    "ordem": 1, "enunciado": "Como evitar reutilização?", "resposta_escolhida": "Reutilize",
                    "resposta_correta": "Use senhas únicas", "explicacao": "Uma senha diferente protege outras contas.",
                    "acertou": False, "alternativas_comentadas": [
                        {"ordem": 1, "texto": "Use senhas únicas", "correta": True, "explicacao": "Limita o impacto."},
                        {"ordem": 2, "texto": "Reutilize", "correta": False, "explicacao": "Propaga o risco."},
                    ],
                }]
                self.conexao.execute.side_effect = [
                    Mock(fetchone=Mock(return_value=tentativa)), Mock(fetchall=Mock(return_value=detalhes)),
                ]
                resposta = self.cliente.get("/quizzes/resultado/31")

                self.assertEqual(resposta.status_code, 200)
                self.assertEqual(resposta.headers["Cache-Control"], "no-store")
                for texto in ("0 de 1", "Resposta incorreta", "Limita o impacto.", "Propaga o risco."):
                    self.assertIn(texto, resposta.text)
                self.assertIn('href="/quizzes/">Ver todos os quizzes', resposta.text)
                for acao in ('href="/avaliacoes/quizzes/31"', "Tentar novamente", "Próximo quiz"):
                    self.assertEqual(acao in resposta.text, publicado)

    def test_resultado_de_outra_conta_nao_e_exibido(self):
        self.conexao.execute.return_value.fetchone.return_value = None
        resposta = self.cliente.get("/quizzes/resultado/31")

        self.assertEqual(resposta.status_code, 404)
        self.assertEqual(self.conexao.execute.call_count, 1)
        self.assertEqual(self.conexao.execute.call_args.args[1], (31, 7))

    def test_guia_exibe_a_ultima_oficina_da_conta(self):
        self.conexao.execute.return_value.fetchall.return_value = [
            {"id": 31, "titulo": "Revisão de golpes", "pontuacao": 1, "total_questoes": 2},
        ]
        resposta = self.cliente.get("/quizzes/guia")

        self.assertEqual(resposta.status_code, 200)
        self.assertIn("1 de 2 trechos com encaixe correto", resposta.text)
        self.assertIn('href="/quizzes/resultado/31"', resposta.text)
        self.assertEqual(self.conexao.execute.call_args.args[1], (7,))
