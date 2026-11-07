import psycopg
from flask import Blueprint, abort, redirect, render_template, request, url_for
from flask_login import current_user
from flask_wtf import FlaskForm

from safeclick.sessoes import exigir_perfis
from safeclick.simulacoes_db import (
    SimulacaoAlterada,
    buscar_resultado_simulacao,
    buscar_simulacao_publicada,
    listar_simulacoes_publicadas,
    salvar_tentativa_publicada,
)


simulacoes = Blueprint("simulacoes", __name__, url_prefix="/simulacoes")


@simulacoes.before_request
@exigir_perfis("usuario", "administrador")
def verificar_acesso_simulacoes():
    request.max_content_length = 4096


@simulacoes.get("/")
def listar():
    try:
        cenarios = listar_simulacoes_publicadas()
    except (psycopg.Error, RuntimeError):
        abort(503, description="Não foi possível carregar as simulações agora.")

    return render_template("lista_simulacoes.html", cenarios=cenarios)


# Preserva o endereço e o nome de rota já utilizados pelo sistema.
@simulacoes.route("/conta-bloqueada", methods=["GET", "POST"])
def conta_bloqueada():
    return _processar_cenario("conta-bloqueada")


@simulacoes.route("/<slug>", methods=["GET", "POST"])
def executar(slug):
    return _processar_cenario(slug)


def _carregar_publicada(slug):
    try:
        cenario = buscar_simulacao_publicada(slug)
    except (psycopg.Error, RuntimeError):
        abort(503, description="Não foi possível carregar a simulação agora.")

    if cenario is None:
        abort(404)
    return cenario


def _processar_cenario(slug):
    formulario = FlaskForm()
    resultado = None
    erro = None
    status = 200
    pode_repetir = True

    
    if request.method == "GET" and "tentativa" in request.args:
        valores = request.args.getlist("tentativa")
        valor = valores[0]
        if (
            len(valores) != 1
            or not 1 <= len(valor) <= 10
            or not valor.isascii()
            or not valor.isdecimal()
            or not 1 <= int(valor) <= 2147483647
        ):
            abort(400)

        try:
            registro = buscar_resultado_simulacao(current_user.id, slug, int(valor))
        except (psycopg.Error, RuntimeError):
            abort(503, description="Não foi possível carregar o resultado agora.")

        if registro is None:
            abort(404)
        cenario = registro["cenario"]
        resultado = registro["resultado"]
        pode_repetir = registro["pode_repetir"]
    else:
        cenario = _carregar_publicada(slug)

    if request.method == "POST":
        campos = {"csrf_token", "versao_id", "opcao"}
        if not formulario.validate_on_submit():
            erro = "Recarregue a página e envie sua resposta novamente."
            status = 400
        elif (
            set(request.form) != campos
            or any(len(request.form.getlist(campo)) != 1 for campo in campos)
        ):
            erro = "Selecione uma alternativa e envie novamente."
            status = 400
        elif request.form["versao_id"] != str(cenario["versao_id"]):
            erro = "A simulação foi atualizada. Leia o cenário abaixo antes de responder novamente."
            status = 409
        elif request.form["opcao"] not in cenario["opcoes"]:
            erro = "Selecione uma alternativa válida."
            status = 400
        else:
            try:
                tentativa_id = salvar_tentativa_publicada(
                    current_user.id,
                    slug,
                    cenario["versao_id"],
                    request.form["opcao"],
                )
            except SimulacaoAlterada:
                
                cenario = _carregar_publicada(slug)
                erro = "A simulação foi atualizada. Leia o cenário abaixo antes de responder novamente."
                status = 409
            except ValueError:
                erro = "Selecione uma alternativa válida."
                status = 400
            except (psycopg.Error, RuntimeError):
                erro = "Não foi possível confirmar o registro da sua tentativa. Tente novamente mais tarde."
                status = 503
            else:
                return redirect(
                    url_for(
                        "simulacoes.executar",
                        slug=slug,
                        tentativa=tentativa_id,
                        _anchor="titulo-resultado",
                    ),
                    code=303,
                )

    return render_template(
        "simulacao.html",
        cenario=cenario,
        url_simulacao=url_for("simulacoes.executar", slug=slug),
        formulario=formulario,
        opcoes=cenario["opcoes"],
        resultado=resultado,
        erro=erro,
        pode_repetir=pode_repetir,
    ), status

def listar_simulacoes_administrativas(*, estado="", pagina=1, por_pagina=20):
    
    if not isinstance(estado, str) or estado not in {"", "rascunho", "publicada", "arquivada"}:
        raise ValueError("Estado inválido.")
    if type(pagina) is not int or not 1 <= pagina <= 1000000:
        raise ValueError("Página inválida.")
    if type(por_pagina) is not int or not 1 <= por_pagina <= 100:
        raise ValueError("Quantidade por página inválida.")

    filtro = " WHERE s.estado = %s" if estado else ""
    parametros = [estado] if estado else []

    with conectar_banco() as conexao:
        total = conexao.execute(
            "SELECT COUNT(*) AS total FROM public.simulacoes AS s" + filtro,
            parametros,
        ).fetchone()["total"]

        registros = conexao.execute(
            """
            SELECT
                s.id,
                s.identificador,
                s.slug,
                s.estado,
                COALESCE(
                    NULLIF(v.conteudo->>'titulo', ''),
                    NULLIF(s.rascunho->>'titulo', ''),
                    s.identificador
                ) AS titulo,
                COALESCE(
                    NULLIF(v.conteudo->>'tipo', ''),
                    NULLIF(s.rascunho->>'tipo', ''),
                    ''
                ) AS tipo,
                v.numero AS versao
            FROM public.simulacoes AS s
            LEFT JOIN public.versoes_simulacao AS v
                ON v.simulacao_id = s.id
               AND v.id = s.versao_publicada_id
            """ + filtro + " ORDER BY s.id LIMIT %s OFFSET %s",
            [*parametros, por_pagina, (pagina - 1) * por_pagina],
        ).fetchall()

    return registros, total
