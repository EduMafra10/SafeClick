import psycopg
from flask import Blueprint, abort, redirect, render_template, request, url_for
from safeclick.sessoes import exigir_perfis
from flask_login import current_user
from flask_wtf import FlaskForm
from safeclick.cenarios_simulacao import CENARIOS

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


@simulacoes.before_request
@exigir_perfis("usuario", "administrador")
def verificar_acesso_simulacoes():
    return None


@simulacoes.get("/")
def listar():
    return render_template("lista_simulacoes.html", cenarios=CENARIOS)


# Mantem o endereço e o nome da rota que o sistema ja utiliza
@simulacoes.route("/conta-bloqueada", methods=["GET", "POST"])
def conta_bloqueada():
    return _processar_cenario("conta_bloqueada")


# Identifica os outros cenarios pelo trecho final do endereço.
@simulacoes.route("/<slug>", methods=["GET", "POST"])
def executar(slug):
    for identificador, cenario in CENARIOS.items():
        if cenario["slug"] == slug:
            return _processar_cenario(identificador)

    abort(404)


# Usa o mesmo processamento para todos os cenarios cadastrados.
def _processar_cenario(identificador):
    cenario = CENARIOS[identificador]

    #define as alternativas e os feedbacks desse cenario
    opcoes = cenario["opcoes"]
    url_simulacao = url_for("simulacoes.executar", slug=cenario["slug"])

    #na abertura da pagina, ainda nao existe escolha processada
    formulario = FlaskForm()
    resultado = None
    erro = None
    status = 200

    if request.method == "POST" and not formulario.validate_on_submit():
        erro = "Recarregue a página e envie sua resposta novamente."
        status = 400

    elif request.method == "POST":
        #usa uma string vazia caso o formulário nao envie a escolha
        opcao_escolhida = request.form.get("opcao", "")

        #valida no servidor pois o formulario pode ser enviado com dados alterados
        resultado = opcoes.get(opcao_escolhida)

        if resultado is None:
            erro = "Selecione uma opção válida para responder à simulação."
            status = 400
        else:
            try:
                #o cenario é definido pela rota e a opcao ja passou pela validacao
                salvar_tentativa_simulacao(
                    current_user.id,
                    identificador,
                    opcao_escolhida,
                )
            except (psycopg.Error, RuntimeError):
                #qualquer falha que possa impedir a confirmacao de que a tentativa foi gravada
                resultado = None
                erro = (
                    "Nao foi possivel confirmar o registro da sua tentativa. "
                    "Tente novamente mais tarde."
                )
                status = 503
            else:
                #apos salvar, o navegador abre o resultado por GET
                return redirect(
                    url_for(
                        "simulacoes.executar",
                        slug=cenario["slug"],
                        resultado=opcao_escolhida,
                        _anchor="titulo-resultado",
                    ),
                    code=303,
                )

    elif "resultado" in request.args:
        #exibe o feedback indicado na URL para uma alternativa deste cenario
        opcao_resultado = request.args.get("resultado", "")
        resultado = opcoes.get(opcao_resultado)

        if resultado is None:
            erro = "Resultado inválido. Selecione uma alternativa no formulário."
            status = 400

    return render_template(
        "simulacao.html",
        cenario=cenario,
        url_simulacao=url_simulacao,
        formulario=formulario,
        opcoes=opcoes,
        resultado=resultado,
        erro=erro,
    ), status