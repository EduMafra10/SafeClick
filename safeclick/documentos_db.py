from safeclick.db import conectar_banco

# tabela de ligacao e coluna de versao de cada documento
_LIGACOES = {
    "politica": ("politica_referencias", "versao_politica"),
    "termos": ("termos_referencias", "versao_termos"),
}


def _versao_valida(versao):
    return isinstance(versao, str) and 1 <= len(versao) <= 32


def buscar_politica(versao):
    """Versao arquivada da politica de privacidade (mesmo formato de buscar_termos)."""
    if not _versao_valida(versao):
        return None

    with conectar_banco() as conexao:
        return conexao.execute(
            """
            SELECT versao, vigente_desde, conteudo_html
            FROM public.versoes_politica
            WHERE versao = %s
            """,
            (versao,),
        ).fetchone()


def buscar_referencias(documento, versao):
    """Leis e artigos citados por uma versao da politica ou dos termos."""
    if documento not in _LIGACOES or not _versao_valida(versao):
        return []

    tabela, coluna = _LIGACOES[documento]

    with conectar_banco() as conexao:
        # nomes de tabela e coluna vem do dicionario acima, nunca da requisicao
        return conexao.execute(
            f"""
            SELECT referencia.norma, referencia.dispositivo,
                   referencia.assunto, referencia.url
            FROM public.{tabela} AS ligacao
            JOIN public.referencias_legais AS referencia
              ON referencia.id = ligacao.referencia_id
            WHERE ligacao.{coluna} = %s
            ORDER BY ligacao.ordem
            """,
            (versao,),
        ).fetchall()
