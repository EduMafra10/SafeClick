from .db import conectar_banco
from .auditoria_db import registrar_evento, usuario_autenticado_id

def listar_conteudos():
    with conectar_banco() as conexao:
        with conexao.cursor() as cursor:
            cursor.execute("Select id, slug, titulo FROM public.conteudos ORDER BY id")
            return cursor.fetchall()

def buscar_conteudos(slug):
    with conectar_banco() as conexao:
        conteudo = conexao.execute(
            """
            SELECT id, slug, titulo, texto
            FROM public.conteudos
            WHERE slug = %s
            """,
            (slug,),
        ).fetchone()

        if conteudo is not None:
            registrar_evento(
                usuario_id=usuario_autenticado_id(),
                evento="conteudo.visualizado",
                resultado="sucesso",
                recurso_tipo="conteudo",
                recurso_id=conteudo["id"],
                conexao=conexao,
            )

        return conteudo
