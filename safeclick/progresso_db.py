from safeclick.db import conectar_banco
from safeclick.painel_db import _filtro_periodo


def buscar_detalhes_painel(usuario_id, inicio=None, fim=None):
    parametros = {'usuario_id': usuario_id, 'inicio': inicio, 'fim': fim}
    origem = """ FROM public.resultados_validos_atividades r
        WHERE usuario_id = %(usuario_id)s """ + _filtro_periodo('r.realizada_em')
    with conectar_banco() as conexao:
        categorias = conexao.execute("""
            SELECT tipo, COUNT(*) AS tentativas, COUNT(DISTINCT chave) AS atividades,
                   round(avg(pontos),1) AS media
        """ + origem + ' GROUP BY tipo ORDER BY tipo', parametros).fetchall()
        revisar = conexao.execute("""
            SELECT * FROM (
                SELECT DISTINCT ON (chave) tipo,formato,item_id,tentativa_id,titulo,pontos,disponivel
        """ + origem + """ ORDER BY chave,realizada_em DESC,tentativa_id DESC
            ) ultimas WHERE disponivel AND pontos < 70 ORDER BY pontos,titulo LIMIT 5
        """, parametros).fetchall()
        proximos = conexao.execute("""
            SELECT c.slug,c.titulo FROM public.conteudos c
            WHERE c.secao='conteudos' AND c.estado='publicada' AND c.removido_em IS NULL
              AND NOT EXISTS (SELECT 1 FROM public.conclusoes_conteudo cc
                              WHERE cc.conteudo_id=c.id AND cc.usuario_id=%s)
            ORDER BY c.id LIMIT 3
        """, (usuario_id,)).fetchall()
    return {'categorias': categorias, 'revisar': revisar, 'proximos': proximos}
