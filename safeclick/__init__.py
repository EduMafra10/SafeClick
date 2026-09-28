# reformulei nosso init por conta do login
import os

from flask import Flask, redirect, session, url_for

from safeclick.conteudos import conteudos_bp
from safeclick.db import verificar_banco
from safeclick.privacidade import privacidade
from safeclick.quizzes import quizzes
from safeclick.simulacoes import simulacoes
from safeclick.sessoes import login_manager
from safeclick.autenticacao import autenticacao
from safeclick.auditoria import auditoria
from safeclick.twilio_api import verificar_twilio

def create_app():
    app = Flask(__name__)

    # carrega a conexao do banco e a chava que assina a sessao
    app.config["DATABASE_URL"] = os.getenv("DATABASE_URL")
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")

    if not app.config["SECRET_KEY"]:
        raise RuntimeError("Configure a variável SECRET_KEY antes de iniciar a aplicação")

    # configuracao da integracao com o twilio
    app.config["TWILIO_ACCOUNT_SID"] = os.getenv("TWILIO_ACCOUNT_SID")
    app.config["TWILIO_AUTH_TOKEN"] = os.getenv("TWILIO_AUTH_TOKEN")
    app.config["TWILIO_VERIFY_SERVICE_SID"] = os.getenv("TWILIO_VERIFY_SERVICE_SID")

    # restringe o acesso e o envio do cookie de sessao pelo navegador
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["SESSION_COOKIE_SECURE"] = (
        os.getenv("SESSION_COOKIE_SECURE", "false").lower() == "true"
    )

    login_manager.init_app(app)

    # registra as paginas de autenticacao
    app.register_blueprint(autenticacao)

    # registra as tres funcionalidades ja desenvolvidas
    app.register_blueprint(conteudos_bp)
    app.register_blueprint(simulacoes)
    app.register_blueprint(quizzes)
    app.register_blueprint(auditoria)

    # Registra as páginas de LGPD (política de privacidade e termos de uso).
    app.register_blueprint(privacidade)

    # Disponibiliza o comando de verificação do banco.
    app.cli.add_command(verificar_banco)
    app.cli.add_command(verificar_twilio)

    @app.after_request
    def evitar_cache_paginas_autenticadas(resposta):
        if session.get("_user_id"):
            resposta.headers["Cache-Control"] = "no-store"
        return resposta

    @app.get("/")
    def inicio():
        # coloquei a simulacao como pagina inicial (podem mudar se quiserem)
        return redirect(url_for("simulacoes.conta_bloqueada"))

    return app

