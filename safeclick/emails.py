import smtplib
import ssl
from contextlib import contextmanager
from email.message import EmailMessage
from email.utils import formataddr

import click
from flask import current_app
from flask.cli import with_appcontext

@contextmanager
def conectar_smtp():
    servidor = current_app.config.get("SMTP_HOST")
    porta = current_app.config.get("SMTP_PORT", 587)
    usuario = current_app.config.get("SMTP_USER")
    senha = current_app.config.get("SMTP_PASSWORD")

    if not all((servidor, usuario, senha)):
        raise RuntimeError(
            "Configure SMTP_HOST, SMTP_USER e SMTP_PASSWORD no .env."
        )

    try:
        with smtplib.SMTP(servidor, porta, timeout=10) as conexao:
            #protege a conexao antes de enviar as credenciais
            conexao.ehlo()
            conexao.starttls(context=ssl.create_default_context())
            conexao.ehlo()
            conexao.login(usuario, senha)
            yield conexao
    except smtplib.SMTPAuthenticationError:
        raise RuntimeError(
            "O Gmail recusou a autenticação. Confira SMTP_USER "
            "e a senha de app."
        ) from None
    except (smtplib.SMTPException, OSError):
        raise RuntimeError(
            "Não foi possível concluir a comunicação com o servidor de e-mail. "
            "Confira a conexão, o servidor e a porta configurada."
        ) from None

def enviar_email(destinatario, assunto, texto):
    remetente = current_app.config.get("SMTP_USER")
    nome = current_app.config.get("SMTP_FROM_NAME", "SafeClick")

    if not remetente:
        raise RuntimeError("Configure SMTP_USER no .env.")

    mensagem = EmailMessage()
    mensagem["From"] = formataddr((nome, remetente))
    mensagem["To"] = destinatario
    mensagem["Subject"] = assunto
    mensagem.set_content(texto)

    with conectar_smtp() as conexao:
        conexao.send_message(
            mensagem,
            from_addr=remetente,
            to_addrs=[destinatario],
        )

@click.command("verificar-email")
@with_appcontext
def verificar_email():
    try:
        # verifica a conexao e a autenticacao sem enviar mensagens
        with conectar_smtp():
            pass
    except RuntimeError as erro:
        raise click.ClickException(str(erro)) from None

    click.echo(
        "Conexão e autenticação SMTP realizadas com sucesso. "
        "Nenhum e-mail enviado."
    )