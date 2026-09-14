from .db import conectar_banco

def listar_conteudos():
    with conectar_banco() as conexao:
        with conexao.cursor() as cursor:
            cursor.execute("Select id, slug, titulo FROM public.conteudos ORDER BY id")
            return cursor.fetchall()

def buscar_conteudos(slug):
    with conectar_banco() as conexao:
        with conexao.cursor() as cursor:
            cursor.execute("SELECT slug, titulo, texto FROM public.conteudos WHERE slug = %s", (slug,))
            return cursor.fetchone()
