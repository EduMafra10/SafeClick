import inspect
import os
import re
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, call, patch

from psycopg import Error
from werkzeug.security import generate_password_hash

from safeclick import auditoria_textos, contas_db, create_app, usuarios_db
from safeclick.auditoria_db import EVENTOS_PERMITIDOS
from safeclick.exclusao_conta_db import (
    ContaJaExcluida,
    agendar_exclusao,
    aplicar_prazos,
    buscar_dados_exclusao,
    gerar_novo_link,
    reativar_conta,
)
from safeclick.sessoes import Usuario, carregar_usuario


RAIZ = Path(__file__).resolve().parents[1]
SENHA = "uma senha de teste bem comprida"
HASH = generate_password_hash(SENHA, method="scrypt")
TOKEN = "A" * 43
DADOS = {
    "senha_hash": HASH,
    "mfa_identidade": "identidade-7",
    "mfa_fator_sid": "YF123",
    "unico_administrador": False,
}
AGENDADA = {
    "nome": "Pessoa Teste",
    "email": "pessoa@example.com",
    "excluir_em": "12/12/2026",
    "token": TOKEN,
}
AMBIENTE = {
    "SECRET_KEY": "chave-exclusiva-dos-testes",
    "DATABASE_URL": "postgresql://nao-usado",
    "APP_BASE_URL": "http://127.0.0.1:5000",
}


class BancoExclusaoTeste(unittest.TestCase):
    """Confere as consultas sem acessar o banco real."""

    def setUp(self):
        self.conexao = MagicMock()
        contexto = MagicMock()
        contexto.__enter__.return_value = self.conexao
        substituicao = patch("safeclick.exclusao_conta_db.conectar_banco", return_value=contexto)
        substituicao.start()
        self.addCleanup(substituicao.stop)
        substituicao = patch("safeclick.exclusao_conta_db.registrar_evento")
        self.registrar = substituicao.start()
        self.addCleanup(substituicao.stop)

    def comandos(self):
        return " ".join(chamada.args[0] for chamada in self.conexao.execute.call_args_list)

    def test_pedido_desativa_a_conta_mas_guarda_os_dados_pelos_30_dias(self):
        self.conexao.execute.return_value.fetchone.return_value = {
            "id": 7, "nome": "Pessoa", "email": "pessoa@example.com", "excluir_em": "12/12/2026",
        }

        dados = agendar_exclusao(7)

        comandos = self.comandos()
        for trecho in ("FOR UPDATE", "exclusao_solicitada_em IS NULL",
                       "exclusao_solicitada_em = CURRENT_TIMESTAMP",
                       "mfa_identidade = gen_random_uuid()", "mfa_fator_sid = NULL",
                       "DELETE FROM public.sessoes_autenticadas",
                       "DELETE FROM public.logins_pendentes",
                       "DELETE FROM public.recuperacoes_senha",
                       "INSERT INTO public.reativacoes_conta"):
            with self.subTest(trecho=trecho):
                self.assertIn(trecho, comandos)
        for trecho in ("nome = NULL", "email = NULL", "senha_hash = NULL", "excluida_em = CURRENT_TIMESTAMP"):
            with self.subTest(trecho=trecho):
                self.assertNotIn(trecho, comandos)
        self.assertNotIn("DELETE FROM public.usuarios", comandos)
        link = next(c for c in self.conexao.execute.call_args_list if "reativacoes_conta" in c.args[0])
        self.assertRegex(link.args[1][0], r"^[0-9a-f]{64}$")
        self.assertEqual(link.args[1][1:], ("30 days", 7))
        self.assertRegex(dados["token"], r"^[A-Za-z0-9_-]{43}$")
        self.assertNotEqual(dados["token"], link.args[1][0])
        self.assertEqual(dados["excluir_em"], "12/12/2026")
        evento = self.registrar.call_args.kwargs
        self.assertEqual((evento["evento"], evento["resultado"]), ("conta.exclusao_agendada", "sucesso"))
        self.assertIs(evento["conexao"], self.conexao)

    def test_conta_ja_excluida_ou_agendada_nao_e_alterada(self):
        self.conexao.execute.return_value.fetchone.return_value = None

        with self.assertRaises(ContaJaExcluida):
            agendar_exclusao(7)

        self.assertEqual(self.conexao.execute.call_count, 1)
        self.registrar.assert_not_called()

    def test_busca_considera_so_contas_ativas(self):
        buscar_dados_exclusao(7)
        consulta, parametros = self.conexao.execute.call_args.args
        self.assertIn("usuario.excluida_em IS NULL", consulta)
        self.assertIn("usuario.exclusao_solicitada_em IS NULL", consulta)
        self.assertIn("outro.exclusao_solicitada_em IS NULL", consulta)
        self.assertEqual(parametros, (7,))

    def test_novo_link_so_para_quem_esta_no_prazo(self):
        self.conexao.execute.return_value.fetchone.return_value = None
        self.assertIsNone(gerar_novo_link(7))
        consulta = self.conexao.execute.call_args.args[0]
        self.assertIn("exclusao_solicitada_em > CURRENT_TIMESTAMP", consulta)

        self.conexao.execute.return_value.fetchone.return_value = {"email": "pessoa@example.com", "excluir_em": "12/12/2026"}
        dados = gerar_novo_link(7)
        self.assertRegex(dados["token"], r"^[A-Za-z0-9_-]{43}$")
        self.assertIn("ON CONFLICT (usuario_id) DO UPDATE", self.comandos())

    def test_link_com_formato_invalido_nem_consulta_o_banco(self):
        for token in ("", "curto", "A" * 42 + "!", None):
            with self.subTest(token=token):
                self.assertIsNone(reativar_conta(token, SENHA))
        self.conexao.execute.assert_not_called()

    def test_reativacao_com_senha_errada_nao_muda_nada(self):
        self.conexao.execute.return_value.fetchone.return_value = {
            "id": 7, "email": "pessoa@example.com", "senha_hash": HASH,
        }

        resultado = reativar_conta(TOKEN, "outra senha qualquer, errada")

        self.assertTrue(resultado["senha_incorreta"])
        self.assertNotIn("UPDATE public.usuarios", self.comandos())
        evento = self.registrar.call_args.kwargs
        self.assertEqual((evento["evento"], evento["resultado"]), ("conta.reativada", "falha"))

    def test_reativacao_com_senha_certa_cancela_a_exclusao_e_gasta_o_link(self):
        self.conexao.execute.return_value.fetchone.return_value = {
            "id": 7, "email": "pessoa@example.com", "senha_hash": HASH,
        }

        resultado = reativar_conta(TOKEN, SENHA)

        self.assertEqual(resultado, {"usuario_id": 7, "email": "pessoa@example.com"})
        comandos = self.comandos()
        for trecho in ("link.expira_em > CURRENT_TIMESTAMP", "FOR UPDATE OF usuario",
                       "SET exclusao_solicitada_em = NULL",
                       "DELETE FROM public.reativacoes_conta"):
            with self.subTest(trecho=trecho):
                self.assertIn(trecho, comandos)
        evento = self.registrar.call_args.kwargs
        self.assertEqual((evento["evento"], evento["resultado"]), ("conta.reativada", "sucesso"))

    def test_fim_do_prazo_apaga_os_dados_pessoais_e_guarda_o_email(self):
        self.conexao.execute.return_value.fetchall.return_value = [{"id": 7}, {"id": 9}]

        self.assertEqual(aplicar_prazos(), [7, 9])

        consulta, parametros = self.conexao.execute.call_args_list[0].args
        for trecho in ("exclusao_solicitada_em <= CURRENT_TIMESTAMP - %(prazo)s::interval",
                       "FOR UPDATE SKIP LOCKED",
                       "INSERT INTO public.contas_excluidas",
                       "DELETE FROM public.reativacoes_conta",
                       "nome = NULL", "email = NULL", "senha_hash = NULL",
                       "excluida_em = CURRENT_TIMESTAMP"):
            with self.subTest(trecho=trecho):
                self.assertIn(trecho, consulta)
        self.assertEqual(parametros, {"prazo": "30 days", "prazo_email": "6 months"})
        self.assertIn("DELETE FROM public.contas_excluidas WHERE descartar_em <= CURRENT_TIMESTAMP",
                      self.comandos())
        eventos = [c.kwargs for c in self.registrar.call_args_list]
        self.assertEqual([e["recurso_id"] for e in eventos], [7, 9])
        self.assertTrue(all(e["evento"] == "conta.excluida" for e in eventos))
        self.assertTrue(all(e["detalhes"] == {"origem": "fim_do_prazo"} for e in eventos))

    def test_prazo_usa_a_conexao_de_quem_chamou(self):
        outra = MagicMock()
        outra.execute.return_value.fetchall.return_value = []
        aplicar_prazos(outra)
        self.conexao.execute.assert_not_called()
        self.assertEqual(outra.execute.call_count, 2)


class AjustesNoSistemaTeste(unittest.TestCase):
    def test_script_cria_o_prazo_os_links_e_a_regra_sem_dados_pessoais(self):
        sql = (RAIZ / "sql" / "adicionar_exclusao_conta.sql").read_text(encoding="utf-8")
        for trecho in ("ADD COLUMN IF NOT EXISTS exclusao_solicitada_em TIMESTAMPTZ",
                       "ADD COLUMN IF NOT EXISTS excluida_em TIMESTAMPTZ",
                       "DROP CONSTRAINT IF EXISTS usuarios_exclusao_sem_dados_pessoais",
                       "CREATE TABLE IF NOT EXISTS public.reativacoes_conta",
                       "token_hash TEXT NOT NULL UNIQUE",
                       "CREATE TABLE IF NOT EXISTS public.contas_excluidas",
                       "descartar_em TIMESTAMPTZ NOT NULL"):
            with self.subTest(trecho=trecho):
                self.assertIn(trecho, sql)
        for coluna in ("nome", "email", "senha_hash"):
            self.assertIn(f"ALTER COLUMN {coluna} DROP NOT NULL", sql)

    def test_eventos_de_auditoria_existem_e_tem_texto(self):
        for evento in ("conta.exclusao_agendada", "conta.reativada", "conta.excluida"):
            with self.subTest(evento=evento):
                self.assertIn(evento, EVENTOS_PERMITIDOS)
                self.assertIn(evento, auditoria_textos.EVENTOS)

    def test_sessao_de_conta_excluida_ou_agendada_nao_e_carregada(self):
        codigo = inspect.getsource(carregar_usuario)
        self.assertIn("usuario.excluida_em IS NULL", codigo)
        self.assertIn("usuario.exclusao_solicitada_em IS NULL", codigo)

    def test_login_recebe_a_marca_de_exclusao_agendada(self):
        self.assertIn("exclusao_solicitada_em", inspect.getsource(usuarios_db.buscar_usuario_por_email))


class RotaBase(unittest.TestCase):
    def substituir(self, substituicao):
        resultado = substituicao.start()
        self.addCleanup(substituicao.stop)
        return resultado

    def preparar_app(self):
        self.substituir(patch.dict(os.environ, AMBIENTE, clear=True))
        for alvo in ("psycopg.connect", "socket.socket.connect"):
            self.substituir(patch(alvo, side_effect=AssertionError("Acesso externo nos testes")))
        self.app = create_app()
        self.app.config.update(TESTING=True)
        self.client = self.app.test_client()
        self.aceitou = self.substituir(patch(
            "safeclick.aceite_termos.usuario_aceitou_termos_atuais", return_value=True
        ))
        self.email = self.substituir(patch("safeclick.exclusao_conta.enviar_email"))

    def csrf(self, endereco):
        html = self.client.get(endereco).get_data(as_text=True)
        return re.search(r'name="csrf_token" type="hidden" value="([^"]+)"', html).group(1)

    def flash(self):
        with self.client.session_transaction() as sessao:
            return str(sessao.get("_flashes"))


class RotaExclusaoTeste(RotaBase):
    """Página Minha conta → Excluir minha conta."""

    def setUp(self):
        self.preparar_app()
        self.substituir(patch("safeclick.conquistas.liberar_conquistas", return_value=[]))
        self.substituir(patch("safeclick.conteudos_db.listar_conteudos", return_value=[]))
        self.permitir = self.substituir(patch(
            "safeclick.exclusao_conta.permitir_tentativa", return_value=True
        ))
        self.buscar = self.substituir(patch(
            "safeclick.exclusao_conta.buscar_dados_exclusao", return_value=dict(DADOS)
        ))
        self.ordem = MagicMock()
        self.remover = self.substituir(patch("safeclick.exclusao_conta.remover_fator_totp"))
        self.agendar = self.substituir(patch(
            "safeclick.exclusao_conta.agendar_exclusao", return_value=dict(AGENDADA)
        ))
        self.ordem.attach_mock(self.remover, "remover")
        self.ordem.attach_mock(self.agendar, "agendar")
        self.desvincular = self.substituir(patch("safeclick.exclusao_conta.desvincular_autenticador"))
        self.recusa = self.substituir(patch("safeclick.exclusao_conta.registrar_recusa"))

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

    def enviar(self, **campos):
        dados = {"csrf_token": self.csrf("/conta/excluir"), "senha": SENHA, "ciente": "y", **campos}
        return self.client.post("/conta/excluir", data={k: v for k, v in dados.items() if v is not None})

    def nada_foi_excluido(self):
        self.remover.assert_not_called()
        self.agendar.assert_not_called()
        self.email.assert_not_called()

    def test_visitante_e_levado_ao_login(self):
        resposta = self.client.get("/conta/excluir")
        self.assertIn(resposta.status_code, (302, 303))
        self.assertIn("/login", resposta.headers["Location"])

    def test_pagina_explica_as_consequencias(self):
        self.entrar()
        html = self.client.get("/conta/excluir").get_data(as_text=True)
        for trecho in ("Excluir minha conta", "você tem 30 dias para mudar de ideia",
                       "depois de 30 dias, a exclusão é definitiva",
                       "sem nenhum dado que identifique você",
                       "seu e-mail fica guardado por mais 6 meses",
                       'autocomplete="current-password"', "Voltar para Minha conta"):
            with self.subTest(trecho=trecho):
                self.assertIn(trecho, html)

    def test_botao_da_pagina_minha_conta_leva_a_exclusao(self):
        from safeclick.conta import ENDPOINT_EXCLUSAO
        with self.app.test_request_context():
            from flask import url_for
            self.assertEqual(url_for(ENDPOINT_EXCLUSAO), "/conta/excluir")

    def test_sem_marcar_a_caixa_nada_acontece(self):
        self.entrar()
        resposta = self.enviar(ciente=None)
        self.assertEqual(resposta.status_code, 400)
        self.assertIn("Marque a caixa", resposta.get_data(as_text=True))
        self.buscar.assert_not_called()
        self.nada_foi_excluido()

    def test_sem_token_csrf_e_recusado(self):
        self.entrar()
        resposta = self.client.post("/conta/excluir", data={"senha": SENHA, "ciente": "y"})
        self.assertEqual(resposta.status_code, 400)
        self.nada_foi_excluido()

    def test_senha_errada_nao_exclui(self):
        self.entrar()
        resposta = self.enviar(senha="outra senha qualquer, errada")
        self.assertEqual(resposta.status_code, 400)
        self.assertIn("Senha incorreta", resposta.get_data(as_text=True))
        self.recusa.assert_called_once_with(7, "senha_incorreta")
        self.nada_foi_excluido()

    def test_pedido_remove_na_twilio_antes_encerra_o_acesso_e_envia_o_link(self):
        self.entrar()
        resposta = self.enviar()

        self.assertEqual(resposta.status_code, 303)
        self.assertTrue(resposta.headers["Location"].endswith("/login"))
        self.assertEqual(self.ordem.mock_calls, [
            call.remover("identidade-7", "YF123", usuario_id=7),
            call.agendar(7),
        ])
        destinatario, assunto, texto = self.email.call_args.args
        self.assertEqual(destinatario, "pessoa@example.com")
        self.assertIn("12/12/2026", assunto)
        self.assertIn(f"http://127.0.0.1:5000/reativar-conta#token={TOKEN}", texto)
        self.assertIn("até 12/12/2026", texto)
        with self.client.session_transaction() as sessao:
            self.assertNotIn("_user_id", sessao)
        aviso = self.flash()
        self.assertIn("será excluída em 12/12/2026", aviso)
        self.assertIn("link para reativá-la", aviso)

    def test_falha_no_email_nao_desfaz_o_pedido_e_explica_o_que_fazer(self):
        self.email.side_effect = RuntimeError("Gmail fora do ar")
        self.entrar()
        resposta = self.enviar()
        self.assertEqual(resposta.status_code, 303)
        self.assertIn("entre com seu e-mail e sua senha para receber o link", self.flash())

    def test_numero_de_outra_conta_no_formulario_e_ignorado(self):
        self.entrar()
        self.enviar(usuario_id="99", id="99")
        self.agendar.assert_called_once_with(7)

    def test_falha_na_twilio_preserva_a_conta(self):
        self.remover.side_effect = RuntimeError("Twilio fora do ar")
        self.entrar()
        resposta = self.enviar()
        self.assertEqual(resposta.status_code, 503)
        self.assertIn("Sua conta não foi excluída", resposta.get_data(as_text=True))
        self.agendar.assert_not_called()

    def test_falha_no_banco_mantem_a_conta_e_desvincula_o_autenticador(self):
        self.agendar.side_effect = Error("banco fora do ar")
        self.entrar()
        resposta = self.enviar()
        self.assertEqual(resposta.status_code, 503)
        self.assertIn("continua ativa", resposta.get_data(as_text=True))
        self.desvincular.assert_called_once_with(7)
        self.email.assert_not_called()

    def test_unico_administrador_nao_pode_excluir(self):
        self.buscar.return_value = dict(DADOS, unico_administrador=True)
        self.entrar("administrador")
        resposta = self.enviar()
        self.assertEqual(resposta.status_code, 409)
        self.assertIn("único administrador", resposta.get_data(as_text=True))
        self.nada_foi_excluido()

    def test_limite_de_tentativas(self):
        self.permitir.return_value = False
        self.entrar()
        resposta = self.enviar()
        self.assertEqual(resposta.status_code, 429)
        self.buscar.assert_not_called()
        self.nada_foi_excluido()

    def test_conta_sem_autenticador_nao_chama_a_twilio(self):
        self.buscar.return_value = dict(DADOS, mfa_fator_sid=None)
        self.entrar()
        self.assertEqual(self.enviar().status_code, 303)
        self.remover.assert_not_called()
        self.agendar.assert_called_once_with(7)

    def test_termos_desatualizados_nao_impedem_a_exclusao(self):
        self.aceitou.return_value = False
        self.entrar()
        self.assertEqual(self.client.get("/conta/excluir").status_code, 200)


class RotaReativacaoTeste(RotaBase):
    """Página pública aberta pelo link do e-mail."""

    def setUp(self):
        self.preparar_app()
        self.permitir = self.substituir(patch(
            "safeclick.exclusao_conta.permitir_tentativa", return_value=True
        ))
        self.prazos = self.substituir(patch("safeclick.exclusao_conta.aplicar_prazos"))
        self.reativar = self.substituir(patch(
            "safeclick.exclusao_conta.reativar_conta",
            return_value={"usuario_id": 7, "email": "pessoa@example.com"},
        ))

    def enviar(self, token=TOKEN, senha=SENHA):
        dados = {"csrf_token": self.csrf("/reativar-conta"), "token_reativacao": token, "senha": senha}
        return self.client.post("/reativar-conta", data=dados)

    def test_pagina_e_publica_e_nao_vaza_o_endereco(self):
        resposta = self.client.get("/reativar-conta")
        html = resposta.get_data(as_text=True)
        self.assertEqual(resposta.status_code, 200)
        for trecho in ("Reativar minha conta", 'name="token_reativacao"',
                       'autocomplete="current-password"', "js/reativacao.js",
                       "configurá-lo de novo"):
            with self.subTest(trecho=trecho):
                self.assertIn(trecho, html)
        self.assertEqual(resposta.headers["Referrer-Policy"], "no-referrer")
        self.assertEqual(resposta.headers["Cache-Control"], "no-store")

    def test_link_e_senha_certos_reativam_e_avisam_por_email(self):
        resposta = self.enviar()
        self.assertEqual(resposta.status_code, 303)
        self.assertTrue(resposta.headers["Location"].endswith("/login"))
        self.prazos.assert_called_once()
        self.reativar.assert_called_once_with(TOKEN, SENHA)
        destinatario, assunto, _ = self.email.call_args.args
        self.assertEqual(destinatario, "pessoa@example.com")
        self.assertIn("reativada", assunto)
        self.assertIn("Sua conta foi reativada", self.flash())

    def test_senha_errada_mantem_a_conta_desativada(self):
        self.reativar.return_value = {"senha_incorreta": True, "usuario_id": 7}
        resposta = self.enviar(senha="outra senha qualquer, errada")
        self.assertEqual(resposta.status_code, 400)
        self.assertIn("Senha incorreta", resposta.get_data(as_text=True))
        self.email.assert_not_called()

    def test_link_vencido_ou_usado(self):
        self.reativar.return_value = None
        resposta = self.enviar()
        self.assertEqual(resposta.status_code, 400)
        self.assertIn("o prazo de 30 dias acabou", resposta.get_data(as_text=True))

    def test_token_mal_formado_nao_chega_ao_banco(self):
        self.reativar.return_value = None
        self.enviar(token="<script>")
        self.reativar.assert_called_once_with("", SENHA)

    def test_limite_de_tentativas(self):
        self.permitir.return_value = False
        resposta = self.enviar()
        self.assertEqual(resposta.status_code, 429)
        self.reativar.assert_not_called()


class LoginContaAgendadaTeste(RotaBase):
    """Quem está nos 30 dias e tenta entrar recebe um link novo, mas não entra."""

    def setUp(self):
        self.preparar_app()
        self.substituir(patch("safeclick.autenticacao.permitir_tentativa", return_value=True))
        self.substituir(patch("safeclick.exclusao_conta.aplicar_prazos"))
        self.registrar = self.substituir(patch("safeclick.autenticacao.registrar_evento"))
        self.iniciar = self.substituir(patch("safeclick.autenticacao.iniciar_login_pendente"))
        self.substituir(patch("safeclick.autenticacao.buscar_usuario_por_email", return_value={
            "id": 7, "nome": "Pessoa", "email": "pessoa@example.com", "senha_hash": HASH,
            "perfil": "usuario", "exclusao_solicitada_em": datetime(2026, 11, 12, tzinfo=timezone.utc),
        }))
        self.link = self.substituir(patch(
            "safeclick.exclusao_conta.gerar_novo_link",
            return_value={"email": "pessoa@example.com", "excluir_em": "12/12/2026", "token": TOKEN},
        ))

    def entrar(self, senha=SENHA):
        return self.client.post("/login", data={
            "csrf_token": self.csrf("/login"), "email": "pessoa@example.com", "senha": senha,
        })

    def test_senha_certa_envia_link_novo_e_nao_entra(self):
        resposta = self.entrar()
        html = resposta.get_data(as_text=True)
        self.assertEqual(resposta.status_code, 403)
        self.assertIn("exclusão marcada para 12/12/2026", html)
        self.iniciar.assert_not_called()
        self.link.assert_called_once_with(7)
        self.assertIn(f"/reativar-conta#token={TOKEN}", self.email.call_args.args[2])
        self.assertEqual(self.registrar.call_args.kwargs["detalhes"],
                         {"etapa": "senha", "motivo": "exclusao_agendada"})

    def test_senha_errada_nao_revela_que_a_conta_esta_agendada(self):
        resposta = self.entrar("outra senha qualquer, errada")
        self.assertEqual(resposta.status_code, 401)
        self.assertNotIn("exclusão", resposta.get_data(as_text=True))
        self.link.assert_not_called()
        self.email.assert_not_called()

    def test_falha_no_email_pede_para_tentar_de_novo(self):
        self.email.side_effect = RuntimeError("Gmail fora do ar")
        resposta = self.entrar()
        self.assertEqual(resposta.status_code, 503)
        self.assertIn("não conseguimos enviar o link", resposta.get_data(as_text=True))

    def test_prazo_acabado_vira_login_invalido(self):
        self.link.return_value = None
        resposta = self.entrar()
        self.assertEqual(resposta.status_code, 401)
        self.assertIn("E-mail ou senha inválidos", resposta.get_data(as_text=True))


def conta_admin(**alteracoes):
    dados = {
        "id": 12, "nome": "Ana Admin", "email": "ana@example.test", "perfil": "administrador",
        "criado_em": datetime(2026, 11, 1, 2, 30, tzinfo=timezone.utc),
        "tem_autenticador": True, "autenticador_ativo": True, "ultimo_acesso": None,
        "excluida_em": None, "exclusao_marcada_para": None,
        "email_guardado": None, "descartar_em": None,
    }
    dados.update(alteracoes)
    return dados


class ContasDbExclusaoTeste(unittest.TestCase):
    """Lista por situação e exclusão de administrador no banco, sem banco real."""

    def setUp(self):
        self.conexao = MagicMock()
        contexto = MagicMock()
        contexto.__enter__.return_value = self.conexao
        for alvo, nome in (("safeclick.contas_db.conectar_banco", None),
                           ("safeclick.contas_db.registrar_evento", "registrar"),
                           ("safeclick.contas_db.aplicar_prazos", "prazos")):
            substituicao = patch(alvo, return_value=contexto) if nome is None else patch(alvo)
            valor = substituicao.start()
            self.addCleanup(substituicao.stop)
            if nome:
                setattr(self, nome, valor)
        self.conexao.execute.return_value.fetchone.return_value = {"total": 0}
        self.conexao.execute.return_value.fetchall.return_value = []

    def comandos(self):
        return " ".join(chamada.args[0] for chamada in self.conexao.execute.call_args_list)

    def test_lista_abre_nas_ativas_e_aplica_os_prazos_antes(self):
        contas_db.listar_contas()
        self.prazos.assert_called_once_with(self.conexao)
        for chamada in self.conexao.execute.call_args_list:
            self.assertIn("usuarios.excluida_em IS NULL AND usuarios.exclusao_solicitada_em IS NULL", chamada.args[0])

    def test_excluidas_mostram_o_email_so_dentro_dos_6_meses(self):
        contas_db.listar_contas(situacao="excluidas", busca="ana@")
        contagem, lista = self.conexao.execute.call_args_list
        for consulta in (contagem.args[0], lista.args[0]):
            self.assertIn("LEFT JOIN public.contas_excluidas AS guardado", consulta)
            self.assertIn("guardado.descartar_em > CURRENT_TIMESTAMP", consulta)
            self.assertIn("usuarios.excluida_em IS NOT NULL", consulta)
            # conta excluída não tem nome nem e-mail: a busca usa o e-mail guardado
            self.assertIn("guardado.email_guardado ILIKE %(padrao)s", consulta)
        self.assertIn("exclusao_solicitada_em + '30 days'::interval AS exclusao_marcada_para", lista.args[0])

    def test_agendadas_e_situacao_invalida(self):
        contas_db.listar_contas(situacao="agendadas")
        self.assertIn("usuarios.exclusao_solicitada_em IS NOT NULL", self.comandos())
        with self.assertRaises(ValueError):
            contas_db.listar_contas(situacao="todas")

    def test_acoes_da_administracao_so_valem_para_contas_ativas(self):
        contas_db.obter_conta(12)
        self.assertIn("AND usuarios.excluida_em IS NULL AND usuarios.exclusao_solicitada_em IS NULL", self.comandos())

    def test_promocao_conta_so_administradores_ativos(self):
        self.conexao.execute.return_value.fetchall.return_value = [{"id": 7}, {"id": 12}]
        self.conexao.execute.return_value.fetchone.return_value = {
            "id": 12, "perfil": "administrador", "autenticador_ativo": True}
        self.conexao.execute.return_value.rowcount = 1
        contas_db.alterar_perfil(7, 12, "usuario")
        travar, conta = (c.args[0] for c in self.conexao.execute.call_args_list[:2])
        self.assertIn("usuarios.exclusao_solicitada_em IS NULL AND perfil = 'administrador' FOR NO KEY UPDATE", travar)
        self.assertIn("usuarios.excluida_em IS NULL", conta)

    def preparar_exclusao(self, administradores=(7, 12), alvo="administrador"):
        self.conexao.execute.return_value.fetchall.return_value = [{"id": n} for n in administradores]
        self.conexao.execute.return_value.fetchone.side_effect = [
            None if alvo is None else {"id": 12, "perfil": alvo, "mfa_identidade": "id-12", "mfa_fator_sid": "YF12"},
            {"email_guardado": "ana@example.test"},
        ]

    def test_exclui_outro_administrador_na_hora_e_registra_motivo(self):
        self.preparar_exclusao()

        resultado = contas_db.excluir_administrador(7, 12, "saiu da equipe do projeto")

        self.assertEqual(resultado, {"identidade": "id-12", "fator_sid": "YF12", "email": "ana@example.test"})
        comandos = self.comandos()
        for trecho in ("perfil = 'administrador' FOR NO KEY UPDATE",
                       "INSERT INTO public.contas_excluidas",
                       "nome = NULL", "email = NULL", "senha_hash = NULL",
                       "mfa_identidade = gen_random_uuid()", "excluida_em = CURRENT_TIMESTAMP",
                       "DELETE FROM public.sessoes_autenticadas",
                       "DELETE FROM public.logins_pendentes",
                       "DELETE FROM public.recuperacoes_senha",
                       "DELETE FROM public.reativacoes_conta"):
            with self.subTest(trecho=trecho):
                self.assertIn(trecho, comandos)
        guardar = next(c for c in self.conexao.execute.call_args_list if "contas_excluidas" in c.args[0])
        self.assertEqual(guardar.args[1], ("6 months", 12))
        evento = self.registrar.call_args.kwargs
        self.assertEqual(evento["usuario_id"], 7)
        self.assertEqual((evento["evento"], evento["recurso_id"]), ("conta.excluida", 12))
        self.assertEqual(evento["detalhes"], {"origem": "administrador", "motivo": "saiu da equipe do projeto"})
        self.assertIs(evento["conexao"], self.conexao)

    def test_exclusoes_de_administrador_recusadas(self):
        casos = (
            ("a própria conta", (7, 7), {}, contas_db.ExclusaoRecusada, "Minha conta"),
            ("quem pede já não é admin", (7, 12), {"administradores": (12, 30)}, contas_db.ExclusaoRecusada, "administradores ativos"),
            ("conta comum", (7, 12), {"alvo": "usuario"}, contas_db.ExclusaoRecusada, "Só contas de administrador"),
            ("conta inexistente ou já excluída", (7, 12), {"alvo": None}, contas_db.ContaNaoEncontrada, ""),
        )
        for nome, argumentos, preparo, erro, mensagem in casos:
            with self.subTest(nome):
                self.preparar_exclusao(**preparo)
                with self.assertRaisesRegex(erro, mensagem):
                    contas_db.excluir_administrador(*argumentos, "motivo de teste")
        self.assertNotIn("excluida_em = CURRENT_TIMESTAMP", self.comandos())
        self.registrar.assert_not_called()

    def test_senha_confere(self):
        self.conexao.execute.return_value.fetchone.return_value = {"senha_hash": HASH}
        self.assertTrue(contas_db.senha_confere(7, SENHA))
        self.assertFalse(contas_db.senha_confere(7, "outra senha qualquer, errada"))
        self.conexao.execute.return_value.fetchone.return_value = None
        self.assertFalse(contas_db.senha_confere(7, SENHA))


class AdministracaoExclusaoTeste(unittest.TestCase):
    """Telas da administração: filtro de situação e exclusão de outro administrador."""

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
        self.substituir("safeclick.aceite_termos.usuario_aceitou_termos_atuais", return_value=True)
        self.substituir("safeclick.sessoes.registrar_evento")
        usuario = Usuario({"id": 7, "nome": "Admin", "email": "admin@example.test", "perfil": "administrador"})
        self.substituir_objeto = patch.object(self.app.login_manager, "_user_callback", return_value=usuario)
        self.substituir_objeto.start()
        self.addCleanup(self.substituir_objeto.stop)
        with self.client.session_transaction() as sessao:
            sessao["_user_id"] = "7"
            sessao["_fresh"] = True
        self.listar = self.substituir("safeclick.administracao.contas_db.listar_contas", return_value=(
            [conta_admin(), conta_admin(id=7, nome="Admin", email="admin@example.test"),
             conta_admin(id=13, nome="Bia", email="bia@example.test", perfil="usuario")], 3))
        self.obter = self.substituir("safeclick.administracao.contas_db.obter_conta", return_value=conta_admin())
        self.permitir = self.substituir("safeclick.administracao.permitir_tentativa", return_value=True)
        self.confere = self.substituir("safeclick.administracao.contas_db.senha_confere", return_value=True)
        self.excluir = self.substituir("safeclick.administracao.contas_db.excluir_administrador", return_value={
            "identidade": "id-12", "fator_sid": "YF12", "email": "ana@example.test"})
        self.remover = self.substituir("safeclick.administracao.remover_fator_totp")
        self.agendar = self.substituir("safeclick.administracao._agendar", return_value=True)

    def enviar(self, **campos):
        pagina = self.client.get("/administracao/contas/12/excluir").get_data(as_text=True)
        token = re.search(r'name="csrf_token" type="hidden" value="([^"]+)"', pagina).group(1)
        dados = {"csrf_token": token, "senha": SENHA, "motivo": "saiu da equipe do projeto", **campos}
        return self.client.post("/administracao/contas/12/excluir",
                                data={k: v for k, v in dados.items() if v is not None})

    def test_lista_so_oferece_excluir_para_outros_administradores(self):
        html = self.client.get("/administracao/contas").get_data(as_text=True)
        self.assertIn('href="/administracao/contas/12/excluir"', html)
        self.assertNotIn('href="/administracao/contas/7/excluir"', html)
        self.assertNotIn('href="/administracao/contas/13/excluir"', html)
        self.assertIn('<option value="ativas" selected>', html)

    def test_filtro_de_excluidas_mostra_o_email_guardado(self):
        self.listar.return_value = ([
            conta_admin(id=20, nome=None, email=None, excluida_em=datetime(2026, 11, 14, 15, tzinfo=timezone.utc),
                        email_guardado="ex@example.test", descartar_em=datetime(2027, 5, 14, 15, tzinfo=timezone.utc)),
            conta_admin(id=21, nome=None, email=None, perfil="usuario",
                        excluida_em=datetime(2026, 1, 2, tzinfo=timezone.utc)),
        ], 2)
        html = self.client.get("/administracao/contas?situacao=excluidas").get_data(as_text=True)
        self.assertEqual(self.listar.call_args.kwargs["situacao"], "excluidas")
        for trecho in ("Conta excluída", "Era admin", "ex@example.test (guardado até 14/05/2027)",
                       "e-mail já descartado", "Excluída em 14/11/2026 às 12:00",
                       '<option value="excluidas" selected>'):
            with self.subTest(trecho=trecho):
                self.assertIn(trecho, html)
        self.assertNotIn("/excluir", html.split("Conta excluída", 1)[1])

    def test_filtro_de_agendadas_mostra_a_data_da_exclusao(self):
        self.listar.return_value = ([conta_admin(
            perfil="usuario", exclusao_marcada_para=datetime(2026, 12, 14, 15, tzinfo=timezone.utc))], 1)
        html = self.client.get("/administracao/contas?situacao=agendadas").get_data(as_text=True)
        self.assertIn("Exclusão definitiva em 14/12/2026", html)

    def test_situacao_invalida(self):
        self.assertEqual(self.client.get("/administracao/contas?situacao=todas").status_code, 400)

    def test_confirmacao_explica_e_pede_senha_e_motivo(self):
        html = self.client.get("/administracao/contas/12/excluir").get_data(as_text=True)
        for trecho in ("Excluir conta de administrador", "sem prazo para desfazer",
                       "Remover acesso de administrador", 'name="motivo"',
                       'autocomplete="current-password"', "Não escreva dados pessoais"):
            with self.subTest(trecho=trecho):
                self.assertIn(trecho, html)

    def test_exclusao_completa(self):
        resposta = self.enviar()
        self.assertEqual(resposta.status_code, 303)
        self.assertTrue(resposta.headers["Location"].endswith("/administracao/contas?situacao=excluidas"))
        self.confere.assert_called_once_with(7, SENHA)
        self.excluir.assert_called_once_with(7, 12, "saiu da equipe do projeto")
        self.remover.assert_called_once_with("id-12", "YF12", usuario_id=12)
        self.assertEqual(self.agendar.call_args.args[1], "ana@example.test")

    def test_senha_errada_nao_exclui(self):
        self.confere.return_value = False
        resposta = self.enviar()
        self.assertEqual(resposta.status_code, 400)
        self.assertIn("Senha incorreta", resposta.get_data(as_text=True))
        self.excluir.assert_not_called()

    def test_motivo_obrigatorio(self):
        for motivo in (None, "curto"):
            with self.subTest(motivo=motivo):
                resposta = self.enviar(motivo=motivo)
                self.assertEqual(resposta.status_code, 400)
        self.excluir.assert_not_called()

    def test_nao_exclui_a_propria_conta_nem_conta_comum(self):
        for conta in (conta_admin(id=7), conta_admin(perfil="usuario")):
            with self.subTest(conta=conta["id"], perfil=conta["perfil"]):
                self.obter.return_value = conta
                self.assertEqual(self.enviar().status_code, 409)
        self.excluir.assert_not_called()

    def test_recusa_do_banco_aparece_na_tela(self):
        self.excluir.side_effect = contas_db.ExclusaoRecusada("Só administradores ativos podem excluir contas.")
        resposta = self.enviar()
        self.assertEqual(resposta.status_code, 409)
        self.assertIn("Só administradores ativos", resposta.get_data(as_text=True))
        self.remover.assert_not_called()

    def test_falha_no_banco_nao_chama_a_twilio(self):
        self.excluir.side_effect = Error("banco fora do ar")
        resposta = self.enviar()
        self.assertEqual(resposta.status_code, 503)
        self.remover.assert_not_called()
        self.agendar.assert_not_called()

    def test_falha_na_twilio_nao_desfaz_a_exclusao(self):
        self.remover.side_effect = RuntimeError("Twilio fora do ar")
        self.assertEqual(self.enviar().status_code, 303)

    def test_limite_de_tentativas(self):
        self.permitir.return_value = False
        self.assertEqual(self.enviar().status_code, 429)
        self.confere.assert_not_called()

    def test_conta_que_nao_esta_ativa_nao_abre(self):
        self.obter.return_value = None
        self.assertEqual(self.client.get("/administracao/contas/12/excluir").status_code, 404)

    def test_usuario_comum_nao_acessa(self):
        comum = Usuario({"id": 9, "nome": "Comum", "email": "c@example.test", "perfil": "usuario"})
        self.substituir_objeto.stop()
        with patch.object(self.app.login_manager, "_user_callback", return_value=comum):
            self.assertIn(self.client.get("/administracao/contas/12/excluir").status_code, (302, 303, 403))
        self.substituir_objeto.start()
