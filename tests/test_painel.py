import json
import os
import re
import unittest
from datetime import date
from unittest.mock import MagicMock, patch

from psycopg import Error

from safeclick import create_app
from safeclick.painel_db import _percentual, buscar_painel_usuario
from safeclick.sessoes import Usuario


def painel(**alteracoes):
    """Monta um retorno de buscar_painel_usuario para os testes de rota."""
    dados = {
        "conteudos": {"concluidos": 1, "total": 2, "percentual": 50},
        "quizzes": {"tentativas": 2, "quizzes_diferentes": 1, "percentual_acertos": 40},
        "simulacoes": {
            "tentativas": 25, "sem_versao": 23, "seguras": 0,
            "arriscadas": 2, "percentual_seguras": 0,
        },
        "evolucao_quizzes": [
            {"data": "26/09", "titulo": "Proteção de senhas e contas", "percentual": 60},
            {"data": "30/10", "titulo": "Proteção de senhas e contas", "percentual": 20},
        ],
        "simulacoes_por_cenario": [
            {"titulo": "Aviso de conta bloqueada", "seguras": 0, "arriscadas": 1},
        ],
    }
    dados.update(alteracoes)
    return dados


PAINEL_VAZIO = painel(
    conteudos={"concluidos": 0, "total": 2, "percentual": 0},
    quizzes={"tentativas": 0, "quizzes_diferentes": 0, "percentual_acertos": None},
    simulacoes={
        "tentativas": 0, "sem_versao": 0, "seguras": 0,
        "arriscadas": 0, "percentual_seguras": None,
    },
    evolucao_quizzes=[],
    simulacoes_por_cenario=[],
)


class ConsultaPainelTeste(unittest.TestCase):
    """Testa os cálculos do painel sem acessar o banco real."""

    def setUp(self):
        self.conexao = MagicMock()
        contexto = MagicMock()
        contexto.__enter__.return_value = self.conexao
        abrir = patch("safeclick.painel_db.conectar_banco", return_value=contexto)
        abrir.start()
        self.addCleanup(abrir.stop)

    def responder(self, conteudos, quizzes, evolucao, simulacoes, por_cenario):
        respostas = []
        for unico, lista in (
            (conteudos, None), (quizzes, None), (None, evolucao),
            (simulacoes, None), (None, por_cenario),
        ):
            resultado = MagicMock()
            resultado.fetchone.return_value = unico
            resultado.fetchall.return_value = lista
            respostas.append(resultado)
        self.conexao.execute.side_effect = respostas

    def test_calcula_indicadores_do_usuario(self):
        self.responder(
            {"total": 2, "concluidos": 1},
            {"tentativas": 3, "quizzes_diferentes": 2, "acertos": 12, "questoes": 15},
            [
                {"data": "01/11", "titulo": "Phishing", "pontuacao": 3, "total_questoes": 5},
                {"data": "02/11", "titulo": "Senhas", "pontuacao": 5, "total_questoes": 5},
            ],
            {"tentativas": 5, "sem_versao": 1},
            [
                {"titulo": "Aviso de conta bloqueada", "seguras": 1, "arriscadas": 1},
                {"titulo": "Promoção em uma loja desconhecida", "seguras": 1, "arriscadas": 0},
            ],
        )

        dados = buscar_painel_usuario(7)

        self.assertEqual(dados["conteudos"], {"concluidos": 1, "total": 2, "percentual": 50})
        self.assertEqual(dados["quizzes"]["percentual_acertos"], 80)
        self.assertEqual(dados["quizzes"]["quizzes_diferentes"], 2)
        self.assertEqual(dados["simulacoes"]["seguras"], 2)
        self.assertEqual(dados["simulacoes"]["arriscadas"], 1)
        self.assertEqual(dados["simulacoes"]["percentual_seguras"], 67)
        self.assertEqual(dados["simulacoes"]["sem_versao"], 1)
        self.assertEqual([item["percentual"] for item in dados["evolucao_quizzes"]], [60, 100])

    def test_todas_as_consultas_filtram_pelo_usuario(self):
        self.responder(
            {"total": 0, "concluidos": 0},
            {"tentativas": 0, "quizzes_diferentes": 0, "acertos": 0, "questoes": 0},
            [], {"tentativas": 0, "sem_versao": 0}, [],
        )

        buscar_painel_usuario(7)

        chamadas = self.conexao.execute.call_args_list
        self.assertEqual(len(chamadas), 5)
        for chamada in chamadas:
            with self.subTest(consulta=chamada.args[0][:40]):
                self.assertEqual(
                    chamada.args[1], {"usuario_id": 7, "inicio": None, "fim": None}
                )
                self.assertIn("usuario_id = %(usuario_id)s", chamada.args[0])
                self.assertIn("%(inicio)s::date", chamada.args[0])
                self.assertIn("%(fim)s::date + 1", chamada.args[0])

    def test_periodo_vai_para_o_banco_como_data(self):
        self.responder(
            {"total": 0, "concluidos": 0},
            {"tentativas": 0, "quizzes_diferentes": 0, "acertos": 0, "questoes": 0},
            [], {"tentativas": 0, "sem_versao": 0}, [],
        )

        buscar_painel_usuario(7, inicio=date(2026, 10, 1), fim=date(2026, 10, 31))

        for chamada in self.conexao.execute.call_args_list:
            with self.subTest(consulta=chamada.args[0][:40]):
                self.assertEqual(chamada.args[1]["inicio"], "2026-10-01")
                self.assertEqual(chamada.args[1]["fim"], "2026-10-31")

    def test_escolhas_sao_classificadas_pela_versao_respondida(self):
        self.responder(
            {"total": 0, "concluidos": 0},
            {"tentativas": 0, "quizzes_diferentes": 0, "acertos": 0, "questoes": 0},
            [], {"tentativas": 0, "sem_versao": 0}, [],
        )

        buscar_painel_usuario(7)

        consulta = self.conexao.execute.call_args_list[4].args[0]
        self.assertIn("v.id = t.versao_simulacao_id", consulta)
        self.assertIn("'segura'", consulta)

    def test_sem_atividades_nao_inventa_percentual(self):
        self.responder(
            {"total": 2, "concluidos": 0},
            {"tentativas": 0, "quizzes_diferentes": 0, "acertos": 0, "questoes": 0},
            [], {"tentativas": 0, "sem_versao": 0}, [],
        )

        dados = buscar_painel_usuario(7)

        self.assertIsNone(dados["quizzes"]["percentual_acertos"])
        self.assertIsNone(dados["simulacoes"]["percentual_seguras"])
        self.assertEqual(dados["conteudos"]["percentual"], 0)
        self.assertEqual(dados["evolucao_quizzes"], [])

    def test_percentual(self):
        for parte, total, esperado in ((0, 0, None), (0, 5, 0), (1, 3, 33), (2, 3, 67), (5, 5, 100)):
            with self.subTest(parte=parte, total=total):
                self.assertEqual(_percentual(parte, total), esperado)


class RotaPainelTeste(unittest.TestCase):
    """Testa a página /painel/ com o banco substituído por respostas fixas."""

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
        self.app.config.update(TESTING=True)
        self.client = self.app.test_client()
        self.substituir(patch(
            "safeclick.aceite_termos.usuario_aceitou_termos_atuais", return_value=True
        ))
        self.buscar = self.substituir(patch(
            "safeclick.painel.buscar_painel_usuario", return_value=painel()
        ))

    def entrar(self, perfil="usuario"):
        usuario = Usuario({
            "id": 7, "nome": "Pessoa Teste",
            "email": "pessoa@example.com", "perfil": perfil,
        })
        self.substituir(patch.object(
            self.app.login_manager, "_user_callback", return_value=usuario
        ))
        with self.client.session_transaction() as sessao:
            sessao["_user_id"] = "7"
            sessao["_fresh"] = True

    def test_exige_login(self):
        resposta = self.client.get("/painel/")
        self.assertEqual(resposta.status_code, 302)
        self.assertTrue(resposta.location.startswith("/login"))
        self.buscar.assert_not_called()

    def test_pagina_inicial_abre_o_painel(self):
        self.entrar()
        resposta = self.client.get("/")
        self.assertEqual(resposta.location, "/painel/")

    def test_quem_ja_esta_logado_volta_para_o_inicio(self):
        self.entrar()
        resposta = self.client.get("/login")
        self.assertEqual(resposta.location, "/")

    def test_exibe_indicadores_e_graficos(self):
        self.entrar()
        resposta = self.client.get("/painel/")
        html = " ".join(resposta.get_data(as_text=True).split())

        self.assertEqual(resposta.status_code, 200)
        self.buscar.assert_called_once_with(7, inicio=None, fim=None)
        for trecho in ("01 · Conteúdos", "02 · Quizzes", "03 · Acertos",
                       "04 · Simulações", "05 · Decisões", "40%",
                       "grafico-evolucao", "grafico-cenarios", "chart.umd.js",
                       "23 simulações feitas antes da atualização"):
            with self.subTest(trecho=trecho):
                self.assertIn(trecho, html)
        self.assertEqual(resposta.headers["Cache-Control"], "no-store")

    def test_envia_dados_dos_graficos_em_json(self):
        self.entrar()
        html = self.client.get("/painel/").get_data(as_text=True)
        bloco = re.search(
            r'<script type="application/json" id="dados-painel">(.*?)</script>', html, re.S
        )
        dados = json.loads(bloco.group(1))
        self.assertEqual(dados["media"], 40)
        self.assertEqual(len(dados["evolucao"]), 2)
        self.assertEqual(dados["cenarios"][0]["arriscadas"], 1)

    def test_titulo_com_html_nao_quebra_o_bloco_de_dados(self):
        self.entrar()
        self.buscar.return_value = painel(simulacoes_por_cenario=[
            {"titulo": "</script><script>alert(1)</script>", "seguras": 1, "arriscadas": 0},
        ])
        html = self.client.get("/painel/").get_data(as_text=True)
        self.assertNotIn("<script>alert(1)", html)
        self.assertIn("\\u003c/script\\u003e", html)

    def test_estado_vazio(self):
        self.entrar()
        self.buscar.return_value = PAINEL_VAZIO
        html = self.client.get("/painel/").get_data(as_text=True)
        self.assertIn("Você ainda não fez nenhuma atividade.", html)
        self.assertNotIn("dados-painel", html)

    def test_so_conteudo_concluido_ja_mostra_o_painel(self):
        self.entrar()
        self.buscar.return_value = dict(
            PAINEL_VAZIO, conteudos={"concluidos": 1, "total": 2, "percentual": 50}
        )
        html = self.client.get("/painel/").get_data(as_text=True)
        self.assertNotIn("Você ainda não fez nenhuma atividade.", html)
        self.assertIn("Responda um quiz para acompanhar sua evolução.", html)
        self.assertIn("Faça uma simulação para ver suas escolhas por cenário.", html)

    def test_administrador_tambem_tem_painel(self):
        self.entrar(perfil="administrador")
        self.assertEqual(self.client.get("/painel/").status_code, 200)

    def hoje(self, dia):
        self.substituir(patch("safeclick.painel._hoje", return_value=dia))

    def test_filtra_pelas_datas_da_url(self):
        self.entrar()
        self.hoje(date(2026, 11, 5))
        resposta = self.client.get("/painel/?inicio=2026-10-01&fim=2026-10-31")
        html = " ".join(resposta.get_data(as_text=True).split())

        self.assertEqual(resposta.status_code, 200)
        self.buscar.assert_called_once_with(7, inicio=date(2026, 10, 1), fim=date(2026, 10, 31))
        self.assertIn("01/10/2026 a 31/10/2026", html)
        self.assertIn("Limpar filtro", html)
        self.assertIn('value="2026-10-01"', html)

    def test_atalho_dos_ultimos_7_dias(self):
        self.entrar()
        self.hoje(date(2026, 11, 5))
        html = " ".join(self.client.get(
            "/painel/?inicio=2026-10-30&fim=2026-11-05"
        ).get_data(as_text=True).split())

        self.assertIn(
            'href="/painel/?inicio=2026-10-30&amp;fim=2026-11-05" aria-current="true"', html
        )
        self.buscar.assert_called_once_with(7, inicio=date(2026, 10, 30), fim=date(2026, 11, 5))

    def test_sem_filtro_mostra_todo_o_periodo(self):
        self.entrar()
        self.hoje(date(2026, 11, 5))
        html = " ".join(self.client.get("/painel/").get_data(as_text=True).split())
        self.assertIn("Mostrando: <strong> todo o período </strong>", html)
        self.assertIn('href="/painel/" aria-current="true"', html)
        self.assertNotIn("Limpar filtro", html)

    def test_datas_invalidas_mostram_aviso_e_todo_o_periodo(self):
        self.entrar()
        self.hoje(date(2026, 11, 5))
        casos = {
            "inicio=05/11/2026": "Use datas válidas",
            "inicio=2026-13-01": "Use datas válidas",
            "inicio=<script>": "Use datas válidas",
            "inicio=2019-12-31": "a partir de 2020",
            "inicio=2026-11-01&fim=2026-10-01": "igual ou anterior",
        }
        for consulta, aviso in casos.items():
            with self.subTest(consulta=consulta):
                self.buscar.reset_mock()
                resposta = self.client.get(f"/painel/?{consulta}")
                self.assertEqual(resposta.status_code, 200)
                self.assertIn(aviso, resposta.get_data(as_text=True))
                self.buscar.assert_called_once_with(7, inicio=None, fim=None)
                self.assertNotIn("<script>", resposta.get_data(as_text=True).split("<main")[1])

    def test_data_final_no_futuro_vira_hoje(self):
        self.entrar()
        self.hoje(date(2026, 11, 5))
        self.client.get("/painel/?inicio=2026-11-01&fim=2030-01-01")
        self.buscar.assert_called_once_with(7, inicio=date(2026, 11, 1), fim=date(2026, 11, 5))

    def test_periodo_sem_atividade(self):
        self.entrar()
        self.hoje(date(2026, 11, 5))
        self.buscar.return_value = PAINEL_VAZIO
        html = self.client.get("/painel/?inicio=2026-11-01").get_data(as_text=True)
        self.assertIn("Nenhuma atividade neste período.", html)
        self.assertNotIn("Você ainda não fez nenhuma atividade.", html)

    def test_falha_no_banco_mostra_indisponivel(self):
        self.entrar()
        self.buscar.side_effect = Error("falha simulada")
        self.assertEqual(self.client.get("/painel/").status_code, 503)


if __name__ == "__main__":
    unittest.main()