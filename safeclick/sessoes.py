# substituindo todo o conteúdo de sessões para o controle de sessões no safeclick

import hashlib
import secrets
from functools import wraps

from flask import abort, current_app, request, session
from flask_login import LoginManager, UserMixin, current_user
from psycopg import Error

from safeclick.db import conectar_banco
from safeclick.auditoria_db import registrar_evento


login_manager = LoginManager()
login_manager.login_view = "autenticacao.login"
login_manager.login_message = "Entre na sua conta para acessar esta página."
login_manager.login_message_category = "aviso"


class Usuario(UserMixin):
    def __init__(self, dados):
        self.id = dados["id"]
        self.nome = dados["nome"]
        self.email = dados["email"]
        self.perfil = dados["perfil"]


def _hash_sessao(token):
    if not isinstance(token, str) or len(token) != 43:
        return None

    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def criar_sessao(usuario_id, token_pendente):
    token_pendente_hash = _hash_sessao(token_pendente)
    if token_pendente_hash is None:
        return None

    token = secrets.token_urlsafe(32)

    with conectar_banco() as conexao:
        # coordena a abertura da sessao com a redefinicao de senha
        usuario = conexao.execute(
            """
            SELECT id FROM public.usuarios
            WHERE id = %s AND mfa_confirmado_em IS NOT NULL
            FOR NO KEY UPDATE
            """,
            (usuario_id,),
        ).fetchone()

        if usuario is None:
            return None

        # uma pendencia aprovada pode criar somente uma sessao
        pendencia = conexao.execute(
            """
            DELETE FROM public.logins_pendentes
            WHERE usuario_id = %s
              AND token_hash = %s
              AND concluido_em IS NOT NULL
              AND expira_em > clock_timestamp()
            RETURNING usuario_id
            """,
            (usuario_id, token_pendente_hash),
        ).fetchone()

        if pendencia is None:
            return None

        conexao.execute(
            """
            DELETE FROM public.sessoes_autenticadas
            WHERE usuario_id = %s AND expira_em <= clock_timestamp()
            """,
            (usuario_id,),
        )

        conexao.execute(
            """
            INSERT INTO public.sessoes_autenticadas
                (token_hash, usuario_id, criada_em, ultima_atividade, expira_em)
            VALUES (
                %s, %s, clock_timestamp(), clock_timestamp(),
                clock_timestamp() + INTERVAL '8 hours'
            )
            """,
            (_hash_sessao(token), usuario_id),
        )

        registrar_evento(
            usuario_id=usuario_id,
            evento="login.sucesso",
            resultado="sucesso",
            recurso_tipo="sessao",
            conexao=conexao,
        )

    return token


@login_manager.user_loader
def carregar_usuario(usuario_id):
    try:
        usuario_id = int(usuario_id)
    except (TypeError, ValueError):
        return None

    token_hash = _hash_sessao(session.get("sessao_token"))

    if token_hash is None or not 1 <= usuario_id <= 2147483647:
        return None

    try:
        with conectar_banco() as conexao:
            dados = conexao.execute(
                """
                UPDATE public.sessoes_autenticadas AS sessao
                SET ultima_atividade = clock_timestamp()
                FROM public.usuarios AS usuario
                WHERE sessao.token_hash = %s
                  AND sessao.usuario_id = %s
                  AND usuario.id = sessao.usuario_id
                  AND usuario.mfa_confirmado_em IS NOT NULL
                  AND sessao.expira_em > clock_timestamp()
                  AND sessao.ultima_atividade >
                      clock_timestamp() - INTERVAL '30 minutes'
                RETURNING usuario.id, usuario.nome, usuario.email, usuario.perfil
                """,
                (token_hash, usuario_id),
            ).fetchone()

    except (Error, RuntimeError):
        abort(
            503,
            description="Não foi possível verificar sua sessão. Tente novamente em instantes.",
        )

    return Usuario(dados) if dados is not None else None


def revogar_sessao():
    usuario_id = int(current_user.id)

    with conectar_banco() as conexao:
        conexao.execute(
            """
            DELETE FROM public.sessoes_autenticadas
            WHERE token_hash = %s AND usuario_id = %s
            """,
            (_hash_sessao(session.get("sessao_token")), usuario_id),
        )
        registrar_evento(
            usuario_id=usuario_id,
            evento="logout.realizado",
            resultado="sucesso",
            recurso_tipo="sessao",
            conexao=conexao,
        )


def exigir_perfis(*perfis):
    def decorar(funcao):
        @wraps(funcao)
        def verificar_acesso(*args, **kwargs):
            if not current_user.is_authenticated:
                return login_manager.unauthorized()

            if current_user.perfil not in perfis:
                try:
                    registrar_evento(
                        usuario_id=int(current_user.id),
                        evento="acesso.negado",
                        resultado="negado",
                        recurso_tipo="pagina",
                        detalhes={"area": request.blueprint},
                    )
                except (Error, RuntimeError):
                    current_app.logger.exception("Falha ao registrar acesso negado")
                    abort(503, description="Não foi possível verificar o acesso agora.")
                abort(
                    403,
                    description="Você não tem permissão para acessar esta página.",
                )

            return funcao(*args, **kwargs)

        return verificar_acesso

    return decorar
