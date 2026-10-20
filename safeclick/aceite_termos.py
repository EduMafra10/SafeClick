from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from psycopg import Error

from safeclick.formularios import FormularioAceiteTermos
from safeclick.termos_db import (
    TermosDesatualizados,
    registrar_aceite_termos,
    usuario_aceitou_termos_atuais,
)


aceite_termos = Blueprint("aceite_termos", __name__)


@aceite_termos.route("/aceitar-termos", methods=["GET", "POST"])
@login_required
def aceitar():
    from safeclick.privacidade import VERSAO_TERMOS

    formulario = FormularioAceiteTermos()
    erro = None
    status = 200
    termos_disponiveis = False

    try:
        ja_aceitou = usuario_aceitou_termos_atuais(current_user.id)
        termos_disponiveis = True
    except (Error, RuntimeError):
        erro = "Não foi possível consultar os termos. Tente novamente em instantes."
        status = 503
    else:
        # Quem ja aceitou a versao atual pode continuar usando o sistema.
        if request.method == "GET" and ja_aceitou:
            return redirect(url_for("inicio"), code=303)

        if formulario.validate_on_submit():
            try:
                registrar_aceite_termos(
                    current_user.id,
                    formulario.versao_termos.data,
                    aceitou=formulario.aceitou_termos.data,
                )
            except TermosDesatualizados:
                formulario.versao_termos.errors.append(
                    "Os termos mudaram. Leia a versão atual e marque o aceite novamente."
                )
                status = 400
            except (Error, RuntimeError):
                erro = "Não foi possível registrar o aceite. Tente novamente em instantes."
                status = 503
            else:
                # Um aceite ja registrado tambem permite continuar, sem duplicar o registro.
                flash("Aceite dos Termos de Uso confirmado.", "sucesso")
                return redirect(url_for("inicio"), code=303)
        elif request.method == "POST":
            status = 400

    # Uma versao diferente exige que a pessoa marque o aceite novamente.
    if request.method == "GET" or formulario.versao_termos.errors:
        formulario.versao_termos.data = VERSAO_TERMOS
        formulario.aceitou_termos.data = False

    return render_template(
        "autenticacao/aceitar_termos.html",
        formulario=formulario,
        erro=erro,
        versao_termos=VERSAO_TERMOS,
        termos_disponiveis=termos_disponiveis,
    ), status

@aceite_termos.before_app_request
def exigir_aceite_dos_termos():
    
    if request.endpoint is None or request.endpoint == "static":
        return None

   
    if request.blueprint in {
        "autenticacao",
        "recuperacao",
        "privacidade",
        "aceite_termos",
    }:
        return None

    if not current_user.is_authenticated:
        return None

    try:
        aceitou = usuario_aceitou_termos_atuais(current_user.id)
    except (Error, RuntimeError):
        abort(
            503,
            description="Não foi possível verificar o aceite dos termos. Tente novamente em instantes.",
        )

    if not aceitou:
        return redirect(url_for("aceite_termos.aceitar"), code=303)

    return None