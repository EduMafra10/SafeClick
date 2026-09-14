from flask import Blueprint, render_template, abort
import logging
from . import conteudos_db

conteudos_bp = Blueprint("conteudos", __name__, url_prefix="/conteudos")

@conteudos_bp.route("/")
def listar():
    try:
        conteudos = conteudos_db.listar_conteudos()
    except Exception:
        logging.exception ("Falha em consultar os conteúdos")
        return render_template("conteudos/indisponivel.html"), 503
    return render_template("conteudos/listar.html", conteudos=conteudos)

@conteudos_bp.route("/<slug>")
def detalhe(slug):
    try:
        conteudo = conteudos_db.buscar_conteudos(slug)
    except Exception:
        logging.exception("Falha em consultar o conteúdo")
        return render_template("conteudos/indisponivel.html"), 503
    if not conteudo:
        abort(404)
    return render_template("conteudos/detalhe.html", conteudo=conteudo)
 