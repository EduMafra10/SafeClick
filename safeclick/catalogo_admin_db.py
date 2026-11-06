from psycopg.errors import UniqueViolation
from psycopg.types.json import Jsonb

from safeclick.auditoria_db import registrar_evento
from safeclick.catalogo_validacao import (
    DadosInvalidos, html_do_texto, texto_do_html, validar, validar_slug,
)
from safeclick.db import conectar_banco


class ItemNaoEncontrado(LookupError):
    pass


class EdicaoConflitante(ValueError):
    pass


_TIPOS = {
    "conteudos": "conteudo", "paginas": "pagina", "quizzes": "quiz", "simulacoes": "simulacao",
}
_ORIGEM = {
    "quizzes": (
        "catalogo_quizzes",
        "LEFT JOIN public.quizzes AS v ON v.catalogo_id = i.id AND v.id = i.versao_publicada_id",
        "v.titulo", "NULL::text", "v.versao", "i.rascunho", "v.id AS versao_id",
    ),
    "simulacoes": (
        "simulacoes",
        "LEFT JOIN public.versoes_simulacao AS v ON v.simulacao_id = i.id AND v.id = i.versao_publicada_id",
        "v.conteudo->>'titulo'", "i.slug", "v.numero",
        "NULLIF(NULLIF(i.rascunho, '{}'::jsonb), v.conteudo)",
        "i.identificador, v.conteudo AS snapshot",
    ),
    "conteudos": (
        "conteudos", "", "i.titulo", "i.slug", "NULLIF(i.versao, 0)", "i.rascunho",
        "i.texto",
    ),
}
_ESTADO = "CASE WHEN i.removido_em IS NOT NULL THEN 'removida' ELSE i.estado END"


def _origem(secao):
    if secao not in _TIPOS:
        raise ItemNaoEncontrado()
    return _ORIGEM["conteudos" if secao == "paginas" else secao]


def _filtro_secao(tabela, secao):
    return (["i.secao = %s"], [secao]) if tabela == "conteudos" else ([], [])


def listar_itens(secao, *, estado="", busca="", pagina=1, por_pagina=20):
    tabela, join, publicado, slug, versao, rascunho, _ = _origem(secao)
    titulo = f"COALESCE(NULLIF(i.rascunho->>'titulo', ''), {publicado}, {slug}, 'Sem título')"
    condicoes, params = _filtro_secao(tabela, secao)
    if estado:
        condicoes.append(_ESTADO + " = %s")
        params.append(estado)
    else:
        condicoes.append("i.removido_em IS NULL")
    if busca:
        condicoes.append(f"(strpos(lower({titulo}), lower(%s)) > 0 OR strpos(lower(COALESCE({slug}, '')), lower(%s)) > 0)")
        params.extend([busca, busca])
    filtro = " AND ".join(condicoes)
    origem = f"FROM public.{tabela} AS i {join} WHERE {filtro}"

    with conectar_banco() as conexao:
        total = conexao.execute(f"SELECT COUNT(*) AS total {origem}", params).fetchone()["total"]
        itens = conexao.execute(
            f"""
            SELECT i.id, {titulo} AS titulo, {slug} AS slug, {_ESTADO} AS estado,
                   {versao} AS versao, ({rascunho}) IS NOT NULL AS tem_rascunho
            {origem}
            ORDER BY i.id DESC LIMIT %s OFFSET %s
            """,
            [*params, por_pagina, (pagina - 1) * por_pagina],
        ).fetchall()
    return itens, total


def _buscar(conexao, secao, item_id, *, bloquear=False):
    tabela, join, publicado, slug, versao, rascunho, extras = _origem(secao)
    condicoes, params = _filtro_secao(tabela, secao)
    filtro = " AND ".join(["i.id = %s", *condicoes])
    lock = " FOR UPDATE OF i" if bloquear else ""
    item = conexao.execute(
        f"""
        SELECT i.id, i.revisao, {_ESTADO} AS estado, {slug} AS slug,
               {publicado} AS titulo_publicado, {versao} AS versao, {rascunho} AS rascunho, {extras}
        FROM public.{tabela} AS i {join}
        WHERE {filtro}{lock}
        """,
        [item_id, *params],
    ).fetchone()
    if item is None:
        raise ItemNaoEncontrado()
    return item


def _dados_publicados(conexao, secao, item):
    if secao == "simulacoes":
        return item["snapshot"] or {}
    if secao in {"conteudos", "paginas"}:
        return {"titulo": item["titulo_publicado"], "corpo": texto_do_html(item["texto"])}
    questoes = {}
    if item["versao_id"] is not None:
        registros = conexao.execute(
            """
            SELECT q.id, q.enunciado, q.explicacao, a.texto, a.correta
            FROM public.questoes AS q
            LEFT JOIN public.alternativas AS a ON a.questao_id = q.id
            WHERE q.quiz_id = %s
            ORDER BY q.ordem, a.ordem
            """,
            (item["versao_id"],),
        ).fetchall()
        for linha in registros:
            questao = questoes.setdefault(linha["id"], {
                "enunciado": linha["enunciado"], "explicacao": linha["explicacao"], "alternativas": [],
            })
            if linha["texto"] is not None:
                questao["alternativas"].append({"texto": linha["texto"], "correta": linha["correta"]})
    return {"titulo": item["titulo_publicado"], "questoes": list(questoes.values())}


def obter_item(secao, item_id):
    with conectar_banco() as conexao:
        item = _buscar(conexao, secao, item_id)
        item["dados"] = item["rascunho"] or _dados_publicados(conexao, secao, item)
    return item


def _exigir_administrador(conexao, usuario_id):
    registro = conexao.execute(
        "SELECT id FROM public.usuarios WHERE id = %s AND perfil = 'administrador' FOR SHARE",
        (usuario_id,),
    ).fetchone()
    if not registro:
        raise PermissionError("Acesso administrativo necessário.")


def _auditar(conexao, usuario_id, secao, item_id, evento, versao=None):
    registrar_evento(
        usuario_id=usuario_id, evento="catalogo." + evento, resultado="sucesso",
        recurso_tipo=_TIPOS[secao], recurso_id=item_id,
        detalhes={"secao": secao, **({"versao": versao} if versao else {})},
        conexao=conexao,
    )


def salvar_rascunho(usuario_id, secao, dados, *, slug=None, item_id=None, revisao=None):
    tabela = _origem(secao)[0]
    dados = validar(secao, dados)
    if item_id is None and secao != "quizzes":
        slug = validar_slug(secao, slug)

    try:
        with conectar_banco() as conexao:
            _exigir_administrador(conexao, usuario_id)
            if item_id is None:
                if secao == "quizzes":
                    registro = conexao.execute(
                        "INSERT INTO public.catalogo_quizzes (rascunho) VALUES (%s) RETURNING id",
                        (Jsonb(dados),),
                    )
                elif secao == "simulacoes":
                    registro = conexao.execute(
                        """
                        INSERT INTO public.simulacoes (identificador, slug, rascunho, criado_por)
                        VALUES (%s, %s, %s, %s) RETURNING id
                        """,
                        (slug.replace("-", "_"), slug, Jsonb(dados), usuario_id),
                    )
                else:
                    registro = conexao.execute(
                        """
                        INSERT INTO public.conteudos (secao, slug, titulo, texto, estado, rascunho, versao)
                        VALUES (%s, %s, %s, '', 'rascunho', %s, 0) RETURNING id
                        """,
                        (secao, slug, dados["titulo"], Jsonb(dados)),
                    )
                item_id = registro.fetchone()["id"]
                _auditar(conexao, usuario_id, secao, item_id, "criado")
            else:
                item = _buscar(conexao, secao, item_id, bloquear=True)
                if item["estado"] == "removida" or item["revisao"] != revisao:
                    raise EdicaoConflitante("O item mudou. Reabra o editor antes de salvar.")
                conexao.execute(
                    f"UPDATE public.{tabela} SET rascunho = %s, revisao = revisao + 1 WHERE id = %s",
                    (Jsonb(dados), item_id),
                )
                _auditar(conexao, usuario_id, secao, item_id, "editado")
    except UniqueViolation:
        raise EdicaoConflitante("Esse endereço já existe. Escolha outro para o novo item.") from None
    return item_id


def _publicar(conexao, usuario_id, secao, item):
    dados = validar(secao, item["rascunho"], publicar=True)
    versao = (item["versao"] or 0) + 1
    if secao == "quizzes":
        versao_id = conexao.execute(
            "INSERT INTO public.quizzes (catalogo_id, versao, titulo) VALUES (%s,%s,%s) RETURNING id",
            (item["id"], versao, dados["titulo"]),
        ).fetchone()["id"]
        for ordem, questao in enumerate(dados["questoes"], 1):
            questao_id = conexao.execute(
                """
                INSERT INTO public.questoes (quiz_id, ordem, enunciado, explicacao)
                VALUES (%s,%s,%s,%s) RETURNING id
                """,
                (versao_id, ordem, questao["enunciado"], questao["explicacao"]),
            ).fetchone()["id"]
            with conexao.cursor() as cursor:
                cursor.executemany(
                    "INSERT INTO public.alternativas (questao_id, ordem, texto, correta) VALUES (%s,%s,%s,%s)",
                    [(questao_id, numero, opcao["texto"], opcao["correta"])
                     for numero, opcao in enumerate(questao["alternativas"], 1)],
                )
        conexao.execute(
            "UPDATE public.catalogo_quizzes SET versao_publicada_id = %s, rascunho = NULL WHERE id = %s",
            (versao_id, item["id"]),
        )
    elif secao == "simulacoes":
        anterior = item["snapshot"] or {}
        if "ordem_catalogo" in anterior:
            dados["ordem_catalogo"] = anterior["ordem_catalogo"]
        dados["slug"] = item["slug"]
        versao_id = conexao.execute(
            """
            INSERT INTO public.versoes_simulacao (simulacao_id, numero, conteudo, publicado_por)
            VALUES (%s,%s,%s,%s) RETURNING id
            """,
            (item["id"], versao, Jsonb(dados), usuario_id),
        ).fetchone()["id"]
        conexao.execute(
            """
            UPDATE public.simulacoes
            SET versao_publicada_id = %s, rascunho = '{}'::jsonb, atualizado_em = CURRENT_TIMESTAMP
            WHERE id = %s
            """,
            (versao_id, item["id"]),
        )
    else:
        html = item["texto"] if dados["corpo"] == texto_do_html(item["texto"]) else html_do_texto(dados["corpo"])
        conexao.execute(
            "UPDATE public.conteudos SET titulo = %s, texto = %s, versao = %s, rascunho = NULL WHERE id = %s",
            (dados["titulo"], html, versao, item["id"]),
        )
    return versao


def alterar_publicacao(usuario_id, secao, item_id, revisao, acao):
    tabela = _origem(secao)[0]
    with conectar_banco() as conexao:
        _exigir_administrador(conexao, usuario_id)
        item = _buscar(conexao, secao, item_id, bloquear=True)
        if item["revisao"] != revisao:
            raise EdicaoConflitante("O item mudou. Confira o estado antes de confirmar novamente.")
        estado, versao = item["estado"], item["versao"]
        if acao == "publicar" and estado != "removida" and (item["rascunho"] or (estado == "arquivada" and versao)):
            if item["rascunho"]:
                versao = _publicar(conexao, usuario_id, secao, item)
            novo_estado, removido, evento = "publicada", False, "publicado"
        elif acao == "despublicar" and estado == "publicada":
            novo_estado, removido, evento = "arquivada", False, "despublicado"
        elif acao == "restaurar" and estado == "removida":
            novo_estado, removido, evento = "arquivada", False, "restaurado"
        elif acao == "remover" and estado != "removida":
            if not versao:
                # Cenários anteriores ao catálogo também podem ter tentativas pelo identificador.
                tem_tentativas = secao == "simulacoes" and conexao.execute(
                    "SELECT 1 FROM public.tentativas_simulacao WHERE simulacao = %s LIMIT 1",
                    (item["identificador"],),
                ).fetchone()
                if not tem_tentativas:
                    conexao.execute(f"DELETE FROM public.{tabela} WHERE id = %s", (item_id,))
                    _auditar(conexao, usuario_id, secao, item_id, "excluido")
                    return
            novo_estado, removido, evento = "arquivada", True, "removido"
        else:
            raise EdicaoConflitante("Esta ação não está disponível no estado atual.")
        conexao.execute(
            f"""
            UPDATE public.{tabela}
            SET estado = %s, revisao = revisao + 1,
                removido_em = CASE WHEN %s THEN CURRENT_TIMESTAMP ELSE NULL END
            WHERE id = %s
            """,
            (novo_estado, removido, item_id),
        )
        _auditar(conexao, usuario_id, secao, item_id, evento, versao)
