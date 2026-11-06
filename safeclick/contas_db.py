from safeclick.auditoria_db import registrar_evento
from safeclick.db import conectar_banco


class ContaNaoEncontrada(LookupError):
    pass


class SemAutenticador(ValueError):
    pass


_COLUNAS = """
    id, nome, email, perfil, criado_em,
    mfa_fator_sid IS NOT NULL AS tem_autenticador,
    mfa_confirmado_em IS NOT NULL AS autenticador_ativo
"""


def _filtro_busca(busca):
    """Busca por número da conta, nome ou e-mail (sem diferenciar maiúsculas)."""
    if not busca:
        return "", {}
    if busca.isdecimal() and len(busca) <= 9:
        return "WHERE id = %(id)s", {"id": int(busca)}
    padrao = "%" + busca.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
    return "WHERE nome ILIKE %(padrao)s OR email ILIKE %(padrao)s", {"padrao": padrao}


def listar_contas(*, busca="", pagina=1, por_pagina=20):
    if not isinstance(pagina, int) or isinstance(pagina, bool) or not 1 <= pagina <= 1000000:
        raise ValueError("Página inválida.")
    if not isinstance(por_pagina, int) or not 1 <= por_pagina <= 100:
        raise ValueError("Quantidade por página inválida.")

    filtro, parametros = _filtro_busca(busca)
    with conectar_banco() as conexao:
        total = conexao.execute(
            f"SELECT count(*) AS total FROM public.usuarios {filtro}", parametros
        ).fetchone()["total"]
        contas = conexao.execute(
            f"""
            SELECT {_COLUNAS}
            FROM public.usuarios
            {filtro}
            ORDER BY id
            LIMIT %(limite)s OFFSET %(deslocamento)s
            """,
            {**parametros, "limite": por_pagina, "deslocamento": (pagina - 1) * por_pagina},
        ).fetchall()
    return contas, total


def obter_conta(usuario_id):
    with conectar_banco() as conexao:
        return conexao.execute(
            f"SELECT {_COLUNAS} FROM public.usuarios WHERE id = %s", (usuario_id,)
        ).fetchone()


def redefinir_autenticador(administrador_id, usuario_id):
    """Desvincula o autenticador, encerra as sessões e registra quem fez.

    Devolve a identidade e o fator antigos para a remoção na Twilio,
    feita depois que o banco já não aceita mais o aplicativo antigo.
    """
    with conectar_banco() as conexao:
        conta = conexao.execute(
            """
            SELECT id, mfa_identidade, mfa_fator_sid
            FROM public.usuarios
            WHERE id = %s
            FOR NO KEY UPDATE
            """,
            (usuario_id,),
        ).fetchone()

        if conta is None:
            raise ContaNaoEncontrada
        if conta["mfa_fator_sid"] is None:
            raise SemAutenticador("Esta conta ainda não configurou o autenticador.")

        conexao.execute(
            """
            UPDATE public.usuarios
            SET mfa_fator_sid = NULL, mfa_confirmado_em = NULL
            WHERE id = %s
            """,
            (usuario_id,),
        )
        sessoes = conexao.execute(
            "DELETE FROM public.sessoes_autenticadas WHERE usuario_id = %s", (usuario_id,)
        ).rowcount
        conexao.execute(
            "DELETE FROM public.logins_pendentes WHERE usuario_id = %s", (usuario_id,)
        )

        registrar_evento(
            usuario_id=administrador_id,
            evento="mfa.reconfiguracao_administrativa",
            resultado="sucesso",
            recurso_tipo="usuario",
            recurso_id=usuario_id,
            detalhes={"sessoes_encerradas": max(sessoes, 0)},
            conexao=conexao,
        )

    return {"identidade": conta["mfa_identidade"], "fator_sid": conta["mfa_fator_sid"]}