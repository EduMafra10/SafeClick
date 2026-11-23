from safeclick.db import conectar_banco
from safeclick.auditoria_db import registrar_evento

_METRICAS = """
    SELECT criterio, valor
    FROM (VALUES
        ('conteudos_concluidos', (
            SELECT COUNT(*) FROM public.conclusoes_conteudo
            WHERE usuario_id = %(usuario_id)s
        )),
        ('quizzes_respondidos', (
            SELECT COUNT(*) FROM public.tentativas_quiz
            WHERE usuario_id = %(usuario_id)s
        )),
        ('acertos_em_um_quiz', (
            SELECT COALESCE(MAX(pontuacao), 0) FROM public.tentativas_quiz
            WHERE usuario_id = %(usuario_id)s
        )),
        ('quizzes_perfeitos', (
            SELECT COUNT(*) FROM public.tentativas_quiz
            WHERE usuario_id = %(usuario_id)s AND pontuacao = total_questoes
        )),
        ('simulacoes_realizadas', (
            SELECT COUNT(*) FROM public.tentativas_simulacao
            WHERE usuario_id = %(usuario_id)s
        )),
        ('escolhas_seguras', (
            SELECT COUNT(*)
            FROM public.tentativas_simulacao AS t
            JOIN public.versoes_simulacao AS v ON v.id = t.versao_simulacao_id
            WHERE t.usuario_id = %(usuario_id)s
              AND (v.conteudo->'opcoes'->t.opcao->>'segura')::boolean IS TRUE
        )),
        ('desafios_senha', (
            SELECT COUNT(*) FROM public.desafios_senha
            WHERE usuario_id = %(usuario_id)s
        ))
    ) AS metricas (criterio, valor)
"""

_LIBERAR = """
    WITH metricas AS (""" + _METRICAS + """),
    novas AS (
        INSERT INTO public.conquistas_usuario (usuario_id, conquista_id)
        SELECT %(usuario_id)s, c.id
        FROM public.conquistas AS c
        JOIN metricas AS m ON m.criterio = c.criterio
        WHERE m.valor >= c.meta
        ON CONFLICT DO NOTHING
        RETURNING conquista_id
    )
    SELECT c.codigo, c.nome, c.descricao, c.criterio
    FROM novas
    JOIN public.conquistas AS c ON c.id = novas.conquista_id
    ORDER BY c.ordem
"""


_LISTAR = """
    WITH metricas AS (""" + _METRICAS + """)
    SELECT
        c.codigo,
        c.nome,
        c.descricao,
        c.criterio,
        c.meta,
        COALESCE(m.valor, 0) AS valor,
        to_char(cu.desbloqueada_em AT TIME ZONE 'America/Sao_Paulo', 'DD/MM/YYYY') AS desbloqueada_em
    FROM public.conquistas AS c
    LEFT JOIN metricas AS m ON m.criterio = c.criterio
    LEFT JOIN public.conquistas_usuario AS cu
        ON cu.conquista_id = c.id
       AND cu.usuario_id = %(usuario_id)s
    ORDER BY c.ordem
"""


def _formatar(linha):
    desbloqueada = linha["desbloqueada_em"] is not None
    return {
        "codigo": linha["codigo"],
        "nome": linha["nome"],
        "descricao": linha["descricao"],
        "criterio": linha["criterio"],
        "desbloqueada": desbloqueada,
        "desbloqueada_em": linha["desbloqueada_em"],
        "meta": linha["meta"],
        "atual": min(linha["valor"], linha["meta"]),
    }


def liberar_conquistas(usuario_id):
    with conectar_banco() as conexao:
        novas = conexao.execute(_LIBERAR, {"usuario_id": usuario_id}).fetchall()
        _registrar_conquistas(conexao, usuario_id, novas)
    return novas


def _registrar_conquistas(conexao, usuario_id, novas):
    for conquista in novas:
        registrar_evento(usuario_id, 'conquista.concedida', 'sucesso', recurso_tipo='conquista',
                         recurso_id=conquista['codigo'], conexao=conexao)


def liberar_e_listar_conquistas(usuario_id):
    parametros = {"usuario_id": usuario_id}

    with conectar_banco() as conexao:
        novas = conexao.execute(_LIBERAR, parametros).fetchall()
        _registrar_conquistas(conexao, usuario_id, novas)
        todas = conexao.execute(_LISTAR, parametros).fetchall()

    return novas, [_formatar(linha) for linha in todas]
