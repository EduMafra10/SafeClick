import re
from functools import wraps

import click
from flask import current_app
from flask.cli import with_appcontext
from psycopg import Error
from requests.exceptions import RequestException
from twilio.base.exceptions import TwilioRestException
from twilio.http.http_client import TwilioHttpClient
from twilio.rest import Client

from safeclick.auditoria_db import registrar_evento


class ErroTwilio(RuntimeError):
    """Falha do Twilio com um tipo curto, seguro para o log (sem dados sensíveis)."""

    def __init__(self, mensagem, tipo, codigo=None):
        super().__init__(mensagem)
        self.tipo = tipo
        self.codigo = codigo


def _erro_twilio(mensagem, erro):
    if isinstance(erro, TwilioRestException):
        if erro.status in (401, 403):
            tipo = "credenciais_recusadas"
        elif erro.status == 429:
            tipo = "limite_twilio"
        elif erro.status and erro.status >= 500:
            tipo = "servico_indisponivel"
        else:
            tipo = "recusado_pelo_twilio"
        return ErroTwilio(mensagem, tipo, erro.code)
    return ErroTwilio(mensagem, "sem_conexao")

def _codigo_valido(codigo):
    return isinstance(codigo, str) and bool(re.fullmatch(r"[0-9]{6}", codigo))

def auditar_consulta_api(operacao, *, exige_codigo=False):
    """Registra o resultado da chamada sem incluir dados enviados à Twilio."""

    def decorar(funcao):
        @wraps(funcao)
        def executar(*args, usuario_id=None, **kwargs):
            codigo = kwargs.get("codigo", args[2] if len(args) > 2 else None)
            if exige_codigo and not _codigo_valido(codigo):
                return funcao(*args, **kwargs)

            try:
                resultado = funcao(*args, **kwargs)
            except (RuntimeError, TwilioRestException, RequestException) as erro:
                _registrar_consulta_api(operacao, "falha", usuario_id, erro)
                raise

            _registrar_consulta_api(operacao, "sucesso", usuario_id)
            return resultado

        return executar

    return decorar

def _registrar_consulta_api(operacao, resultado, usuario_id=None, erro=None):
    # usuario_id vem do login pendente: a senha da conta já foi conferida.
    detalhes = {"servico": "twilio_verify", "operacao": operacao}
    if erro is not None:
        detalhes["erro"] = getattr(erro, "tipo", "falha_inesperada")
        if getattr(erro, "codigo", None):
            detalhes["codigo_twilio"] = erro.codigo
    try:
        registrar_evento(
            usuario_id=usuario_id,
            evento="api.consultada",
            resultado=resultado,
            recurso_tipo="api",
            detalhes=detalhes,
        )
    except (Error, RuntimeError):
        current_app.logger.warning("Falha ao registrar consulta da API na auditoria")

def obter_servico_twilio():
    account_sid = current_app.config.get("TWILIO_ACCOUNT_SID")
    auth_token = current_app.config.get("TWILIO_AUTH_TOKEN")
    service_sid = current_app.config.get("TWILIO_VERIFY_SERVICE_SID")

    if not all((account_sid, auth_token, service_sid)):
        raise ErroTwilio(
            "Configure TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN e "
            "TWILIO_VERIFY_SERVICE_SID no .env",
            "configuracao_ausente",
        )

    # limita o tempo que de espera da resposta da API
    cliente = Client(
        account_sid,
        auth_token,
        http_client=TwilioHttpClient(timeout=10),
    )

    return cliente.verify.v2.services(service_sid)

@click.command("verificar-twilio")
@with_appcontext
def verificar_twilio():
    try:
        # consulta o servico sem enviar codigo e sem criar algum usuario
        servico = obter_servico_twilio().fetch()
    except RuntimeError as erro:
        raise click.ClickException(str(erro)) from None
    except TwilioRestException as erro:
        raise click.ClickException(
            f"Falha ao consultar a Twilio: HTTP {erro.status}, "
            f"código {erro.code}."
        ) from None
    except RequestException:
        raise click.ClickException(
            "Não foi possível conectar à Twilio."
            "Confira sua conexão e tente novamente."
        ) from None

    click.echo(f"Conexão realizada com sucesso. Serviço: {servico.friendly_name}")

@auditar_consulta_api("criar_fator_totp")
def criar_fator_totp(identidade):
    try:
        entidade = obter_servico_twilio().entities(str(identidade))
        fator = entidade.new_factors.create(
            friendly_name=f"SafeClick - {identidade}",
            factor_type="totp",
        )
    except (TwilioRestException, RequestException) as erro:
        raise _erro_twilio(
            "Nao foi possivel iniciar a configuraçao do autenticador.", erro
        ) from None

    # a URI sera usada para gerar o QRCode da ativaçao
    binding = fator.binding if isinstance(fator.binding, dict) else {}
    uri = binding.get("uri")

    if not fator.sid or not isinstance(uri, str) or not uri.startswith("otpauth://totp/"):
        raise RuntimeError("A Twilio não retornou uma configuração válida.")

    return {"sid": fator.sid, "uri": uri}

@auditar_consulta_api("validar_ativacao_totp", exige_codigo=True)
def validar_ativacao_totp(identidade, fator_sid, codigo):
    if not _codigo_valido(codigo):
        return False

    try:
        entidade = obter_servico_twilio().entities(str(identidade))
        fator = entidade.factors(fator_sid).update(auth_payload=codigo)
    except (TwilioRestException, RequestException) as erro:
        raise _erro_twilio(
            "Nao foi possivel confirmar a ativaçao do autenticador.", erro
        ) from None

    return fator.status == "verified"

@auditar_consulta_api("validar_codigo_totp", exige_codigo=True)
def validar_codigo_totp(identidade, fator_sid, codigo):
    if not _codigo_valido(codigo):
        return False

    try:
        entidade = obter_servico_twilio().entities(str(identidade))
        desafio = entidade.challenges.create(
            factor_sid=fator_sid,
            auth_payload=codigo,
        )
    except (TwilioRestException, RequestException) as erro:
        raise _erro_twilio(
            "Nao foi possivel verificar o código do autenticador.", erro
        ) from None

    # apenas um desafio aprovado comprova o segundo fator do login
    return desafio.status == "approved"

@auditar_consulta_api("consultar_fator_totp")
def consultar_fator_totp(identidade, fator_sid):
    try:
        fator = (
            obter_servico_twilio()
            .entities(str(identidade))
            .factors(fator_sid)
            .fetch()
        )
    except TwilioRestException as erro:
        if erro.status == 404:
            return None
        raise _erro_twilio("Não foi possível consultar o autenticador.", erro) from None
    except RequestException as erro:
        raise _erro_twilio("Não foi possível consultar o autenticador.", erro) from None

    if fator.status not in("unverified", "verified"):
        raise RuntimeError("A Twilio retornou uma situação inesperada.")

    return fator.status

@auditar_consulta_api("remover_fator_totp")
def remover_fator_totp(identidade, fator_sid):
    try:
        (
            obter_servico_twilio()
            .entities(str(identidade))
            .factors(fator_sid)
            .delete()
        )
    except TwilioRestException as erro:
        if erro.status != 404:
            raise _erro_twilio("Não foi possível reiniciar a configuração.", erro) from None
    except RequestException as erro:
        raise _erro_twilio("Não foi possível reiniciar a configuração.", erro) from None