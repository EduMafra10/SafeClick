import os
import re
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

from psycopg import Error
from werkzeug.security import generate_password_hash

from safeclick import auditoria_textos, conta_db, create_app
from safeclick.icones_perfil import ICONES
from safeclick.sessoes import Usuario

SESSAO = "a" * 64


def dados_conta(**alteracoes):
    dados = {"nome": "Ana Souza", "email": "ana@example.test", "icone": None, "autenticador_ativo": True,
             "outras_sessoes": 2, "versao_termos": "1.0", "aceito_em": datetime(2026, 11, 2, 15, tzinfo=timezone.utc)}
    dados.update(alteracoes)
    return dados


class ContaBancoTeste(unittest.TestCase):
    def setUp(self):
        self.conexao = MagicMock()
        contexto = MagicMock()
        contexto.__enter__.return_value = self.conexao
        patch("safeclick.conta_db.conectar_banco", return_value=contexto).start()
        self.registrar = patch("safeclick.conta_db.registrar_evento").start()
        self.addCleanup(patch.stopall)

    def test_troca_de_senha_grava_hash_e_encerra_outras_sessoes(self):
        self.conexao.execute.return_value.fetchone.return_value = {
            "senha_hash": generate_password_hash("senha antiga bem longa", method="scrypt"), "email": "ana@example.test"}
        self.conexao.execute.return_value.rowcount = 2
        email = conta_db.trocar_senha(7, "senha antiga bem longa", "uma frase nova bem longa", SESSAO)
        self.assertEqual(email, "ana@example.test")
        comandos = [chamada.args for chamada in self.conexao.execute.call_args_list]
        self.assertIn("FOR NO KEY UPDATE", comandos[0][0])
        self.assertTrue(comandos[1][1][0].startswith("scrypt:"))
        self.assertEqual(comandos[2][1], (7, SESSAO))
        self.assertIn("token_hash <> %s", comandos[2][0])
        self.assertIn("logins_pendentes", comandos[3][0])
        dados = self.registrar.call_args.kwargs
        self.assertEqual((dados["evento"], dados["resultado"], dados["detalhes"]),
                         ("usuario.senha_alterada", "sucesso", {"sessoes_encerradas": 2}))
        self.assertNotIn("senha", str(dados["detalhes"]))

    def test_senha_atual_errada_nao_altera_e_fica_na_auditoria(self):
        self.conexao.execute.return_value.fetchone.return_value = {
            "senha_hash": generate_password_hash("senha antiga bem longa", method="scrypt"), "email": "ana@example.test"}
        with self.assertRaises(conta_db.SenhaAtualIncorreta):
            conta_db.trocar_senha(7, "errada", "uma frase nova bem longa", SESSAO)
        self.assertEqual(len(self.conexao.execute.call_args_list), 1)
        self.assertEqual(self.registrar.call_args.kwargs["resultado"], "falha")
        self.assertEqual(self.registrar.call_args.kwargs["detalhes"], {"motivo": "senha_atual_incorreta"})

    def test_senha_nova_curta_e_recusada_antes_do_banco(self):
        with self.assertRaises(ValueError):
            conta_db.trocar_senha(7, "qualquer", "curta", SESSAO)
        self.conexao.execute.assert_not_called()

    def test_icone_so_aceita_os_personagens(self):
        conta_db.atualizar_icone(7, "raposa")
        self.assertEqual(self.conexao.execute.call_args.args[1], ("raposa", 7, "raposa"))
        self.assertEqual(self.registrar.call_args.kwargs['detalhes'], {'campos': ['icone']})
        self.assertIs(self.registrar.call_args.kwargs['conexao'], self.conexao)
        conta_db.atualizar_icone(7, None)
        self.assertEqual(self.conexao.execute.call_args.args[1], (None, 7, None))
        with self.assertRaises(ValueError):
            conta_db.atualizar_icone(7, "<script>")

    def test_reenviar_o_mesmo_icone_nao_gera_log(self):
        self.conexao.execute.return_value.rowcount = 0
        conta_db.atualizar_icone(7, 'raposa')
        self.registrar.assert_not_called()

    def test_nome_so_registra_quando_muda(self):
        self.conexao.execute.return_value.rowcount = 0
        self.assertFalse(conta_db.atualizar_nome(7, "Ana"))
        self.registrar.assert_not_called()
        self.conexao.execute.return_value.rowcount = 1
        self.assertTrue(conta_db.atualizar_nome(7, "Ana Souza"))
        self.assertEqual(self.registrar.call_args.kwargs["detalhes"], {"campos": ["nome"]})

    def test_encerrar_sessoes_preserva_a_atual(self):
        self.conexao.execute.return_value.rowcount = 3
        self.assertEqual(conta_db.encerrar_outras_sessoes(7, SESSAO), 3)
        self.assertEqual(self.conexao.execute.call_args_list[0].args[1], (7, SESSAO))
        self.assertEqual(self.registrar.call_args.kwargs["evento"], "sessoes.encerradas")

    def test_lista_de_icones_bate_com_o_sql(self):
        sql = (Path(__file__).resolve().parents[1] / "sql" / "adicionar_icone_usuarios.sql").read_text(encoding="utf-8")
        self.assertEqual(re.findall(r"'([a-z]+)'", sql.split("IN (", 1)[1]), list(ICONES))

    def test_textos_da_auditoria(self):
        self.assertEqual(auditoria_textos.descrever_detalhes("usuario.senha_alterada", {"motivo": "senha_atual_incorreta"}),
                         ["Senha atual incorreta"])
        self.assertEqual(auditoria_textos.descrever_detalhes("sessoes.encerradas", {"sessoes_encerradas": 2}),
                         ["Outras sessões encerradas: 2"])


class ContaRotasTeste(unittest.TestCase):
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
        self.usuario = Usuario({"id": 7, "nome": "Ana Souza", "email": "ana@example.test", "perfil": "usuario", "icone": None})
        self.substituir("safeclick.aceite_termos.usuario_aceitou_termos_atuais", return_value=True)
        self.substituir("safeclick.sessoes.registrar_evento")
        carregar = patch.object(self.app.login_manager, "_user_callback", return_value=self.usuario)
        carregar.start()
        self.addCleanup(carregar.stop)
        with self.client.session_transaction() as sessao:
            sessao["_user_id"] = "7"
            sessao["_fresh"] = True
            sessao["sessao_token"] = "t" * 43
        self.buscar = self.substituir("safeclick.conta.conta_db.buscar_conta", return_value=dados_conta())
        self.limite = self.substituir("safeclick.conta.permitir_tentativa", return_value=True)
        self.agendar = self.substituir("safeclick.conta._agendar", return_value=True)

    def token(self):
        return re.search(r'name="csrf_token" type="hidden" value="([^"]+)"',
                         self.client.get("/conta/").get_data(as_text=True)).group(1)

    def postar(self, caminho, **campos):
        return self.client.post(caminho, data={"csrf_token": self.token(), **campos})

    def test_pagina_mostra_secoes_e_menu_do_cabecalho(self):
        resposta = self.client.get("/conta/")
        html = resposta.get_data(as_text=True)
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.headers["Cache-Control"], "no-store")
        for texto in ("Meu perfil", "Segurança da conta", "Privacidade", "✓ Ativa", "Agora: 2 outras sessões",
                      "Versão 1.0 aceita em 02/11/2026", 'href="/conta/">Minha conta', 'value="raposa"', "Fale com o suporte"):
            self.assertIn(texto, html)
        self.assertIn('value="Ana Souza"', html)
        self.assertEqual(self.buscar.call_args.args[0], 7)

    def test_cabecalho_mostra_o_personagem_escolhido(self):
        self.usuario.icone = "coruja"
        html = self.client.get("/conta/").get_data(as_text=True)
        self.assertIn(ICONES["coruja"]["fundo"], html.split("site-conta-botao", 1)[1][:600])

    def test_salvar_nome(self):
        with patch("safeclick.conta.conta_db.atualizar_nome") as atualizar:
            resposta = self.postar("/conta/nome", nome="  Ana Maria  ")
        self.assertEqual(resposta.status_code, 303)
        atualizar.assert_called_once_with(7, "Ana Maria")
        with patch("safeclick.conta.conta_db.atualizar_nome") as atualizar:
            resposta = self.postar("/conta/nome", nome="   ")
        self.assertEqual(resposta.status_code, 400)
        self.assertIn("Informe o seu nome.", resposta.get_data(as_text=True))
        atualizar.assert_not_called()

    def test_trocar_icone_e_voltar_para_iniciais(self):
        with patch("safeclick.conta.conta_db.atualizar_icone") as atualizar:
            self.assertEqual(self.postar("/conta/icone", icone="panda").status_code, 303)
            self.assertEqual(self.postar("/conta/icone", icone="iniciais").status_code, 303)
            self.assertEqual(self.postar("/conta/icone", icone="dragao").status_code, 400)
        self.assertEqual([c.args for c in atualizar.call_args_list], [(7, "panda"), (7, None)])

    def test_trocar_senha_avisa_por_email(self):
        with patch("safeclick.conta.conta_db.trocar_senha", return_value="ana@example.test") as trocar:
            resposta = self.postar("/conta/senha", senha_atual="senha antiga bem longa",
                                   nova_senha="uma frase nova bem longa", confirmar_senha="uma frase nova bem longa")
        self.assertEqual(resposta.status_code, 303)
        trocar.assert_called_once()
        self.assertEqual(trocar.call_args.args[:3], (7, "senha antiga bem longa", "uma frase nova bem longa"))
        self.assertEqual(self.agendar.call_args.args[1], "ana@example.test")
        self.assertEqual(self.limite.call_args.args, ("troca_senha", "7", 5))

    def test_erros_da_troca_de_senha_reabrem_a_janela(self):
        casos = (
            ({"nova_senha": "curta", "confirmar_senha": "curta"}, None, 400, "15 a 128"),
            ({"nova_senha": "uma frase nova bem longa", "confirmar_senha": "outra frase nova longa"}, None, 400, "iguais"),
            ({"nova_senha": "senha antiga bem longa", "confirmar_senha": "senha antiga bem longa"}, None, 400, "diferente da atual"),
            ({"nova_senha": "aaaaaaaaaaaaaaa", "confirmar_senha": "aaaaaaaaaaaaaaa"}, None, 400, "Evite repetições"),
            ({"nova_senha": "souza gosta de cafe", "confirmar_senha": "souza gosta de cafe"}, None, 400, "o seu nome"),
            ({}, conta_db.SenhaAtualIncorreta(), 400, "senha atual está incorreta"),
            ({}, Error("banco"), 503, "Nada foi alterado"),
        )
        for campos, erro, status, texto in casos:
            with self.subTest(texto=texto), patch("safeclick.conta.conta_db.trocar_senha", side_effect=erro) as trocar:
                dados = {"senha_atual": "senha antiga bem longa", "nova_senha": "uma frase nova bem longa",
                         "confirmar_senha": "uma frase nova bem longa", **campos}
                resposta = self.postar("/conta/senha", **dados)
                html = resposta.get_data(as_text=True)
                self.assertEqual(resposta.status_code, status)
                self.assertIn(texto, html)
                self.assertIn("data-abrir-ao-carregar", html)
                if erro is None:
                    trocar.assert_not_called()
        self.agendar.assert_not_called()

    def test_limite_de_tentativas_da_troca_de_senha(self):
        self.limite.return_value = False
        with patch("safeclick.conta.conta_db.trocar_senha") as trocar:
            resposta = self.postar("/conta/senha", senha_atual="x" * 20,
                                   nova_senha="uma frase nova bem longa", confirmar_senha="uma frase nova bem longa")
        self.assertEqual(resposta.status_code, 429)
        trocar.assert_not_called()

    def test_encerrar_outras_sessoes(self):
        with patch("safeclick.conta.conta_db.encerrar_outras_sessoes", return_value=2) as encerrar:
            resposta = self.postar("/conta/sessoes")
        self.assertEqual(resposta.status_code, 303)
        self.assertEqual(encerrar.call_args.args[0], 7)
        self.assertIn("2 sessões encerradas.", self.client.get("/conta/").get_data(as_text=True))

    def test_exige_login_csrf_e_campos_exatos(self):
        self.assertEqual(self.client.post("/conta/nome", data={"nome": "Ana"}).status_code, 400)
        self.assertEqual(self.postar("/conta/nome", nome="Ana", perfil="administrador").status_code, 400)
        with self.client.session_transaction() as sessao:
            sessao.clear()
        self.assertEqual(self.client.get("/conta/").status_code, 302)


if __name__ == "__main__":
    unittest.main()
