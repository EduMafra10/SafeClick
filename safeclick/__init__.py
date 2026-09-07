#Parte feita por Eduardo Mafra, 07/09/2026

from flask import Flask  #importa a classe usada para a criar a nossa aplicação.

def create_app(): #funçao que inicia o sistema, monta e devolve nossa aplicaçao
    app = Flask(__name__) #cria a aplicacao para informar ao flask o modulo ao qual ela pertence, isso ajuda para localizar recursos do nosso projeto

    @app.get("/") #associa o endereço incial do site para a funcao abaixo (inicio), o get é usado para solicitar a informaçao passada
    def inicio():
        return "SafeClick - Aprenda Antes de clicar" #essa é a mensagem que ira aparecer no navegador 

    return app

