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