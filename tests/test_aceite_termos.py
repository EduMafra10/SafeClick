import os
import socket
import unittest
from datetime import date
from html.parser import HTMLParser
from unittest.mock import MagicMock, patch

import psycopg

from safeclick import create_app
from safeclick.termos_db import TermosDesatualizados, buscar_termos
from safeclick.usuarios_db import criar_usuario


DOCUMENTO = {
    "versao": "1.0",
    "vigente_desde": date(2026, 9, 28),
    "conteudo_html": '<h1>Termos de Uso</h1><p>Versão 1.0 — Documento arquivado para teste.</p>',
}


class Elementos(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.campos = {}
        self.links = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        atributos = dict(attrs)
        if tag == "input":
            self.campos[atributos.get("name")] = atributos
        if tag == "a":
            self.links.append(atributos)


class CadastroTermosHTTPTeste(unittest.TestCase):
    def setUp(self):
        for substituicao in [
            patch.dict(os.environ, {"SECRET_KEY": "chave-teste-termos", "DATABASE_URL": "postgresql://nao-usado"}, clear=True),
            patch.object(socket, "create_connection", side_effect=AssertionError("Rede real proibida")),
            patch("psycopg.connect", side_effect=AssertionError("Banco real proibido")),
        ]:
            substituicao.start()
            self.addCleanup(substituicao.stop)
        self.app = create_app()
        self.app.config.update(TESTING=True, WTF_CSRF_ENABLED=True)
        self.client = self.app.test_client()
        self.buscar_patch = patch("safeclick.autenticacao.buscar_termos", return_value=DOCUMENTO)
        self.buscar = self.buscar_patch.start()
        self.addCleanup(self.buscar_patch.stop)
        # as leis citadas tambem vem do banco; aqui a consulta e simulada
        self.referencias_patch = patch("safeclick.privacidade.buscar_referencias", return_value=[])
        self.referencias_patch.start()
        self.addCleanup(self.referencias_patch.stop)
        self.criar_patch = patch("safeclick.autenticacao.criar_usuario", return_value=11)
        self.criar = self.criar_patch.start()
        self.addCleanup(self.criar_patch.stop)

    def dados(self):
        pagina = self.client.get("/cadastro")
        self.assertEqual(pagina.status_code, 200)
        campos = Elementos(pagina.get_data(as_text=True)).campos
        return {
            "nome": "Pessoa Teste",
            "email": "PESSOA@example.com",
            "senha": "senha-ficticia-longa",
            "confirmar_senha": "senha-ficticia-longa",
            "aceitou_termos": "y",
            "versao_termos": campos["versao_termos"]["value"],
            "csrf_token": campos["csrf_token"]["value"],
        }

    def test_pagina_tem_checkbox_desmarcado_e_links_publicos(self):
        resposta = self.client.get("/cadastro")
        elementos = Elementos(resposta.get_data(as_text=True))
        campo = elementos.campos["aceitou_termos"]
        self.assertEqual(campo["type"], "checkbox")
        self.assertNotIn("checked", campo)
        self.assertIn("required", campo)
        self.assertEqual(elementos.campos["versao_termos"]["value"], "1.0")
        links = {a.get("href"): a for a in elementos.links}
        for endereco in ["/termos-de-uso?versao=1.0", "/politica-de-privacidade"]:
            self.assertIn(endereco, links)
            self.assertEqual(links[endereco]["target"], "_blank")
            self.assertEqual(links[endereco]["rel"], "noopener")

    def test_sem_aceite_servidor_recusa(self):
        dados = self.dados()
        dados.pop("aceitou_termos")
        resposta = self.client.post("/cadastro", data=dados)
        self.assertEqual(resposta.status_code, 400)
        self.assertIn("Para criar a conta, aceite", resposta.get_data(as_text=True))
        self.criar.assert_not_called()

    def test_valores_falsos_nao_sao_aceite(self):
        for falso in ["", "false", "0", "off", "no"]:
            with self.subTest(falso=falso):
                dados = self.dados()
                dados["aceitou_termos"] = falso
                self.assertEqual(self.client.post("/cadastro", data=dados).status_code, 400)
        self.criar.assert_not_called()

    def test_versao_antiga_invalida_ou_ausente_exige_novo_aceite(self):
        for versao in ["0.9", "9.9", "", "x" * 33]:
            with self.subTest(versao=versao):
                dados = self.dados()
                dados["versao_termos"] = versao
                resposta = self.client.post("/cadastro", data=dados)
                self.assertEqual(resposta.status_code, 400)
                campos = Elementos(resposta.get_data(as_text=True)).campos
                self.assertNotIn("checked", campos["aceitou_termos"])
                self.assertEqual(campos["versao_termos"]["value"], "1.0")
        self.criar.assert_not_called()

    def test_csrf_obrigatorio_mesmo_com_aceite(self):
        dados = self.dados()
        dados.pop("csrf_token")
        resposta = self.client.post("/cadastro", data=dados)
        self.assertEqual(resposta.status_code, 400)
        self.criar.assert_not_called()

    def test_campos_invalidos_nao_criam_conta_nem_reexibem_senha(self):
        dados = self.dados()
        dados["confirmar_senha"] = "outra-senha-ficticia"
        resposta = self.client.post("/cadastro", data=dados)
        self.assertEqual(resposta.status_code, 400)
        self.assertNotIn(dados["senha"], resposta.get_data(as_text=True))
        self.criar.assert_not_called()

    def test_sucesso_encaminha_aceite_versao_e_nao_autentica(self):
        resposta = self.client.post("/cadastro", data=self.dados())
        self.assertEqual(resposta.status_code, 303)
        self.assertTrue(resposta.headers["Location"].endswith("/cadastro"))
        self.criar.assert_called_once_with(
            "Pessoa Teste", "pessoa@example.com", "senha-ficticia-longa",
            aceitou_termos=True, versao_termos="1.0",
        )
        with self.client.session_transaction() as sessao:
            self.assertNotIn("_user_id", sessao)
        campos = Elementos(self.client.get("/cadastro").get_data(as_text=True)).campos
        self.assertNotIn("checked", campos["aceitou_termos"])

    def test_sem_termos_publicados_cadastro_indisponivel(self):
        dados = self.dados()
        self.buscar.return_value = None
        for resposta in [self.client.get("/cadastro"), self.client.post("/cadastro", data=dados)]:
            self.assertEqual(resposta.status_code, 503)
            self.assertIn("disabled", Elementos(resposta.get_data(as_text=True)).campos["enviar"])
        self.criar.assert_not_called()

    def test_falha_na_consulta_de_termos_nao_cria_conta(self):
        self.buscar.side_effect = psycopg.Error("detalhe-interno")
        resposta = self.client.get("/cadastro")
        self.assertEqual(resposta.status_code, 503)
        self.assertNotIn("detalhe-interno", resposta.get_data(as_text=True))
        self.criar.assert_not_called()

    def test_email_duplicado_retorna_conflito(self):
        dados = self.dados()
        self.criar.side_effect = psycopg.errors.UniqueViolation
        self.assertEqual(self.client.post("/cadastro", data=dados).status_code, 409)

    def test_falha_de_gravacao_retorna_erro_sem_sucesso(self):
        dados = self.dados()
        self.criar.side_effect = psycopg.Error("detalhe-interno")
        resposta = self.client.post("/cadastro", data=dados)
        self.assertEqual(resposta.status_code, 503)
        self.assertNotIn("Cadastro realizado com sucesso", resposta.get_data(as_text=True))
        self.assertNotIn("detalhe-interno", resposta.get_data(as_text=True))

    def test_versao_mudou_antes_da_transacao(self):
        dados = self.dados()
        self.criar.side_effect = TermosDesatualizados
        resposta = self.client.post("/cadastro", data=dados)
        self.assertEqual(resposta.status_code, 400)
        self.assertNotIn("checked", Elementos(resposta.get_data(as_text=True)).campos["aceitou_termos"])

    def test_pagina_usa_texto_arquivado(self):
        with patch("safeclick.privacidade.buscar_termos", return_value=DOCUMENTO) as buscar:
            resposta = self.client.get("/termos-de-uso?versao=1.0")
        self.assertEqual(resposta.status_code, 200)
        self.assertIn(DOCUMENTO["conteudo_html"], resposta.get_data(as_text=True))
        self.assertEqual(resposta.headers["Cache-Control"], "no-store")
        buscar.assert_called_once_with("1.0")

    def test_pagina_permite_consultar_versao_historica(self):
        antigo = dict(DOCUMENTO, versao="0.9", conteudo_html="<h1>Documento antigo</h1>")
        with patch("safeclick.privacidade.buscar_termos", return_value=antigo) as buscar:
            resposta = self.client.get("/termos-de-uso?versao=0.9")
        self.assertEqual(resposta.status_code, 200)
        self.assertIn("Documento antigo", resposta.get_data(as_text=True))
        buscar.assert_called_once_with("0.9")

    def test_pagina_inexistente_404_e_banco_indisponivel_503(self):
        with patch("safeclick.privacidade.buscar_termos", return_value=None):
            self.assertEqual(self.client.get("/termos-de-uso?versao=9.9").status_code, 404)
        with patch("safeclick.privacidade.buscar_termos", side_effect=psycopg.Error):
            self.assertEqual(self.client.get("/termos-de-uso").status_code, 503)


class CadastroTermosTransacaoTeste(unittest.TestCase):
    def setUp(self):
        self.conexao = MagicMock()
        self.conexao.execute.return_value.fetchone.return_value = {"id": 11}
        self.contexto = MagicMock()
        self.contexto.__enter__.return_value = self.conexao
        self.contexto.__exit__.return_value = False
        self.mocks = {}
        for nome, substituicao in {
            "abrir": patch("safeclick.usuarios_db.conectar_banco", return_value=self.contexto),
            "hash": patch("safeclick.usuarios_db.generate_password_hash", return_value="hash-ficticio"),
            "buscar": patch("safeclick.usuarios_db.buscar_termos", return_value=DOCUMENTO),
            "auditar": patch("safeclick.usuarios_db.registrar_evento"),
        }.items():
            self.mocks[nome] = substituicao.start()
            self.addCleanup(substituicao.stop)

    def criar(self, **kwargs):
        argumentos = {"aceitou_termos": True, "versao_termos": "1.0"}
        argumentos.update(kwargs)
        return criar_usuario(" Pessoa ", "PESSOA@example.com", "senha-ficticia-longa", **argumentos)

    def test_conta_aceite_e_dois_eventos_usam_mesma_transacao(self):
        self.assertEqual(self.criar(), 11)
        self.mocks["buscar"].assert_called_once_with("1.0", conexao=self.conexao)
        chamadas = self.conexao.execute.call_args_list
        self.assertEqual(len(chamadas), 2)
        self.assertIn("INSERT INTO public.usuarios", chamadas[0].args[0])
        self.assertIn("INSERT INTO public.aceites_termos", chamadas[1].args[0])
        self.assertEqual(chamadas[1].args[1], (11, "1.0"))
        # aceito_em vem do DEFAULT do banco, nao de um valor enviado pelo navegador.
        self.assertNotIn("aceito_em", chamadas[1].args[0])
        eventos = self.mocks["auditar"].call_args_list
        self.assertEqual([c.kwargs["evento"] for c in eventos], ["usuario.cadastrado", "termo.aceito"])
        for chamada in eventos:
            self.assertIs(chamada.kwargs["conexao"], self.conexao)
            self.assertEqual(chamada.kwargs["usuario_id"], 11)
        self.assertEqual(eventos[1].kwargs["detalhes"], {"versao": "1.0"})
        self.assertIsNone(self.contexto.__exit__.call_args.args[0])

    def test_sem_aceite_nao_abre_banco_nem_calcula_hash(self):
        for valor in [False, None, "true", 1]:
            with self.subTest(valor=valor), self.assertRaises(ValueError):
                self.criar(aceitou_termos=valor)
        self.mocks["abrir"].assert_not_called()
        self.mocks["hash"].assert_not_called()

    def test_versao_antiga_rejeitada_antes_de_gravar(self):
        with self.assertRaises(TermosDesatualizados):
            self.criar(versao_termos="0.9")
        self.mocks["abrir"].assert_not_called()

    def test_sem_documento_nao_insere_conta(self):
        self.mocks["buscar"].return_value = None
        with self.assertRaises(RuntimeError):
            self.criar()
        self.conexao.execute.assert_not_called()
        self.assertIs(self.contexto.__exit__.call_args.args[0], RuntimeError)

    def test_falha_no_aceite_propaga_erro_para_rollback(self):
        self.conexao.execute.side_effect = [MagicMock(fetchone=lambda: {"id": 11}), psycopg.Error()]
        with self.assertRaises(psycopg.Error):
            self.criar()
        self.assertIs(self.contexto.__exit__.call_args.args[0], psycopg.Error)

    def test_falha_na_auditoria_do_aceite_propaga_erro_para_rollback(self):
        self.mocks["auditar"].side_effect = [None, psycopg.Error()]
        with self.assertRaises(psycopg.Error):
            self.criar()
        self.assertIs(self.contexto.__exit__.call_args.args[0], psycopg.Error)

    def test_email_duplicado_nao_insere_aceite(self):
        self.conexao.execute.side_effect = psycopg.errors.UniqueViolation
        with self.assertRaises(psycopg.errors.UniqueViolation):
            self.criar()
        self.assertEqual(self.conexao.execute.call_count, 1)
        self.mocks["auditar"].assert_not_called()
        self.assertIs(self.contexto.__exit__.call_args.args[0], psycopg.errors.UniqueViolation)


class ConsultaTermosTeste(unittest.TestCase):
    def test_versao_parametrizada_e_bloqueada_na_transacao(self):
        conexao = MagicMock()
        conexao.execute.return_value.fetchone.return_value = DOCUMENTO
        self.assertEqual(buscar_termos("1.0", conexao=conexao), DOCUMENTO)
        consulta, parametros = conexao.execute.call_args.args
        self.assertIn("WHERE versao = %s", consulta)
        self.assertIn("FOR SHARE", consulta)
        self.assertEqual(parametros, ("1.0",))

    def test_versao_invalida_nao_consulta_banco(self):
        with patch("safeclick.termos_db.conectar_banco") as abrir:
            for versao in [None, "", "x" * 33, 1]:
                self.assertIsNone(buscar_termos(versao))
            abrir.assert_not_called()


if __name__ == "__main__":
    unittest.main()
