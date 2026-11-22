from flask import Blueprint, abort, redirect, render_template, url_for
from flask_login import current_user
from flask_wtf import FlaskForm
from safeclick.sessoes import exigir_perfis
import logging
from . import conteudos_db, conteudos_leitura

conteudos_bp = Blueprint("conteudos", __name__, url_prefix="/conteudos")
paginas_bp = Blueprint("paginas", __name__, url_prefix="/paginas")


@paginas_bp.before_request
@exigir_perfis("usuario", "administrador")
def verificar_acesso_paginas():
    return None


@paginas_bp.get("/")
def listar_paginas():
    try:
        paginas = conteudos_db.listar_conteudos("paginas")
    except Exception:
        logging.exception("Falha em consultar as páginas")
        return render_template("conteudos/indisponivel.html"), 503
    return render_template("conteudos/paginas.html", paginas=paginas)


@paginas_bp.get("/<slug>", endpoint="detalhe")
def detalhe_pagina(slug):
    try:
        pagina = conteudos_db.buscar_conteudos(slug, "paginas")
    except Exception:
        logging.exception("Falha em consultar a página")
        return render_template("conteudos/indisponivel.html"), 503
    if pagina is None:
        abort(404)
    return render_template("conteudos/detalhe.html", conteudo=pagina, pagina_editorial=True,
                           leitura=conteudos_leitura.dividir(pagina.get("texto")),
                           tema=conteudos_leitura.tema(None), minutos=conteudos_leitura.minutos(pagina.get("texto")))


@conteudos_bp.route("/")
def listar():
    try:
        conteudos = conteudos_db.listar_conteudos()
    except Exception:
        logging.exception("Falha em consultar os conteúdos")
        return render_template("conteudos/indisponivel.html"), 503
    return render_template("conteudos/listar.html", conteudos=[conteudos_leitura.cartao(c) for c in conteudos])


@conteudos_bp.route("/<slug>")
def detalhe(slug):
    try:
        conteudo = conteudos_db.buscar_conteudos(slug)
    except Exception:
        logging.exception("Falha em consultar o conteúdo")
        return render_template("conteudos/indisponivel.html"), 503
    if not conteudo:
        abort(404)
    # Formulário vazio: serve só para gerar o token CSRF do botão
    return render_template(
        "conteudos/detalhe.html", conteudo=conteudo, formulario=FlaskForm(),
        leitura=conteudos_leitura.dividir(conteudo.get("texto")),
        tema=conteudos_leitura.tema(conteudo.get("slug")),
        minutos=conteudos_leitura.minutos(conteudo.get("texto")),
        **_vizinhos(slug, conteudo.get("proxima_referencia")),
    )


def _vizinhos(atual, proximo, quantidade=6):
    # Próximo conteúdo e sugestões da lateral; sem eles a página continua funcionando
    try:
        lista = [conteudos_leitura.cartao(c) for c in conteudos_db.listar_conteudos()]
    except Exception:
        logging.warning("Sem sugestões de leitura para %s", atual)
        return {"proximo": None, "outros": []}
    seguinte = next((c for c in lista if c["slug"] == proximo), None)
    outros = [c for c in lista if c["slug"] not in (atual, proximo)]
    outros.sort(key=lambda c: bool(c.get("concluido")))
    return {"proximo": seguinte, "outros": outros[:quantidade]}


@conteudos_bp.post("/<slug>/concluir")
def concluir(slug):
    formulario = FlaskForm()
    if not formulario.validate_on_submit():
        abort(400, description="Recarregue a página e tente novamente.")
    try:
        concluido = conteudos_db.concluir_conteudo(int(current_user.id), slug)
    except Exception:
        logging.exception("Falha em registrar a conclusão do conteúdo")
        return render_template("conteudos/indisponivel.html"), 503
    if concluido is None:
        abort(404)
    # Volta para o conteúdo por GET: atualizar a página não reenvia o formulário
    return redirect(url_for("conteudos.detalhe", slug=slug), code=303)


@conteudos_bp.before_request
@exigir_perfis("usuario", "administrador")
def verificar_acesso_conteudos():
    return None
