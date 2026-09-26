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