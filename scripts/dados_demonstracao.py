
import random
import secrets
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import click
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from werkzeug.security import generate_password_hash  

from safeclick import create_app 
from safeclick.db import conectar_banco 
from safeclick.privacidade import VERSAO_TERMOS  

DOMINIO = "@demonstracao.example"
NOMES = [
    "Mariana Alves", "Rafael Souza", "Beatriz Lima", "Lucas Ferreira", "Camila Rocha",
    "Gustavo Martins", "Larissa Gomes", "Pedro Henrique Dias", "Juliana Ribeiro", "Thiago Carvalho",
]
ICONES = ["raposa", "coruja", "panda", None, "gato", "robo", None, "pinguim", "urso", "astronauta"]


def _email(nome):
    return nome.lower().replace(" ", ".") + DOMINIO


def _momento(agora, sorteio, dias):
    # mais atividade nos dias recentes, como numa turma que começou a usar a plataforma
    atras = int(dias * sorteio.random() ** 1.6)
    return agora - timedelta(days=atras, hours=sorteio.randint(0, 12), minutes=sorteio.randint(0, 59))


def _catalogo(conexao):
    conteudos = [linha["id"] for linha in conexao.execute(
        "SELECT id FROM public.conteudos WHERE secao = 'conteudos' AND estado = 'publicada' AND removido_em IS NULL ORDER BY id"
    ).fetchall()]
    quizzes = []
    for quiz in conexao.execute(
        "SELECT c.id AS catalogo_id, c.versao_publicada_id AS quiz_id FROM public.catalogo_quizzes AS c "
        "WHERE c.estado = 'publicada' AND c.removido_em IS NULL AND c.versao_publicada_id IS NOT NULL ORDER BY c.id"
    ).fetchall():
        questoes = {}
        for linha in conexao.execute(
            "SELECT q.id AS questao_id, a.id AS alternativa_id, a.correta FROM public.questoes AS q "
            "JOIN public.alternativas AS a ON a.questao_id = q.id WHERE q.quiz_id = %s ORDER BY q.ordem, a.ordem",
            (quiz["quiz_id"],),
        ).fetchall():
            questoes.setdefault(linha["questao_id"], []).append(linha)
        if questoes:
            quizzes.append({**quiz, "questoes": questoes})
    simulacoes = []
    for linha in conexao.execute(
        "SELECT s.identificador, v.id AS versao_id, v.conteudo FROM public.simulacoes AS s "
        "JOIN public.versoes_simulacao AS v ON v.id = s.versao_publicada_id WHERE s.estado = 'publicada' ORDER BY s.id"
    ).fetchall():
        opcoes = linha["conteudo"].get("opcoes") or {}
        seguras = [chave for chave, opcao in opcoes.items() if opcao.get("segura")]
        risco = [chave for chave, opcao in opcoes.items() if not opcao.get("segura")]
        if seguras and risco:
            simulacoes.append({**linha, "seguras": seguras, "risco": risco})
    return conteudos, quizzes, simulacoes


def criar(conexao, agora):
    existentes = conexao.execute(
        "SELECT count(*) AS total FROM public.usuarios WHERE email LIKE %s", ("%" + DOMINIO,)
    ).fetchone()["total"]
    if existentes:
        raise click.ClickException("Os dados de demonstração já existem. Use --apagar antes de criar de novo.")

    conteudos, quizzes, simulacoes = _catalogo(conexao)
    if not (conteudos and quizzes and simulacoes):
        raise click.ClickException("Publique ao menos um conteúdo, um quiz e uma simulação antes.")

    sorteio = random.Random(2026)
    # cada questão tem uma dificuldade fixa, para algumas aparecerem como as que mais erram
    dificuldade = {q: sorteio.uniform(0.35, 0.92) for quiz in quizzes for q in quiz["questoes"]}
    cuidado = {s["identificador"]: sorteio.uniform(0.35, 0.8) for s in simulacoes}
    senha = generate_password_hash(secrets.token_urlsafe(32), method="scrypt")
    totais = {"contas": 0, "atividades": 0}

    for indice, nome in enumerate(NOMES):
        criado_em = agora - timedelta(days=sorteio.randint(5, 45), hours=sorteio.randint(0, 23))
        confirmado = indice not in (3, 8)
        usuario_id = conexao.execute(
            """
            INSERT INTO public.usuarios (nome, email, senha_hash, perfil, criado_em, mfa_identidade,
                                         mfa_fator_sid, mfa_confirmado_em, icone)
            VALUES (%s, %s, %s, 'usuario', %s, %s, %s, %s, %s) RETURNING id
            """,
            (nome, _email(nome), senha, criado_em, uuid.uuid4(),
             "YFdemo" + secrets.token_hex(14) if confirmado else None,
             criado_em + timedelta(minutes=3) if confirmado else None, ICONES[indice]),
        ).fetchone()["id"]
        conexao.execute(
            "INSERT INTO public.aceites_termos (usuario_id, versao_termos, aceito_em) VALUES (%s, %s, %s)",
            (usuario_id, VERSAO_TERMOS, criado_em),
        )
        totais["contas"] += 1
        if not confirmado:
            continue

        dias = max(1, (agora - criado_em).days)
        lidos = sorteio.sample(conteudos, sorteio.randint(2, len(conteudos)))
        for conteudo_id in lidos:
            conexao.execute(
                "INSERT INTO public.conclusoes_conteudo (usuario_id, conteudo_id, concluido_em) VALUES (%s, %s, %s)",
                (usuario_id, conteudo_id, _momento(agora, sorteio, dias)),
            )
            if sorteio.random() < 0.6:
                conexao.execute(
                    "INSERT INTO public.avaliacoes_conteudo (usuario_id, conteudo_id, nota) VALUES (%s, %s, %s)",
                    (usuario_id, conteudo_id, sorteio.choices([2, 3, 4, 5], [1, 2, 4, 4])[0]),
                )
        totais["atividades"] += len(lidos)

        for quiz in sorteio.sample(quizzes, sorteio.randint(1, len(quizzes))):
            for _ in range(sorteio.choice([1, 1, 2])):
                escolhas = []
                for questao_id, alternativas in quiz["questoes"].items():
                    corretas = [a for a in alternativas if a["correta"]]
                    erradas = [a for a in alternativas if not a["correta"]]
                    acerta = sorteio.random() < dificuldade[questao_id] or not erradas
                    escolhas.append((questao_id, sorteio.choice(corretas if acerta else erradas)))
                pontos = sum(1 for _, alternativa in escolhas if alternativa["correta"])
                tentativa_id = conexao.execute(
                    "INSERT INTO public.tentativas_quiz (usuario_id, quiz_id, pontuacao, total_questoes, criada_em) "
                    "VALUES (%s, %s, %s, %s, %s) RETURNING id",
                    (usuario_id, quiz["quiz_id"], pontos, len(escolhas), _momento(agora, sorteio, dias)),
                ).fetchone()["id"]
                for questao_id, alternativa in escolhas:
                    conexao.execute(
                        "INSERT INTO public.respostas_tentativa_quiz (tentativa_id, questao_id, alternativa_id) VALUES (%s, %s, %s)",
                        (tentativa_id, questao_id, alternativa["alternativa_id"]),
                    )
                totais["atividades"] += 1
            if sorteio.random() < 0.5:
                conexao.execute(
                    "INSERT INTO public.avaliacoes_quiz (usuario_id, catalogo_id, nota) VALUES (%s, %s, %s) "
                    "ON CONFLICT DO NOTHING",
                    (usuario_id, quiz["catalogo_id"], sorteio.choices([2, 3, 4, 5], [1, 2, 4, 3])[0]),
                )

        for simulacao in sorteio.sample(simulacoes, sorteio.randint(1, len(simulacoes))):
            chance = cuidado[simulacao["identificador"]]
            for tentativa in range(sorteio.choice([1, 1, 2])):
                segura = sorteio.random() < chance + 0.3 * tentativa
                conexao.execute(
                    "INSERT INTO public.tentativas_simulacao (usuario_id, simulacao, opcao, versao_simulacao_id, criada_em) "
                    "VALUES (%s, %s, %s, %s, %s)",
                    (usuario_id, simulacao["identificador"],
                     sorteio.choice(simulacao["seguras"] if segura else simulacao["risco"]),
                     simulacao["versao_id"], _momento(agora, sorteio, dias)),
                )
                totais["atividades"] += 1

        for _ in range(sorteio.randint(0, 2)):
            conexao.execute(
                "INSERT INTO public.desafios_senha (usuario_id, acertos, total_rodadas, token_partida, concluido_em) "
                "VALUES (%s, %s, 5, %s, %s)",
                (usuario_id, sorteio.randint(1, 5), secrets.token_urlsafe(24), _momento(agora, sorteio, dias)),
            )
            totais["atividades"] += 1
    return totais


def apagar(conexao):
    filtro = "SELECT id FROM public.usuarios WHERE email LIKE %s"
    parametro = ("%" + DOMINIO,)
    conexao.execute(f"DELETE FROM public.tentativas_quiz WHERE usuario_id IN ({filtro})", parametro)
    conexao.execute(f"DELETE FROM public.tentativas_simulacao WHERE usuario_id IN ({filtro})", parametro)
    return conexao.execute("DELETE FROM public.usuarios WHERE email LIKE %s", parametro).rowcount


@click.command()
@click.option("--criar", "acao", flag_value="criar", help="Cria as contas e o histórico de demonstração.")
@click.option("--apagar", "acao", flag_value="apagar", help="Apaga tudo o que foi criado por este script.")
def main(acao):
    if acao is None:
        raise click.UsageError("Informe --criar ou --apagar.")
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    with create_app().app_context(), conectar_banco() as conexao:
        if acao == "criar":
            totais = criar(conexao, datetime.now(timezone.utc))
            click.echo(f"Pronto: {totais['contas']} contas fictícias ({DOMINIO}) e {totais['atividades']} atividades criadas.")
        else:
            click.echo(f"Pronto: {apagar(conexao)} contas de demonstração apagadas com todo o histórico.")


if __name__ == "__main__":
    main()
