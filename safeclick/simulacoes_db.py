from copy import deepcopy

import click
from flask.cli import with_appcontext
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


@click.command("importar-cenarios-iniciais")
@with_appcontext
def importar_cenarios_cli():
    resultado = importar_cenarios_iniciais()
    click.echo(f"{resultado['criadas']} cenários criados; {resultado['existentes']} já existentes.")


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
