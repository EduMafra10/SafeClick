import os

from flask import Flask, redirect, url_for

from safeclick.conteudos import conteudos_bp
from safeclick.db import verificar_banco
from safeclick.quizzes import quizzes
from safeclick.simulacoes import simulacoes


def create_app():
    app = Flask(__name__)

    # Carrega a conexão do banco e a chave da sessão dos quizzes.
    app.config["DATABASE_URL"] = os.getenv("DATABASE_URL")
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")

    # Registra as três funcionalidades do grupo.
    app.register_blueprint(conteudos_bp)
    app.register_blueprint(simulacoes)
    app.register_blueprint(quizzes)

    # Disponibiliza o comando de verificação do banco.
    app.cli.add_command(verificar_banco)

    @app.get("/")
    def inicio():
        # Mantém a simulação como página inicial.
        return redirect(url_for("simulacoes.conta_bloqueada"))

    return app