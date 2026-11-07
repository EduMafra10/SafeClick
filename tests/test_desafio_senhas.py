import os
import unittest
from html.parser import HTMLParser
from unittest.mock import MagicMock, patch

from psycopg import Error

from safeclick import create_app
from safeclick import desafio_senhas
from safeclick.auditoria_db import EVENTOS_PERMITIDOS
from safeclick.desafio_senhas import (
    LISTA_SENHAS,
    TOTAL_RODADAS,
    escolha_correta,
    sortear_partida,
)
from safeclick.desafios_senha_db import salvar_desafio_senha
from safeclick.pwned_api import ServicoSenhasIndisponivel, contar_vazamentos
from safeclick.sessoes import Usuario


# Contagens fictícias: cada senha de exemplo recebe um número diferente.
CONTAGENS = {senha: (indice + 1) * 1000 for indice, senha in enumerate(LISTA_SENHAS)}


class CamposHTML(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.campos = {}
        self.feed(html)

    def handle_starttag(self, tag, atributos):
        atributos = dict(atributos)
        if tag == "input" and atributos.get("name"):
            self.campos[atributos["name"]] = atributos


class ContarVazamentosTeste(unittest.TestCase):
    def test_envia_so_o_prefixo_e_encontra_o_sufixo(self):
        # SHA-1 de "123456" = 7C4A8D09CA3762AF61E59520943DC26494F8941B
        resposta = (
            "0018A45C4D1DEF81644B54AB7F969B88D65:3\r\n"
            "D09CA3762AF61E59520943DC26494F8941B:179000000\r\n"
            "00D4F6E8FA6EECAD2A3AA415EEC418D38EC:0"
        )
        with patch("safeclick.pwned_api.consultar_prefixo_senha", return_value=resposta) as consultar:
            self.assertEqual(contar_vazamentos("123456"), 179000000)
        consultar.assert_called_once_with("7C4A8")

    def test_senha_fora_da_base_conta_zero(self):
        with patch("safeclick.pwned_api.consultar_prefixo_senha",
                   return_value="0018A45C4D1DEF81644B54AB7F969B88D65:3"):
            self.assertEqual(contar_vazamentos("123456"), 0)

    def test_falha_da_api_e_repassada(self):
        with patch("safeclick.pwned_api.consultar_prefixo_senha",
                   side_effect=ServicoSenhasIndisponivel("fora do ar")):
            with self.assertRaises(ServicoSenhasIndisponivel):
                contar_vazamentos("123456")


class RegrasDesafioTeste(unittest.TestCase):
    def test_partida_tem_duplas_sem_repetir_senha(self):
        for _ in range(20):
            pares = sortear_partida()
            indices = [indice for par in pares for indice in par]
            self.assertEqual(len(pares), TOTAL_RODADAS)
            self.assertEqual(len(set(indices)), TOTAL_RODADAS * 2)
            self.assertTrue(all(0 <= indice < len(LISTA_SENHAS) for indice in indices))

    def test_escolha_correta(self):
        self.assertTrue(escolha_correta([10, 5], 0))
        self.assertFalse(escolha_correta([10, 5], 1))
        # Empate: as duas respostas são aceitas.
        self.assertTrue(escolha_correta([7, 7], 0))
        self.assertTrue(escolha_correta([7, 7], 1))

    def test_cache_expira(self):
        desafio_senhas.limpar_cache()
        with patch("safeclick.desafio_senhas.time.monotonic", return_value=1000):
            desafio_senhas.guardar_contagem("123456", 42)
            self.assertEqual(desafio_senhas.contagem_em_cache("123456"), 42)
        with patch("safeclick.desafio_senhas.time.monotonic", return_value=1000 + 13 * 3600):
            self.assertIsNone(desafio_senhas.contagem_em_cache("123456"))

    def test_toda_senha_tem_licao(self):
        for senha, licao in desafio_senhas.SENHAS_EXEMPLO.items():
            with self.subTest(senha=senha):
                self.assertTrue(licao.strip())


class SalvarDesafioTeste(unittest.TestCase):
    def setUp(self):
        self.conexao = MagicMock()
        contexto = MagicMock()
        contexto.__enter__.return_value = self.conexao
        abrir = patch("safeclick.desafios_senha_db.conectar_banco", return_value=contexto)
        abrir.start()
        self.addCleanup(abrir.stop)
        registrar = patch("safeclick.desafios_senha_db.registrar_evento")
        self.registrar = registrar.start()
        self.addCleanup(registrar.stop)

    def test_salva_e_audita_na_mesma_transacao(self):
        self.conexao.execute.return_value.fetchone.return_value = {"id": 9}
        self.assertTrue(salvar_desafio_senha(7, 3, 5, "token-da-partida"))
        consulta, parametros = self.conexao.execute.call_args.args
        self.assertIn("ON CONFLICT (token_partida) DO NOTHING", consulta)
        self.assertEqual(parametros, (7, 3, 5, "token-da-partida"))
        self.registrar.assert_called_once_with(
            usuario_id=7, evento="desafio_senha.concluido", resultado="sucesso",
            recurso_tipo="desafio_senha", recurso_id=9,
            detalhes={"acertos": 3, "total": 5}, conexao=self.conexao,
        )

    def test_partida_repetida_nao_duplica(self):
        self.conexao.execute.return_value.fetchone.return_value = None
        self.assertFalse(salvar_desafio_senha(7, 3, 5, "token-da-partida"))
        self.registrar.assert_not_called()

    def test_evento_esta_liberado_na_auditoria(self):
        self.assertIn("desafio_senha.concluido", EVENTOS_PERMITIDOS)


class RotasDesafioTeste(unittest.TestCase):
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
        desafio_senhas.limpar_cache()
        self.app = create_app()
        self.app.config.update(TESTING=True, WTF_CSRF_ENABLED=True)
        self.client = self.app.test_client()
        self.substituir(patch(
            "safeclick.aceite_termos.usuario_aceitou_termos_atuais", return_value=True
        ))
        self.limite = self.substituir(patch(
            "safeclick.senhas.permitir_tentativa", return_value=True
        ))
        self.auditoria = self.substituir(patch("safeclick.senhas.registrar_evento"))
        self.contar = self.substituir(patch(
            "safeclick.senhas.contar_vazamentos", side_effect=lambda senha: CONTAGENS[senha]
        ))
        self.salvar = self.substituir(patch(
            "safeclick.senhas.salvar_desafio_senha", return_value=True
        ))
        self.entrar()

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

    def token(self):
        html = self.client.get("/laboratorio-senhas/").get_data(as_text=True)
        return CamposHTML(html).campos["csrf_token"]["value"]

    def iniciar(self):
        resposta = self.client.post(
            "/laboratorio-senhas/desafio/iniciar", data={"csrf_token": self.token()}
        )
        self.assertEqual(resposta.status_code, 200)
        return resposta.get_json()

    def responder(self, rodada, escolha):
        return self.client.post("/laboratorio-senhas/desafio/responder", data={
            "csrf_token": self.token(), "rodada": str(rodada), "escolha": str(escolha),
        })

    def melhor_escolha(self, opcoes):
        return 0 if CONTAGENS[opcoes[0]] >= CONTAGENS[opcoes[1]] else 1

    def test_iniciar_devolve_a_primeira_rodada(self):
        dados = self.iniciar()
        self.assertEqual(dados["rodada"], 1)
        self.assertEqual(dados["total"], TOTAL_RODADAS)
        self.assertEqual(len(dados["opcoes"]), 2)
        self.assertTrue(set(dados["opcoes"]) <= set(LISTA_SENHAS))
        self.limite.assert_called_once_with("desafio_senha", "7", 10)

    def test_partida_completa_salva_o_resultado(self):
        dados = self.iniciar()
        for numero in range(1, TOTAL_RODADAS + 1):
            # Acerta as rodadas ímpares e erra as pares: 3 acertos no fim.
            certa = self.melhor_escolha(dados["opcoes"])
            escolha = certa if numero % 2 else 1 - certa
            resposta = self.responder(numero, escolha)
            self.assertEqual(resposta.status_code, 200)
            dados_resposta = resposta.get_json()
            self.assertEqual(dados_resposta["correta"], numero % 2 == 1)
            self.assertEqual(
                [item["vazamentos"] for item in dados_resposta["resultado"]],
                [CONTAGENS[senha] for senha in dados["opcoes"]],
            )
            self.assertTrue(all(item["licao"] for item in dados_resposta["resultado"]))
            if numero < TOTAL_RODADAS:
                dados = dados_resposta["proxima"]
                self.assertEqual(dados["rodada"], numero + 1)

        self.assertEqual(dados_resposta["final"], {"acertos": 3, "total": TOTAL_RODADAS})
        self.assertIsNone(dados_resposta["proxima"])
        self.salvar.assert_called_once()
        usuario, acertos, total, token = self.salvar.call_args.args
        self.assertEqual((usuario, acertos, total), (7, 3, TOTAL_RODADAS))
        self.assertTrue(len(token) >= 40)
        with self.client.session_transaction() as sessao:
            self.assertNotIn("desafio_senha", sessao)

    def test_nao_responde_a_mesma_rodada_duas_vezes(self):
        self.iniciar()
        self.assertEqual(self.responder(1, 0).status_code, 200)
        self.assertEqual(self.responder(1, 1).status_code, 409)
        self.assertEqual(self.responder(3, 0).status_code, 409)

    def test_responder_sem_partida(self):
        self.assertEqual(self.responder(1, 0).status_code, 409)

    def test_rejeita_escolha_ou_rodada_invalidas(self):
        self.iniciar()
        for rodada, escolha in ((1, 2), (1, -1), ("x", 0), (0, 0), (11, 0)):
            with self.subTest(rodada=rodada, escolha=escolha):
                self.assertEqual(self.responder(rodada, escolha).status_code, 400)

    def test_rejeita_csrf_ausente_e_campos_extras(self):
        self.assertEqual(
            self.client.post("/laboratorio-senhas/desafio/iniciar", data={}).status_code, 400
        )
        self.iniciar()
        resposta = self.client.post("/laboratorio-senhas/desafio/responder", data={
            "csrf_token": self.token(), "rodada": "1", "escolha": "0", "acertos": "5",
        })
        self.assertEqual(resposta.status_code, 400)
        self.salvar.assert_not_called()

    def test_usa_cache_e_audita_so_consultas_reais(self):
        dados = self.iniciar()
        self.responder(1, 0)
        self.assertEqual(self.contar.call_count, 2)
        self.assertEqual(self.auditoria.call_count, 2)
        # Uma nova partida com as mesmas senhas não consulta a API de novo.
        with patch("safeclick.senhas.sortear_partida",
                   return_value=[[LISTA_SENHAS.index(s) for s in dados["opcoes"]]] + [[10, 11]] * 4):
            self.iniciar()
        self.responder(1, 0)
        self.assertEqual(self.contar.call_count, 2)

    def test_api_indisponivel_nao_consome_a_rodada(self):
        self.iniciar()
        self.contar.side_effect = ServicoSenhasIndisponivel("fora do ar")
        self.assertEqual(self.responder(1, 0).status_code, 503)
        self.contar.side_effect = lambda senha: CONTAGENS[senha]
        self.assertEqual(self.responder(1, 0).status_code, 200)

    def test_falha_ao_salvar_permite_reenviar_a_ultima_rodada(self):
        dados = self.iniciar()
        for numero in range(1, TOTAL_RODADAS):
            dados = self.responder(numero, 0).get_json()["proxima"]
        self.salvar.side_effect = Error("falha simulada")
        self.assertEqual(self.responder(TOTAL_RODADAS, 0).status_code, 503)
        self.salvar.side_effect = None
        self.assertEqual(self.responder(TOTAL_RODADAS, 0).status_code, 200)

    def test_limite_de_partidas(self):
        self.limite.return_value = False
        resposta = self.client.post(
            "/laboratorio-senhas/desafio/iniciar", data={"csrf_token": self.token()}
        )
        self.assertEqual(resposta.status_code, 429)
        self.assertEqual(resposta.headers["Retry-After"], "300")

    def test_exige_login(self):
        with self.client.session_transaction() as sessao:
            sessao.clear()
        resposta = self.client.post("/laboratorio-senhas/desafio/iniciar")
        self.assertEqual(resposta.status_code, 302)
        self.assertTrue(resposta.location.startswith("/login"))

    def test_respostas_nao_sao_guardadas_em_cache_pelo_navegador(self):
        resposta = self.client.post(
            "/laboratorio-senhas/desafio/iniciar", data={"csrf_token": self.token()}
        )
        self.assertEqual(resposta.headers["Cache-Control"], "no-store")


if __name__ == "__main__":
    unittest.main()