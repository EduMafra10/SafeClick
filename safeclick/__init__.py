
import os

from flask import Flask, redirect, render_template, request, send_from_directory, session, url_for
from werkzeug.exceptions import HTTPException
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_login import current_user

from safeclick.config import carregar_configuracao
from safeclick.conteudos import conteudos_bp, paginas_bp
from safeclick.db import verificar_banco
from safeclick.privacidade import privacidade
from safeclick.quizzes import quizzes
from safeclick.simulacoes import simulacoes
from safeclick.simulacoes_db import importar_cenarios_cli
from safeclick.sessoes import login_manager
from safeclick.autenticacao import autenticacao
from safeclick.auditoria import auditoria
from safeclick.twilio_api import verificar_twilio
from safeclick.emails import verificar_email
from safeclick.recuperacao import recuperacao
from safeclick.aceite_termos import aceite_termos
from safeclick.senhas import senhas
from safeclick.conta import conta
from safeclick.administracao import administracao
from safeclick.painel import painel
from safeclick.conquistas import conquistas
from safeclick.avaliacoes import avaliacoes
from safeclick.exclusao_conta import exclusao_conta, reativacao_conta
from safeclick.moderacao_avaliacoes import moderacao_avaliacoes
from safeclick.mascara import mascarar_email
from flask_wtf.csrf import generate_csrf


REPOSITORIO = "https://github.com/EduMafra10/SafeClick"

# tudo vem do próprio site; o estilo inline cobre os atributos style dos templates
POLITICA_CONTEUDO = "; ".join((
    "default-src 'self'",
    "script-src 'self'",
    "style-src 'self' 'unsafe-inline'",
    "img-src 'self' data:",
    "font-src 'self'",
    "connect-src 'self'",
    "worker-src 'self'",
    "object-src 'none'",
    "base-uri 'self'",
    "form-action 'self'",
    "frame-ancestors 'self'",
))


def create_app():
    app = Flask(__name__)

    app.config.update(carregar_configuracao())

    # na Vercel o IP do usuário chega pelo proxy
    if os.environ.get("VERCEL"):
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)

    login_manager.init_app(app)

    app.add_template_filter(mascarar_email, "mascarar_email")
    app.jinja_env.globals["gerar_csrf"] = generate_csrf

    app.register_blueprint(autenticacao)
    app.register_blueprint(recuperacao)

    app.register_blueprint(conteudos_bp)
    app.register_blueprint(paginas_bp)
    app.register_blueprint(simulacoes)
    app.register_blueprint(quizzes)
    app.register_blueprint(auditoria)
    app.register_blueprint(administracao)
    app.register_blueprint(painel)
    app.register_blueprint(conquistas)
    app.register_blueprint(avaliacoes)
    app.register_blueprint(exclusao_conta)
    app.register_blueprint(reativacao_conta)
    app.register_blueprint(moderacao_avaliacoes)

    app.register_blueprint(privacidade)
    app.register_blueprint(aceite_termos)
    app.register_blueprint(senhas)
    app.register_blueprint(conta)

    app.cli.add_command(verificar_banco)
    app.cli.add_command(verificar_twilio)
    app.cli.add_command(verificar_email)
    app.cli.add_command(importar_cenarios_cli)

    @app.after_request
    def proteger_cabecalhos(resposta):
        resposta.headers.setdefault("X-Content-Type-Options", "nosniff")
        resposta.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
        resposta.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        resposta.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        if resposta.mimetype == "text/html":
            resposta.headers.setdefault("Content-Security-Policy", POLITICA_CONTEUDO)
        if request.is_secure:
            resposta.headers.setdefault("Strict-Transport-Security", "max-age=31536000")
        return resposta

    @app.errorhandler(HTTPException)
    def exibir_erro(erro):
        if erro.code in (None, 413) or erro.code < 400 or request.path.startswith("/laboratorio-senhas/desafio"):
            return erro
        # mantém a mensagem própria da rota, quando ela existir
        detalhe = erro.description if erro.description != type(erro).description else None
        resposta = erro.get_response()
        resposta.set_data(render_template("erro.html", codigo=erro.code, detalhe=detalhe))
        resposta.content_type = "text/html; charset=utf-8"
        return resposta

    @app.errorhandler(500)
    def exibir_erro_interno(erro):
        return render_template("erro.html", codigo=500), 500

    @app.after_request
    def evitar_cache_paginas_autenticadas(resposta):
        if session.get("_user_id"):
            resposta.headers["Cache-Control"] = "no-store"
        return resposta

    @app.get("/")
    def inicio():
        if not current_user.is_authenticated:
            return render_template("inicio.html", repositorio=REPOSITORIO)
        if current_user.perfil == "administrador":
            return redirect(url_for("administracao.inicio"))
        return redirect(url_for("painel.exibir"))

    @app.get("/favicon.ico")
    def favicon():
        return send_from_directory(
            os.path.join(app.static_folder, "img"), "favicon.ico", mimetype="image/vnd.microsoft.icon", max_age=86400
        )

    return app
