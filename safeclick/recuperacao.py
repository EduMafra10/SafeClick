import os
import re
from concurrent.futures import ThreadPoolExecutor
from threading import BoundedSemaphore
from urllib.parse import urlsplit

from flask import Blueprint, current_app, flash, redirect, render_template, request, session, url_for
from psycopg import Error

from safeclick.emails import enviar_email
from safeclick.modelo_email import montar_email
from safeclick.formularios import FormularioRecuperarSenha, FormularioRedefinirSenha
from safeclick.limites import permitir_tentativa
from safeclick.recuperacao_db import (
    buscar_recuperacao,
    cancelar_recuperacao,
    criar_recuperacao,
    redefinir_senha,
)


recuperacao = Blueprint("recuperacao", __name__)

_EXECUTOR = ThreadPoolExecutor(max_workers=2, thread_name_prefix="recuperacao")
_VAGAS = BoundedSemaphore(20)


def _base_publica():
    base = current_app.config.get("APP_BASE_URL", "").rstrip("/")
    try:
        partes = urlsplit(base)
        porta = partes.port
        valida = (
            bool(partes.hostname)
            and not any(c.isspace() for c in base)
            and not partes.username
            and not partes.password
            and not partes.path
            and not partes.query
            and not partes.fragment
            and (porta is None or 1 <= porta <= 65535)
            and (
                partes.scheme == "https"
                or (
                    partes.scheme == "http"
                    and partes.hostname in {"localhost", "127.0.0.1", "::1"}
                )
            )
        )
    except ValueError:
        valida = False
    if not valida:
        raise RuntimeError("Configure APP_BASE_URL com a origem publica do site.")
    return base


def _executar(app, funcao, argumentos):
    try:
        with app.app_context():
            funcao(*argumentos)
    except Exception as erro:

        app.logger.error(
            "Falha no processamento de e-mail da recuperacao de senha (%s).",
            type(erro).__name__,
        )
    finally:
        _VAGAS.release()


def _agendar(funcao, *argumentos):
    if not _VAGAS.acquire(blocking=False):
        return False
    if os.environ.get("VERCEL"):
        _executar(current_app._get_current_object(), funcao, argumentos)
        return True
    try:
        _EXECUTOR.submit(
            _executar, current_app._get_current_object(), funcao, argumentos
        )
    except RuntimeError:
        _VAGAS.release()
        return False
    return True


def _enviar_recuperacao(email, endereco_pagina):
    dados = criar_recuperacao(email)
    if dados is None:
        return

    link = f"{endereco_pagina}#token={dados['token']}"
    try:
        texto, html = montar_email(
            "Segurança da conta",
            "Vamos criar uma nova senha",
            ["Recebemos um pedido para redefinir a senha da sua conta no SafeClick. "
             "O link abaixo vale por 30 minutos e pode ser usado uma única vez. "
             "Se você pedir outro link, este deixa de funcionar."],
            botao=("Redefinir senha", link),
            aviso=("Não foi você?", "Ignore esta mensagem. Sua senha continua a mesma."),
        )
        enviar_email(dados["email"], "SafeClick - Recuperação de senha", texto, html=html)
    except Exception:

        cancelar_recuperacao(dados["token"])
        raise


def _avisar_redefinicao(email):
    texto, html = montar_email(
        "Segurança da conta",
        "Sua senha foi alterada",
        ["A senha da sua conta no SafeClick foi redefinida e as sessões anteriores foram encerradas. "
         "Para entrar novamente, use a nova senha e o código do autenticador."],
        aviso=("Não foi você?", "Fale com a equipe pelo canal informado na Política de Privacidade do site."),
    )
    enviar_email(email, "SafeClick - Sua senha foi alterada", texto, html=html)


@recuperacao.before_request
def limitar_tamanho_formulario():
    request.max_content_length = 16 * 1024


@recuperacao.after_request
def proteger_resposta(resposta):
    resposta.headers["Cache-Control"] = "no-store"
    resposta.headers["Referrer-Policy"] = "no-referrer"
    resposta.headers["X-Robots-Tag"] = "noindex, nofollow"
    return resposta


@recuperacao.route("/recuperar-senha", methods=["GET", "POST"])
def solicitar():
    formulario = FormularioRecuperarSenha()
    erro = None
    status = 200

    if formulario.validate_on_submit():
        try:
            endereco = _base_publica() + url_for("recuperacao.redefinir")
            ip = request.remote_addr or "desconhecido"
            permitido = permitir_tentativa("recuperacao_ip", ip, 5)
            if permitido:
                permitido = permitir_tentativa(
                    "recuperacao_email", formulario.email.data, 3
                )

            if permitido and not _agendar(
                _enviar_recuperacao, formulario.email.data, endereco
            ):
                raise RuntimeError("Fila indisponivel.")

        except (Error, RuntimeError):
            erro = "Não foi possível receber a solicitação. Tente novamente em instantes."
            status = 503
        else:

            flash(
                "Se houver uma conta com esse e-mail e o limite de solicitações "
                "não tiver sido atingido, enviaremos um link de recuperação. "
                "Confira também o spam. Aguarde cinco minutos antes de tentar novamente.",
                "aviso",
            )
            return redirect(url_for("recuperacao.solicitar"), code=303)
    elif request.method == "POST":
        status = 400

    return render_template(
        "autenticacao/recuperar_senha.html", formulario=formulario, erro=erro
    ), status


@recuperacao.route("/redefinir-senha", methods=["GET", "POST"])
def redefinir():
    formulario = FormularioRedefinirSenha()
    erro = None
    status = 200
    link_invalido = False
    token = request.form.get("token_recuperacao", "") if request.method == "POST" else ""
    if not re.fullmatch(r"[A-Za-z0-9_-]{43}", token):
        token = ""

    if formulario.validate_on_submit():
        try:
            ip = request.remote_addr or "desconhecido"
            if not permitir_tentativa("redefinicao_ip", ip, 5):
                erro = "Muitas tentativas. Aguarde cinco minutos e tente novamente."
                status = 429
            elif buscar_recuperacao(token) is None:
                link_invalido = True
            else:

                usuario = redefinir_senha(token, formulario.senha.data)
                if usuario is None:
                    link_invalido = True
                else:
                    session.clear()
                    if not _agendar(_avisar_redefinicao, usuario["email"]):
                        current_app.logger.error("Aviso de troca de senha nao agendado.")
                    flash(
                        "Senha alterada! Entre com a nova senha e o código do autenticador.",
                        "sucesso",
                    )
                    return redirect(url_for("autenticacao.login"), code=303)
        except (Error, RuntimeError, ValueError):
            erro = "Não foi possível redefinir a senha. Tente novamente em instantes."
            status = 503
    elif request.method == "POST":
        status = 400

    if link_invalido:
        token = ""
        erro = "Este link é inválido, expirou ou já foi utilizado. Solicite um novo link."
        status = 400

    return render_template(
        "autenticacao/redefinir_senha.html",
        formulario=formulario,
        erro=erro,
        token_recuperacao=token,
        link_invalido=link_invalido,
    ), status
