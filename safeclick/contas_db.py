from werkzeug.security import check_password_hash

from safeclick.auditoria_db import registrar_evento
from safeclick.db import conectar_banco
from safeclick.exclusao_conta_db import PRAZO_ARREPENDIMENTO, PRAZO_EMAIL, aplicar_prazos


class ContaNaoEncontrada(LookupError):
    pass


class SemAutenticador(ValueError):
    pass


_COLUNAS = f"""
    id, nome, email, perfil, criado_em,
    mfa_fator_sid IS NOT NULL AS tem_autenticador,
    mfa_confirmado_em IS NOT NULL AS autenticador_ativo,
    (
        SELECT max(a.criado_em) FROM public.logs_auditoria AS a
        WHERE a.usuario_id = usuarios.id AND a.evento = 'login.sucesso'
    ) AS ultimo_acesso,
    excluida_em,
    exclusao_solicitada_em + '{PRAZO_ARREPENDIMENTO}'::interval AS exclusao_marcada_para,
    guardado.email_guardado,
    guardado.descartar_em
"""

_GUARDADO = """
    LEFT JOIN public.contas_excluidas AS guardado
        ON guardado.usuario_id = usuarios.id
       AND guardado.descartar_em > CURRENT_TIMESTAMP
"""

SITUACOES_CONTA = {
    "ativas": "usuarios.excluida_em IS NULL AND usuarios.exclusao_solicitada_em IS NULL",
    "agendadas": "usuarios.excluida_em IS NULL AND usuarios.exclusao_solicitada_em IS NOT NULL",
    "excluidas": "usuarios.excluida_em IS NOT NULL",
}

_ATIVA = SITUACOES_CONTA["ativas"]

SITUACOES_AUTENTICADOR = {
    "ativo": "mfa_confirmado_em IS NOT NULL",
    "pendente": "mfa_fator_sid IS NOT NULL AND mfa_confirmado_em IS NULL",
    "sem": "mfa_fator_sid IS NULL",
}


def _filtros(busca, autenticador, situacao="ativas"):

    condicoes, parametros = [], {}
    if busca:
        if busca.isdecimal() and len(busca) <= 9:
            condicoes.append("id = %(id)s")
            parametros["id"] = int(busca)
        else:
            padrao = "%" + busca.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
            if situacao == "excluidas":
                condicoes.append("guardado.email_guardado ILIKE %(padrao)s")
            else:
                condicoes.append("(nome ILIKE %(padrao)s OR email ILIKE %(padrao)s)")
            parametros["padrao"] = padrao
    if autenticador:
        condicoes.append(SITUACOES_AUTENTICADOR[autenticador])
    condicoes.append(SITUACOES_CONTA[situacao])
    filtro = "WHERE " + " AND ".join(condicoes) if condicoes else ""
    return filtro, parametros


ORDENS_CONTAS = {
    "recentes": "id DESC",
    "antigas": "id",
    "nome": "lower(nome), id",
}


def listar_contas(*, busca="", autenticador=None, situacao="ativas", ordem="recentes", pagina=1, por_pagina=20):
    if not isinstance(pagina, int) or isinstance(pagina, bool) or not 1 <= pagina <= 1000000:
        raise ValueError("Página inválida.")
    if not isinstance(por_pagina, int) or not 1 <= por_pagina <= 100:
        raise ValueError("Quantidade por página inválida.")

    if autenticador is not None and autenticador not in SITUACOES_AUTENTICADOR:
        raise ValueError("Situação do autenticador inválida.")
    if situacao not in SITUACOES_CONTA:
        raise ValueError("Situação da conta inválida.")
    if ordem not in ORDENS_CONTAS:
        raise ValueError("Ordem inválida.")

    filtro, parametros = _filtros(busca, autenticador, situacao)
    with conectar_banco() as conexao:
        aplicar_prazos(conexao)
        total = conexao.execute(
            f"SELECT count(*) AS total FROM public.usuarios {_GUARDADO} {filtro}", parametros
        ).fetchone()["total"]
        contas = conexao.execute(
            f"""
            SELECT {_COLUNAS}
            FROM public.usuarios
            {_GUARDADO}
            {filtro}
            ORDER BY {ORDENS_CONTAS[ordem]}
            LIMIT %(limite)s OFFSET %(deslocamento)s
            """,
            {**parametros, "limite": por_pagina, "deslocamento": (pagina - 1) * por_pagina},
        ).fetchall()
    return contas, total


def obter_conta(usuario_id):
    """Só contas ativas: as excluídas e as agendadas não aceitam ações da administração."""
    with conectar_banco() as conexao:
        return conexao.execute(
            f"SELECT {_COLUNAS} FROM public.usuarios {_GUARDADO} WHERE id = %s AND {_ATIVA}",
            (usuario_id,),
        ).fetchone()


def revelar_email(administrador_id, usuario_id, tela):
    """Devolve o e-mail completo e registra na auditoria quem viu o e-mail de quem.

    Vale também para contas excluídas enquanto o e-mail ainda está guardado.
    Sem registro, sem e-mail: os dois acontecem na mesma transação.
    """
    with conectar_banco() as conexao:
        conta = conexao.execute(
            f"""
            SELECT COALESCE(usuarios.email, guardado.email_guardado) AS email
            FROM public.usuarios {_GUARDADO}
            WHERE usuarios.id = %s
            """,
            (usuario_id,),
        ).fetchone()
        if conta is None or not conta["email"]:
            return None
        registrar_evento(
            usuario_id=administrador_id,
            evento="dados.email_visualizado",
            resultado="sucesso",
            recurso_tipo="usuario",
            recurso_id=usuario_id,
            detalhes={"tela": tela},
            conexao=conexao,
        )
        return conta["email"]


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
            f"SELECT id FROM public.usuarios WHERE {_ATIVA} AND perfil = 'administrador' FOR NO KEY UPDATE"
        ).fetchall()
        conta = conexao.execute(
            f"""
            SELECT id, perfil, mfa_confirmado_em IS NOT NULL AS autenticador_ativo
            FROM public.usuarios
            WHERE id = %s AND {_ATIVA}
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


class ExclusaoRecusada(ValueError):
    pass


def senha_confere(usuario_id, senha):
    """Confere a senha de quem está pedindo uma ação sensível (a própria conta da sessão)."""
    with conectar_banco() as conexao:
        conta = conexao.execute(
            f"SELECT senha_hash FROM public.usuarios WHERE id = %s AND {_ATIVA}", (usuario_id,)
        ).fetchone()
    return conta is not None and check_password_hash(conta["senha_hash"], senha)


def excluir_administrador(administrador_id, usuario_id, motivo):
    """Exclui de vez a conta de outro administrador (por exemplo, quem saiu da equipe).

    Sem prazo de arrependimento e sem link: os dados pessoais são apagados na hora,
    o e-mail fica guardado por 6 meses e a auditoria registra quem excluiu e por quê.
    Devolve a identidade e o fator antigos (para a limpeza na Twilio) e o e-mail (para o aviso).
    """
    if administrador_id == usuario_id:
        raise ExclusaoRecusada("Para excluir a sua própria conta, use Minha conta → Excluir conta.")

    with conectar_banco() as conexao:
        administradores = conexao.execute(
            f"SELECT id FROM public.usuarios WHERE {_ATIVA} AND perfil = 'administrador' FOR NO KEY UPDATE"
        ).fetchall()
        if administrador_id not in {linha["id"] for linha in administradores}:
            raise ExclusaoRecusada("Só administradores ativos podem excluir contas.")

        conta = conexao.execute(
            f"""
            SELECT id, perfil, mfa_identidade, mfa_fator_sid
            FROM public.usuarios
            WHERE id = %s AND {_ATIVA}
            FOR NO KEY UPDATE
            """,
            (usuario_id,),
        ).fetchone()
        if conta is None:
            raise ContaNaoEncontrada
        if conta["perfil"] != "administrador":
            raise ExclusaoRecusada(
                "Só contas de administrador são excluídas por aqui. "
                "As outras pessoas excluem a própria conta em Minha conta."
            )

        email = conexao.execute(
            """
            INSERT INTO public.contas_excluidas (usuario_id, email_guardado, descartar_em)
            SELECT id, email, CURRENT_TIMESTAMP + %s::interval
            FROM public.usuarios
            WHERE id = %s
            ON CONFLICT (usuario_id) DO UPDATE
            SET email_guardado = EXCLUDED.email_guardado,
                descartar_em = EXCLUDED.descartar_em
            RETURNING email_guardado
            """,
            (PRAZO_EMAIL, usuario_id),
        ).fetchone()["email_guardado"]

        conexao.execute(
            """
            UPDATE public.usuarios
            SET nome = NULL,
                email = NULL,
                senha_hash = NULL,
                mfa_identidade = gen_random_uuid(),
                mfa_fator_sid = NULL,
                mfa_confirmado_em = NULL,
                exclusao_solicitada_em = NULL,
                excluida_em = CURRENT_TIMESTAMP
            WHERE id = %s
            """,
            (usuario_id,),
        )

        for tabela in ("sessoes_autenticadas", "logins_pendentes", "recuperacoes_senha", "reativacoes_conta"):
            conexao.execute(f"DELETE FROM public.{tabela} WHERE usuario_id = %s", (usuario_id,))

        registrar_evento(
            usuario_id=administrador_id,
            evento="conta.excluida",
            resultado="sucesso",
            recurso_tipo="usuario",
            recurso_id=usuario_id,
            detalhes={"origem": "administrador", "motivo": motivo},
            conexao=conexao,
        )

    return {"identidade": conta["mfa_identidade"], "fator_sid": conta["mfa_fator_sid"], "email": email}
