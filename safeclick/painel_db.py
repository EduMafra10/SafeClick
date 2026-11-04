from safeclick.db import conectar_banco


_RESUMO_QUIZZES = """
    SELECT
        COUNT(*) AS tentativas,
        COUNT(DISTINCT quiz_id) AS quizzes_diferentes,
        COALESCE(SUM(pontuacao), 0) AS acertos,
        COALESCE(SUM(total_questoes), 0) AS questoes
    FROM public.tentativas_quiz
    WHERE usuario_id = %s
"""


_EVOLUCAO_QUIZZES = """
    SELECT data, titulo, pontuacao, total_questoes
    FROM (
        SELECT
            t.id,
            t.criada_em,
            to_char(t.criada_em AT TIME ZONE 'America/Sao_Paulo', 'DD/MM') AS data,
            q.titulo,
            t.pontuacao,
            t.total_questoes
        FROM public.tentativas_quiz AS t
        JOIN public.quizzes AS q
            ON q.id = t.quiz_id
        WHERE t.usuario_id = %s
        ORDER BY t.criada_em DESC, t.id DESC
        LIMIT 10
    ) AS ultimas
    ORDER BY criada_em, id
"""


_RESUMO_SIMULACOES = """
    SELECT
        COUNT(*) AS tentativas,
        COUNT(*) FILTER (WHERE versao_simulacao_id IS NULL) AS sem_versao
    FROM public.tentativas_simulacao
    WHERE usuario_id = %s
"""


_SIMULACOES_POR_CENARIO = """
    SELECT
        (array_agg(v.conteudo->>'titulo' ORDER BY v.numero DESC))[1] AS titulo,
        COUNT(*) FILTER (
            WHERE (v.conteudo->'opcoes'->t.opcao->>'segura')::boolean IS TRUE
        ) AS seguras,
        COUNT(*) FILTER (
            WHERE (v.conteudo->'opcoes'->t.opcao->>'segura')::boolean IS FALSE
        ) AS arriscadas
    FROM public.tentativas_simulacao AS t
    JOIN public.versoes_simulacao AS v
        ON v.id = t.versao_simulacao_id
    WHERE t.usuario_id = %s
    GROUP BY v.simulacao_id
    ORDER BY titulo
"""


# Conteúdos concluídos pelo usuário e total de conteúdos disponíveis.
_RESUMO_CONTEUDOS = """
    SELECT
        (SELECT COUNT(*) FROM public.conteudos) AS total,
        (
            SELECT COUNT(*)
            FROM public.conclusoes_conteudo
            WHERE usuario_id = %s
        ) AS concluidos
"""


def _percentual(parte, total):
    # Evita divisão por zero: sem atividades, não existe percentual.
    if not total:
        return None
    return round(100 * parte / total)


def buscar_painel_usuario(usuario_id):
    """Reúne os indicadores do painel de progresso de um usuário."""
    with conectar_banco() as conexao:
        conteudos = conexao.execute(_RESUMO_CONTEUDOS, (usuario_id,)).fetchone()
        quizzes = conexao.execute(_RESUMO_QUIZZES, (usuario_id,)).fetchone()
        evolucao = conexao.execute(_EVOLUCAO_QUIZZES, (usuario_id,)).fetchall()
        simulacoes = conexao.execute(_RESUMO_SIMULACOES, (usuario_id,)).fetchone()
        por_cenario = conexao.execute(
            _SIMULACOES_POR_CENARIO, (usuario_id,)
        ).fetchall()

    seguras = sum(linha["seguras"] for linha in por_cenario)
    arriscadas = sum(linha["arriscadas"] for linha in por_cenario)

    return {
        "conteudos": {
            "concluidos": conteudos["concluidos"],
            "total": conteudos["total"],
            "percentual": _percentual(
                conteudos["concluidos"], conteudos["total"]
            ),
        },
        "quizzes": {
            "tentativas": quizzes["tentativas"],
            "quizzes_diferentes": quizzes["quizzes_diferentes"],
            "percentual_acertos": _percentual(
                quizzes["acertos"], quizzes["questoes"]
            ),
        },
        "simulacoes": {
            "tentativas": simulacoes["tentativas"],
            "sem_versao": simulacoes["sem_versao"],
            "seguras": seguras,
            "arriscadas": arriscadas,
            "percentual_seguras": _percentual(seguras, seguras + arriscadas),
        },
        "evolucao_quizzes": [
            {
                "data": linha["data"],
                "titulo": linha["titulo"],
                "percentual": _percentual(
                    linha["pontuacao"], linha["total_questoes"]
                ),
            }
            for linha in evolucao
        ],
        "simulacoes_por_cenario": [
            {
                "titulo": linha["titulo"],
                "seguras": linha["seguras"],
                "arriscadas": linha["arriscadas"],
            }
            for linha in por_cenario
        ],
    }