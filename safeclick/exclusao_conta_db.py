import hashlib
import re
import secrets

from werkzeug.security import check_password_hash

from safeclick.auditoria_db import registrar_evento
from safeclick.db import conectar_banco

PRAZO_ARREPENDIMENTO = "30 days"
PRAZO_EMAIL = "6 months"


class ContaJaExcluida(Exception):
    """A conta não existe mais, já foi excluída ou já está aguardando a exclusão."""


def _hash_token(token):
    """Mesmo formato dos links de recuperação de senha: só o hash vai para o banco."""
    if not isinstance(token, str) or not re.fullmatch(r"[A-Za-z0-9_-]{43}", token):
        return None
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def buscar_dados_exclusao(usuario_id):
    """Busca o que precisa ser conferido antes de excluir a conta."""
    with conectar_banco() as conexao:
        return conexao.execute(
            """
            SELECT
                usuario.senha_hash,
                usuario.mfa_identidade,
                usuario.mfa_fator_sid,
                -- o último administrador não pode sair, senão ninguém mais administra o site
                usuario.perfil = 'administrador' AND NOT EXISTS (
                    SELECT 1
                    FROM public.usuarios AS outro
                    WHERE outro.perfil = 'administrador'
                      AND outro.excluida_em IS NULL
                      AND outro.exclusao_solicitada_em IS NULL
                      AND outro.id <> usuario.id
                ) AS unico_administrador
            FROM public.usuarios AS usuario
            WHERE usuario.id = %s
              AND usuario.excluida_em IS NULL
              AND usuario.exclusao_solicitada_em IS NULL
            """,
            (usuario_id,),
        ).fetchone()


def registrar_recusa(usuario_id, motivo):
    """Registra na auditoria um pedido de exclusão que não foi adiante."""
    with conectar_banco() as conexao:
        registrar_evento(
            usuario_id=usuario_id,
            evento="conta.exclusao_agendada",
            resultado="falha",
            recurso_tipo="usuario",
            recurso_id=usuario_id,
            detalhes={"motivo": motivo},
            conexao=conexao,
        )


def _salvar_link(conexao, usuario_id):
    """Cria o link de reativação; um novo link substitui o anterior."""
    token = secrets.token_urlsafe(32)
    conexao.execute(
        """
        INSERT INTO public.reativacoes_conta (usuario_id, token_hash, criado_em, expira_em)
        SELECT id, %s, CURRENT_TIMESTAMP, exclusao_solicitada_em + %s::interval
        FROM public.usuarios
        WHERE id = %s
        ON CONFLICT (usuario_id) DO UPDATE
        SET token_hash = EXCLUDED.token_hash,
            criado_em = EXCLUDED.criado_em,
            expira_em = EXCLUDED.expira_em
        """,
        (_hash_token(token), PRAZO_ARREPENDIMENTO, usuario_id),
    )
    return token


def agendar_exclusao(usuario_id):
    """Desativa a conta na hora e abre o prazo de 30 dias para o titular se arrepender.

    Tudo acontece em uma transação: se algo falhar, nada muda (RN64).
    Devolve o e-mail, o nome, a data da exclusão definitiva (DD/MM/AAAA) e o token do link.
    """
    with conectar_banco() as conexao:
        conta = conexao.execute(
            """
            SELECT id
            FROM public.usuarios
            WHERE id = %s
              AND excluida_em IS NULL
              AND exclusao_solicitada_em IS NULL
            FOR UPDATE
            """,
            (usuario_id,),
        ).fetchone()

        if conta is None:
            raise ContaJaExcluida

        dados = conexao.execute(
            """
            UPDATE public.usuarios
            SET exclusao_solicitada_em = CURRENT_TIMESTAMP,
                mfa_identidade = gen_random_uuid(),
                mfa_fator_sid = NULL,
                mfa_confirmado_em = NULL
            WHERE id = %s
            RETURNING nome, email,
                to_char((exclusao_solicitada_em + %s::interval) AT TIME ZONE 'America/Sao_Paulo',
                        'DD/MM/YYYY') AS excluir_em
            """,
            (usuario_id, PRAZO_ARREPENDIMENTO),
        ).fetchone()

        # encerra o acesso em todos os dispositivos e invalida links pendentes (RN66)
        conexao.execute(
            "DELETE FROM public.sessoes_autenticadas WHERE usuario_id = %s", (usuario_id,)
        )
        conexao.execute(
            "DELETE FROM public.logins_pendentes WHERE usuario_id = %s", (usuario_id,)
        )
        conexao.execute(
            "DELETE FROM public.recuperacoes_senha WHERE usuario_id = %s", (usuario_id,)
        )

        token = _salvar_link(conexao, usuario_id)

        registrar_evento(
            usuario_id=usuario_id,
            evento="conta.exclusao_agendada",
            resultado="sucesso",
            recurso_tipo="usuario",
            recurso_id=usuario_id,
            conexao=conexao,
        )

    return {**dados, "token": token}


def gerar_novo_link(usuario_id):
    """Gera outro link para quem ainda está no prazo (usado quando a pessoa tenta entrar).

    Devolve None se a conta não estiver aguardando a exclusão ou se o prazo já acabou.
    """
    with conectar_banco() as conexao:
        dados = conexao.execute(
            """
            SELECT email,
                to_char((exclusao_solicitada_em + %s::interval) AT TIME ZONE 'America/Sao_Paulo',
                        'DD/MM/YYYY') AS excluir_em
            FROM public.usuarios
            WHERE id = %s
              AND excluida_em IS NULL
              AND exclusao_solicitada_em > CURRENT_TIMESTAMP - %s::interval
            FOR UPDATE
            """,
            (PRAZO_ARREPENDIMENTO, usuario_id, PRAZO_ARREPENDIMENTO),
        ).fetchone()

        if dados is None:
            return None

        return {**dados, "token": _salvar_link(conexao, usuario_id)}


def reativar_conta(token, senha):
    """Reativa a conta quando o link é válido e a senha confere.

    Devolve None para link inválido, {"senha_incorreta": True, ...} para senha errada
    e {"email": ...} quando a conta volta a ficar ativa.
    """
    token_hash = _hash_token(token)
    if token_hash is None:
        return None

    with conectar_banco() as conexao:
        conta = conexao.execute(
            """
            SELECT usuario.id, usuario.email, usuario.senha_hash
            FROM public.usuarios AS usuario
            JOIN public.reativacoes_conta AS link ON link.usuario_id = usuario.id
            WHERE link.token_hash = %s
              AND link.expira_em > CURRENT_TIMESTAMP
              AND usuario.excluida_em IS NULL
              AND usuario.exclusao_solicitada_em IS NOT NULL
            FOR UPDATE OF usuario
            """,
            (token_hash,),
        ).fetchone()

        if conta is None:
            return None

        if not check_password_hash(conta["senha_hash"], senha):
            registrar_evento(
                usuario_id=conta["id"],
                evento="conta.reativada",
                resultado="falha",
                recurso_tipo="usuario",
                recurso_id=conta["id"],
                detalhes={"motivo": "senha_incorreta"},
                conexao=conexao,
            )
            return {"senha_incorreta": True, "usuario_id": conta["id"]}

        conexao.execute(
            "UPDATE public.usuarios SET exclusao_solicitada_em = NULL WHERE id = %s",
            (conta["id"],),
        )
        # o link é de uso único
        conexao.execute(
            "DELETE FROM public.reativacoes_conta WHERE usuario_id = %s", (conta["id"],)
        )
        registrar_evento(
            usuario_id=conta["id"],
            evento="conta.reativada",
            resultado="sucesso",
            recurso_tipo="usuario",
            recurso_id=conta["id"],
            conexao=conexao,
        )

    return {"usuario_id": conta["id"], "email": conta["email"]}


def aplicar_prazos(conexao=None):
    """Conclui as exclusões cujo prazo de 30 dias acabou e descarta os e-mails vencidos.

    Não há agendador no projeto: a função é chamada no login, no cadastro,
    na reativação e na gestão de contas. Com uma conexão, entra na transação de quem chamou.
    Devolve os números das contas anonimizadas.
    """
    if conexao is None:
        with conectar_banco() as nova_conexao:
            return aplicar_prazos(nova_conexao)

    anonimizadas = conexao.execute(
        """
        WITH vencidas AS (
            SELECT id, email
            FROM public.usuarios
            WHERE excluida_em IS NULL
              AND exclusao_solicitada_em <= CURRENT_TIMESTAMP - %(prazo)s::interval
            FOR UPDATE SKIP LOCKED
        ),
        guardadas AS (
            -- o e-mail vai para a tabela separada, com data para ser descartado
            INSERT INTO public.contas_excluidas (usuario_id, email_guardado, descartar_em)
            SELECT id, email, CURRENT_TIMESTAMP + %(prazo_email)s::interval
            FROM vencidas
            ON CONFLICT (usuario_id) DO NOTHING
        ),
        links AS (
            DELETE FROM public.reativacoes_conta
            WHERE usuario_id IN (SELECT id FROM vencidas)
        )
        -- fica só o número da conta, o perfil e as datas
        UPDATE public.usuarios AS usuario
        SET nome = NULL,
            email = NULL,
            senha_hash = NULL,
            mfa_fator_sid = NULL,
            mfa_confirmado_em = NULL,
            excluida_em = CURRENT_TIMESTAMP
        FROM vencidas
        WHERE usuario.id = vencidas.id
        RETURNING usuario.id
        """,
        {"prazo": PRAZO_ARREPENDIMENTO, "prazo_email": PRAZO_EMAIL},
    ).fetchall()

    for conta in anonimizadas:
        registrar_evento(
            usuario_id=conta["id"],
            evento="conta.excluida",
            resultado="sucesso",
            recurso_tipo="usuario",
            recurso_id=conta["id"],
            detalhes={"origem": "fim_do_prazo"},
            conexao=conexao,
        )

    conexao.execute(
        "DELETE FROM public.contas_excluidas WHERE descartar_em <= CURRENT_TIMESTAMP"
    )

    return [conta["id"] for conta in anonimizadas]


def desvincular_autenticador(usuario_id):
    """Usado quando a Twilio já removeu o fator, mas o pedido de exclusão falhou.

    Assim o próximo login pede para configurar o aplicativo de novo.
    """
    with conectar_banco() as conexao:
        conexao.execute(
            """
            UPDATE public.usuarios
            SET mfa_fator_sid = NULL, mfa_confirmado_em = NULL
            WHERE id = %s AND excluida_em IS NULL
            """,
            (usuario_id,),
        )