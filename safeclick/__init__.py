# reformulei nosso init por conta do login
import os

from flask import Flask, redirect, url_for

from safeclick.conteudos import conteudos_bp
from safeclick.db import verificar_banco
from safeclick.quizzes import quizzes
from safeclick.simulacoes import simulacoes
from safeclick.sessoes import login_manager

def create_app():
    app = Flask(__name__)

    # carrega a conexao do banco e a chava que assina a sessao
    app.config["DATABASE_URL"] = os.getenv("DATABASE_URL")
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")

    if not app.config["SECRET_KEY"]:
        raise RuntimeError("Configure a variável SECRET_KEY antes de iniciar a aplicação")

    # restringe o acesso e o envio do cookie de sessao pelo navegador
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

    login_manager.init_app(app)

    # registra as tres funcionalidades ja desenvolvidas
    app.register_blueprint(conteudos_bp)
    app.register_blueprint(simulacoes)
    app.register_blueprint(quizzes)

    # disponibiliza o comando de verificacao do banco
    app.cli.add_command(verificar_banco)

    @app.get("/")
    def inicio():
        # coloquei a simulacao como pagina inicial (podem mudar se quiserem)
        return redirect(url_for("simulacoes.conta_bloqueada"))

    return app

