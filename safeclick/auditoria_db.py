from flask import has_request_context
from flask_login import current_user
from psycopg.types.json import Jsonb

from safeclick.db import conectar_banco


EVENTOS_PERMITIDOS = {
    "usuario.cadastrado",
    "login.sucesso",
    "login.falha",
    "logout.realizado",
    "acesso.negado",
    "quiz.concluido",
    "simulacao.concluida",
    "conteudo.visualizado",
    "api.consultada",
    "termo.aceito",
    "auditoria.consultada",
}

RESULTADOS_PERMITIDOS = {
    "sucesso",
    "falha",
    "negado",
}


def usuario_autenticado_id():
    """Identifica o usuário da requisição, quando houver login."""

    if has_request_context() and current_user.is_authenticated:
        return int(current_user.id)
    return None


def _validar_evento(evento, resultado, detalhes):
    """Valida os dados antes de gravar o evento."""

    if evento not in EVENTOS_PERMITIDOS:
        raise ValueError("Evento de auditoria não permitido")

    if resultado not in RESULTADOS_PERMITIDOS:
        raise ValueError("Resultado de auditoria não permitido")

    if detalhes is not None and not isinstance(detalhes, dict):
        raise ValueError("Os detalhes devem ser um objeto")

    return detalhes or {}


def _inserir_evento(
    conexao,
    usuario_id,
    evento,
    resultado,
    recurso_tipo,
    recurso_id,
    detalhes,
):
    """Insere o evento usando uma conexão já aberta."""

    registro = conexao.execute(
        """
        INSERT INTO public.logs_auditoria (
            usuario_id,
            evento,
            resultado,
            recurso_tipo,
            recurso_id,
            detalhes
        )
        VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING id
        """,
        (
            usuario_id,
            evento,
            resultado,
            recurso_tipo,
            str(recurso_id) if recurso_id is not None else None,
            Jsonb(detalhes),
        ),
    ).fetchone()

    return registro["id"]


def registrar_evento(
    usuario_id,
    evento,
    resultado,
    recurso_tipo=None,
    recurso_id=None,
    detalhes=None,
    conexao=None,
):
    """Registra uma ação do sistema no banco de dados."""

    detalhes = _validar_evento(evento, resultado, detalhes)

    if conexao is not None:
        return _inserir_evento(
            conexao,
            usuario_id,
            evento,
            resultado,
            recurso_tipo,
            recurso_id,
            detalhes,
        )

    with conectar_banco() as nova_conexao:
        return _inserir_evento(
            nova_conexao,
            usuario_id,
            evento,
            resultado,
            recurso_tipo,
            recurso_id,
            detalhes,
        )


def listar_eventos(conexao, *, pagina, por_pagina, evento=None, usuario_id=None,
                   data_inicio=None, data_fim=None):
    """Consulta os eventos com filtros e paginação."""

    condicoes = []
    parametros = []

    if evento:
        condicoes.append("logs.evento = %s")
        parametros.append(evento)
    if usuario_id is not None:
        condicoes.append("logs.usuario_id = %s")
        parametros.append(usuario_id)
    if data_inicio is not None:
        condicoes.append("logs.criado_em >= %s")
        parametros.append(data_inicio)
    if data_fim is not None:
        condicoes.append("logs.criado_em < %s")
        parametros.append(data_fim)

    filtro_sql = " WHERE " + " AND ".join(condicoes) if condicoes else ""
    total = conexao.execute(
        "SELECT COUNT(*) AS total FROM public.logs_auditoria AS logs" + filtro_sql,
        parametros,
    ).fetchone()["total"]

    registros = conexao.execute(
        """
        SELECT logs.id, logs.criado_em, logs.usuario_id, usuario.nome AS usuario_nome,
               logs.evento, logs.resultado, logs.recurso_tipo, logs.recurso_id,
               logs.detalhes
        FROM public.logs_auditoria AS logs
        LEFT JOIN public.usuarios AS usuario ON usuario.id = logs.usuario_id
        """ + filtro_sql + " ORDER BY logs.criado_em DESC, logs.id DESC"
        " LIMIT %s OFFSET %s",
        [*parametros, por_pagina, (pagina - 1) * por_pagina],
    ).fetchall()

    return registros, total
