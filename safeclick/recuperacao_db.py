import hashlib
import re
import secrets

from werkzeug.security import generate_password_hash
from safeclick.auditoria_db import registrar_evento
from safeclick.db import conectar_banco


def _hash_token(token):
    if not isinstance(token, str):
        return None

    if not re.fullmatch(r"[A-Za-z0-9_-]{43}", token):
        return None

    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def criar_recuperacao(email):
    email = email.strip().lower()
    token = secrets.token_urlsafe(32)

    with conectar_banco() as conexao:
        # organiza as solicitacoes simultaneas para a mesma conta
        usuario = conexao.execute(
            """
            SELECT id, nome, email
            FROM public.usuarios
            WHERE lower(email) = %s
            FOR UPDATE
            """,
            (email,),
        ).fetchone()

        if usuario is None:
            return None

        # uma nova solicitacao substitui o token anterior
        conexao.execute(
            """
            INSERT INTO public.recuperacoes_senha (
                usuario_id, token_hash, criado_em, expira_em, utilizado_em
            )
            VALUES (
                %s, %s, clock_timestamp(),
                clock_timestamp() + INTERVAL '30 minutes', NULL
            )
            ON CONFLICT (usuario_id)
            DO UPDATE SET
                token_hash = EXCLUDED.token_hash,
                criado_em = EXCLUDED.criado_em,
                expira_em = EXCLUDED.expira_em,
                utilizado_em = NULL
            """,
            (usuario["id"], _hash_token(token)),
        )

    # o token original fica disponivel apenas para montar o link do e-mail
    return {
        "usuario_id": usuario["id"],
        "nome": usuario["nome"],
        "email": usuario["email"],
        "token": token,
    }


def buscar_recuperacao(token):
    token_hash = _hash_token(token)
    if token_hash is None:
        return None

    with conectar_banco() as conexao:
        return conexao.execute(
            """
            SELECT usuario_id, expira_em
            FROM public.recuperacoes_senha
            WHERE token_hash = %s
              AND expira_em > clock_timestamp()
              AND utilizado_em IS NULL
            """,
            (token_hash,),
        ).fetchone()


def cancelar_recuperacao(token):
    token_hash = _hash_token(token)
    if token_hash is None:
        return False

    with conectar_banco() as conexao:
        # cancela somente este token, preservando uma solicitacao mais recente
        registro = conexao.execute(
            """
            DELETE FROM public.recuperacoes_senha
            WHERE token_hash = %s
              AND utilizado_em IS NULL
            RETURNING usuario_id
            """,
            (token_hash,),
        ).fetchone()

    return registro is not None

def redefinir_senha(token, nova_senha):
    token_hash = _hash_token(token)
    if token_hash is None:
        return None

    if (
        not isinstance(nova_senha, str)
        or not 15 <= len(nova_senha) <= 128
        or not nova_senha.strip()
    ):
        raise ValueError("Informe uma senha válida com 15 a 128 caracteres.")

    # calcula o hash antes de bloquear registros no banco
    senha_hash = generate_password_hash(nova_senha, method="scrypt")

    with conectar_banco() as conexao:
        # bloqueia primeiro a conta, como no inicio do login
        usuario = conexao.execute(
            """
            SELECT usuario.id, usuario.nome, usuario.email
            FROM public.usuarios AS usuario
            JOIN public.recuperacoes_senha AS recuperacao
                ON recuperacao.usuario_id = usuario.id
            WHERE recuperacao.token_hash = %s
              AND recuperacao.expira_em > clock_timestamp()
              AND recuperacao.utilizado_em IS NULL
            FOR NO KEY UPDATE OF usuario
            """,
            (token_hash,),
        ).fetchone()

        if usuario is None:
            return None

        # confere novamente e marca o token como usado na mesma operacao
        recuperacao = conexao.execute(
            """
            UPDATE public.recuperacoes_senha
            SET utilizado_em = clock_timestamp()
            WHERE usuario_id = %s
              AND token_hash = %s
              AND expira_em > clock_timestamp()
              AND utilizado_em IS NULL
            RETURNING usuario_id
            """,
            (usuario["id"], token_hash),
        ).fetchone()

        if recuperacao is None:
            return None

        conexao.execute(
            """
            UPDATE public.usuarios
            SET senha_hash = %s
            WHERE id = %s
            """,
            (senha_hash, usuario["id"]),
        )

        # encerra as sessoes existentes e as tentativas de login pendentes
        conexao.execute(
            "DELETE FROM public.sessoes_autenticadas WHERE usuario_id = %s",
            (usuario["id"],),
        )
        conexao.execute(
            "DELETE FROM public.logins_pendentes WHERE usuario_id = %s",
            (usuario["id"],),
        )

        # registra a acao sem incluir senha, hash ou token no log
        registrar_evento(
            usuario_id=usuario["id"],
            evento="usuario.senha_redefinida",
            resultado="sucesso",
            recurso_tipo="usuario",
            recurso_id=usuario["id"],
            conexao=conexao,
        )

    return usuario