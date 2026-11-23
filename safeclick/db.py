import click
import psycopg
from flask import current_app
from flask.cli import with_appcontext
from psycopg.conninfo import conninfo_to_dict
from psycopg.rows import dict_row

SEM_TLS = {None, "disable", "allow", "prefer"}


def conectar_banco():
    database_url = current_app.config.get("DATABASE_URL")

    if not database_url:
        raise RuntimeError(
            "DATABASE_URL nao está configurado, verifique o arquivo .env"
        )

    opcoes = {}
    if current_app.config.get("APP_ENV") == "producao" and conninfo_to_dict(database_url).get("sslmode") in SEM_TLS:
        opcoes["sslmode"] = "require"

    return psycopg.connect(
        database_url,
        connect_timeout=10,
        row_factory=dict_row,
        **opcoes,
    )


def salvar_tentativa_simulacao(usuario_id, simulacao, opcao):
    from safeclick.auditoria_db import registrar_evento

    with conectar_banco() as conexao:
        tentativa = conexao.execute(
            """
            INSERT INTO public.tentativas_simulacao (usuario_id, simulacao, opcao)
            VALUES (%s, %s, %s)
            RETURNING id
            """,
            (usuario_id, simulacao, opcao),
        ).fetchone()

        registrar_evento(
            usuario_id=usuario_id,
            evento="simulacao.concluida",
            resultado="sucesso",
            recurso_tipo="tentativa_simulacao",
            recurso_id=tentativa["id"],
            detalhes={"simulacao": simulacao, "opcao": opcao},
            conexao=conexao,
        )

    return tentativa["id"]


@click.command("verificar-banco")
@with_appcontext
def verificar_banco():
    try:

        with conectar_banco() as conexao:
            registro = conexao.execute(
                "SELECT current_database() AS banco"
            ).fetchone()

    except RuntimeError as erro:
        raise click.ClickException(str(erro)) from None

    except psycopg.Error:
        raise click.ClickException(
            "Nao foi possivel acessar o PostgreSQL. "
            "Confira se a configuração da conexão esta correta e a disponibilidade do banco."
        ) from None

    click.echo(f"Conexão realizada com sucesso. Banco: {registro['banco']}")
