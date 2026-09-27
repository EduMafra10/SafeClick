from datetime import date, datetime, time, timedelta, timezone

import psycopg
from flask import Blueprint, abort, current_app, render_template, request
from flask_login import current_user, login_required

from safeclick.auditoria_db import EVENTOS_PERMITIDOS, listar_eventos, registrar_evento
from safeclick.db import conectar_banco


auditoria = Blueprint("auditoria", __name__, url_prefix="/auditoria")
POR_PAGINA = 50


def _inteiro_positivo(valor, *, maximo):
    if not valor.isdecimal() or len(valor) > 10:
        abort(400)
    numero = int(valor)
    if not 1 <= numero <= maximo:
        abort(400)
    return numero


def _data_utc(valor):
    if not valor:
        return None
    try:
        dia = date.fromisoformat(valor)
    except ValueError:
        abort(400)
    if dia.isoformat() != valor:
        abort(400)
    return datetime.combine(dia, time.min, tzinfo=timezone.utc)


@auditoria.get("/")
@login_required
def listar():
    """Mostra o histórico somente para administradores."""

    if current_user.perfil != "administrador":
        try:
            registrar_evento(
                usuario_id=int(current_user.id),
                evento="acesso.negado",
                resultado="negado",
                recurso_tipo="auditoria",
            )
        except (psycopg.Error, RuntimeError):
            current_app.logger.exception("Falha ao registrar acesso negado à auditoria")
        abort(403)

    pagina = _inteiro_positivo(request.args.get("pagina", "1"), maximo=100000)
    evento = request.args.get("evento", "").strip()
    if evento and evento not in EVENTOS_PERMITIDOS:
        abort(400)

    usuario = request.args.get("usuario_id", "").strip()
    usuario_id = _inteiro_positivo(usuario, maximo=2147483647) if usuario else None
    inicio = request.args.get("inicio", "").strip()
    fim = request.args.get("fim", "").strip()
    data_inicio = _data_utc(inicio)
    data_fim = _data_utc(fim)
    if data_fim is not None:
        try:
            data_fim += timedelta(days=1)
        except OverflowError:
            abort(400)
    if data_inicio is not None and data_fim is not None and data_inicio >= data_fim:
        abort(400)

    try:
        with conectar_banco() as conexao:
            registrar_evento(
                usuario_id=int(current_user.id),
                evento="auditoria.consultada",
                resultado="sucesso",
                recurso_tipo="auditoria",
                conexao=conexao,
            )
            registros, total = listar_eventos(
                conexao,
                pagina=pagina,
                por_pagina=POR_PAGINA,
                evento=evento or None,
                usuario_id=usuario_id,
                data_inicio=data_inicio,
                data_fim=data_fim,
            )
    except (psycopg.Error, RuntimeError):
        current_app.logger.exception("Falha ao consultar a auditoria")
        abort(503, description="Não foi possível consultar a auditoria agora.")

    resposta = render_template(
        "auditoria/lista.html",
        registros=registros,
        total=total,
        pagina=pagina,
        ultima_pagina=max(1, (total + POR_PAGINA - 1) // POR_PAGINA),
        eventos=sorted(EVENTOS_PERMITIDOS),
        utc=timezone.utc,
        filtros={"evento": evento, "usuario_id": usuario, "inicio": inicio, "fim": fim},
    )
    return resposta, 200, {"Cache-Control": "no-store"}
