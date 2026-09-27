import hashlib
import secrets

from safeclick.db import conectar_banco

def _hash_token(token):
    if not isinstance(token, str) or len(token) != 43:
        return None

    return hashlib.sha256(token.encode("utf-8")).hexdigest()

def iniciar_login_pendente(usuario_id):
    token = secrets.token_urlsafe(32)

    with conectar_banco() as conexao:
        # serializa o inicio de logins para a mesma conta
        usuario = conexao.execute(
            "SELECT id FROM public.usuarios WHERE id = %s FOR UPDATE",
            (usuario_id,),
        ).fetchone()

        if usuario is None:
            return None

        # uma nova janela só irá comecar apos expiracao ou login concluido
        conexao.execute(
            """
            DELETE FROM public.logins_pendentes
            WHERE usuario_id = %s
              AND (expira_em <= CURRENT_TIMESTAMP OR concluido_em IS NOT NULL)
            """,
            (usuario_id,),
        )

        registro = conexao.execute(
            """
            INSERT INTO public.logins_pendentes (usuario_id, token_hash)
            VALUES (%s, %s)
            ON CONFLICT (usuario_id)
            DO UPDATE SET token_hash = EXCLUDED.token_hash
            WHERE logins_pendentes.tentativas < 5
            RETURNING usuario_id
            """,
            (usuario_id, _hash_token(token)),
        ).fetchone()

    return token if registro is not None else None

def buscar_login_pendente(token):
    token_hash = _hash_token(token)
    if token_hash is None:
        return None

    with conectar_banco() as conexao:
        return conexao.execute(
            """
            SELECT usuario_id, tentativas, expira_em
            FROM public.logins_pendentes
            WHERE token_hash = %s
              AND expira_em > CURRENT_TIMESTAMP
              AND concluido_em IS NULL
            """,
            (token_hash,),
        ).fetchone()

def reservar_tentativa_mfa(token):
    token_hash = _hash_token(token)
    if token_hash is None:
        return None

    # essa funcao conta o envio antes de consultar a twilio
    with conectar_banco() as conexao:
        return conexao.execute(
            """
            UPDATE public.logins_pendentes
            SET tentativas = tentativas + 1
            WHERE token_hash = %s
              AND expira_em > CURRENT_TIMESTAMP
              AND concluido_em IS NULL
              AND tentativas < 5
            RETURNING usuario_id, tentativas
            """,
            (token_hash,)
        ).fetchone()

def concluir_login_pendente(token):
    token_hash = _hash_token(token)
    if token_hash is None:
        return None

    # chamada somente após a aprovacao do segundo fator
    with conectar_banco() as conexao:
        registro = conexao.execute(
             """
            UPDATE public.logins_pendentes
            SET concluido_em = CURRENT_TIMESTAMP
            WHERE token_hash = %s
              AND expira_em > CURRENT_TIMESTAMP
              AND concluido_em IS NULL
              AND tentativas BETWEEN 1 AND 5
            RETURNING usuario_id
            """,
            (token_hash,),
        ).fetchone()

    return registro["usuario_id"] if registro is not None else None