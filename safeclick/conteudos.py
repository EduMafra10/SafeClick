from flask import Blueprint, abort, redirect, render_template, url_for
from flask_login import current_user
from flask_wtf import FlaskForm
from safeclick.sessoes import exigir_perfis
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
    # Formulário vazio: serve só para gerar o token CSRF do botão
    return render_template(
        "conteudos/detalhe.html", conteudo=conteudo, formulario=FlaskForm()
    )

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