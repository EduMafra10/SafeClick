
from datetime import timedelta

from safeclick.db import conectar_banco

PERIODOS = (7, 30, 90)
TIPOS_ATIVIDADE = ("conteudo", "quiz", "simulacao", "desafio")

_DESDE = "(%(inicio)s::date)::timestamp AT TIME ZONE 'America/Sao_Paulo'"
_SO_USUARIOS = "JOIN public.usuarios AS u ON u.id = {tabela}.usuario_id AND u.perfil = 'usuario'"

_ATIVIDADES = f"""
    SELECT 'conteudo' AS tipo, c.usuario_id, c.concluido_em AS momento
    FROM public.conclusoes_conteudo AS c {_SO_USUARIOS.format(tabela='c')}
    WHERE c.concluido_em >= {_DESDE}
    UNION ALL
    SELECT 'quiz', q.usuario_id, q.criada_em
    FROM public.tentativas_quiz AS q {_SO_USUARIOS.format(tabela='q')}
    WHERE q.criada_em >= {_DESDE}
    UNION ALL
    SELECT 'simulacao', s.usuario_id, s.criada_em
    FROM public.tentativas_simulacao AS s {_SO_USUARIOS.format(tabela='s')}
    WHERE s.criada_em >= {_DESDE}
    UNION ALL
    SELECT 'desafio', d.usuario_id, d.concluido_em
    FROM public.desafios_senha AS d {_SO_USUARIOS.format(tabela='d')}
    WHERE d.concluido_em >= {_DESDE}
"""

_CONTAS = f"""
    SELECT
        count(*) AS total,
        count(*) FILTER (WHERE criado_em >= {_DESDE}) AS novas,
        count(*) FILTER (WHERE mfa_confirmado_em IS NOT NULL) AS autenticador_ativo,
        count(*) FILTER (WHERE mfa_fator_sid IS NOT NULL AND mfa_confirmado_em IS NULL) AS autenticador_pendente
    FROM public.usuarios
    WHERE perfil = 'usuario'
"""

_ATIVOS = f"SELECT count(DISTINCT usuario_id) AS ativos FROM ({_ATIVIDADES}) AS atividades"

_POR_DIA = f"""
    SELECT (momento AT TIME ZONE 'America/Sao_Paulo')::date AS dia, tipo, count(*) AS total
    FROM ({_ATIVIDADES}) AS atividades
    GROUP BY dia, tipo
"""

# primeira escolha de cada usuário em cada cenário, dentro do período
_SIMULACOES = f"""
    WITH primeiras AS (
        SELECT DISTINCT ON (t.usuario_id, v.simulacao_id)
            v.simulacao_id,
            v.numero,
            v.conteudo->>'titulo' AS titulo,
            (v.conteudo->'opcoes'->t.opcao->>'segura')::boolean AS segura
        FROM public.tentativas_simulacao AS t
        {_SO_USUARIOS.format(tabela='t')}
        JOIN public.versoes_simulacao AS v ON v.id = t.versao_simulacao_id
        WHERE t.criada_em >= {_DESDE}
        ORDER BY t.usuario_id, v.simulacao_id, t.criada_em, t.id
    )
    SELECT
        (array_agg(titulo ORDER BY numero DESC))[1] AS titulo,
        count(*) AS pessoas,
        count(*) FILTER (WHERE segura) AS seguras
    FROM primeiras
    GROUP BY simulacao_id
    ORDER BY count(*) FILTER (WHERE segura)::numeric / count(*), titulo
"""

_QUIZZES = f"""
    SELECT
        (array_agg(quiz.titulo ORDER BY quiz.versao DESC))[1] AS titulo,
        count(*) AS tentativas,
        sum(t.pontuacao) AS acertos,
        sum(t.total_questoes) AS questoes
    FROM public.tentativas_quiz AS t
    {_SO_USUARIOS.format(tabela='t')}
    JOIN public.quizzes AS quiz ON quiz.id = t.quiz_id
    WHERE t.criada_em >= {_DESDE}
    GROUP BY quiz.catalogo_id
    ORDER BY sum(t.pontuacao)::numeric / sum(t.total_questoes), titulo
    LIMIT 5
"""

_CATALOGO = """
    SELECT secao,
        count(*) FILTER (WHERE estado = 'publicada') AS publicados,
        count(*) FILTER (WHERE estado = 'rascunho') AS rascunhos
    FROM public.conteudos
    GROUP BY secao
    UNION ALL
    SELECT 'quizzes',
        count(*) FILTER (WHERE estado = 'publicada'),
        count(*) FILTER (WHERE estado = 'rascunho')
    FROM public.catalogo_quizzes
    UNION ALL
    SELECT 'simulacoes',
        count(*) FILTER (WHERE estado = 'publicada'),
        count(*) FILTER (WHERE estado = 'rascunho')
    FROM public.simulacoes
"""

_SEGURANCA = """
    SELECT evento, count(*) AS total
    FROM public.logs_auditoria
    WHERE criado_em >= now() - interval '24 hours'
      AND evento IN ('login.falha', 'acesso.negado', 'mfa.reconfiguracao_administrativa')
    GROUP BY evento
"""

# só eventos de acesso e de conta; o restante fica na auditoria completa
_ULTIMOS_EVENTOS = """
    SELECT criado_em, evento, resultado
    FROM public.logs_auditoria
    WHERE criado_em >= now() - interval '24 hours'
      AND evento IN (
        'login.sucesso', 'login.falha', 'logout.realizado', 'acesso.negado',
        'usuario.senha_redefinida', 'usuario.perfil_alterado', 'mfa.reconfiguracao_administrativa'
      )
    ORDER BY criado_em DESC, id DESC
    LIMIT 6
"""


def _percentual(parte, total):
    if not total:
        return None
    return round(100 * parte / total)


def _serie_por_dia(linhas, inicio, hoje):
    contagem = {(linha["dia"], linha["tipo"]): linha["total"] for linha in linhas}
    dias = [inicio + timedelta(days=n) for n in range((hoje - inicio).days + 1)]
    return {
        "dias": [dia.strftime("%d/%m") for dia in dias],
        "series": {
            tipo: [contagem.get((dia, tipo), 0) for dia in dias]
            for tipo in TIPOS_ATIVIDADE
        },
    }


def buscar_visao_geral(dias, hoje):
    if dias not in PERIODOS:
        raise ValueError("Período inválido.")

    inicio = hoje - timedelta(days=dias - 1)
    parametros = {"inicio": inicio.isoformat()}

    with conectar_banco() as conexao:
        contas = conexao.execute(_CONTAS, parametros).fetchone()
        ativos = conexao.execute(_ATIVOS, parametros).fetchone()["ativos"]
        por_dia = conexao.execute(_POR_DIA, parametros).fetchall()
        simulacoes = conexao.execute(_SIMULACOES, parametros).fetchall()
        quizzes = conexao.execute(_QUIZZES, parametros).fetchall()
        catalogo = conexao.execute(_CATALOGO).fetchall()
        seguranca = conexao.execute(_SEGURANCA).fetchall()
        ultimos = conexao.execute(_ULTIMOS_EVENTOS).fetchall()

    serie = _serie_por_dia(por_dia, inicio, hoje)
    totais_por_tipo = {tipo: sum(valores) for tipo, valores in serie["series"].items()}
    eventos = {linha["evento"]: linha["total"] for linha in seguranca}

    return {
        "dias": dias,
        "inicio": inicio,
        "contas": {
            "total": contas["total"],
            "novas": contas["novas"],
            "ativas": ativos,
            "percentual_ativas": _percentual(ativos, contas["total"]),
            "autenticador_ativo": contas["autenticador_ativo"],
            "percentual_autenticador": _percentual(contas["autenticador_ativo"], contas["total"]),
            "autenticador_pendente": contas["autenticador_pendente"],
        },
        "atividades": {
            "total": sum(totais_por_tipo.values()),
            "por_tipo": totais_por_tipo,
            "por_dia": serie,
        },
        "simulacoes": [
            {
                "titulo": linha["titulo"],
                "pessoas": linha["pessoas"],
                "percentual_seguras": _percentual(linha["seguras"], linha["pessoas"]),
            }
            for linha in simulacoes
        ],
        "quizzes": [
            {
                "titulo": linha["titulo"],
                "tentativas": linha["tentativas"],
                "percentual_acertos": _percentual(linha["acertos"], linha["questoes"]),
            }
            for linha in quizzes
        ],
        "catalogo": {
            linha["secao"]: {"publicados": linha["publicados"], "rascunhos": linha["rascunhos"]}
            for linha in catalogo
        },
        "seguranca": {
            "falhas_login": eventos.get("login.falha", 0),
            "acessos_negados": eventos.get("acesso.negado", 0),
            "autenticadores_redefinidos": eventos.get("mfa.reconfiguracao_administrativa", 0),
        },
        "ultimos_eventos": ultimos,
    }
