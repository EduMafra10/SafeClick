import os
import unittest
from datetime import date, datetime, timezone
from unittest.mock import MagicMock, patch

from flask_login import UserMixin, login_user

from safeclick import create_app
from safeclick import auditoria_textos as textos
from safeclick.auditoria_db import EVENTOS_PERMITIDOS, usuario_autenticado_id
from safeclick.sessoes import login_manager


class UsuarioTeste(UserMixin):
    def __init__(self, perfil):
        self.id = 7
        self.perfil = perfil


class AuditoriaAcessoTeste(unittest.TestCase):
    def setUp(self):
        with patch.dict(os.environ, {"SECRET_KEY": "chave-de-teste", "DATABASE_URL": "postgresql://nao-usado"}):
            self.app = create_app()
        self.app.testing = True
        self.client = self.app.test_client()
        aceite = patch(
            "safeclick.aceite_termos.usuario_aceitou_termos_atuais",
            return_value=True,
        )
        aceite.start()
        self.addCleanup(aceite.stop)

    def autenticar(self, perfil):
        usuario = UsuarioTeste(perfil)
        with self.client.session_transaction() as sessao:
            sessao["_user_id"] = str(usuario.id)
            sessao["_fresh"] = True
        return patch.object(login_manager, "_user_callback", return_value=usuario)

    def test_visitante_nao_acessa_logs(self):
        resposta = self.client.get("/auditoria/")
        self.assertEqual(resposta.status_code, 302)
        self.assertIn("/login", resposta.headers["Location"])

    def test_identificacao_usa_a_sessao_autenticada(self):
        self.assertIsNone(usuario_autenticado_id())
        with self.app.test_request_context("/"):
            self.assertIsNone(usuario_autenticado_id())
            login_user(UsuarioTeste("usuario"))
            self.assertEqual(usuario_autenticado_id(), 7)

    def test_usuario_comum_nao_acessa_logs(self):
        with self.autenticar("usuario"), patch("safeclick.auditoria.registrar_evento") as registrar:
            resposta = self.client.get("/auditoria/")
        self.assertEqual(resposta.status_code, 403)
        self.assertEqual(registrar.call_args.kwargs["evento"], "acesso.negado")

    def registro(self, **alteracoes):
        dados = {
            "id": 12,
            "criado_em": datetime(2026, 9, 27, 12, 30, tzinfo=timezone.utc),
            "usuario_id": 7,
            "usuario_nome": "Administrador",
            "usuario_email": "admin@example.com",
            "usuario_perfil": "administrador",
            "evento": "quiz.concluido",
            "resultado": "sucesso",
            "recurso_tipo": "tentativa_quiz",
            "recurso_id": "20",
            "detalhes": {"quiz_id": 1, "pontuacao": 4, "total_questoes": 5},
        }
        dados.update(alteracoes)
        return dados

    def consultar(self, url, registros=None):
        resumo = {"total": 1, "falhas": 0, "negados": 0, "usuarios": 1}
        conexao = MagicMock()
        contexto = MagicMock()
        contexto.__enter__.return_value = conexao
        with self.autenticar("administrador"), \
             patch("safeclick.auditoria.conectar_banco", return_value=contexto), \
             patch("safeclick.auditoria.registrar_evento") as registrar, \
             patch("safeclick.auditoria.listar_eventos",
                   return_value=(registros if registros is not None else [self.registro()], resumo)) as listar:
            resposta = self.client.get(url)
        html = " ".join(resposta.get_data(as_text=True).split())
        return resposta, html, registrar, listar

    def test_administrador_consulta_lista_paginada(self):
        resposta, html, registrar, listar = self.consultar("/auditoria/?evento=quiz.concluido&pagina=1")

        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.headers["Cache-Control"], "no-store")
        self.assertEqual(registrar.call_args.kwargs["evento"], "auditoria.consultada")
        self.assertEqual(listar.call_args.kwargs["eventos"], {"quiz.concluido"})
        for trecho in ("Quiz respondido", "Acertou 4 de 5", "Quiz nº 1",
                       "Tentativa de quiz nº 20", "admin@example.com", "Admin"):
            with self.subTest(trecho=trecho):
                self.assertIn(trecho, html)

    def test_mostra_horario_de_brasilia(self):
        _, html, _, _ = self.consultar("/auditoria/")
        self.assertIn("27/09/2026", html)
        self.assertIn("09:30:00", html)

    def test_filtra_e_exibe_o_salvamento_da_avaliacao(self):
        registros = [self.registro(evento="avaliacao.salva", recurso_tipo="avaliacao_quiz",
                                   recurso_id=None, detalhes={})]
        resposta, html, _, listar = self.consultar("/auditoria/?evento=avaliacao.salva", registros)

        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(listar.call_args.kwargs["eventos"], {"avaliacao.salva"})
        self.assertIn("Avaliação salva", html)
        self.assertIn("Avaliação de quiz", html)

    def test_explica_registro_sem_usuario(self):
        registros = [
            self.registro(usuario_id=None, usuario_nome=None, usuario_email=None, usuario_perfil=None,
                          evento="login.falha", resultado="falha", recurso_tipo="autenticacao",
                          recurso_id=None, detalhes={"etapa": "senha", "motivo": "email_nao_cadastrado"}),
            self.registro(usuario_id=None, usuario_nome=None, usuario_email=None, usuario_perfil=None,
                          evento="api.consultada", recurso_tipo="api", recurso_id=None,
                          detalhes={"servico": "twilio_verify", "operacao": "criar_fator_totp"}),
        ]
        _, html, _, _ = self.consultar("/auditoria/", registros)
        for trecho in ("Visitante não identificado", "E-mail não cadastrado", "Etapa: senha",
                       "Não registrado (anterior à atualização)",
                       "Twilio (verificação em duas etapas)", "Ação: gerar o QR Code do autenticador"):
            with self.subTest(trecho=trecho):
                self.assertIn(trecho, html)

    def test_detalhes_com_html_sao_escapados(self):
        registros = [self.registro(evento="evento.desconhecido", detalhes={"campo": "<script>x</script>"})]
        _, html, _, _ = self.consultar("/auditoria/", registros)
        self.assertNotIn("<script>x</script>", html)
        self.assertIn("&lt;script&gt;", html)

    def test_filtros_de_categoria_resultado_e_usuario(self):
        _, _, _, listar = self.consultar("/auditoria/?evento=cat:acesso&resultado=falha&usuario=maria")
        consulta = listar.call_args.kwargs
        self.assertIn("login.falha", consulta["eventos"])
        self.assertNotIn("quiz.concluido", consulta["eventos"])
        self.assertEqual(consulta["resultado"], "falha")
        self.assertEqual(consulta["busca"], "maria")
        self.assertIsNone(consulta["usuario_id"])

    def test_usuario_por_numero(self):
        for valor in ("7", "%237"):
            with self.subTest(valor=valor):
                _, _, _, listar = self.consultar(f"/auditoria/?usuario={valor}")
                self.assertEqual(listar.call_args.kwargs["usuario_id"], 7)
                self.assertIsNone(listar.call_args.kwargs["busca"])

    def test_datas_usam_o_dia_de_brasilia(self):
        _, _, _, listar = self.consultar("/auditoria/?inicio=2026-11-01&fim=2026-11-04")
        consulta = listar.call_args.kwargs
        self.assertEqual(consulta["data_inicio"], datetime(2026, 11, 1, 3, 0, tzinfo=timezone.utc))
        self.assertEqual(consulta["data_fim"], datetime(2026, 11, 5, 3, 0, tzinfo=timezone.utc))

    def test_filtro_invalido_mostra_aviso_e_e_ignorado(self):
        casos = {
            "evento=nao.existe": "O evento escolhido não existe.",
            "resultado=talvez": "O resultado escolhido não existe.",
            "inicio=31/12/2026": "Use datas válidas",
            "inicio=2026-11-05&fim=2026-11-01": "igual ou anterior",
        }
        for consulta, aviso in casos.items():
            with self.subTest(consulta=consulta):
                resposta, html, _, listar = self.consultar(f"/auditoria/?{consulta}&pagina=abc")
                self.assertEqual(resposta.status_code, 200)
                self.assertIn(aviso, html)
                dados = listar.call_args.kwargs
                self.assertIsNone(dados["eventos"])
                self.assertIsNone(dados["resultado"])
                self.assertIsNone(dados["data_inicio"])
                self.assertEqual(dados["pagina"], 1)

    def test_consultas_a_auditoria_ficam_ocultas_por_padrao(self):
        casos = {
            "/auditoria/": {"auditoria.consultada"},
            "/auditoria/?consultas=1": None,
            "/auditoria/?evento=auditoria.consultada": None,
        }
        for url, esperado in casos.items():
            with self.subTest(url=url):
                _, _, _, listar = self.consultar(url)
                self.assertEqual(listar.call_args.kwargs["excluir_eventos"], esperado)

    def test_atalhos_de_periodo_mantem_os_outros_filtros(self):
        with patch("safeclick.auditoria._hoje", return_value=date(2026, 11, 5)):
            _, html, _, listar = self.consultar("/auditoria/?resultado=falha&inicio=2026-10-30&fim=2026-11-05")
        self.assertIn(
            'href="/auditoria/?resultado=falha&amp;inicio=2026-10-30&amp;fim=2026-11-05" aria-current="true"',
            html,
        )
        self.assertIn('href="/auditoria/?resultado=falha&amp;inicio=2026-11-05&amp;fim=2026-11-05"', html)

    def test_nome_do_usuario_filtra_pela_conta(self):
        _, html, _, _ = self.consultar("/auditoria/?resultado=sucesso")
        self.assertIn('href="/auditoria/?resultado=sucesso&amp;usuario=7"', html)

    def test_mostra_motivo_da_falha_do_twilio(self):
        registros = [self.registro(evento="api.consultada", resultado="falha", recurso_tipo="api",
                                   recurso_id=None, detalhes={
                                       "servico": "twilio_verify", "operacao": "criar_fator_totp",
                                       "erro": "configuracao_ausente"})]
        _, html, _, _ = self.consultar("/auditoria/", registros)
        self.assertIn("Motivo: configuração do Twilio ausente no servidor (.env)", html)


class AuditoriaTextosTeste(unittest.TestCase):
    def test_todo_evento_permitido_tem_titulo_e_categoria(self):
        for evento in EVENTOS_PERMITIDOS:
            with self.subTest(evento=evento):
                self.assertNotEqual(textos.titulo_evento(evento), evento)
                self.assertNotEqual(textos.categoria_evento(evento), "Outros")

    def test_detalhe_desconhecido_vira_chave_e_valor(self):
        self.assertEqual(
            textos.descrever_detalhes("evento.novo", {"campo_novo": 3}), ["Campo novo: 3"]
        )


if __name__ == "__main__":
    unittest.main()
