from safeclick.auditoria_db import registrar_evento
from safeclick.db import conectar_banco
from safeclick.navegacao_atividades import PROXIMO_CONTEUDO, PROXIMO_QUIZ
from safeclick.avaliacoes_config import VERSAO_AVISO


_ALVOS = {
    "conteudo": (
        f"""
        SELECT item.id, item.titulo, avaliacao.nota, avaliacao.comentario,
            avaliacao.publicar_nota, avaliacao.publicar_comentario, avaliacao.maior_de_idade,
            avaliacao.moderacao,
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
            avaliacao.publicar_nota, avaliacao.publicar_comentario, avaliacao.maior_de_idade,
            avaliacao.moderacao,
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


def salvar_avaliacao(conexao, tipo, usuario_id, item_id, nota, comentario, *,
                     publicar_nota=False, publicar_comentario=False, maior_de_idade=False, aviso_versao=None):
    # Tabela e coluna vêm do mapa interno de tipos de atividade.
    _, _, tabela, coluna = _ALVOS[tipo]
    if type(nota) is not int or not 1 <= nota <= 5:
        raise ValueError('Informe uma nota inteira de 1 a 5.')
    if comentario is not None and (not isinstance(comentario, str) or len(comentario) > 500 or '\x00' in comentario):
        raise ValueError('Comentário inválido.')
    if any(type(v) is not bool for v in (publicar_nota, publicar_comentario, maior_de_idade)):
        raise ValueError('Opção de privacidade inválida.')
    if (publicar_nota and (not maior_de_idade or aviso_versao != VERSAO_AVISO)
            or publicar_comentario and (not publicar_nota or not comentario or not comentario.strip())):
        raise ValueError('Confira a autorização de publicação e o comentário.')
    # Serializa o envio com uma eventual desativação ou exclusão da conta.
    titular = conexao.execute('''
        SELECT id FROM public.usuarios WHERE id=%s
          AND excluida_em IS NULL AND exclusao_solicitada_em IS NULL FOR SHARE
    ''', (usuario_id,)).fetchone()
    if titular is None:
        raise PermissionError('A conta não está disponível para enviar avaliações.')
    conexao.execute(
        f"""
        INSERT INTO public.{tabela} AS atual
            (usuario_id, {coluna}, nota, comentario, publicar_nota, publicar_comentario,
             maior_de_idade, aviso_versao, autorizado_em, atualizada_em, moderacao)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s,
                CASE WHEN %s THEN CURRENT_TIMESTAMP END, CURRENT_TIMESTAMP, %s)
        ON CONFLICT (usuario_id, {coluna}) DO UPDATE
        SET nota = EXCLUDED.nota, comentario = EXCLUDED.comentario,
            publicar_nota = EXCLUDED.publicar_nota, publicar_comentario = EXCLUDED.publicar_comentario,
            maior_de_idade = EXCLUDED.maior_de_idade, aviso_versao = EXCLUDED.aviso_versao,
            autorizado_em = EXCLUDED.autorizado_em, atualizada_em = CURRENT_TIMESTAMP,
            revisao = atual.revisao + 1,
            moderacao = CASE WHEN NOT EXCLUDED.publicar_comentario THEN 'nao_solicitada'
                WHEN atual.publicar_comentario AND atual.comentario IS NOT DISTINCT FROM EXCLUDED.comentario
                THEN atual.moderacao ELSE 'pendente' END,
            moderado_por = CASE WHEN EXCLUDED.publicar_comentario AND atual.publicar_comentario
                AND atual.comentario IS NOT DISTINCT FROM EXCLUDED.comentario THEN atual.moderado_por END,
            moderado_em = CASE WHEN EXCLUDED.publicar_comentario AND atual.publicar_comentario
                AND atual.comentario IS NOT DISTINCT FROM EXCLUDED.comentario THEN atual.moderado_em END
        """,
        (usuario_id, item_id, nota, comentario, publicar_nota, publicar_comentario,
         maior_de_idade, aviso_versao, publicar_nota, 'pendente' if publicar_comentario else 'nao_solicitada'),
    )
    registrar_evento(
        usuario_id=usuario_id,
        evento="avaliacao.salva",
        resultado="sucesso",
        recurso_tipo=f"avaliacao_{tipo}",
        conexao=conexao,
        detalhes=({'nota_publica': publicar_nota, 'comentario_publico': publicar_comentario,
                   'aviso': aviso_versao} if aviso_versao else None),
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


BASE_AVALIACOES = """
    SELECT 'conteudo'::text AS tipo, c.id AS item_id, c.titulo, c.slug,
           a.usuario_id, a.nota, a.comentario, a.publicar_nota, a.publicar_comentario,
           a.maior_de_idade, a.aviso_versao, a.moderacao, a.atualizada_em, a.revisao,
           c.estado = 'publicada' AND c.removido_em IS NULL AS publicada,
           u.excluida_em IS NULL AND u.exclusao_solicitada_em IS NULL AS conta_ativa
    FROM public.avaliacoes_conteudo a JOIN public.conteudos c ON c.id = a.conteudo_id
    JOIN public.usuarios u ON u.id = a.usuario_id
    WHERE c.secao = 'conteudos'
    UNION ALL
    SELECT 'quiz', c.id, q.titulo, NULL::text, a.usuario_id, a.nota, a.comentario,
           a.publicar_nota, a.publicar_comentario, a.maior_de_idade, a.aviso_versao,
           a.moderacao, a.atualizada_em, a.revisao,
           c.estado = 'publicada' AND c.removido_em IS NULL,
           u.excluida_em IS NULL AND u.exclusao_solicitada_em IS NULL
    FROM public.avaliacoes_quiz a JOIN public.catalogo_quizzes c ON c.id = a.catalogo_id
    JOIN public.quizzes q ON q.id = c.versao_publicada_id
    JOIN public.usuarios u ON u.id = a.usuario_id
"""
FILTRO_PUBLICO = 'publicada AND conta_ativa AND publicar_nota AND maior_de_idade AND aviso_versao = %(aviso)s'


def listar_publicas(*, tipo='', busca='', pagina=1):
    origem = """
        WITH itens AS (
            SELECT 'conteudo'::text AS tipo, id, titulo FROM public.conteudos
            WHERE secao = 'conteudos' AND estado = 'publicada' AND removido_em IS NULL
            UNION ALL
            SELECT 'quiz', c.id, q.titulo FROM public.catalogo_quizzes c
            JOIN public.quizzes q ON q.id = c.versao_publicada_id
            WHERE c.estado = 'publicada' AND c.removido_em IS NULL
        ), avaliacoes AS (""" + BASE_AVALIACOES + """), medias AS (
            SELECT tipo, item_id, COUNT(*) AS total, round(avg(nota), 1) AS media
            FROM avaliacoes WHERE """ + FILTRO_PUBLICO + """ GROUP BY tipo, item_id
        )
    """
    filtro = "WHERE (%(tipo)s = '' OR i.tipo = %(tipo)s) AND strpos(lower(i.titulo), lower(%(busca)s)) > 0"
    parametros = {'tipo': tipo, 'busca': busca, 'aviso': VERSAO_AVISO, 'inicio': (pagina - 1) * 20}
    with conectar_banco() as conexao:
        total = conexao.execute(origem + 'SELECT COUNT(*) AS total FROM itens i ' + filtro, parametros).fetchone()['total']
        itens = conexao.execute(origem + """
            SELECT i.*, COALESCE(m.total, 0) AS total, m.media FROM itens i
            LEFT JOIN medias m ON m.tipo = i.tipo AND m.item_id = i.id
        """ + filtro + ' ORDER BY i.tipo, i.titulo, i.id LIMIT 20 OFFSET %(inicio)s', parametros).fetchall()
    return itens, total


def detalhar_publicas(tipo, item_id, pagina=1):
    with conectar_banco() as conexao:
        if tipo == 'conteudo':
            consulta = "SELECT id,titulo,slug FROM public.conteudos WHERE id=%s AND secao='conteudos' AND estado='publicada' AND removido_em IS NULL"
        elif tipo == 'quiz':
            consulta = """SELECT c.id,q.titulo,NULL::text AS slug FROM public.catalogo_quizzes c
                          JOIN public.quizzes q ON q.id=c.versao_publicada_id
                          WHERE c.id=%s AND c.estado='publicada' AND c.removido_em IS NULL"""
        else:
            raise ValueError('Tipo de atividade inválido.')
        atividade = conexao.execute(consulta, (item_id,)).fetchone()
        if atividade is None:
            return None
        parametros = {'tipo': tipo, 'item': item_id, 'aviso': VERSAO_AVISO, 'inicio': (pagina - 1) * 10}
        origem = 'WITH avaliacoes AS (' + BASE_AVALIACOES + ') '
        filtro = ' FROM avaliacoes WHERE tipo=%(tipo)s AND item_id=%(item)s AND ' + FILTRO_PUBLICO
        resumo = conexao.execute(origem + """
            SELECT COUNT(*) AS total, round(avg(nota),1) AS media,
                   COUNT(*) FILTER (WHERE publicar_comentario AND moderacao='aprovada') AS comentarios
        """ + filtro, parametros).fetchone()
        comentarios = conexao.execute(origem + """
            SELECT nota,comentario,to_char(atualizada_em AT TIME ZONE 'America/Sao_Paulo','DD/MM/YYYY') AS data
        """ + filtro + """ AND publicar_comentario AND moderacao='aprovada'
            ORDER BY atualizada_em DESC, usuario_id LIMIT 10 OFFSET %(inicio)s
        """, parametros).fetchall()
    return atividade, resumo, comentarios


def listar_minhas(usuario_id):
    with conectar_banco() as conexao:
        return conexao.execute('WITH avaliacoes AS (' + BASE_AVALIACOES + """ )
            SELECT tipo,item_id,titulo,slug,nota,comentario,publicar_nota,publicar_comentario,moderacao,publicada,
                (SELECT MAX(r.tentativa_id) FROM public.resultados_validos_atividades r
                 WHERE r.usuario_id=avaliacoes.usuario_id AND r.tipo='quiz' AND r.item_id=avaliacoes.item_id) AS ultimo_resultado
            FROM avaliacoes WHERE usuario_id=%s ORDER BY atualizada_em DESC NULLS LAST,titulo
        """, (usuario_id,)).fetchall()


def excluir_avaliacao(usuario_id, tipo, item_id):
    _, _, tabela, coluna = _ALVOS[tipo]
    with conectar_banco() as conexao:
        excluida = conexao.execute(f'DELETE FROM public.{tabela} WHERE usuario_id=%s AND {coluna}=%s RETURNING usuario_id',
                                   (usuario_id, item_id)).fetchone()
        if excluida:
            registrar_evento(usuario_id, 'avaliacao.excluida', 'sucesso', recurso_tipo='avaliacao_' + tipo, conexao=conexao)
    return excluida is not None


def retirar_publicacao(usuario_id, tipo, item_id):
    _, _, tabela, coluna = _ALVOS[tipo]
    with conectar_banco() as conexao:
        item = conexao.execute(f"""
            UPDATE public.{tabela} SET publicar_nota=FALSE,publicar_comentario=FALSE,
                autorizado_em=NULL,moderacao='nao_solicitada',moderado_por=NULL,moderado_em=NULL,revisao=revisao+1
            WHERE usuario_id=%s AND {coluna}=%s RETURNING usuario_id
        """, (usuario_id, item_id)).fetchone()
        if item:
            registrar_evento(usuario_id, 'avaliacao.publicacao_retirada', 'sucesso',
                             recurso_tipo='avaliacao_' + tipo, conexao=conexao)
    return item is not None


def listar_gestao(pagina=1, estado=''):
    parametros = {'aviso': VERSAO_AVISO, 'estado': estado, 'inicio': (pagina - 1) * 20}
    origem = 'WITH avaliacoes AS (' + BASE_AVALIACOES + ') '
    filtro = ' FROM avaliacoes WHERE conta_ativa AND aviso_versao=%(aviso)s AND (%(estado)s=\'\' OR moderacao=%(estado)s)'
    with conectar_banco() as conexao:
        total = conexao.execute(origem + 'SELECT COUNT(*) AS total' + filtro, parametros).fetchone()['total']
        itens = conexao.execute(origem + """SELECT tipo,item_id,titulo,usuario_id,nota,comentario,publicar_nota,
            publicar_comentario,moderacao,revisao,publicada""" + filtro
                                + ' ORDER BY atualizada_em DESC,usuario_id,item_id LIMIT 20 OFFSET %(inicio)s', parametros).fetchall()
    return itens, total


def moderar_comentario(administrador_id, tipo, item_id, autor_id, revisao, acao):
    if acao not in {'aprovar', 'ocultar'}:
        raise ValueError('Ação inválida.')
    _, _, tabela, coluna = _ALVOS[tipo]
    with conectar_banco() as conexao:
        from safeclick.catalogo_admin_db import _exigir_administrador
        _exigir_administrador(conexao, administrador_id)
        item = conexao.execute('WITH avaliacoes AS (' + BASE_AVALIACOES + """ )
            SELECT comentario,publicada,conta_ativa,publicar_nota,publicar_comentario,maior_de_idade,aviso_versao
            FROM avaliacoes WHERE tipo=%s AND item_id=%s AND usuario_id=%s
        """, (tipo, item_id, autor_id)).fetchone()
        exigidos = ('publicada', 'conta_ativa', 'publicar_nota', 'publicar_comentario', 'maior_de_idade')
        if not item or not all(item[k] for k in exigidos) or item['aviso_versao'] != VERSAO_AVISO:
            raise ValueError('O comentário não está disponível para publicação.')
        # A revisão impede aprovar um texto alterado depois da leitura do administrador.
        alterada = conexao.execute(f"""
            UPDATE public.{tabela} SET moderacao=%s,moderado_por=%s,moderado_em=CURRENT_TIMESTAMP,revisao=revisao+1
            WHERE usuario_id=%s AND {coluna}=%s AND revisao=%s RETURNING revisao
        """, ('aprovada' if acao == 'aprovar' else 'rejeitada', administrador_id, autor_id, item_id, revisao)).fetchone()
        if not alterada:
            raise ValueError('A avaliação mudou. Reabra a lista antes de moderar.')
        registrar_evento(administrador_id, 'avaliacao.moderada', 'sucesso', recurso_tipo='avaliacao_' + tipo,
                         detalhes={'acao': acao}, conexao=conexao)
