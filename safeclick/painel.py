from datetime import date, datetime, timedelta, timezone

from flask import Blueprint, abort, render_template, request
from flask_login import current_user
from psycopg import Error

from safeclick.conquistas import carregar_conquistas_painel
from safeclick.painel_db import buscar_painel_usuario
from safeclick.sessoes import exigir_perfis


painel = Blueprint("painel", __name__, url_prefix="/painel")


FUSO_BRASILIA = timezone(timedelta(hours=-3))


ATALHOS_PERIODO = (
    ("Últimos 7 dias", 7),
    ("Últimos 30 dias", 30),
    ("Últimos 90 dias", 90),
    ("Todo o período", None),
)


DATA_MINIMA = date(2020, 1, 1)


@painel.before_request
@exigir_perfis("usuario", "administrador")
def verificar_acesso_painel():
    return None


def _hoje():
    return datetime.now(FUSO_BRASILIA).date()


def _ler_data(nome):
    
    valor = request.args.get(nome, "").strip()
    if not valor:
        return None, None

    try:
        if len(valor) != 10:
            raise ValueError
        data = date.fromisoformat(valor)
    except ValueError:
        return None, "Use datas válidas no formato dia/mês/ano."

    if data < DATA_MINIMA:
        return None, "Escolha uma data a partir de 2020."

    return data, None


def ler_filtro_periodo():
    
    hoje = _hoje()
    inicio, erro_inicio = _ler_data("inicio")
    fim, erro_fim = _ler_data("fim")
    erro = erro_inicio or erro_fim

    
    if fim and fim > hoje:
        fim = hoje

    if not erro and inicio and fim and inicio > fim:
        erro = "A data inicial precisa ser igual ou anterior à data final."

    
    if erro:
        inicio = fim = None

    atalhos = []
    for rotulo, dias in ATALHOS_PERIODO:
        atalho_inicio = hoje - timedelta(days=dias - 1) if dias else None
        atalho_fim = hoje if dias else None
        atalhos.append({
            "rotulo": rotulo,
            "inicio": atalho_inicio,
            "fim": atalho_fim,
            "ativo": (inicio, fim) == (atalho_inicio, atalho_fim),
        })

    return {
        "inicio": inicio,
        "fim": fim,
        "ativo": bool(inicio or fim),
        "erro": erro,
        "hoje": hoje,
        "atalhos": atalhos,
    }


@painel.get("/")
def exibir():
    filtro = ler_filtro_periodo()

    try:
        dados = buscar_painel_usuario(
            int(current_user.id), inicio=filtro["inicio"], fim=filtro["fim"]
        )
    except (Error, RuntimeError):
        abort(
            503,
            description="Não foi possível carregar o seu painel agora. Tente novamente em instantes.",
        )

    conquistas = carregar_conquistas_painel(int(current_user.id))

    return render_template(
        "painel/usuario.html", dados=dados, filtro=filtro, conquistas=conquistas
    )