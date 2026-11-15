
from flask import Flask, redirect, session, url_for
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

def create_app():
    app = Flask(__name__)

    app.config.update(carregar_configuracao())

    login_manager.init_app(app)

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

    app.register_blueprint(privacidade)
    app.register_blueprint(aceite_termos)
    app.register_blueprint(senhas)
    app.register_blueprint(conta)

    app.cli.add_command(verificar_banco)
    app.cli.add_command(verificar_twilio)
    app.cli.add_command(verificar_email)
    app.cli.add_command(importar_cenarios_cli)

    @app.after_request
    def evitar_cache_paginas_autenticadas(resposta):
        if session.get("_user_id"):
            resposta.headers["Cache-Control"] = "no-store"
        return resposta

    @app.get("/")
    def inicio():
        if current_user.is_authenticated and current_user.perfil == "administrador":
            return redirect(url_for("administracao.inicio"))
        return redirect(url_for("painel.exibir"))

    return app
