import click
import psycopg
from flask import current_app
from flask.cli import with_appcontext
from psycopg.rows import dict_row

#serve para obter a conexao configurada na nossa aplicaçao, sem escrever credenciais no codigo
def conectar_banco():
    database_url = current_app.config.get("DATABASE_URL")

    #interrompe a operaçao se o endereço do banco nao estiver configurado corretamente
    if not database_url:
        raise RuntimeError(
            "DATABASE_URL nao está configurado, verifique o arquivo .env"
        )

    #abre a conexao com o Postgre e permite acessar os resultados pelo nome da coluna 
    return psycopg.connect(
        database_url,
        connect_timeout=10,
        row_factory=dict_row,
    )

#registra a tentativa sem vinculo com usuario nessa etapa
def salvar_tentativa_simulacao(simulacao, opcao):
    #gerencia a transaçao e fecha a conexao ao sair do bloco
    with conectar_banco() as conexao:
        #envia os valores como parametros separados do comando SQL
        conexao.execute(
            """
            INSERT INTO public.tentativas_simulacao (simulacao, opcao)
            VALUES (%s, %s)
            """,
            (simulacao, opcao),
        )

#disponibiliza a verifiçao pelo terminal com acesso a config do flask
@click.command("verificar-banco")
@with_appcontext
def verificar_banco():
    try:

        #consulta o nome do banco e fecha a conexao ao sair do bloco
        with conectar_banco() as conexao:
            registro = conexao.execute(
                "SELECT current_database() AS banco"
            ).fetchone()

    #apresenta uma mensagem quando faltar alguma configuraçao
    except RuntimeError as erro:
        raise click.ClickException(str(erro)) from None

    #trata erros do Postgre sem exibir mensagem bruta da conexao
    except psycopg.Error:
        raise click.ClickException(
            "Nao foi possivel acessar o PostgreSQL. "
            "Confira se a configuração da conexão esta correta e a disponibilidade do banco."
        ) from None

    click.echo(f"Conexão realizada com sucesso. Banco: {registro['banco']}")