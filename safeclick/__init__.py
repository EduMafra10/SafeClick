import os

from flask import Flask, redirect, url_for

from safeclick.db import verificar_banco
from safeclick.quizzes import quizzes


def create_app():
    # Configura a aplicação e registra a funcionalidade de quizzes.
    app = Flask(__name__)
    app.config["DATABASE_URL"] = os.getenv("DATABASE_URL")
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")

    app.register_blueprint(quizzes)
    app.cli.add_command(verificar_banco)

    @app.get("/")
    def inicio():
        # Abre a lista dos quizzes na página inicial.
        return redirect(url_for("quizzes.listar_quizzes"))

    return app
