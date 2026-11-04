from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user
from psycopg import Error

from safeclick.sessoes import exigir_perfis
from safeclick.formularios_administracao import FormularioNovoCenario
from safeclick.simulacoes_db import (
    SimulacaoDuplicada,
    criar_rascunho_simulacao,
    listar_simulacoes_administrativas,
)


administracao = Blueprint("administracao", __name__, url_prefix="/administracao")

ESTADOS = {
    "rascunho": "Rascunho",
    "publicada": "Publicado",
    "arquivada": "Arquivado",
}

TIPOS = {
    "email": "E-mail",
    "sms": "SMS",
    "conversa": "Conversa",
    "loja": "Loja",
}


@administracao.before_request
@exigir_perfis("administrador")
def verificar_acesso_administracao():
    
    return None


@administracao.get("/")
def inicio():
    return redirect(url_for("administracao.listar_simulacoes"))


@administracao.get("/simulacoes")
def listar_simulacoes():
    if (
        set(request.args) - {"estado", "pagina"}
        or any(len(request.args.getlist(campo)) != 1 for campo in request.args)
    ):
        abort(400, description="Filtros inválidos.")

    estado = request.args.get("estado", "")
    pagina_texto = request.args.get("pagina", "1")
    if estado and estado not in ESTADOS:
        abort(400, description="Estado inválido.")
    if (
        not 1 <= len(pagina_texto) <= 7
        or not pagina_texto.isascii()
        or not pagina_texto.isdecimal()
        or not 1 <= int(pagina_texto) <= 1000000
    ):
        abort(400, description="Página inválida.")

    pagina = int(pagina_texto)
    por_pagina = 20
    try:
        registros, total = listar_simulacoes_administrativas(
            estado=estado, pagina=pagina, por_pagina=por_pagina
        )
    except (Error, RuntimeError):
        abort(503, description="Não foi possível carregar os cenários agora. Tente novamente em instantes.")

    ultima_pagina = max(1, (total + por_pagina - 1) // por_pagina)
    if pagina > ultima_pagina:
        abort(404, description="Página não encontrada.")

    return render_template(
        "administracao/simulacoes.html",
        registros=registros,
        total=total,
        estado=estado,
        estados=ESTADOS,
        tipos=TIPOS,
        pagina=pagina,
        ultima_pagina=ultima_pagina,
    )


@administracao.route("/simulacoes/novo", methods=["GET", "POST"])
def novo_cenario():
    request.max_content_length = 16384
    formulario = FormularioNovoCenario()
    erro = None
    status = 200

    if request.method == "POST":
        permitidos = {"csrf_token", "titulo", "slug", "tipo", "resumo"}
        if (
            set(request.form) != permitidos
            or any(len(request.form.getlist(campo)) != 1 for campo in permitidos)
            or request.files
        ):
            erro = "Confira os campos e envie o formulário novamente."
            status = 400
        elif not formulario.validate_on_submit():
            erro = "Confira os campos indicados. Se a sessão do formulário expirou, recarregue a página."
            status = 400
        else:
            try:
                criar_rascunho_simulacao(
                    current_user.id,
                    titulo=formulario.titulo.data,
                    slug=formulario.slug.data,
                    tipo=formulario.tipo.data,
                    resumo=formulario.resumo.data,
                )
            except SimulacaoDuplicada:
                formulario.slug.errors.append("Já existe um cenário com esse endereço. Escolha outro.")
                erro = "Escolha outro endereço para o cenário."
                status = 409
            except PermissionError:
                abort(403, description="Você não tem permissão para cadastrar cenários.")
            except (Error, RuntimeError, ValueError):
                erro = "Não foi possível confirmar o cadastro. Consulte a listagem antes de tentar novamente."
                status = 503
            else:
                flash("Cenário salvo como rascunho. Ele ainda não aparece no catálogo dos usuários.", "administracao_sucesso")
                return redirect(url_for("administracao.listar_simulacoes", estado="rascunho"), code=303)

    return render_template(
        "administracao/novo_cenario.html", formulario=formulario, erro=erro
    ), status
