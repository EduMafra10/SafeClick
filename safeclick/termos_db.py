from safeclick.db import conectar_banco


class TermosDesatualizados(ValueError):
    """O formulario se refere a uma versao diferente da oferecida no cadastro."""


def buscar_termos(versao, *, conexao=None):
    if not isinstance(versao, str) or not 1 <= len(versao) <= 32:
        return None

    consulta = """
        SELECT versao, vigente_desde, conteudo_html
        FROM public.versoes_termos
        WHERE versao = %s
    """

    if conexao is not None:
        
        return conexao.execute(consulta + " FOR SHARE", (versao,)).fetchone()

    with conectar_banco() as nova_conexao:
        return nova_conexao.execute(consulta, (versao,)).fetchone()

def usuario_aceitou_termos_atuais(usuario_id):
    
    from safeclick.privacidade import VERSAO_TERMOS

    with conectar_banco() as conexao:
        registro = conexao.execute(
            """
            SELECT EXISTS (
                SELECT 1
                FROM public.aceites_termos AS aceite
                WHERE aceite.usuario_id = %s
                  AND aceite.versao_termos = versao.versao
            ) AS aceitou
            FROM public.versoes_termos AS versao
            WHERE versao.versao = %s
            """,
            (usuario_id, VERSAO_TERMOS),
        ).fetchone()

    
    if registro is None:
        raise RuntimeError(
            "A versão atual dos Termos de Uso ainda não foi publicada."
        )

    return registro["aceitou"]

def registrar_aceite_termos(usuario_id, versao, *, aceitou):
    
    from safeclick.auditoria_db import registrar_evento
    from safeclick.privacidade import VERSAO_TERMOS

  
    if aceitou is not True:
        raise ValueError("É necessário aceitar os Termos de Uso para continuar.")

    if versao != VERSAO_TERMOS:
        raise TermosDesatualizados(
            "Os termos mudaram. Leia a versão atual e aceite novamente."
        )

    with conectar_banco() as conexao:
        documento = buscar_termos(versao, conexao=conexao)
        if documento is None:
            raise RuntimeError(
                "A versão atual dos Termos de Uso ainda não foi publicada."
            )

        registro = conexao.execute(
            """
            INSERT INTO public.aceites_termos (usuario_id, versao_termos)
            VALUES (%s, %s)
            ON CONFLICT (usuario_id, versao_termos) DO NOTHING
            RETURNING id
            """,
            (usuario_id, versao),
        ).fetchone()

        if registro is None:
            # Esta conta ja aceitou a mesma versao.
            return False

        registrar_evento(
            usuario_id=usuario_id,
            evento="termo.aceito",
            resultado="sucesso",
            recurso_tipo="aceite_termos",
            recurso_id=registro["id"],
            detalhes={"versao": versao},
            conexao=conexao,
        )

    return True