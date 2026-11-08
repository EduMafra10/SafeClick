from flask import Blueprint, current_app, g, request, session
from flask_login import current_user

from safeclick.conquistas_db import liberar_conquistas, liberar_e_listar_conquistas

conquistas = Blueprint("conquistas", __name__)

_VERIFICAR = "conquistas_verificar"


def _avisar_falha():
    current_app.logger.warning("Não foi possível verificar as conquistas", exc_info=True)


@conquistas.after_app_request
def marcar_verificacao(resposta):
    ja_conferiu = "conquistas_novas" in g
    if (
        request.method == "POST"
        and resposta.status_code < 400
        and not ja_conferiu
        and current_user.is_authenticated
    ):
        session[_VERIFICAR] = True
    return resposta


def conquistas_para_exibir():
    if "conquistas_novas" in g:
        return g.conquistas_novas

    g.conquistas_novas = []

    if not current_user.is_authenticated:
        return []

    pendente = session.pop(_VERIFICAR, False)
    if not pendente and request.method != "POST":
        return []

    try:
        g.conquistas_novas = liberar_conquistas(int(current_user.id))
    except Exception:
        _avisar_falha()

    return g.conquistas_novas


def carregar_conquistas_painel(usuario_id):
    """Libera o que faltar e devolve a lista completa para o painel (ou None se falhar)."""
    session.pop(_VERIFICAR, None)

    try:
        novas, todas = liberar_e_listar_conquistas(usuario_id)
    except Exception:
        _avisar_falha()
        g.conquistas_novas = []
        return None

    g.conquistas_novas = novas
    return todas


@conquistas.app_context_processor
def disponibilizar_conquistas():
    return {"conquistas_para_exibir": conquistas_para_exibir}