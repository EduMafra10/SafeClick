import os
import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from flask_login import UserMixin, login_user

from safeclick import create_app
from safeclick.auditoria_db import usuario_autenticado_id
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

    def autenticar(self, perfil):
        usuario = UsuarioTeste(perfil)
        with self.client.session_transaction() as sessao:
            sessao["_user_id"] = str(usuario.id)
            sessao["_fresh"] = True
        return patch.object(login_manager, "_user_callback", return_value=usuario)

    def test_visitante_nao_acessa_logs(self):
        resposta = self.client.get("/auditoria/")
        self.assertEqual(resposta.status_code, 401)

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

    def test_administrador_consulta_lista_paginada(self):
        registro = SimpleNamespace(
            id=12,
            criado_em=datetime(2026, 9, 27, 12, 30, tzinfo=timezone.utc),
            usuario_id=7,
            usuario_nome="Administrador",
            evento="quiz.concluido",
            resultado="sucesso",
            recurso_tipo="tentativa_quiz",
            recurso_id="20",
            detalhes={"quiz_id": 1},
        )
        conexao = MagicMock()
        contexto = MagicMock()
        contexto.__enter__.return_value = conexao
        with self.autenticar("administrador"), \
             patch("safeclick.auditoria.conectar_banco", return_value=contexto), \
             patch("safeclick.auditoria.registrar_evento") as registrar, \
             patch("safeclick.auditoria.listar_eventos", return_value=([registro], 1)) as listar:
            resposta = self.client.get("/auditoria/?evento=quiz.concluido&pagina=1")

        self.assertEqual(resposta.status_code, 200)
        self.assertIn(b"quiz.concluido", resposta.data)
        self.assertEqual(resposta.headers["Cache-Control"], "no-store")
        self.assertEqual(registrar.call_args.kwargs["evento"], "auditoria.consultada")
        self.assertEqual(listar.call_args.kwargs["evento"], "quiz.concluido")

    def test_filtro_invalido_nao_consulta_o_banco(self):
        with self.autenticar("administrador"), patch("safeclick.auditoria.conectar_banco") as conectar:
            resposta = self.client.get("/auditoria/?usuario_id=abc")
        self.assertEqual(resposta.status_code, 400)
        conectar.assert_not_called()


if __name__ == "__main__":
    unittest.main()
