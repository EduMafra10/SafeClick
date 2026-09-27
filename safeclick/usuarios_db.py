from werkzeug.security import generate_password_hash

from safeclick.db import conectar_banco

def buscar_usuario_por_email(email):
    email = email.strip().lower()

    with conectar_banco() as conexao:
        return conexao.execute(
            """
            SELECT id, nome, email, senha_hash, perfil
            FROM public.usuarios
            WHERE lower(email) = %s
            """,
            (email,),
        ).fetchone()

def buscar_usuario_por_id(usuario_id):
    # sessao precisa dos dados do usuario sem carregar o hash da senha
    with conectar_banco() as conexao:
        return conexao.execute(
            """
            SELECT id, nome, email, perfil
            FROM public.usuarios
            WHERE id = %s
            """,
            (usuario_id,),
        ).fetchone()

def criar_usuario(nome, email, senha):
    nome = nome.strip()
    email = email.strip().lower()

    # gera o hash antes de abrir a conexao, a senha original nao vai para o banco
    senha_hash = generate_password_hash(senha, method="scrypt")

    with conectar_banco() as conexao:
        registro = conexao.execute(
            """
            INSERT INTO public.usuarios (nome, email, senha_hash, perfil)
            VALUES (%s, %s, %s, 'usuario')
            RETURNING id
            """,
            (nome, email, senha_hash),
        ).fetchone()

    return registro["id"]