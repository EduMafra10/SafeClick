from safeclick.auditoria_db import registrar_evento
from safeclick.db import conectar_banco


class ContaNaoEncontrada(LookupError):
    pass


class SemAutenticador(ValueError):
    pass


_COLUNAS = """
    id, nome, email, perfil, criado_em,
    mfa_fator_sid IS NOT NULL AS tem_autenticador,
    mfa_confirmado_em IS NOT NULL AS autenticador_ativo,
    (
        SELECT max(a.criado_em) FROM public.logs_auditoria AS a
        WHERE a.usuario_id = usuarios.id AND a.evento = 'login.sucesso'
    ) AS ultimo_acesso
"""

SITUACOES_AUTENTICADOR = {
    "ativo": "mfa_confirmado_em IS NOT NULL",
    "pendente": "mfa_fator_sid IS NOT NULL AND mfa_confirmado_em IS NULL",
    "sem": "mfa_fator_sid IS NULL",
}


def _filtros(busca, autenticador):
    
    condicoes, parametros = [], {}
    if busca:
        if busca.isdecimal() and len(busca) <= 9:
            condicoes.append("id = %(id)s")
            parametros["id"] = int(busca)
        else:
            padrao = "%" + busca.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
            condicoes.append("(nome ILIKE %(padrao)s OR email ILIKE %(padrao)s)")
            parametros["padrao"] = padrao
    if autenticador:
        condicoes.append(SITUACOES_AUTENTICADOR[autenticador])
    filtro = "WHERE " + " AND ".join(condicoes) if condicoes else ""
    return filtro, parametros


def listar_contas(*, busca="", autenticador=None, pagina=1, por_pagina=20):
    if not isinstance(pagina, int) or isinstance(pagina, bool) or not 1 <= pagina <= 1000000:
        raise ValueError("Página inválida.")
    if not isinstance(por_pagina, int) or not 1 <= por_pagina <= 100:
        raise ValueError("Quantidade por página inválida.")

    if autenticador is not None and autenticador not in SITUACOES_AUTENTICADOR:
        raise ValueError("Situação do autenticador inválida.")

    filtro, parametros = _filtros(busca, autenticador)
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



PERFIS = ("usuario", "administrador")


class AlteracaoDePerfilRecusada(ValueError):
    pass


def alterar_perfil(administrador_id, usuario_id, novo_perfil):
    
    if novo_perfil not in PERFIS:
        raise ValueError("Perfil inválido.")
    if administrador_id == usuario_id:
        raise AlteracaoDePerfilRecusada("Você não pode alterar o próprio perfil.")

    with conectar_banco() as conexao:
        # trava os administradores para duas remoções simultâneas não deixarem o sistema sem nenhum
        administradores = conexao.execute(
            "SELECT id FROM public.usuarios WHERE perfil = 'administrador' FOR NO KEY UPDATE"
        ).fetchall()
        conta = conexao.execute(
            """
            SELECT id, perfil, mfa_confirmado_em IS NOT NULL AS autenticador_ativo
            FROM public.usuarios
            WHERE id = %s
            FOR NO KEY UPDATE
            """,
            (usuario_id,),
        ).fetchone()

        if conta is None:
            raise ContaNaoEncontrada
        if conta["perfil"] == novo_perfil:
            raise AlteracaoDePerfilRecusada("A conta já tem esse perfil.")
        if novo_perfil == "administrador" and not conta["autenticador_ativo"]:
            raise AlteracaoDePerfilRecusada(
                "Só é possível promover contas com o autenticador ativo."
            )
        if novo_perfil == "usuario" and len(administradores) <= 1:
            raise AlteracaoDePerfilRecusada("O sistema precisa ter pelo menos um administrador.")

        conexao.execute(
            "UPDATE public.usuarios SET perfil = %s WHERE id = %s", (novo_perfil, usuario_id)
        )
        sessoes = conexao.execute(
            "DELETE FROM public.sessoes_autenticadas WHERE usuario_id = %s", (usuario_id,)
        ).rowcount

        registrar_evento(
            usuario_id=administrador_id,
            evento="usuario.perfil_alterado",
            resultado="sucesso",
            recurso_tipo="usuario",
            recurso_id=usuario_id,
            detalhes={
                "perfil_anterior": conta["perfil"],
                "perfil_novo": novo_perfil,
                "sessoes_encerradas": max(sessoes, 0),
            },
            conexao=conexao,
        )