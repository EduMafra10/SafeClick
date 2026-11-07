from datetime import date, datetime, time, timedelta

import psycopg
from flask import Blueprint, abort, current_app, render_template, request
from flask_login import current_user, login_required

from safeclick import auditoria_textos as textos
from safeclick.auditoria_db import EVENTOS_PERMITIDOS, listar_eventos, registrar_evento
from safeclick.db import conectar_banco
from safeclick.painel import FUSO_BRASILIA


auditoria = Blueprint("auditoria", __name__, url_prefix="/auditoria")
POR_PAGINA = 50
TODOS_EVENTOS = EVENTOS_PERMITIDOS | set(textos.EVENTOS_ANTIGOS)
CONSULTAS = "auditoria.consultada"
ATALHOS_PERIODO = (("Hoje", 1), ("7 dias", 7), ("30 dias", 30), ("Todo o período", None))


def _hoje():
    return datetime.now(FUSO_BRASILIA).date()


def _ler_filtros():
    """Lê os filtros da URL. Valores inválidos são ignorados e geram um aviso."""
    avisos = []
    args = request.args

    pagina = args.get("pagina", "1").strip()
    pagina = int(pagina) if pagina.isdecimal() and len(pagina) <= 6 and int(pagina) >= 1 else 1

    evento = args.get("evento", "").strip()
    eventos = None
    if evento.startswith("cat:") and evento[4:] in textos.CATEGORIAS:
        eventos = textos.eventos_da_categoria(evento[4:])
    elif evento in TODOS_EVENTOS:
        eventos = {evento}
    elif evento:
        avisos.append("O evento escolhido não existe.")
        evento = ""

    resultado = args.get("resultado", "").strip()
    if resultado and resultado not in textos.RESULTADOS:
        avisos.append("O resultado escolhido não existe.")
        resultado = ""

    usuario = args.get("usuario", "").strip()[:100]
    usuario_id = busca = None
    if usuario.isdecimal() and len(usuario) <= 10:
        usuario_id = int(usuario)
    elif usuario.startswith("#") and usuario[1:].isdecimal() and len(usuario) <= 11:
        usuario_id = int(usuario[1:])
    elif usuario:
        busca = usuario

    datas = {}
    for nome in ("inicio", "fim"):
        valor = args.get(nome, "").strip()
        datas[nome] = None
        if not valor:
            continue
        try:
            if len(valor) != 10:
                raise ValueError
            datas[nome] = date.fromisoformat(valor)
        except ValueError:
            avisos.append("Use datas válidas no formato dia/mês/ano.")

    # As próprias consultas à auditoria ficam ocultas, a não ser que sejam pedidas.
    mostrar_consultas = args.get("consultas") == "1"
    excluir_eventos = None if mostrar_consultas or eventos == {CONSULTAS} else {CONSULTAS}

    if datas["inicio"] and datas["fim"] and datas["inicio"] > datas["fim"]:
        avisos.append("A data inicial precisa ser igual ou anterior à data final.")
        datas = {"inicio": None, "fim": None}

    # Os dias são interpretados no horário de Brasília.
    data_inicio = (
        datetime.combine(datas["inicio"], time.min, tzinfo=FUSO_BRASILIA)
        if datas["inicio"] else None
    )
    data_fim = (
        datetime.combine(datas["fim"] + timedelta(days=1), time.min, tzinfo=FUSO_BRASILIA)
        if datas["fim"] else None
    )

    filtros_url = {
        "evento": evento,
        "resultado": resultado,
        "usuario": usuario,
        "inicio": datas["inicio"].isoformat() if datas["inicio"] else "",
        "fim": datas["fim"].isoformat() if datas["fim"] else "",
        "consultas": "1" if mostrar_consultas else "",
    }

    consulta = {
        "eventos": eventos,
        "excluir_eventos": excluir_eventos,
        "resultado": resultado or None,
        "usuario_id": usuario_id,
        "busca": busca,
        "data_inicio": data_inicio,
        "data_fim": data_fim,
    }

    return pagina, consulta, filtros_url, list(dict.fromkeys(avisos))


def _atalhos(filtros):
    hoje = _hoje()
    sem_datas = {
        chave: valor for chave, valor in filtros.items()
        if valor and chave not in ("inicio", "fim")
    }
    atalhos = []
    for rotulo, dias in ATALHOS_PERIODO:
        inicio = (hoje - timedelta(days=dias - 1)).isoformat() if dias else ""
        fim = hoje.isoformat() if dias else ""
        parametros = dict(sem_datas, inicio=inicio, fim=fim) if dias else sem_datas
        atalhos.append({
            "rotulo": rotulo,
            "parametros": parametros,
            "ativo": (filtros["inicio"], filtros["fim"]) == (inicio, fim),
        })
    return atalhos


def _preparar(registro):
    """Monta o que a tabela exibe para cada registro."""
    return {
        "quando": registro["criado_em"].astimezone(FUSO_BRASILIA),
        "usuario_id": registro["usuario_id"],
        "usuario_nome": registro["usuario_nome"],
        "usuario_email": registro["usuario_email"],
        "administrador": registro["usuario_perfil"] == "administrador",
        "sem_usuario": textos.explicar_sem_usuario(registro["evento"], registro["detalhes"]),
        "titulo": textos.titulo_evento(registro["evento"]),
        "categoria": textos.categoria_evento(registro["evento"]),
        "evento": registro["evento"],
        "resultado": registro["resultado"],
        "resultado_rotulo": textos.RESULTADOS.get(registro["resultado"], registro["resultado"]),
        "detalhes": textos.descrever_detalhes(
            registro["evento"], registro["detalhes"],
            registro["recurso_tipo"], registro["recurso_id"],
        ),
    }


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

    pagina, consulta, filtros, avisos = _ler_filtros()

    try:
        with conectar_banco() as conexao:
            registrar_evento(
                usuario_id=int(current_user.id),
                evento="auditoria.consultada",
                resultado="sucesso",
                recurso_tipo="auditoria",
                conexao=conexao,
            )
            registros, resumo = listar_eventos(
                conexao, pagina=pagina, por_pagina=POR_PAGINA, **consulta
            )
    except (psycopg.Error, RuntimeError):
        current_app.logger.exception("Falha ao consultar a auditoria")
        abort(503, description="Não foi possível consultar a auditoria agora.")

    total = resumo["total"]
    filtros_ativos = {chave: valor for chave, valor in filtros.items() if valor}

    resposta = render_template(
        "auditoria/lista.html",
        registros=[_preparar(registro) for registro in registros],
        resumo=resumo,
        pagina=pagina,
        ultima_pagina=max(1, (total + POR_PAGINA - 1) // POR_PAGINA),
        grupos=textos.opcoes_de_filtro(),
        resultados=textos.RESULTADOS,
        filtros=filtros,
        filtros_ativos=filtros_ativos,
        atalhos=_atalhos(filtros),
        hoje=_hoje(),
        avisos=avisos,
    )
    return resposta, 200, {"Cache-Control": "no-store"}