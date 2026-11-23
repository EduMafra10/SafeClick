import hashlib
import re
import secrets

from werkzeug.security import check_password_hash

from safeclick.auditoria_db import registrar_evento
from safeclick.db import conectar_banco

PRAZO_ARREPENDIMENTO = "30 days"
PRAZO_EMAIL = "6 months"


class ContaJaExcluida(Exception):
    pass


def _hash_token(token):
    if not isinstance(token, str) or not re.fullmatch(r"[A-Za-z0-9_-]{43}", token):
        return None
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def buscar_dados_exclusao(usuario_id):
    with conectar_banco() as conexao:
        return conexao.execute(
            """
            SELECT
                usuario.senha_hash,
                usuario.mfa_identidade,
                usuario.mfa_fator_sid,
                usuario.perfil = 'administrador' AND NOT EXISTS (
                    SELECT 1
                    FROM public.usuarios AS outro
                    WHERE outro.perfil = 'administrador'
                      AND outro.excluida_em IS NULL
                      AND outro.exclusao_solicitada_em IS NULL
                      AND outro.id <> usuario.id
                ) AS unico_administrador
            FROM public.usuarios AS usuario
            WHERE usuario.id = %s
              AND usuario.excluida_em IS NULL
              AND usuario.exclusao_solicitada_em IS NULL
            """,
            (usuario_id,),
        ).fetchone()


def registrar_recusa(usuario_id, motivo):
    with conectar_banco() as conexao:
        registrar_evento(
            usuario_id=usuario_id,
            evento="conta.exclusao_agendada",
            resultado="falha",
            recurso_tipo="usuario",
            recurso_id=usuario_id,
            detalhes={"motivo": motivo},
            conexao=conexao,
        )


def _salvar_link(conexao, usuario_id):
    token = secrets.token_urlsafe(32)
    conexao.execute(
        """
        INSERT INTO public.reativacoes_conta (usuario_id, token_hash, criado_em, expira_em)
        SELECT id, %s, CURRENT_TIMESTAMP, exclusao_solicitada_em + %s::interval
        FROM public.usuarios
        WHERE id = %s
        ON CONFLICT (usuario_id) DO UPDATE
        SET token_hash = EXCLUDED.token_hash,
            criado_em = EXCLUDED.criado_em,
            expira_em = EXCLUDED.expira_em
        """,
        (_hash_token(token), PRAZO_ARREPENDIMENTO, usuario_id),
    )
    return token


def agendar_exclusao(usuario_id):
    with conectar_banco() as conexao:
        conta = conexao.execute(
            """
            SELECT id
            FROM public.usuarios
            WHERE id = %s
              AND excluida_em IS NULL
              AND exclusao_solicitada_em IS NULL
            FOR UPDATE
            """,
            (usuario_id,),
        ).fetchone()

        if conta is None:
            raise ContaJaExcluida

        dados = conexao.execute(
            """
            UPDATE public.usuarios
            SET exclusao_solicitada_em = CURRENT_TIMESTAMP,
                mfa_identidade = gen_random_uuid(),
                mfa_fator_sid = NULL,
                mfa_confirmado_em = NULL
            WHERE id = %s
            RETURNING nome, email,
                to_char((exclusao_solicitada_em + %s::interval) AT TIME ZONE 'America/Sao_Paulo',
                        'DD/MM/YYYY') AS excluir_em
            """,
            (usuario_id, PRAZO_ARREPENDIMENTO),
        ).fetchone()

        conexao.execute(
            "DELETE FROM public.sessoes_autenticadas WHERE usuario_id = %s", (usuario_id,)
        )
        conexao.execute(
            "DELETE FROM public.logins_pendentes WHERE usuario_id = %s", (usuario_id,)
        )
        conexao.execute(
            "DELETE FROM public.recuperacoes_senha WHERE usuario_id = %s", (usuario_id,)
        )

        token = _salvar_link(conexao, usuario_id)

        registrar_evento(
            usuario_id=usuario_id,
            evento="conta.exclusao_agendada",
            resultado="sucesso",
            recurso_tipo="usuario",
            recurso_id=usuario_id,
            conexao=conexao,
        )

    return {**dados, "token": token}


def gerar_novo_link(usuario_id):
    with conectar_banco() as conexao:
        dados = conexao.execute(
            """
            SELECT email,
                to_char((exclusao_solicitada_em + %s::interval) AT TIME ZONE 'America/Sao_Paulo',
                        'DD/MM/YYYY') AS excluir_em
            FROM public.usuarios
            WHERE id = %s
              AND excluida_em IS NULL
              AND exclusao_solicitada_em > CURRENT_TIMESTAMP - %s::interval
            FOR UPDATE
            """,
            (PRAZO_ARREPENDIMENTO, usuario_id, PRAZO_ARREPENDIMENTO),
        ).fetchone()

        if dados is None:
            return None

        return {**dados, "token": _salvar_link(conexao, usuario_id)}


def reativar_conta(token, senha):
    token_hash = _hash_token(token)
    if token_hash is None:
        return None

    with conectar_banco() as conexao:
        conta = conexao.execute(
            """
            SELECT usuario.id, usuario.email, usuario.senha_hash
            FROM public.usuarios AS usuario
            JOIN public.reativacoes_conta AS link ON link.usuario_id = usuario.id
            WHERE link.token_hash = %s
              AND link.expira_em > CURRENT_TIMESTAMP
              AND usuario.excluida_em IS NULL
              AND usuario.exclusao_solicitada_em IS NOT NULL
            FOR UPDATE OF usuario
            """,
            (token_hash,),
        ).fetchone()

        if conta is None:
            return None

        if not check_password_hash(conta["senha_hash"], senha):
            registrar_evento(
                usuario_id=conta["id"],
                evento="conta.reativada",
                resultado="falha",
                recurso_tipo="usuario",
                recurso_id=conta["id"],
                detalhes={"motivo": "senha_incorreta"},
                conexao=conexao,
            )
            return {"senha_incorreta": True, "usuario_id": conta["id"]}

        conexao.execute(
            "UPDATE public.usuarios SET exclusao_solicitada_em = NULL WHERE id = %s",
            (conta["id"],),
        )
        conexao.execute(
            "DELETE FROM public.reativacoes_conta WHERE usuario_id = %s", (conta["id"],)
        )
        registrar_evento(
            usuario_id=conta["id"],
            evento="conta.reativada",
            resultado="sucesso",
            recurso_tipo="usuario",
            recurso_id=conta["id"],
            conexao=conexao,
        )

    return {"usuario_id": conta["id"], "email": conta["email"]}


def aplicar_prazos(conexao=None):
    if conexao is None:
        with conectar_banco() as nova_conexao:
            return aplicar_prazos(nova_conexao)

    anonimizadas = conexao.execute(
        """
        WITH vencidas AS (
            SELECT id, email
            FROM public.usuarios
            WHERE excluida_em IS NULL
              AND exclusao_solicitada_em <= CURRENT_TIMESTAMP - %(prazo)s::interval
            FOR UPDATE SKIP LOCKED
        ),
        guardadas AS (
            INSERT INTO public.contas_excluidas (usuario_id, email_guardado, descartar_em)
            SELECT id, email, CURRENT_TIMESTAMP + %(prazo_email)s::interval
            FROM vencidas
            ON CONFLICT (usuario_id) DO NOTHING
        ),
        links AS (
            DELETE FROM public.reativacoes_conta
            WHERE usuario_id IN (SELECT id FROM vencidas)
        )
        UPDATE public.usuarios AS usuario
        SET nome = NULL,
            email = NULL,
            senha_hash = NULL,
            mfa_fator_sid = NULL,
            mfa_confirmado_em = NULL,
            excluida_em = CURRENT_TIMESTAMP
        FROM vencidas
        WHERE usuario.id = vencidas.id
        RETURNING usuario.id
        """,
        {"prazo": PRAZO_ARREPENDIMENTO, "prazo_email": PRAZO_EMAIL},
    ).fetchall()

    for conta in anonimizadas:
        registrar_evento(
            usuario_id=conta["id"],
            evento="conta.excluida",
            resultado="sucesso",
            recurso_tipo="usuario",
            recurso_id=conta["id"],
            detalhes={"origem": "fim_do_prazo"},
            conexao=conexao,
        )

    conexao.execute(
        "DELETE FROM public.contas_excluidas WHERE descartar_em <= CURRENT_TIMESTAMP"
    )

    return [conta["id"] for conta in anonimizadas]


def desvincular_autenticador(usuario_id):
    with conectar_banco() as conexao:
        conexao.execute(
            """
            UPDATE public.usuarios
            SET mfa_fator_sid = NULL, mfa_confirmado_em = NULL
            WHERE id = %s AND excluida_em IS NULL
            """,
            (usuario_id,),
        )
