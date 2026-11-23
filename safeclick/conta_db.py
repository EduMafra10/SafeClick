from werkzeug.security import check_password_hash, generate_password_hash

from safeclick.auditoria_db import registrar_evento
from safeclick.db import conectar_banco
from safeclick.icones_perfil import ICONES


class SenhaAtualIncorreta(ValueError):
    pass


class ContaIndisponivel(LookupError):
    pass


def buscar_conta(usuario_id, sessao_atual):
    with conectar_banco() as conexao:
        conta = conexao.execute(
            """
            SELECT u.nome, u.email, u.icone, u.mfa_confirmado_em IS NOT NULL AS autenticador_ativo,
                   (SELECT count(*) FROM public.sessoes_autenticadas AS s
                    WHERE s.usuario_id = u.id AND s.token_hash <> %s
                      AND s.expira_em > clock_timestamp()) AS outras_sessoes,
                   aceite.versao_termos, aceite.aceito_em
            FROM public.usuarios AS u
            LEFT JOIN LATERAL (
                SELECT versao_termos, aceito_em FROM public.aceites_termos
                WHERE usuario_id = u.id ORDER BY aceito_em DESC LIMIT 1
            ) AS aceite ON true
            WHERE u.id = %s
            """,
            (sessao_atual, usuario_id),
        ).fetchone()
    if conta is None:
        raise ContaIndisponivel
    return conta


def atualizar_nome(usuario_id, nome):
    with conectar_banco() as conexao:
        alterada = conexao.execute(
            "UPDATE public.usuarios SET nome = %s WHERE id = %s AND nome IS DISTINCT FROM %s",
            (nome, usuario_id, nome),
        ).rowcount
        if alterada:
            registrar_evento(
                usuario_id=usuario_id, evento="usuario.perfil_atualizado", resultado="sucesso",
                recurso_tipo="usuario", recurso_id=usuario_id, detalhes={"campos": ["nome"]},
                conexao=conexao,
            )
    return bool(alterada)


def atualizar_icone(usuario_id, icone):
    if icone is not None and icone not in ICONES:
        raise ValueError("Ícone inválido.")
    with conectar_banco() as conexao:
        alterada = conexao.execute("""UPDATE public.usuarios SET icone = %s
            WHERE id = %s AND icone IS DISTINCT FROM %s""", (icone, usuario_id, icone)).rowcount
        if alterada:
            registrar_evento(
                usuario_id=usuario_id, evento="usuario.perfil_atualizado", resultado="sucesso",
                recurso_tipo="usuario", recurso_id=usuario_id, detalhes={"campos": ["icone"]},
                conexao=conexao,
            )


def trocar_senha(usuario_id, senha_atual, nova_senha, sessao_atual):
    if not isinstance(nova_senha, str) or not 15 <= len(nova_senha) <= 128 or not nova_senha.strip():
        raise ValueError("Use uma senha com 15 a 128 caracteres.")
    novo_hash = generate_password_hash(nova_senha, method="scrypt")

    with conectar_banco() as conexao:
        conta = conexao.execute(
            "SELECT senha_hash, email FROM public.usuarios WHERE id = %s FOR NO KEY UPDATE",
            (usuario_id,),
        ).fetchone()
        if conta is None:
            raise ContaIndisponivel
        correta = check_password_hash(conta["senha_hash"], senha_atual)
        if correta:
            conexao.execute("UPDATE public.usuarios SET senha_hash = %s WHERE id = %s", (novo_hash, usuario_id))
            encerradas = _encerrar_outras(conexao, usuario_id, sessao_atual)
            conexao.execute("DELETE FROM public.logins_pendentes WHERE usuario_id = %s", (usuario_id,))
            detalhes = {"sessoes_encerradas": encerradas}
        else:
            detalhes = {"motivo": "senha_atual_incorreta"}
        registrar_evento(
            usuario_id=usuario_id, evento="usuario.senha_alterada", resultado="sucesso" if correta else "falha",
            recurso_tipo="usuario", recurso_id=usuario_id, detalhes=detalhes, conexao=conexao,
        )
    if not correta:
        raise SenhaAtualIncorreta
    return conta["email"]


def encerrar_outras_sessoes(usuario_id, sessao_atual):
    with conectar_banco() as conexao:
        encerradas = _encerrar_outras(conexao, usuario_id, sessao_atual)
        registrar_evento(
            usuario_id=usuario_id, evento="sessoes.encerradas", resultado="sucesso",
            recurso_tipo="sessao", detalhes={"sessoes_encerradas": encerradas}, conexao=conexao,
        )
    return encerradas


def _encerrar_outras(conexao, usuario_id, sessao_atual):
    return max(conexao.execute(
        "DELETE FROM public.sessoes_autenticadas WHERE usuario_id = %s AND token_hash <> %s",
        (usuario_id, sessao_atual),
    ).rowcount, 0)
