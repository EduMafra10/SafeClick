from copy import deepcopy

from psycopg.types.json import Jsonb

from safeclick.cenarios_simulacao import CENARIOS
from safeclick.db import conectar_banco


def importar_cenarios_iniciais():
    """Importa os quatro cenários existentes sem sobrescrever cadastros."""
    tipos = {
        "conta_bloqueada": "email",
        "entrega_sms": "sms",
        "falso_conhecido": "conversa",
        "loja_falsa": "loja",
    }
    criadas = 0
    existentes = 0

    
    with conectar_banco() as conexao:
        for ordem, (identificador, tipo) in enumerate(tipos.items(), start=1):
            conteudo = deepcopy(CENARIOS[identificador])
            conteudo["tipo"] = tipo
            conteudo["ordem_catalogo"] = ordem

        
            conteudo["ordem_opcoes"] = list(conteudo["opcoes"])

            simulacao = conexao.execute(
                """
                INSERT INTO public.simulacoes
                    (identificador, slug, rascunho)
                VALUES (%s, %s, %s)
                ON CONFLICT (identificador) DO NOTHING
                RETURNING id
                """,
                (identificador, conteudo["slug"], Jsonb(conteudo)),
            ).fetchone()

            if simulacao is None:
                existentes += 1
                continue

            versao = conexao.execute(
                """
                INSERT INTO public.versoes_simulacao
                    (simulacao_id, numero, conteudo)
                VALUES (%s, 1, %s)
                RETURNING id
                """,
                (simulacao["id"], Jsonb(conteudo)),
            ).fetchone()

            conexao.execute(
                """
                UPDATE public.simulacoes
                SET estado = 'publicada',
                    versao_publicada_id = %s,
                    atualizado_em = CURRENT_TIMESTAMP
                WHERE id = %s
                """,
                (versao["id"], simulacao["id"]),
            )
            criadas += 1

    return {"criadas": criadas, "existentes": existentes}

_CONSULTA_PUBLICADAS = """
    SELECT
        s.id AS simulacao_id,
        s.identificador,
        s.slug,
        v.id AS versao_id,
        v.numero AS versao,
        v.conteudo
    FROM public.simulacoes AS s
    JOIN public.versoes_simulacao AS v
        ON v.simulacao_id = s.id
       AND v.id = s.versao_publicada_id
    WHERE s.estado = 'publicada'
"""


def _preparar_cenario_publicado(registro):
    """Adapta o documento do banco ao formato utilizado pelas páginas."""
    conteudo = registro["conteudo"]
    if not isinstance(conteudo, dict):
        raise RuntimeError("O conteúdo da simulação está inválido.")

    opcoes = conteudo.get("opcoes")
    ordem = conteudo.get("ordem_opcoes")

    if (
        not isinstance(opcoes, dict)
        or not opcoes
        or not isinstance(ordem, list)
        or not all(isinstance(chave, str) for chave in ordem)
        or len(ordem) != len(opcoes)
        or set(ordem) != set(opcoes)
    ):
        raise RuntimeError("A ordem das alternativas está inválida.")

    cenario = deepcopy(conteudo)
    cenario["opcoes"] = {
        chave: cenario["opcoes"][chave] for chave in ordem
    }
    cenario["simulacao_id"] = registro["simulacao_id"]
    cenario["identificador"] = registro["identificador"]
    cenario["slug"] = registro["slug"]
    cenario["versao_id"] = registro["versao_id"]
    cenario["versao"] = registro["versao"]
    return cenario


def listar_simulacoes_publicadas():
    
    with conectar_banco() as conexao:
        registros = conexao.execute(
            _CONSULTA_PUBLICADAS
            + " ORDER BY (v.conteudo->>'ordem_catalogo')::integer NULLS LAST, s.id"
        ).fetchall()

    return {
        registro["identificador"]: _preparar_cenario_publicado(registro)
        for registro in registros
    }


def buscar_simulacao_publicada(slug):
    
    if not isinstance(slug, str) or not 1 <= len(slug) <= 80:
        return None

    with conectar_banco() as conexao:
        registro = conexao.execute(
            _CONSULTA_PUBLICADAS + " AND s.slug = %s",
            (slug,),
        ).fetchone()

    if registro is None:
        return None

    return _preparar_cenario_publicado(registro)



class SimulacaoAlterada(ValueError):
    """O cenário foi atualizado ou retirado de publicação durante a resposta."""


def salvar_tentativa_publicada(usuario_id, slug, versao_id, opcao):
    
    from safeclick.auditoria_db import registrar_evento

    with conectar_banco() as conexao:
        # Mantém a publicação estável até concluir a gravação da resposta.
        registro = conexao.execute(
            _CONSULTA_PUBLICADAS
            + " AND s.slug = %s FOR SHARE OF s, v",
            (slug,),
        ).fetchone()

        if registro is None or registro["versao_id"] != versao_id:
            raise SimulacaoAlterada()

        cenario = _preparar_cenario_publicado(registro)
        if not isinstance(opcao, str) or opcao not in cenario["opcoes"]:
            raise ValueError("Selecione uma alternativa válida.")

        tentativa = conexao.execute(
            """
            INSERT INTO public.tentativas_simulacao
                (usuario_id, simulacao, opcao, versao_simulacao_id)
            VALUES (%s, %s, %s, %s)
            RETURNING id
            """,
            (usuario_id, cenario["identificador"], opcao, cenario["versao_id"]),
        ).fetchone()

        registrar_evento(
            usuario_id=usuario_id,
            evento="simulacao.concluida",
            resultado="sucesso",
            recurso_tipo="tentativa_simulacao",
            recurso_id=tentativa["id"],
            detalhes={
                "simulacao": cenario["identificador"],
                "opcao": opcao,
                "versao_id": cenario["versao_id"],
            },
            conexao=conexao,
        )

    return tentativa["id"]


def buscar_resultado_simulacao(usuario_id, slug, tentativa_id):
    
    with conectar_banco() as conexao:
        registro = conexao.execute(
            """
            SELECT
                s.id AS simulacao_id,
                s.identificador,
                s.slug,
                s.estado,
                v.id AS versao_id,
                v.numero AS versao,
                v.conteudo,
                t.opcao
            FROM public.tentativas_simulacao AS t
            JOIN public.versoes_simulacao AS v
                ON v.id = t.versao_simulacao_id
            JOIN public.simulacoes AS s
                ON s.id = v.simulacao_id
               AND s.identificador = t.simulacao
            WHERE t.id = %s
              AND t.usuario_id = %s
              AND s.slug = %s
            """,
            (tentativa_id, usuario_id, slug),
        ).fetchone()

    if registro is None:
        return None

    cenario = _preparar_cenario_publicado(registro)
    resultado = cenario["opcoes"].get(registro["opcao"])
    if not isinstance(resultado, dict):
        raise RuntimeError("A resposta registrada está inválida.")

    return {
        "cenario": cenario,
        "resultado": resultado,
        "pode_repetir": registro["estado"] == "publicada",
    }

def listar_simulacoes_administrativas(*, estado="", pagina=1, por_pagina=20):
    
    if not isinstance(estado, str) or estado not in {
        "", "rascunho", "publicada", "arquivada"
    }:
        raise ValueError("Estado inválido.")

    if type(pagina) is not int or not 1 <= pagina <= 1000000:
        raise ValueError("Página inválida.")

    if type(por_pagina) is not int or not 1 <= por_pagina <= 100:
        raise ValueError("Quantidade por página inválida.")

    filtro = " WHERE s.estado = %s" if estado else ""
    parametros = [estado] if estado else []

    with conectar_banco() as conexao:
        total = conexao.execute(
            "SELECT COUNT(*) AS total FROM public.simulacoes AS s" + filtro,
            parametros,
        ).fetchone()["total"]

        registros = conexao.execute(
            """
            SELECT
                s.id,
                s.identificador,
                s.slug,
                s.estado,
                COALESCE(
                    NULLIF(v.conteudo->>'titulo', ''),
                    NULLIF(s.rascunho->>'titulo', ''),
                    s.identificador
                ) AS titulo,
                COALESCE(
                    NULLIF(v.conteudo->>'tipo', ''),
                    NULLIF(s.rascunho->>'tipo', ''),
                    ''
                ) AS tipo,
                v.numero AS versao
            FROM public.simulacoes AS s
            LEFT JOIN public.versoes_simulacao AS v
                ON v.simulacao_id = s.id
               AND v.id = s.versao_publicada_id
            """ + filtro + " ORDER BY s.id LIMIT %s OFFSET %s",
            [*parametros, por_pagina, (pagina - 1) * por_pagina],
        ).fetchall()

    return registros, total

class SimulacaoDuplicada(ValueError):
    """Já existe um cenário com esse endereço ou identificador."""


def criar_rascunho_simulacao(usuario_id, *, titulo, slug, tipo, resumo):
    """Cria somente um rascunho e registra a ação na mesma transação."""
    import re

    from safeclick.auditoria_db import registrar_evento

    canais = {
        "email": "E-mail fictício", "sms": "SMS fictício",
        "conversa": "Conversa fictícia", "loja": "Loja virtual fictícia",
    }
    if any(not isinstance(valor, str) or "\x00" in valor for valor in (titulo, slug, tipo, resumo)):
        raise ValueError("Dados do cenário inválidos.")
    titulo, slug, resumo = titulo.strip(), slug.strip(), resumo.strip()
    if (
        not 1 <= len(titulo) <= 120
        or not 1 <= len(resumo) <= 300
        or not 1 <= len(slug) <= 80
        or re.fullmatch(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*", slug) is None
        or tipo not in canais
    ):
        raise ValueError("Dados do cenário inválidos.")

    identificador = slug.replace("-", "_")
    conteudo = {
        "titulo": titulo, "slug": slug, "tipo": tipo,
        "resumo": resumo, "canal": canais[tipo],
    }

    with conectar_banco() as conexao:
        # Confere a permissão atual e impede sua alteração durante a gravação.
        administrador = conexao.execute(
            "SELECT id FROM public.usuarios WHERE id = %s AND perfil = 'administrador' FOR SHARE",
            (usuario_id,),
        ).fetchone()
        if administrador is None:
            raise PermissionError("Acesso administrativo necessário.")

        registro = conexao.execute(
            """
            INSERT INTO public.simulacoes
                (identificador, slug, estado, rascunho, criado_por)
            VALUES (%s, %s, 'rascunho', %s, %s)
            ON CONFLICT DO NOTHING
            RETURNING id
            """,
            (identificador, slug, Jsonb(conteudo), usuario_id),
        ).fetchone()
        if registro is None:
            raise SimulacaoDuplicada("Já existe um cenário com esse endereço.")

        registrar_evento(
            usuario_id=usuario_id,
            evento="simulacao.criada",
            resultado="sucesso",
            recurso_tipo="simulacao",
            recurso_id=registro["id"],
            detalhes={"identificador": identificador, "estado": "rascunho"},
            conexao=conexao,
        )

    return registro["id"]
