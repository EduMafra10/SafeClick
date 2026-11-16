from .db import conectar_banco
from .auditoria_db import registrar_evento, usuario_autenticado_id
from .navegacao_atividades import PROXIMO_CONTEUDO


def listar_conteudos(secao="conteudos"):
   
    with conectar_banco() as conexao:
        return conexao.execute(
            """
            SELECT
                c.id,
                c.slug,
                c.titulo,
                cc.concluido_em IS NOT NULL AS concluido
            FROM public.conteudos AS c
            LEFT JOIN public.conclusoes_conteudo AS cc
                ON cc.conteudo_id = c.id
               AND cc.usuario_id = %s
            WHERE c.secao = %s AND c.estado = 'publicada'
            ORDER BY c.id
            """,
            (usuario_autenticado_id(), secao),
        ).fetchall()


def buscar_conteudos(slug, secao="conteudos"):
    with conectar_banco() as conexao:
        conteudo = conexao.execute(
            f"""
            SELECT
                item.id,
                item.slug,
                item.titulo,
                item.texto,
                to_char(
                    cc.concluido_em AT TIME ZONE 'America/Sao_Paulo',
                    'DD/MM/YYYY'
                ) AS concluido_em,
                {PROXIMO_CONTEUDO}
            FROM public.conteudos AS item
            LEFT JOIN public.conclusoes_conteudo AS cc
                ON cc.conteudo_id = item.id
               AND cc.usuario_id = %s
            WHERE item.slug = %s AND item.secao = %s AND item.estado = 'publicada'
            """,
            (usuario_autenticado_id(), slug, secao),
        ).fetchone()

        if conteudo is not None and secao == "conteudos":
            registrar_evento(
                usuario_id=usuario_autenticado_id(),
                evento="conteudo.visualizado",
                resultado="sucesso",
                recurso_tipo="conteudo",
                recurso_id=conteudo["id"],
                conexao=conexao,
            )

        return conteudo


def concluir_conteudo(usuario_id, slug):
    
    with conectar_banco() as conexao:
        conteudo = conexao.execute(
            """
            SELECT id FROM public.conteudos
            WHERE slug = %s AND secao = 'conteudos' AND estado = 'publicada'
            FOR SHARE
            """,
            (slug,),
        ).fetchone()

        if conteudo is None:
            return None

        
        registro = conexao.execute(
            """
            INSERT INTO public.conclusoes_conteudo (usuario_id, conteudo_id)
            VALUES (%s, %s)
            ON CONFLICT (usuario_id, conteudo_id) DO NOTHING
            RETURNING conteudo_id
            """,
            (usuario_id, conteudo["id"]),
        ).fetchone()

        if registro is None:
            return False

        
        registrar_evento(
            usuario_id=usuario_id,
            evento="conteudo.concluido",
            resultado="sucesso",
            recurso_tipo="conteudo",
            recurso_id=conteudo["id"],
            conexao=conexao,
        )

        return True
