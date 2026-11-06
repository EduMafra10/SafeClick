import os
import unittest
from copy import deepcopy
from unittest.mock import MagicMock, patch

from psycopg import Error

from safeclick import create_app
from safeclick.sessoes import Usuario
from safeclick.simulacoes_db import listar_simulacoes_administrativas


REGISTROS = [
    {
        "id": 1, "identificador": "conta_bloqueada", "slug": "conta-bloqueada",
        "estado": "publicada", "titulo": "Aviso de conta bloqueada",
        "tipo": "email", "versao": 1,
    },
    {
        "id": 2, "identificador": "nova_conversa", "slug": "nova-conversa",
        "estado": "rascunho", "titulo": "Nova conversa",
        "tipo": "conversa", "versao": None,
    },
    {
        "id": 3, "identificador": "entrega_antiga", "slug": "entrega-antiga",
        "estado": "arquivada", "titulo": "Entrega antiga",
        "tipo": "sms", "versao": 2,
    },
]


class ConsultaAdministrativaTeste(unittest.TestCase):
    def setUp(self):
        self.conexao = MagicMock()
        consulta = MagicMock()
        consulta.fetchone.return_value = {"total": 3}
        consulta.fetchall.return_value = deepcopy(REGISTROS)
        self.conexao.execute.return_value = consulta
        contexto = MagicMock()
        contexto.__enter__.return_value = self.conexao
        abrir = patch("safeclick.simulacoes_db.conectar_banco", return_value=contexto)
        self.abrir = abrir.start()
        self.addCleanup(abrir.stop)
        bloqueio = patch("psycopg.connect", side_effect=AssertionError("Banco real proibido"))
        bloqueio.start()
        self.addCleanup(bloqueio.stop)

    def test_lista_inclui_cenarios_sem_publicacao(self):
        registros, total = listar_simulacoes_administrativas()
        self.assertEqual(total, 3)
        self.assertEqual(registros[1]["estado"], "rascunho")
        self.assertIsNone(registros[1]["versao"])
        contagem, consulta = self.conexao.execute.call_args_list
        self.assertNotIn("WHERE", contagem.args[0])
        self.assertIn("LEFT JOIN public.versoes_simulacao", consulta.args[0])
        self.assertEqual(consulta.args[1], [20, 0])

    def test_filtra_e_pagina_usando_parametros(self):
        listar_simulacoes_administrativas(estado="arquivada", pagina=2, por_pagina=20)
        contagem, consulta = self.conexao.execute.call_args_list
        self.assertIn("WHERE s.estado = %s", consulta.args[0])
        self.assertNotIn("arquivada", consulta.args[0])
        self.assertEqual(contagem.args[1], ["arquivada"])
        self.assertEqual(consulta.args[1], ["arquivada", 20, 20])

    def test_argumentos_invalidos_nao_abrem_banco(self):
        for argumentos in [
            {"estado": "inexistente"}, {"estado": []}, {"pagina": 0},
            {"pagina": True}, {"pagina": 1000001}, {"por_pagina": 101},
        ]:
            with self.subTest(argumentos=argumentos), self.assertRaises(ValueError):
                listar_simulacoes_administrativas(**argumentos)
        self.abrir.assert_not_called()


class AdministracaoAcessoTeste(unittest.TestCase):
    def substituir(self, alvo, **argumentos):
        substituicao = patch(alvo, **argumentos)
        valor = substituicao.start()
        self.addCleanup(substituicao.stop)
        return valor

    def setUp(self):
        ambiente = patch.dict(os.environ, {
            "SECRET_KEY": "chave-exclusiva-dos-testes",
            "DATABASE_URL": "postgresql://nao-usado",
        }, clear=True)
        ambiente.start()
        self.addCleanup(ambiente.stop)
        self.substituir("psycopg.connect", side_effect=AssertionError("Banco real proibido"))
        self.substituir("socket.socket.connect", side_effect=AssertionError("Rede real proibida"))
        self.app = create_app()
        self.app.config.update(TESTING=True, WTF_CSRF_ENABLED=True)
        self.client = self.app.test_client()
        self.usuario = Usuario({
            "id": 7, "nome": "Pessoa Teste", "email": "pessoa@example.test",
            "perfil": "administrador",
        })
        usuario = patch.object(self.app.login_manager, "_user_callback", return_value=self.usuario)
        usuario.start()
        self.addCleanup(usuario.stop)
        with self.client.session_transaction() as sessao:
            sessao["_user_id"] = "7"
            sessao["_fresh"] = True
        self.aceite = self.substituir(
            "safeclick.aceite_termos.usuario_aceitou_termos_atuais", return_value=True
        )
        self.auditar = self.substituir("safeclick.sessoes.registrar_evento")
        self.listar = self.substituir(
            "safeclick.administracao.listar_simulacoes_administrativas",
            return_value=(deepcopy(REGISTROS), 3),
        )

    def test_administrador_consulta_todos_os_estados(self):
        resposta = self.client.get("/administracao/simulacoes")
        self.assertEqual(resposta.status_code, 200)
        html = resposta.get_data(as_text=True)
        for texto in ["Aviso de conta bloqueada", "Publicado", "Nova conversa",
                      "Rascunho", "Arquivado", "Versão 1", "Ainda não publicado"]:
            with self.subTest(texto=texto):
                self.assertIn(texto, html)
        self.assertIn('href="/simulacoes/conta-bloqueada"', html)
        self.assertNotIn('href="/simulacoes/nova-conversa"', html)
        self.assertNotIn('href="/simulacoes/entrega-antiga"', html)
        self.assertEqual(resposta.headers["Cache-Control"], "no-store")
        self.listar.assert_called_once_with(estado="", pagina=1, por_pagina=20)

    def test_inicio_administrativo_oferece_as_secoes_do_catalogo(self):
        resposta = self.client.get("/administracao/")
        self.assertEqual(resposta.status_code, 200)
        html = resposta.get_data(as_text=True)
        for secao in ("conteudos", "quizzes", "simulacoes", "paginas"):
            self.assertIn(f'href="/administracao/catalogo/{secao}"', html)
        self.listar.assert_not_called()

    def test_conta_comum_nao_abre_previa_nem_grava_catalogo(self):
        self.usuario.perfil = "usuario"
        with patch("safeclick.catalogo_admin.db.obter_item") as obter, \
             patch("safeclick.catalogo_admin.db.salvar_rascunho") as salvar:
            for caminho, metodo in (
                ("/administracao/catalogo/quizzes/2/previa", "GET"),
                ("/administracao/catalogo/quizzes/novo", "POST"),
                ("/administracao/catalogo/conteudos/1/remover", "POST"),
                ("/administracao/catalogo/simulacoes/1/publicar", "POST"),
                ("/administracao/catalogo/paginas/1/restaurar", "POST"),
            ):
                self.assertEqual(self.client.open(caminho, method=metodo).status_code, 403)
            obter.assert_not_called()
            salvar.assert_not_called()

    def test_admin_sem_csrf_nao_cria_rascunho(self):
        with patch("safeclick.catalogo_admin.db.salvar_rascunho") as salvar:
            resposta = self.client.post("/administracao/catalogo/quizzes/novo",
                                        data={"titulo": "Quiz", "estrutura": "[]"})
        self.assertEqual(resposta.status_code, 400)
        salvar.assert_not_called()

    def test_visitante_precisa_login(self):
        with self.client.session_transaction() as sessao:
            sessao.clear()
        for caminho in ["/administracao/", "/administracao/simulacoes"]:
            with self.subTest(caminho=caminho):
                resposta = self.client.get(caminho)
                self.assertEqual(resposta.status_code, 302)
                self.assertTrue(resposta.location.startswith("/login"))
        self.listar.assert_not_called()

    def test_usuario_comum_nao_acessa_nem_por_url(self):
        self.usuario.perfil = "usuario"
        for caminho in ["/administracao/", "/administracao/simulacoes"]:
            with self.subTest(caminho=caminho):
                self.assertEqual(self.client.get(caminho).status_code, 403)
        self.listar.assert_not_called()
        self.assertEqual(self.auditar.call_count, 2)
        self.assertEqual(self.auditar.call_args.kwargs["evento"], "acesso.negado")
        self.assertEqual(self.auditar.call_args.kwargs["detalhes"], {"area": "administracao"})

    def test_perfil_invalido_e_parametro_nao_concedem_acesso(self):
        for perfil in ["admin", "moderador", None, "usuario"]:
            with self.subTest(perfil=perfil):
                self.usuario.perfil = perfil
                resposta = self.client.get("/administracao/simulacoes?perfil=administrador")
                self.assertEqual(resposta.status_code, 403)
        self.listar.assert_not_called()

    def test_permissao_e_reavaliada_na_proxima_requisicao(self):
        self.assertEqual(self.client.get("/administracao/simulacoes").status_code, 200)
        self.listar.reset_mock()
        self.usuario.perfil = "usuario"
        self.assertEqual(self.client.get("/administracao/simulacoes").status_code, 403)
        self.listar.assert_not_called()

    def test_aceite_dos_termos_continua_obrigatorio(self):
        self.aceite.return_value = False
        resposta = self.client.get("/administracao/simulacoes")
        self.assertEqual(resposta.status_code, 303)
        self.assertEqual(resposta.location, "/aceitar-termos")
        self.listar.assert_not_called()

    def test_filtra_estado_e_preserva_filtro_na_paginacao(self):
        self.listar.return_value = ([deepcopy(REGISTROS[2])], 41)
        resposta = self.client.get("/administracao/simulacoes?estado=arquivada&pagina=2")
        self.assertEqual(resposta.status_code, 200)
        html = resposta.get_data(as_text=True)
        self.assertIn('value="arquivada" selected', html)
        self.assertIn("Página 2 de 3", html)
        self.assertIn("estado=arquivada&amp;pagina=1", html)
        self.assertIn("estado=arquivada&amp;pagina=3", html)
        self.listar.assert_called_once_with(estado="arquivada", pagina=2, por_pagina=20)

    def test_filtros_invalidos_nao_consultam_banco(self):
        for query in ["estado=invalido", "estado=publicada&estado=arquivada",
                      "pagina=0", "pagina=-1", "pagina=1.5", "pagina=abc",
                      "pagina=1000001", "pagina=", "pagina=1&pagina=2", "extra=1"]:
            with self.subTest(query=query):
                resposta = self.client.get("/administracao/simulacoes?" + query)
                self.assertEqual(resposta.status_code, 400)
        self.listar.assert_not_called()

    def test_estado_sem_registros_mostra_mensagem(self):
        self.listar.return_value = ([], 0)
        resposta = self.client.get("/administracao/simulacoes?estado=rascunho")
        self.assertEqual(resposta.status_code, 200)
        self.assertIn("Nenhum cenário encontrado", resposta.get_data(as_text=True))

    def test_pagina_fora_do_total_retorna_404(self):
        self.assertEqual(self.client.get("/administracao/simulacoes?pagina=2").status_code, 404)

    def test_falha_no_banco_nao_expoe_detalhes(self):
        self.listar.side_effect = Error("detalhe-interno")
        resposta = self.client.get("/administracao/simulacoes")
        self.assertEqual(resposta.status_code, 503)
        self.assertNotIn("detalhe-interno", resposta.get_data(as_text=True))

    def test_html_do_titulo_e_escapado(self):
        registro = deepcopy(REGISTROS[0])
        registro["titulo"] = '<script>alert("exemplo")</script>'
        self.listar.return_value = ([registro], 1)
        html = self.client.get("/administracao/simulacoes").get_data(as_text=True)
        self.assertNotIn('<script>alert(', html)
        self.assertIn("&lt;script&gt;", html)

    def test_listagem_nao_aceita_post(self):
        self.assertEqual(self.client.post("/administracao/simulacoes").status_code, 405)
        self.listar.assert_not_called()

    def test_link_do_menu_aparece_apenas_para_administrador(self):
        with patch("safeclick.simulacoes.listar_simulacoes_publicadas", return_value={}):
            html = self.client.get("/simulacoes/").get_data(as_text=True)
            self.assertIn('href="/administracao/simulacoes"', html)
            self.usuario.perfil = "usuario"
            html = self.client.get("/simulacoes/").get_data(as_text=True)
            self.assertNotIn('href="/administracao/simulacoes"', html)


if __name__ == "__main__":
    unittest.main()
