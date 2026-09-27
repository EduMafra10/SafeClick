import hashlib
from base64 import b64encode
from contextlib import contextmanager
from urllib.parse import parse_qs, urlsplit

import qrcode
from qrcode.image.svg import SvgPathFillImage

from safeclick.limites import permitir_tentativa
from safeclick.db import conectar_banco
from safeclick.logins_db import buscar_login_pendente, reservar_tentativa_mfa
from safeclick.twilio_api import (
    consultar_fator_totp,
    criar_fator_totp,
    remover_fator_totp,
    validar_ativacao_totp,
    validar_codigo_totp,
)

class ErroMFA(Exception):
    def __init__(self, mensagem, status=400):
        super().__init__(mensagem)
        self.status = status

@contextmanager
def _bloquear_pendencia(token):
    pendencia = buscar_login_pendente(token)

    if pendencia is None:
        raise ErroMFA(
            "O prazo terminou. Volte ao login e informe sua senha.",
            401,
        )

    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()

    with conectar_banco() as conexao:
        # mantem a mesma ordem de bloqueio usado no inicio do login
        usuario = conexao.execute(
            """
            SELECT id, nome, email, perfil, mfa_identidade,
                   mfa_fator_sid, mfa_confirmado_em
            FROM public.usuarios
            WHERE id = %s
            FOR UPDATE
            """,
            (pendencia["usuario_id"],),
        ).fetchone()

        atual = conexao.execute(
            """
            SELECT usuario_id, tentativas
            FROM public.logins_pendentes
            WHERE token_hash = %s
              AND expira_em > clock_timestamp()
              AND concluido_em IS NULL
            FOR UPDATE
            """,
            (token_hash,),
        ).fetchone()

        if usuario is None or atual is None:
            raise ErroMFA(
                "Esta tentativa não está mais disponível. Entre novamente.",
                401,
            )

        yield conexao, usuario, atual, token_hash

def configurar_autenticador(token, fator_anterior):
    with _bloquear_pendencia(token) as (conexao, usuario, pendencia, _):
        if pendencia["tentativas"] >= 5:
            raise ErroMFA(
                "Limite atingido. Aguarde alguns minutos e entre novamente.",
                429,
            )

        fator_sid = usuario["mfa_fator_sid"]

        if usuario["mfa_confirmado_em"] is not None:
            raise ErroMFA(
                "O autenticador já está configurado. Informe o código do aplicativo.",
                409,
            )

        if(fator_sid or "") != (fator_anterior or ""):
            raise ErroMFA(
                "A configuração mudou. Recarregue esta página.",
                409,
            )

        if not permitir_tentativa("qr", str(usuario["id"]), 3):
            raise ErroMFA(
                "Limite de configurações atingido. Aguarde cinco minutos e tente novamente.",
                429,
            )

        if fator_sid:
            estado = consultar_fator_totp(
                usuario["mfa_identidade"],
                fator_sid,
            )

            if estado == "verified":
                raise ErroMFA(
                    "O autenticador já foi ativado. Informe o código do aplicativo.",
                    409,
                )

            if estado == "unverified":
                remover_fator_totp(
                    usuario["mfa_identidade"],
                    fator_sid,
                )

        fator = criar_fator_totp(usuario["mfa_identidade"])

        chave = parse_qs(
            urlsplit(fator["uri"]).query
        ).get("secret", [None])[0]

        if not chave:
            raise RuntimeError(
                "Não foi possível obter a configuração do autenticador."
            )

        imagem = qrcode.make(
            fator["uri"],
            image_factory=SvgPathFillImage,
        )

        qr_code = b64encode(imagem.to_string()).decode("ascii")

        conexao.execute(
            """
            UPDATE public.usuarios
            SET mfa_fator_sid = %s
            WHERE id = %s
            """,
            (fator["sid"], usuario["id"]),
        )

    # a imagem fica somente na resposta e nao vai para o cookie e nem pro nosso banco
    return {"qr_code": qr_code, "chave": chave}

def confirmar_autenticador(token, codigo):
    # grava a tentativa antes da chamada externa, mesmo se houver falha da API
    if reservar_tentativa_mfa(token) is None:
        raise ErroMFA(
            "Prazo ou limite de tentativas atingido. Entre novamente mais tarde.",
            429,
        )

    with _bloquear_pendencia(token) as (conexao, usuario, _, token_hash):
        identidade = usuario["mfa_identidade"]
        fator_sid = usuario["mfa_fator_sid"]

        if not fator_sid:
            raise ErroMFA(
                "Configure o autenticador antes de informar o código."
            )

        estado = consultar_fator_totp(identidade, fator_sid)

        if estado is None:
            raise ErroMFA(
                "A configuração do autenticador não está disponível.",
                503,
            )

        if estado == "unverified":
            if not validar_ativacao_totp(identidade, fator_sid, codigo):
                raise ErroMFA(
                    "Código inválido. Confira o aplicativo e tente novamente."
                )

            conexao.execute(
                """
                UPDATE public.usuarios
                SET mfa_confirmado_em = CURRENT_TIMESTAMP
                WHERE id = %s
                  AND mfa_confirmado_em IS NULL
                """,
                (usuario["id"],),
            )

            # ativar o aplicativo nao abre uma sessao de login
            return None

        if not validar_codigo_totp(identidade, fator_sid, codigo):
            raise ErroMFA(
                "Código inválido. Confira o aplicativo e tente novamente."
            )

        concluido = conexao.execute(
            """
            UPDATE public.logins_pendentes
            SET concluido_em = clock_timestamp()
            WHERE token_hash = %s
              AND expira_em > clock_timestamp()
              AND concluido_em IS NULL
            RETURNING usuario_id
            """,
            (token_hash,),
        ).fetchone()

        if concluido is None:
            raise ErroMFA(
                "O prazo terminou. Volte ao login e informe sua senha.",
                401,
            )

        conexao.execute(
            """
            UPDATE public.usuarios
            SET mfa_confirmado_em = COALESCE(
                mfa_confirmado_em,
                CURRENT_TIMESTAMP
            )
            WHERE id = %s
            """,
            (usuario["id"],),
        )

    return usuario
