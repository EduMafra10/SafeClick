#Parte feita por Eduardo Mafra, atualizado em 08-09-2026

from flask import Flask, redirect, url_for  #importa a classe usada para a criar a nossa aplicação.
from safeclick.simulacoes import simulacoes

def create_app(): #funçao que inicia o sistema, monta e devolve nossa aplicaçao
    app = Flask(__name__) #cria a aplicacao para informar ao flask o modulo ao qual ela pertence, isso ajuda para localizar recursos do nosso projeto

    app.register_blueprint(simulacoes)

    @app.get("/") #associa o endereço incial do site para a funcao abaixo (inicio), o get é usado para solicitar a informaçao passada
    def inicio():
        return redirect(url_for("simulacoes.conta_bloqueada")) #pagina que irá exibir de simulacoes

    return app

