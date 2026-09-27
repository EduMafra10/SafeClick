import hashlib
import hmac

from flask import current_app

from safeclick.db import conectar_banco

def permitir_tentativa(acao, identificador, limite):
    chave = hmac.new(
        current_app.secret_key.encode("utf-8"),
        f"{acao}:{identificador}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    # confirma a tentiva antes de verificar a senha ou consultar a api
    with conectar_banco() as conexao:
        conexao.execute(
            """
            DELETE FROM public.limites_autenticacao
            WHERE expira_em < CURRENT_TIMESTAMP - INTERVAL '1 day'
            """
        )

        registro = conexao.execute(
            """
            INSERT INTO public.limites_autenticacao
                (chave_hash, tentativas, expira_em)
            VALUES (%s, 1, clock_timestamp() + INTERVAL '5 minutes')
            ON CONFLICT (chave_hash) DO UPDATE
            SET tentativas = CASE
                    WHEN limites_autenticacao.expira_em <= clock_timestamp()
                    THEN 1
                    ELSE limites_autenticacao.tentativas + 1
                END,
                expira_em = CASE
                    WHEN limites_autenticacao.expira_em <= clock_timestamp()
                    THEN EXCLUDED.expira_em
                    ELSE limites_autenticacao.expira_em
                END
            WHERE limites_autenticacao.expira_em <= clock_timestamp()
               OR limites_autenticacao.tentativas < %s
            RETURNING chave_hash
            """,
            (chave, limite),
        ).fetchone()

    return registro is not None