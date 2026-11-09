from safeclick.auditoria_db import registrar_evento
from safeclick.db import conectar_banco
from safeclick.navegacao_atividades import PROXIMO_CONTEUDO, PROXIMO_QUIZ


_ALVOS = {
    "conteudo": (
        f"""
        SELECT item.id, item.titulo, avaliacao.nota, avaliacao.comentario,
            {PROXIMO_CONTEUDO}
        FROM public.conteudos AS item
        JOIN public.conclusoes_conteudo AS conclusao ON conclusao.conteudo_id = item.id
        LEFT JOIN public.avaliacoes_conteudo AS avaliacao
            ON avaliacao.conteudo_id = item.id AND avaliacao.usuario_id = conclusao.usuario_id
        WHERE conclusao.usuario_id = %s AND item.slug = %s
          AND item.secao = 'conteudos' AND item.estado = 'publicada'
        """,
        "FOR SHARE OF item, conclusao",
        "avaliacoes_conteudo",
        "conteudo_id",
    ),
    "quiz": (
        f"""
        SELECT item.id, versao.titulo, avaliacao.nota, avaliacao.comentario,
            {PROXIMO_QUIZ}
        FROM public.tentativas_quiz AS tentativa
        JOIN public.quizzes AS versao ON versao.id = tentativa.quiz_id
        JOIN public.catalogo_quizzes AS item ON item.id = versao.catalogo_id
        JOIN public.quizzes AS publicada ON publicada.id = item.versao_publicada_id
        LEFT JOIN public.avaliacoes_quiz AS avaliacao
            ON avaliacao.catalogo_id = item.id AND avaliacao.usuario_id = tentativa.usuario_id
        WHERE tentativa.usuario_id = %s AND tentativa.id = %s AND item.estado = 'publicada'
          AND tentativa.total_questoes > 0
          AND tentativa.total_questoes = (
              SELECT count(*) FROM public.respostas_tentativa_quiz AS resposta
              JOIN public.questoes AS questao ON questao.id = resposta.questao_id
              WHERE resposta.tentativa_id = tentativa.id AND questao.quiz_id = versao.id
          )
        """,
        "FOR SHARE OF item, tentativa",
        "avaliacoes_quiz",
        "catalogo_id",
    ),
}


def buscar_atividade(conexao, tipo, usuario_id, referencia, *, bloquear=False):
    consulta, bloqueio, _, _ = _ALVOS[tipo]
    if bloquear:
        consulta += bloqueio
    return conexao.execute(consulta, (usuario_id, referencia)).fetchone()


def salvar_avaliacao(conexao, tipo, usuario_id, item_id, nota, comentario):
    # Tabela e coluna vêm do mapa interno de tipos de atividade.
    _, _, tabela, coluna = _ALVOS[tipo]
    conexao.execute(
        f"""
        INSERT INTO public.{tabela} (usuario_id, {coluna}, nota, comentario)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (usuario_id, {coluna}) DO UPDATE
        SET nota = EXCLUDED.nota, comentario = EXCLUDED.comentario
        """,
        (usuario_id, item_id, nota, comentario),
    )
    registrar_evento(
        usuario_id=usuario_id,
        evento="avaliacao.salva",
        resultado="sucesso",
        recurso_tipo=f"avaliacao_{tipo}",
        conexao=conexao,
    )


def listar_resumo_avaliacoes():
    with conectar_banco() as conexao:
        return conexao.execute(
            """
            SELECT 'Conteúdo' AS tipo, item.titulo, resumo.total, resumo.media
            FROM public.conteudos AS item
            LEFT JOIN (
                SELECT conteudo_id, count(*) AS total, round(avg(nota), 1) AS media
                FROM public.avaliacoes_conteudo
                GROUP BY conteudo_id
            ) AS resumo ON resumo.conteudo_id = item.id
            WHERE item.secao = 'conteudos' AND item.estado = 'publicada'
            UNION ALL
            SELECT 'Quiz', versao.titulo, resumo.total, resumo.media
            FROM public.catalogo_quizzes AS item
            JOIN public.quizzes AS versao ON versao.id = item.versao_publicada_id
            LEFT JOIN (
                SELECT catalogo_id, count(*) AS total, round(avg(nota), 1) AS media
                FROM public.avaliacoes_quiz
                GROUP BY catalogo_id
            ) AS resumo ON resumo.catalogo_id = item.id
            WHERE item.estado = 'publicada'
            ORDER BY tipo, titulo
            """
        ).fetchall()
