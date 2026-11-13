from flask import has_request_context
from flask_login import current_user
from psycopg.types.json import Jsonb

from safeclick.db import conectar_banco


EVENTOS_PERMITIDOS = {
    "usuario.cadastrado",
    "usuario.senha_redefinida",
    "login.sucesso",
    "login.falha",
    "logout.realizado",
    "acesso.negado",
    "quiz.concluido",
    "simulacao.concluida",
    "simulacao.criada",
    "conteudo.visualizado",
    "conteudo.concluido",
    "avaliacao.salva",
    "api.consultada",
    "desafio_senha.concluido",
    "termo.aceito",
    "auditoria.consultada",
    "catalogo.criado",
    "catalogo.editado",
    "catalogo.publicado",
    "catalogo.despublicado",
    "catalogo.removido",
    "catalogo.excluido",
    "catalogo.restaurado",
    "mfa.reconfiguracao_administrativa",
    "usuario.perfil_alterado",
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


def listar_eventos(conexao, *, pagina, por_pagina, eventos=None, excluir_eventos=None,
                   resultado=None, usuario_id=None, busca=None,
                   data_inicio=None, data_fim=None):
    """Consulta os eventos com filtros e paginação. Devolve (registros, resumo)."""

    condicoes = []
    parametros = []

    if eventos:
        condicoes.append("logs.evento = ANY(%s)")
        parametros.append(sorted(eventos))
    if excluir_eventos:
        condicoes.append("logs.evento <> ALL(%s)")
        parametros.append(sorted(excluir_eventos))
    if resultado:
        condicoes.append("logs.resultado = %s")
        parametros.append(resultado)
    if usuario_id is not None:
        condicoes.append("logs.usuario_id = %s")
        parametros.append(usuario_id)
    if busca:
        termo = "%" + busca.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
        condicoes.append("(usuario.nome ILIKE %s OR usuario.email ILIKE %s)")
        parametros.extend([termo, termo])
    if data_inicio is not None:
        condicoes.append("logs.criado_em >= %s")
        parametros.append(data_inicio)
    if data_fim is not None:
        condicoes.append("logs.criado_em < %s")
        parametros.append(data_fim)

    origem = """
        FROM public.logs_auditoria AS logs
        LEFT JOIN public.usuarios AS usuario ON usuario.id = logs.usuario_id
    """
    filtro_sql = " WHERE " + " AND ".join(condicoes) if condicoes else ""

    resumo = conexao.execute(
        """
        SELECT COUNT(*) AS total,
               COUNT(*) FILTER (WHERE logs.resultado = 'falha') AS falhas,
               COUNT(*) FILTER (WHERE logs.resultado = 'negado') AS negados,
               COUNT(DISTINCT logs.usuario_id) AS usuarios
        """ + origem + filtro_sql,
        parametros,
    ).fetchone()

    registros = conexao.execute(
        """
        SELECT logs.id, logs.criado_em, logs.usuario_id,
               usuario.nome AS usuario_nome, usuario.email AS usuario_email,
               usuario.perfil AS usuario_perfil,
               logs.evento, logs.resultado, logs.recurso_tipo, logs.recurso_id,
               logs.detalhes
        """ + origem + filtro_sql + " ORDER BY logs.criado_em DESC, logs.id DESC"
        " LIMIT %s OFFSET %s",
        [*parametros, por_pagina, (pagina - 1) * por_pagina],
    ).fetchall()

    return registros, resumo
