import io
import os
import unittest
from datetime import date, datetime, timezone
from unittest.mock import MagicMock, patch

from openpyxl import load_workbook
from psycopg import Error

from safeclick import create_app
from safeclick import visao_geral_db
from safeclick.visao_geral_excel import gerar_planilha
from safeclick.sessoes import Usuario

def dados_visao_geral(**alteracoes):
    dados = {
        "dias": 30,
        "inicio": date(2026, 10, 14),
        "contas": {
            "total": 40, "novas": 13, "ativas": 25, "percentual_ativas": 62,
            "autenticador_ativo": 32, "percentual_autenticador": 80, "autenticador_pendente": 6,
        },
        "atividades": {
            "total": 3,
            "por_tipo": {"conteudo": 1, "quiz": 1, "simulacao": 1, "desafio": 0},
            "por_dia": {"dias": ["11/11", "12/11"], "series": {
                "conteudo": [1, 0], "quiz": [0, 1], "simulacao": [1, 0], "desafio": [0, 0]}},
        },
        "simulacoes": [{"titulo": "Promoção em uma loja desconhecida", "pessoas": 5, "percentual_seguras": 40}],
        "quizzes": [{"titulo": "Phishing: aprenda antes de clicar", "tentativas": 13, "percentual_acertos": 45}],
        "catalogo": {"conteudos": {"publicados": 8, "rascunhos": 0}, "quizzes": {"publicados": 4, "rascunhos": 2}},
        "seguranca": {"falhas_login": 7, "acessos_negados": 2, "autenticadores_redefinidos": 1},
        "ultimos_eventos": [{
            "criado_em": datetime(2026, 11, 12, 16, 30, tzinfo=timezone.utc),
            "evento": "login.falha", "resultado": "falha",
        }],
    }
    dados.update(alteracoes)
    return dados


class VisaoGeralBancoTeste(unittest.TestCase):
    def setUp(self):
        self.conexao = MagicMock()
        consulta = MagicMock()
        consulta.fetchone.return_value = {
            "total": 10, "novas": 2, "autenticador_ativo": 8, "autenticador_pendente": 1, "ativos": 4,
        }
        consulta.fetchall.return_value = []
        self.conexao.execute.return_value = consulta
        contexto = MagicMock()
        contexto.__enter__.return_value = self.conexao
        abrir = patch("safeclick.visao_geral_db.conectar_banco", return_value=contexto)
        self.abrir = abrir.start()
        self.addCleanup(abrir.stop)

    def consultas(self):
        return [chamada.args[0] for chamada in self.conexao.execute.call_args_list]

    def test_indicadores_ignoram_administradores_e_usam_parametros(self):
        visao_geral_db.buscar_visao_geral(7, date(2026, 11, 12))
        consultas = self.consultas()
        for sql in consultas[:5]:
            with self.subTest(sql=sql[:40]):
                self.assertIn("perfil = 'usuario'", sql)
        self.assertIn("interval '24 hours'", consultas[-1])
        self.assertIn("LIMIT 6", consultas[-1])
        self.assertNotIn("conteudo.", consultas[-1])
        parametros = self.conexao.execute.call_args_list[0].args[1]
        self.assertEqual(parametros, {"inicio": "2026-11-06"})
        self.assertNotIn("2026-11-06", " ".join(consultas))

    def test_percentuais_e_dias_sem_atividade(self):
        dados = visao_geral_db.buscar_visao_geral(7, date(2026, 11, 12))
        self.assertEqual(dados["contas"]["percentual_autenticador"], 80)
        self.assertEqual(dados["contas"]["percentual_ativas"], 40)
        self.assertEqual(len(dados["atividades"]["por_dia"]["dias"]), 7)
        self.assertEqual(dados["atividades"]["por_dia"]["series"]["quiz"], [0] * 7)
        self.assertEqual(dados["atividades"]["total"], 0)

    def test_serie_soma_por_dia_e_tipo(self):
        linhas = [
            {"dia": date(2026, 11, 11), "tipo": "quiz", "total": 3},
            {"dia": date(2026, 11, 12), "tipo": "conteudo", "total": 2},
        ]
        serie = visao_geral_db._serie_por_dia(linhas, date(2026, 11, 10), date(2026, 11, 12))
        self.assertEqual(serie["dias"], ["10/11", "11/11", "12/11"])
        self.assertEqual(serie["series"]["quiz"], [0, 3, 0])
        self.assertEqual(serie["series"]["conteudo"], [0, 0, 2])

    def test_sem_contas_nao_divide_por_zero(self):
        self.conexao.execute.return_value.fetchone.return_value = {
            "total": 0, "novas": 0, "autenticador_ativo": 0, "autenticador_pendente": 0, "ativos": 0,
        }
        dados = visao_geral_db.buscar_visao_geral(30, date(2026, 11, 12))
        self.assertIsNone(dados["contas"]["percentual_autenticador"])

    def test_resumo_do_catalogo_por_secao(self):
        catalogo = [{"secao": "quizzes", "publicados": 4, "rascunhos": 1}]
        self.conexao.execute.return_value.fetchall.side_effect = [[], [], [], catalogo, [], []]
        dados = visao_geral_db.buscar_visao_geral(30, date(2026, 11, 12))
        self.assertEqual(dados["catalogo"]["quizzes"], {"publicados": 4, "rascunhos": 1})

    def test_periodo_invalido_nao_abre_banco(self):
        for dias in (0, 15, "30", None):
            with self.subTest(dias=dias), self.assertRaises(ValueError):
                visao_geral_db.buscar_visao_geral(dias, date(2026, 11, 12))
        self.abrir.assert_not_called()


class VisaoGeralRotasTeste(unittest.TestCase):
    def substituir(self, alvo, **argumentos):
        substituicao = patch(alvo, **argumentos)
        valor = substituicao.start()
        self.addCleanup(substituicao.stop)
        return valor

    def setUp(self):
        with patch.dict(os.environ, {"SECRET_KEY": "chave-de-teste", "DATABASE_URL": "postgresql://nao-usado",
                                     "AVALIACOES_ATIVAS": "true"}):
            self.app = create_app()
        self.app.config.update(TESTING=True)
        self.client = self.app.test_client()
        self.substituir("psycopg.connect", side_effect=AssertionError("Banco real proibido"))
        self.usuario = Usuario({"id": 7, "nome": "Ana Admin", "email": "ana@example.test", "perfil": "administrador"})
        self.substituir("safeclick.aceite_termos.usuario_aceitou_termos_atuais", return_value=True)
        self.substituir("safeclick.sessoes.registrar_evento")
        usuario = patch.object(self.app.login_manager, "_user_callback", return_value=self.usuario)
        usuario.start()
        self.addCleanup(usuario.stop)
        with self.client.session_transaction() as sessao:
            sessao["_user_id"] = "7"
            sessao["_fresh"] = True
        self.buscar = self.substituir("safeclick.administracao.buscar_visao_geral", return_value=dados_visao_geral())
        self.avaliacoes = self.substituir("safeclick.administracao.listar_resumo_avaliacoes", return_value=[
            {"tipo": "Quiz", "titulo": "Proteção de senhas", "total": 20, "media": 2.0},
            {"tipo": "Conteúdo", "titulo": "Phishing", "total": 5, "media": 4.5},
            {"tipo": "Conteúdo", "titulo": "Sem notas", "total": None, "media": None},
        ])

    def test_mostra_indicadores_pendencias_e_seguranca(self):
        resposta = self.client.get("/administracao/")
        html = " ".join(resposta.get_data(as_text=True).split())
        self.assertEqual(resposta.status_code, 200)
        for texto in ("Visão geral", "Usuários cadastrados", "80%", "Promoção em uma loja desconhecida",
                      "Phishing: aprenda antes de clicar", "Conteúdo publicado", "Login recusado",
                      "12/11 13:30", "Atividades com nota abaixo de 3"):
            with self.subTest(texto=texto):
                self.assertIn(texto, html)
        self.assertIn('href="/administracao/catalogo/quizzes?estado=rascunho"', html)
        self.assertIn('href="/auditoria/?evento=login.falha"', html)
        self.assertIn('href="/administracao/contas?autenticador=pendente"', html)
        self.assertNotIn("Sem notas", html)
        self.assertIn('id="dados-visao-geral"', html)
        self.buscar.assert_called_once()
        self.assertEqual(self.buscar.call_args.args[0], 30)

    def test_periodo_escolhido_e_validado(self):
        self.client.get("/administracao/?periodo=7")
        self.assertEqual(self.buscar.call_args.args[0], 7)
        for url in ("/administracao/?periodo=15", "/administracao/?periodo=abc",
                    "/administracao/?periodo=7&periodo=30", "/administracao/?outro=1"):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 400)

    def test_falha_no_banco_nao_expoe_detalhes(self):
        self.buscar.side_effect = Error("detalhe-interno")
        resposta = self.client.get("/administracao/")
        self.assertEqual(resposta.status_code, 503)
        self.assertNotIn("detalhe-interno", resposta.get_data(as_text=True))

    def test_sem_atividades_mostra_estado_vazio(self):
        vazio = dados_visao_geral(simulacoes=[], quizzes=[], catalogo={})
        vazio["atividades"] = {**vazio["atividades"], "total": 0}
        self.buscar.return_value = vazio
        html = self.client.get("/administracao/").get_data(as_text=True)
        self.assertIn("Nenhuma atividade no período.", html)
        self.assertNotIn('id="grafico-atividades"', html)

    def test_menu_lateral_marca_a_pagina_atual(self):
        html = self.client.get("/administracao/").get_data(as_text=True)
        self.assertIn('href="/administracao/" aria-current="page"', " ".join(html.split()))
        for destino in ("/administracao/catalogo/conteudos", "/administracao/contas",
                        "/administracao/avaliacoes", "/auditoria/", "/simulacoes/"):
            with self.subTest(destino=destino):
                self.assertIn(f'href="{destino}"', html)

    def test_telas_antigas_de_simulacao_levam_ao_catalogo(self):
        resposta = self.client.get("/administracao/simulacoes")
        self.assertEqual(resposta.status_code, 301)
        self.assertEqual(resposta.location, "/administracao/catalogo/simulacoes")
        resposta = self.client.get("/administracao/simulacoes/novo")
        self.assertEqual(resposta.location, "/administracao/catalogo/simulacoes/novo")

    def test_administrador_entra_na_visao_geral(self):
        self.assertEqual(self.client.get("/").location, "/administracao/")
        self.assertEqual(self.client.get("/painel/").location, "/administracao/")

    def test_usuario_comum_continua_no_proprio_painel(self):
        self.usuario.perfil = "usuario"
        self.assertEqual(self.client.get("/").location, "/painel/")
        self.assertEqual(self.client.get("/administracao/").status_code, 403)

    def test_cabecalho_da_plataforma_para_o_administrador(self):
        with patch("safeclick.simulacoes.listar_simulacoes_publicadas", return_value={}):
            html = self.client.get("/simulacoes/").get_data(as_text=True)
            self.assertIn("Você está vendo a plataforma como usuário", html)
            self.assertIn("Área administrativa", html)
            self.assertNotIn("Meu progresso", html)
            self.usuario.perfil = "usuario"
            html = self.client.get("/simulacoes/").get_data(as_text=True)
            self.assertNotIn("Você está vendo a plataforma como usuário", html)
            self.assertNotIn("Área administrativa", html)
            self.assertIn("Meu progresso", html)

    def test_administrador_nao_recebe_avisos_de_conquista(self):
        with patch("safeclick.conquistas.liberar_conquistas") as liberar, \
             patch("safeclick.simulacoes.listar_simulacoes_publicadas", return_value={}):
            self.client.get("/simulacoes/")
            liberar.assert_not_called()

    def test_exportar_planilha_registra_na_auditoria(self):
        with patch("safeclick.administracao.registrar_evento") as registrar:
            resposta = self.client.get("/administracao/visao-geral.xlsx?periodo=7")
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.mimetype, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        self.assertRegex(resposta.headers["Content-Disposition"],
                         r'attachment; filename="safeclick-visao-geral-7-dias-\d{4}-\d{2}-\d{2}\.xlsx"')
        self.assertEqual(resposta.headers["Cache-Control"], "no-store")
        planilha = load_workbook(io.BytesIO(resposta.data))
        self.assertEqual(planilha.sheetnames, ["Resumo", "Atividades por dia"])
        self.assertEqual(self.buscar.call_args.args[0], 7)
        dados = registrar.call_args.kwargs
        self.assertEqual((dados["usuario_id"], dados["evento"]), (7, "visao_geral.exportada"))
        self.assertEqual(dados["detalhes"], {"periodo_dias": 7})

    def test_exportar_planilha_valida_periodo_e_perfil(self):
        with patch("safeclick.administracao.registrar_evento") as registrar:
            self.assertEqual(self.client.get("/administracao/visao-geral.xlsx?periodo=15").status_code, 400)
            self.usuario.perfil = "usuario"
            self.assertEqual(self.client.get("/administracao/visao-geral.xlsx").status_code, 403)
        registrar.assert_not_called()

    def test_exportar_sem_registro_na_auditoria_nao_entrega_o_arquivo(self):
        with patch("safeclick.administracao.registrar_evento", side_effect=Error("falhou")):
            resposta = self.client.get("/administracao/visao-geral.xlsx")
        self.assertEqual(resposta.status_code, 503)
        self.assertNotIn("Usuários cadastrados", resposta.get_data(as_text=True))

    def test_botao_de_exportar_usa_o_periodo_da_tela(self):
        self.buscar.return_value = dados_visao_geral(dias=90)
        html = self.client.get("/administracao/?periodo=90").get_data(as_text=True)
        self.assertIn('href="/administracao/visao-geral.xlsx?periodo=90"', html)


class VisaoGeralPlanilhaTeste(unittest.TestCase):
    def gerar(self, **alteracoes):
        avaliacoes = alteracoes.pop("avaliacoes", None)
        conteudo = gerar_planilha(dados_visao_geral(**alteracoes), {"conteudo": "Conteúdos", "quiz": "Quizzes",
                                  "simulacao": "Simulações", "desafio": "Desafios"},
                                  {"conteudos": "Conteúdos educativos", "quizzes": "Quizzes"},
                                  avaliacoes, datetime(2026, 11, 14, 15, 30))
        return load_workbook(io.BytesIO(conteudo))

    def linhas(self, aba):
        resultado = []
        for linha in aba.iter_rows(values_only=True):
            linha = list(linha)
            while linha and linha[-1] is None:
                linha.pop()
            resultado.append(tuple(linha))
        return resultado

    def celula(self, aba, texto):
        return next(c for linha in aba.iter_rows() for c in linha if c.value == texto)

    def test_resumo_com_numeros_e_porcentagens_de_verdade(self):
        resumo = self.gerar()["Resumo"]
        linhas = self.linhas(resumo)
        self.assertEqual(linhas[0][0], "SafeClick - Visão geral")
        self.assertIn("(14/10/2026 a 12/11/2026)", linhas[1][0])
        self.assertIn("Gerado em 14/11/2026 às 15:30", linhas[2][0])
        self.assertIn(("Usuários ativos no período", 25, 0.62), linhas)
        self.assertIn(("Promoção em uma loja desconhecida", 5, 0.4), linhas)
        self.assertIn(("Quizzes", 4, 2), linhas)
        self.assertIn(("Falhas de login", 7), linhas)
        ativos = self.celula(resumo, "Usuários ativos no período")
        self.assertEqual(resumo.cell(ativos.row, 3).number_format, "0%")
        self.assertTrue(self.celula(resumo, "Indicador").font.bold)
        self.assertFalse(any(l and "Menores notas" in str(l[0]) for l in linhas))

    def test_atividades_por_dia_com_datas_e_total(self):
        aba = self.gerar()["Atividades por dia"]
        linhas = self.linhas(aba)
        self.assertEqual(linhas[0], ("Dia", "Conteúdos", "Quizzes", "Simulações", "Desafios", "Total"))
        self.assertEqual(linhas[1], (datetime(2026, 10, 14), 1, 0, 1, 0, 2))
        self.assertEqual(linhas[-1], ("Total", 1, 1, 1, 0, 3))
        self.assertEqual(aba["A2"].number_format, "dd/mm/yyyy")
        self.assertEqual(aba.freeze_panes, "A2")

    def test_nao_inclui_dados_pessoais(self):
        planilha = self.gerar()
        textos = " ".join(str(v) for aba in planilha for l in self.linhas(aba) for v in l)
        self.assertNotIn("Login recusado", textos)
        self.assertNotIn("login.falha", textos)

    def test_avaliacoes_quando_ativas(self):
        resumo = self.gerar(avaliacoes=[{"tipo": "Quiz", "titulo": "Senhas", "total": 4, "media": 2.25}])["Resumo"]
        self.assertIn(("Senhas", "Quiz", 4, 2.25), self.linhas(resumo))
        self.assertEqual(self.celula(resumo, 2.25).number_format, "0.0")

    def test_secao_vazia_e_texto_que_parece_formula(self):
        resumo = self.gerar(quizzes=[], simulacoes=[
            {"titulo": '=HYPERLINK("http://x")', "pessoas": 1, "percentual_seguras": None}])["Resumo"]
        celula = self.celula(resumo, '=HYPERLINK("http://x")')
        self.assertEqual(celula.data_type, "s")
        self.assertIn(("Nenhum registro no período.",), self.linhas(resumo))


if __name__ == "__main__":
    unittest.main()
