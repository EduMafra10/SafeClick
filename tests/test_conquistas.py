import os
import re
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from psycopg import Error

from safeclick import create_app
from safeclick.conquistas_db import liberar_conquistas, liberar_e_listar_conquistas
from safeclick.sessoes import Usuario


RAIZ = Path(__file__).resolve().parents[1]

NOVA = {
    "codigo": "primeiro-quiz",
    "nome": "Primeiro quiz",
    "descricao": "Respondeu um quiz até o fim.",
    "criterio": "quizzes_respondidos",
}


def conquista(codigo, criterio, meta, atual, data=None):
    return {
        "codigo": codigo, "nome": codigo.replace("-", " ").capitalize(),
        "descricao": f"Descrição de {codigo}.", "criterio": criterio,
        "desbloqueada": data is not None, "desbloqueada_em": data,
        "meta": meta, "atual": atual,
    }


LISTA = [
    conquista("primeiro-conteudo", "conteudos_concluidos", 1, 1, "05/11/2026"),
    conquista("leitor-dedicado", "conteudos_concluidos", 5, 2),
    conquista("nota-maxima", "quizzes_perfeitos", 1, 0),
]


class ConsultaConquistasTeste(unittest.TestCase):
    """Confere as consultas sem acessar o banco real."""

    def setUp(self):
        self.conexao = MagicMock()
        contexto = MagicMock()
        contexto.__enter__.return_value = self.conexao
        abrir = patch("safeclick.conquistas_db.conectar_banco", return_value=contexto)
        abrir.start()
        self.addCleanup(abrir.stop)

    def test_liberar_grava_sem_duplicar_e_filtra_pelo_usuario(self):
        self.conexao.execute.return_value.fetchall.return_value = [NOVA]

        self.assertEqual(liberar_conquistas(7), [NOVA])

        consulta, parametros = self.conexao.execute.call_args.args
        self.assertEqual(parametros, {"usuario_id": 7})
        self.assertIn("INSERT INTO public.conquistas_usuario", consulta)
        self.assertIn("ON CONFLICT DO NOTHING", consulta)
        self.assertIn("m.valor >= c.meta", consulta)
        # todas as contagens são do próprio usuário
        self.assertEqual(consulta.count("usuario_id = %(usuario_id)s"), 7)

    def test_lista_limita_o_progresso_a_meta(self):
        primeira, segunda = MagicMock(), MagicMock()
        primeira.fetchall.return_value = []
        segunda.fetchall.return_value = [
            {"codigo": "leitor-dedicado", "nome": "Leitor dedicado", "descricao": "d",
             "criterio": "conteudos_concluidos", "meta": 5, "valor": 7,
             "desbloqueada_em": "05/11/2026"},
            {"codigo": "escolha-segura", "nome": "Escolha segura", "descricao": "d",
             "criterio": "escolhas_seguras", "meta": 3, "valor": 1,
             "desbloqueada_em": None},
        ]
        self.conexao.execute.side_effect = [primeira, segunda]

        novas, todas = liberar_e_listar_conquistas(7)

        self.assertEqual(novas, [])
        self.assertEqual((todas[0]["desbloqueada"], todas[0]["atual"]), (True, 5))
        self.assertEqual((todas[1]["desbloqueada"], todas[1]["atual"]), (False, 1))


class ScriptConquistasTeste(unittest.TestCase):
    def test_script_cria_as_oito_conquistas_com_criterios_conhecidos(self):
        sql = (RAIZ / "sql" / "criar_conquistas.sql").read_text(encoding="utf-8")
        consulta = (RAIZ / "safeclick" / "conquistas_db.py").read_text(encoding="utf-8")

        linhas = re.findall(r"\('([a-z0-9-]+)', '[^']+', '[^']+', '([a-z_]+)', (\d+), (\d+)\)", sql)
        codigos = [codigo for codigo, _, _, _ in linhas]

        self.assertEqual(len(linhas), 8)
        self.assertEqual(len(set(codigos)), 8)
        for codigo in ("primeiro-conteudo", "primeiro-quiz", "cinco-acertos"):
            self.assertIn(codigo, codigos)  # as três conquistas do RF15
        for _, criterio, _, _ in linhas:
            with self.subTest(criterio=criterio):
                self.assertIn(f"('{criterio}', (", consulta)
        self.assertIn("ON DELETE CASCADE", sql)


PAINEL = {
    "conteudos": {"concluidos": 1, "total": 9, "percentual": 11},
    "quizzes": {"tentativas": 1, "quizzes_diferentes": 1, "percentual_acertos": 80},
    "simulacoes": {
        "tentativas": 0, "sem_versao": 0, "seguras": 0,
        "arriscadas": 0, "percentual_seguras": None,
    },
    "evolucao_quizzes": [{"data": "05/11", "titulo": "Phishing", "percentual": 80}],
    "simulacoes_por_cenario": [],
}


class RotasBase(unittest.TestCase):
    """Prepara o site com o banco substituído por respostas fixas."""

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
        self.substituir(patch("safeclick.conteudos_db.listar_conteudos", return_value=[]))
        self.substituir(patch("safeclick.conteudos_db.concluir_conteudo", return_value=True))
        self.liberar = self.substituir(patch(
            "safeclick.conquistas.liberar_conquistas", return_value=[NOVA]
        ))

    def entrar(self):
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


class AvisoConquistasTeste(RotasBase):
    """Confere quando o aviso de conquista aparece nas páginas."""

    def concluir(self):
        # o token CSRF vem do formulário "Sair da conta", presente em toda página
        html = self.client.get("/conteudos/").get_data(as_text=True)
        token = re.search(r'name="csrf_token" type="hidden" value="([^"]+)"', html).group(1)
        return self.client.post("/conteudos/phishing/concluir", data={"csrf_token": token})

    def test_navegar_sem_fazer_nada_nao_consulta_conquistas(self):
        self.entrar()
        html = self.client.get("/conteudos/").get_data(as_text=True)
        self.liberar.assert_not_called()
        self.assertNotIn("Conquista desbloqueada", html)

    def test_aviso_aparece_na_pagina_seguinte_a_uma_acao(self):
        self.entrar()
        self.assertEqual(self.concluir().status_code, 303)

        html = self.client.get("/conteudos/").get_data(as_text=True)

        self.liberar.assert_called_once_with(7)
        self.assertIn("Conquista desbloqueada", html)
        self.assertIn("Primeiro quiz", html)
        self.assertIn("js/conquistas.js", html)

    def test_aviso_aparece_uma_vez_so(self):
        self.entrar()
        self.concluir()
        self.client.get("/conteudos/")

        html = self.client.get("/conteudos/").get_data(as_text=True)

        self.liberar.assert_called_once()
        self.assertNotIn("Conquista desbloqueada", html)

    def test_varias_conquistas_mostram_resumo(self):
        self.liberar.return_value = [dict(NOVA, nome=f"Conquista {n}") for n in range(5)]
        self.entrar()
        self.concluir()

        html = self.client.get("/conteudos/").get_data(as_text=True)

        self.assertEqual(html.count('class="conquista-aviso"'), 4)
        self.assertIn("Mais 2 conquistas", html)

    def test_falha_no_banco_nao_derruba_a_pagina(self):
        self.liberar.side_effect = Error("banco fora do ar")
        self.entrar()
        self.concluir()

        resposta = self.client.get("/conteudos/")

        self.assertEqual(resposta.status_code, 200)
        self.assertNotIn("Conquista desbloqueada", resposta.get_data(as_text=True))

    def test_visitante_nao_consulta_conquistas(self):
        self.client.get("/login")
        self.liberar.assert_not_called()

    def test_nome_da_conquista_e_escapado(self):
        self.liberar.return_value = [dict(NOVA, nome="<script>alert(1)</script>")]
        self.entrar()
        self.concluir()

        html = self.client.get("/conteudos/").get_data(as_text=True)

        self.assertNotIn("<script>alert(1)", html)
        self.assertIn("&lt;script&gt;", html)


class PainelConquistasTeste(RotasBase):
    """Seção "Suas conquistas" no painel de progresso."""

    def setUp(self):
        super().setUp()
        self.substituir(patch("safeclick.painel.buscar_painel_usuario", return_value=PAINEL))
        self.carregar = self.substituir(patch(
            "safeclick.conquistas.liberar_e_listar_conquistas", return_value=([], LISTA)
        ))

    def test_painel_mostra_conquistas_e_progresso(self):
        self.entrar()
        html = " ".join(self.client.get("/painel/").get_data(as_text=True).split())

        self.carregar.assert_called_once_with(7)
        for trecho in ("Suas conquistas", "<strong>1</strong> de 3 desbloqueadas",
                       "Desbloqueada em 05/11/2026", "2 de 5", "Ainda bloqueada",
                       "css/conquistas.css"):
            with self.subTest(trecho=trecho):
                self.assertIn(trecho, html)
        self.assertNotIn("Conquista desbloqueada", html)

    def test_painel_mostra_o_aviso_das_liberadas_agora(self):
        self.carregar.return_value = ([NOVA], LISTA)
        self.entrar()
        html = self.client.get("/painel/").get_data(as_text=True)
        self.assertIn("Conquista desbloqueada", html)
        self.liberar.assert_not_called()

    def test_painel_funciona_sem_as_tabelas_de_conquistas(self):
        self.carregar.side_effect = Error("relation conquistas does not exist")
        self.entrar()
        resposta = self.client.get("/painel/")
        self.assertEqual(resposta.status_code, 200)
        self.assertNotIn("Suas conquistas", resposta.get_data(as_text=True))


if __name__ == "__main__":
    unittest.main()