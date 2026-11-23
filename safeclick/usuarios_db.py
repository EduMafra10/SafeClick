from werkzeug.security import generate_password_hash

from safeclick.auditoria_db import registrar_evento
from safeclick.db import conectar_banco
from safeclick.exclusao_conta_db import aplicar_prazos
from safeclick.termos_db import TermosDesatualizados, buscar_termos


def buscar_usuario_por_email(email):
    email = email.strip().lower()

    with conectar_banco() as conexao:
        return conexao.execute(
            """
            SELECT id, nome, email, senha_hash, perfil, exclusao_solicitada_em
            FROM public.usuarios
            WHERE lower(email) = %s
            """,
            (email,),
        ).fetchone()


def criar_usuario(nome, email, senha, *, aceitou_termos, versao_termos):
    from safeclick.privacidade import VERSAO_TERMOS

    if aceitou_termos is not True:
        raise ValueError("O aceite dos Termos de Uso é obrigatório.")
    if versao_termos != VERSAO_TERMOS:
        raise TermosDesatualizados("Leia e aceite a versão atual dos Termos de Uso.")

    nome = nome.strip()
    email = email.strip().lower()

    senha_hash = generate_password_hash(senha, method="scrypt")

    with conectar_banco() as conexao:
        documento = buscar_termos(versao_termos, conexao=conexao)
        if documento is None:
            raise RuntimeError("A versão dos Termos de Uso ainda não foi publicada.")
        aplicar_prazos(conexao)

        registro = conexao.execute(
            """
            INSERT INTO public.usuarios (nome, email, senha_hash, perfil)
            VALUES (%s, %s, %s, 'usuario')
            RETURNING id
            """,
            (nome, email, senha_hash),
        ).fetchone()

        registrar_evento(
            usuario_id=registro["id"],
            evento="usuario.cadastrado",
            resultado="sucesso",
            recurso_tipo="usuario",
            recurso_id=registro["id"],
            conexao=conexao,
        )

        aceite = conexao.execute(
            """
            INSERT INTO public.aceites_termos (usuario_id, versao_termos)
            VALUES (%s, %s)
            RETURNING id
            """,
            (registro["id"], versao_termos),
        ).fetchone()

        registrar_evento(
            usuario_id=registro["id"],
            evento="termo.aceito",
            resultado="sucesso",
            recurso_tipo="aceite_termos",
            recurso_id=aceite["id"],
            detalhes={"versao": versao_termos},
            conexao=conexao,
        )

    return registro["id"]


def buscar_mfa_por_usuario(usuario_id):
    with conectar_banco() as conexao:
        return conexao.execute(
            """
            SELECT id, mfa_identidade, mfa_fator_sid, mfa_confirmado_em
            FROM public.usuarios
            WHERE id = %s
            """,
            (usuario_id,),
        ).fetchone()
