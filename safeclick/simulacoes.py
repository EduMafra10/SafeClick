import psycopg
from flask import Blueprint, redirect, render_template, request, url_for

from safeclick.db import salvar_tentativa_simulacao
#Blueprint para agrupar as rotas relacionadas as simulaçoes
#render_template para gerar a pagina HTML usando um template e os dados fornecidos pelo Python
#request para consultar as informaçoes da requisiçao atual, como o metodo e os campos que sao enviados pelo formulario

#Agrupa os endereços dessa funcionalidade de simulaçoes
simulacoes = Blueprint(

    "simulacoes",
    __name__,
    url_prefix="/simulacoes",
)

#definir as alternativas e os feedbacks desse cenario de conta bloqueada
OPCOES = {
    "clicar_link": {
        "texto": "Clicar no link e informar meus dados",
        "consequencia": (
            "Nessa situação simulada, seus dados seriam entregues para uma página fraudulenta."
        ),
        "explicacao": (
            "A urgência que o e-mail propoe e a ameaça de bloqueio tentam te induzir a uma ação sem verificação."
        ),
    },
    "responder_email": {
        "texto": (
            "Responder ao e-mail enviando meus dados para confirmar minha identidade."
        ),
        "consequencia": (
            "Nessa situação simulada, seus dados seriam enviados ao remetente que está tentando aplicar a fraude."
        ),
        "explicacao": (
            "Responder a mensagem não confirma a identidade do remetente, nem torna seguro compartilhar informações, principalmente pessoais."
        ),
    },
    "acessar_canal_oficial": {
        "texto": (
            "Abrir o aplicativo ou acessar o site oficial que já tenho conhecimento para verificar se está tudo certo com a conta."
        ),
        "consequencia": (
            "Dessa forma, você evita fornecer seus dados por essa mensagem suspeita e verifica a situação por um canal válido."
        ),
        "explicacao": (
            "A conferência acontece sem depender dos links suspeitos ou dos contatos fornecidos pelo próprio e-mail."
        ),
    },
}

#declarando a rota
@simulacoes.route("/conta-bloqueada", methods=["GET", "POST"])

def conta_bloqueada(): #na abertura da pagina, ainda nao existe escolha processada
    resultado = None
    erro = None
    status = 200

    if request.method == "POST":
        opcao_escolhida = request.form.get("opcao", "") #usa uma string vazia caso o formulário nao envie a escolha
        resultado = OPCOES.get(opcao_escolhida) #valida no servidor pois o formulario pode ser enviado com dados alterados

        if resultado is None:
            erro = "Selecione uma opção válida para responder à simulação."
            status = 400

        else:
            try:
                #o cenario é definido pela rota e a opcao ja passou pela validacao
                salvar_tentativa_simulacao("conta_bloqueada", opcao_escolhida)
            except (psycopg.Error, RuntimeError):
                #qualquer falha que possa impedir a confirmacao de que a tentativa foi gravada
                erro = (
                    "Nao foi possivel confirmar o registro da sua tentativa. "
                    "Tente novamente mais tarde."
                )

                status = 503
            else:
                #apos salvar, o navegador abre o resultado por GET
                return redirect(
                    url_for(
                        "simulacoes.conta_bloqueada",
                        resultado=opcao_escolhida
                    ),
                    code=303,
                )
    elif "resultado" in request.args:
        #exibe o feedback indicado na URL
        opcao_resultado = request.args.get("resultado", "")
        resultado = OPCOES.get(opcao_resultado)

        if resultado is None:
            erro = "Resultado inválido. Selecione uma alternativa no formulário."
            status = 400

    return render_template(
        "simulacao.html",
        opcoes=OPCOES,
        resultado=resultado,
        erro=erro,
    ), status

    