from flask import abort
from flask_login import LoginManager, UserMixin
from psycopg import Error

from safeclick.usuarios_db import buscar_usuario_por_id

login_manager = LoginManager()

class Usuario(UserMixin):
    # representa que o usuário está autenticado sem guardar a senha ou seu hash
    def __init__(self, dados):
        self.id = dados["id"]
        self.nome = dados["nome"]
        self.email = dados["email"]
        self.perfil = dados["perfil"]

@login_manager.user_loader
def carregar_usuario(usuario_id):
    # o flask login recupera da sessao o ID como texto
    try:
        usuario_id = int(usuario_id)
    except (TypeError, ValueError):
        return None

    # aceita somente IDS que sao positivos dentro do limite da INTEGER no banco
    if not 1 <= usuario_id <= 2147483647:
        return None

    try:
        dados = buscar_usuario_por_id(usuario_id)
    except (Error, RuntimeError):
        abort(
            503,
            description="Não foi possível verificar sua sessão. Tente novamente em instantes",
        )

    # uma conta que nao existe mais, nao pode continuar autenticada no sistema
    if dados is None:
        return None

    return Usuario(dados)