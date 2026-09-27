import re

import click
from flask import current_app
from flask.cli import with_appcontext
from requests.exceptions import RequestException
from twilio.base.exceptions import TwilioRestException
from twilio.http.http_client import TwilioHttpClient
from twilio.rest import Client

def obter_servico_twilio():
    account_sid = current_app.config.get("TWILIO_ACCOUNT_SID")
    auth_token = current_app.config.get("TWILIO_AUTH_TOKEN")
    service_sid = current_app.config.get("TWILIO_VERIFY_SERVICE_SID")

    if not all((account_sid, auth_token, service_sid)):
        raise RuntimeError(
            "Configure TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN e "
            "TWILIO_VERIFY_SERVICE_SID no .env"
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

def criar_fator_totp(identidade):
    try:
        entidade = obter_servico_twilio().entities(str(identidade))
        fator = entidade.new_factors.create(
            friendly_name="SafeClick",
            factor_type="totp",
        )
    except (TwilioRestException, RequestException):
        raise RuntimeError(
            "Nao foi possivel iniciar a configuraçao do autenticador."
        ) from None

    # a URI sera usada para gerar o QRCode da ativaçao
    binding = fator.binding if isinstance(fator.binding, dict) else {}
    uri = binding.get("uri")

    if not fator.sid or not isinstance(uri, str) or not uri.startswith("otpauth://totp/"):
        raise RuntimeError("A Twilio não retornou uma configuração válida.")

    return {"sid": fator.sid, "uri": uri}

def validar_ativacao_totp(identidade, fator_sid, codigo):
    if not isinstance(codigo, str) or not re.fullmatch(r"[0-9]{6}", codigo):
        return False

    try:
        entidade = obter_servico_twilio().entities(str(identidade))
        fator = entidade.factors(fator_sid).update(auth_payload=codigo)
    except (TwilioRestException, RequestException):
        raise RuntimeError(
            "Nao foi possivel confirmar a ativaçao do autenticador."
        ) from None

    return fator.status == "verified"

def validar_codigo_totp(identidade, fator_sid, codigo):
    if not isinstance(codigo, str) or not re.fullmatch(r"[0-9]{6}", codigo):
        return False

    try:
        entidade = obter_servico_twilio().entities(str(identidade))
        desafio = entidade.challenges.create(
            factor_sid=fator_sid,
            auth_payload=codigo,
        )
    except (TwilioRestException, RequestException):
        raise RuntimeError(
            "Nao foi possivel verificar o código do autenticador."
        ) from None

    # apenas um desafio aprovado comprova o segundo fator do login
    return desafio.status == "approved"

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
        raise RuntimeError("Não foi possível consultar o autenticador.") from None
    except RequestException:
        raise RuntimeError("Não foi possível consultar o autenticador.") from None

    if fator.status not in("unverified", "verified"):
        raise RuntimeError("A Twilio retornou uma situação inesperada.")

    return fator.status

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
            raise RuntimeError ("Não foi possível reiniciar a configuração.") from None
    except RequestException:
        raise RuntimeError("Não foi possível reiniciar a configuração.") from None