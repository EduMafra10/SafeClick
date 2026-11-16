import secrets

from safeclick.auditoria_db import registrar_evento
from safeclick.db import conectar_banco

VERSAO_AVISO = 'participacao-2026-11-v1'

CLASSIFICACAO = """
WITH melhores AS (
    SELECT r.usuario_id, r.chave, MAX(r.pontos) AS pontos
    FROM public.resultados_validos_atividades r
    JOIN public.usuarios u ON u.id = r.usuario_id
    JOIN public.preferencias_ranking p ON p.usuario_id = u.id
    WHERE r.disponivel AND u.perfil = 'usuario'
      AND u.excluida_em IS NULL AND u.exclusao_solicitada_em IS NULL
      AND p.maior_de_idade AND p.aviso_versao = %(aviso)s
    GROUP BY r.usuario_id, r.chave
), totais AS (
    SELECT usuario_id, SUM(pontos) AS pontos, COUNT(*) AS atividades
    FROM melhores GROUP BY usuario_id
), classificados AS (
    SELECT t.usuario_id, p.apelido, t.pontos, t.atividades,
           DENSE_RANK() OVER (ORDER BY t.pontos DESC, t.atividades DESC) AS posicao
    FROM totais t JOIN public.preferencias_ranking p ON p.usuario_id = t.usuario_id
)
"""


def buscar_ranking(pagina=1, por_pagina=20):
    with conectar_banco() as conexao:
        parametros = {'aviso': VERSAO_AVISO, 'limite': por_pagina, 'inicio': (pagina - 1) * por_pagina}
        total = conexao.execute(CLASSIFICACAO + 'SELECT COUNT(*) AS total FROM classificados', parametros).fetchone()['total']
        linhas = conexao.execute(CLASSIFICACAO + """
            SELECT apelido, pontos, atividades, posicao FROM classificados
            ORDER BY pontos DESC, atividades DESC, apelido LIMIT %(limite)s OFFSET %(inicio)s
        """, parametros).fetchall()
    return linhas, total


def buscar_preferencia(usuario_id):
    with conectar_banco() as conexao:
        return conexao.execute(
            'SELECT apelido, autorizado_em FROM public.preferencias_ranking WHERE usuario_id = %s',
            (usuario_id,),
        ).fetchone()


def alterar_participacao(usuario_id, participar, maior_de_idade):
    with conectar_banco() as conexao:
        usuario = conexao.execute("""
            SELECT id, perfil FROM public.usuarios WHERE id = %s
              AND excluida_em IS NULL AND exclusao_solicitada_em IS NULL FOR UPDATE
        """, (usuario_id,)).fetchone()
        if not usuario or (participar and usuario['perfil'] != 'usuario'):
            raise PermissionError('Somente contas de usuário ativas podem participar do ranking.')
        if type(participar) is not bool or (participar and maior_de_idade is not True):
            raise ValueError('A participação pública está disponível para quem declara ter 18 anos ou mais.')
        if participar:
            codigo = secrets.token_hex(6).upper()
            apelido = f'Participante {codigo[:4]}-{codigo[4:8]}-{codigo[8:]}'
            conexao.execute("""
                INSERT INTO public.preferencias_ranking (usuario_id, apelido, aviso_versao, maior_de_idade)
                VALUES (%s, %s, %s, TRUE) ON CONFLICT (usuario_id) DO NOTHING
            """, (usuario_id, apelido, VERSAO_AVISO))
        else:
            conexao.execute('DELETE FROM public.preferencias_ranking WHERE usuario_id = %s', (usuario_id,))
        registrar_evento(usuario_id, 'ranking.preferencia_atualizada', 'sucesso', recurso_tipo='ranking',
                         detalhes={'participar': participar, 'aviso': VERSAO_AVISO}, conexao=conexao)


def buscar_resumo_pessoal(usuario_id):
    with conectar_banco() as conexao:
        resumo = conexao.execute("""
            SELECT COALESCE(SUM(pontos), 0) AS pontos, COUNT(*) AS atividades
            FROM (SELECT chave, MAX(pontos) AS pontos FROM public.resultados_validos_atividades
                  WHERE usuario_id = %s AND disponivel GROUP BY chave) melhores
        """, (usuario_id,)).fetchone()
        posicao = conexao.execute(CLASSIFICACAO + """
            SELECT posicao, apelido FROM classificados WHERE usuario_id = %(usuario)s
        """, {'aviso': VERSAO_AVISO, 'usuario': usuario_id}).fetchone()
    return dict(resumo, posicao=posicao['posicao'] if posicao else None)
