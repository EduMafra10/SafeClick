from flask import Blueprint, flash, redirect, render_template, request, url_for
from psycopg import Error
from psycopg.errors import UniqueViolation

from safeclick.formularios import FormularioCadastro
from safeclick.usuarios_db import criar_usuario

autenticacao = Blueprint("autenticacao", __name__)

@autenticacao.route("/cadastro", methods=["GET", "POST"])
def cadastro():
    formulario = FormularioCadastro()
    erro = None
    status = 200

    # valida os campos e o token CSRF antes de gravar no banco
    if formulario.validate_on_submit():
        try:
            criar_usuario(
                formulario.nome.data,
                formulario.email.data,
                formulario.senha.data,
            )
        except UniqueViolation:
            formulario.email.errors.append(
                "Não foi possível usar este e-mail. Confira os dados informados"
            )
            status = 409
        except (Error, RuntimeError):
            erro = "Não foi possível concluir o cadastro. Tente novamente em instantes"
            status = 503
        else:
            # o redirecionamento evita reenviar o cadastro se atualizarem a pagina
            flash("Cadastro realizado com sucesso!", "sucesso")
            return redirect(url_for("autenticacao.cadastro"), code=303)
    
    elif request.method == "POST":
        status = 400

    return render_template(
        "autenticacao/cadastro.html",
        formulario = formulario,
        erro = erro,
    ), status