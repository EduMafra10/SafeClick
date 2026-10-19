from werkzeug.security import generate_password_hash

from safeclick.auditoria_db import registrar_evento
from safeclick.db import conectar_banco
from safeclick.termos_db import TermosDesatualizados, buscar_termos

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

def criar_usuario(nome, email, senha, *, aceitou_termos, versao_termos):
    from safeclick.privacidade import VERSAO_TERMOS

    # A verificacao no servidor tambem protege chamadas fora do formulario.
    if aceitou_termos is not True:
        raise ValueError("O aceite dos Termos de Uso é obrigatório.")
    if versao_termos != VERSAO_TERMOS:
        raise TermosDesatualizados("Leia e aceite a versão atual dos Termos de Uso.")

    nome = nome.strip()
    email = email.strip().lower()

    # gera o hash antes de abrir a conexao, a senha original nao vai para o banco
    senha_hash = generate_password_hash(senha, method="scrypt")

    with conectar_banco() as conexao:
        documento = buscar_termos(versao_termos, conexao=conexao)
        if documento is None:
            raise RuntimeError("A versão dos Termos de Uso ainda não foi publicada.")

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

        # Conta, aceite e auditoria sao confirmados ou desfeitos juntos.
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

def salvar_fator_mfa(usuario_id, fator_sid, fator_anterior=None):
    # so altera uma configuracao pendente que ainda nao foi substituida
    with conectar_banco() as conexao:
        registro = conexao.execute(
            """
            UPDATE public.usuarios
            SET mfa_fator_sid = %s
            WHERE id = %s
              AND mfa_confirmado_em IS NULL
              AND mfa_fator_sid IS NOT DISTINCT FROM %s
            RETURNING id
            """,
            (fator_sid, usuario_id, fator_anterior),
        ).fetchone()
    return registro is not None

def confirmar_mfa(usuario_id, fator_sid):
    # é usado apos o twilio confirmar o primeiro codigo do autenticador
    with conectar_banco() as conexao:
        registro = conexao.execute(
            """
            UPDATE public.usuarios
            SET mfa_confirmado_em = CURRENT_TIMESTAMP
            WHERE id = %s
              AND mfa_fator_sid = %s
              AND mfa_confirmado_em IS NULL
            RETURNING id
            """,
            (usuario_id, fator_sid),
        ).fetchone()
    return registro is not None
