# As consultas principais fornecem o item atual e a versão publicada do quiz.
PROXIMO_CONTEUDO = """
    (
        SELECT seguinte.slug
        FROM public.conteudos AS seguinte
        WHERE item.secao = 'conteudos'
          AND seguinte.secao = item.secao AND seguinte.estado = 'publicada'
          AND seguinte.id > item.id
        ORDER BY seguinte.id
        LIMIT 1
    ) AS proxima_referencia
"""

# A lista de quizzes apresenta primeiro as perguntas e depois as oficinas.
PROXIMO_QUIZ = """
    (
        SELECT seguinte.id
        FROM public.catalogo_quizzes AS seguinte
        JOIN public.quizzes AS versao_seguinte
            ON versao_seguinte.id = seguinte.versao_publicada_id
        WHERE seguinte.estado = 'publicada'
          AND (versao_seguinte.formato = 'oficina', seguinte.id)
              > (publicada.formato = 'oficina', item.id)
        ORDER BY versao_seguinte.formato = 'oficina', seguinte.id
        LIMIT 1
    ) AS proxima_referencia
"""
