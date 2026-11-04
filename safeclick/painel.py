from flask import Blueprint, abort, render_template
from flask_login import current_user
from psycopg import Error

from safeclick.painel_db import buscar_painel_usuario
from safeclick.sessoes import exigir_perfis


painel = Blueprint("painel", __name__, url_prefix="/painel")



@painel.before_request
@exigir_perfis("usuario", "administrador")
def verificar_acesso_painel():
    return None


@painel.get("/")
def exibir():
    try:
        
        dados = buscar_painel_usuario(int(current_user.id))
    except (Error, RuntimeError):
        abort(
            503,
            description="Não foi possível carregar o seu painel agora. Tente novamente em instantes.",
        )

    return render_template("painel/usuario.html", dados=dados)