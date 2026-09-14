from flask import (
    Blueprint,
    abort,
    current_app,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
import secrets
import psycopg

from safeclick.db import conectar_banco


quizzes = Blueprint(
    "quizzes",
    __name__,
    url_prefix="/quizzes",
)


@quizzes.get("/")
def listar_quizzes():
    with conectar_banco() as conexao:
        registros = conexao.execute(
            """
            SELECT id, titulo
            FROM public.quizzes
            ORDER BY id
            """
        ).fetchall()

    return render_template(
        "quizzes/lista.html",
        quizzes=registros,
    )

@quizzes.route("/<int:quiz_id>", methods=["GET", "POST"])
def exibir_quiz(quiz_id):
    with conectar_banco() as conexao:
        quiz = conexao.execute(
            """
            SELECT id, titulo
            FROM public.quizzes
            WHERE id = %s
            """,
            (quiz_id,),
        ).fetchone()

        if quiz is None:
            abort(404)

        questoes = conexao.execute(
            """
            SELECT id, enunciado, ordem
            FROM public.questoes
            WHERE quiz_id = %s
            ORDER BY ordem
            """,
            (quiz_id,),
        ).fetchall()

        alternativas = conexao.execute(
            """
            SELECT
                alternativa.id,
                alternativa.questao_id,
                alternativa.texto,
                alternativa.ordem
            FROM public.alternativas AS alternativa
            JOIN public.questoes AS questao
                ON questao.id = alternativa.questao_id
            WHERE questao.quiz_id = %s
            ORDER BY questao.ordem, alternativa.ordem
            """,
            (quiz_id,),
        ).fetchall()

    alternativas_por_questao = {}

    for alternativa in alternativas:
        questao_id = alternativa["questao_id"]

        alternativas_por_questao.setdefault(
            questao_id, []
        ).append(alternativa)

    for questao in questoes:
        questao["alternativas"] = alternativas_por_questao.get(
            questao["id"], []
        )

    if not current_app.config.get("SECRET_KEY"):
        abort(
            503,
            description="A configuração da sessão está pendente.",
        )

    chave_token = f"token_quiz_{quiz_id}"

    if request.method == "GET":
        session[chave_token] = secrets.token_hex(32)

    token_envio = session.get(chave_token)

    erro = None
    mensagem = None
    respostas = {}
    status = 200


    if request.method == "POST":
        campos_esperados = {
            f"questao_{questao['id']}"
            for questao in questoes
        }
        campos_esperados.add("token_envio")
        tokens_recebidos = request.form.getlist("token_envio")

        if (
            not token_envio
            or len(tokens_recebidos) != 1
            or not secrets.compare_digest(
                tokens_recebidos[0].encode("utf-8"),
                token_envio.encode("utf-8"),
            )
        ):
            erro = (
                "Este formulário expirou ou é inválido. "
                "Volte à lista e abra o quiz novamente."
            )
            status = 400

        elif len(questoes) != 5:
            erro = "Este quiz está indisponível no momento."
            status = 503

        elif set(request.form.keys()) != campos_esperados:
            erro = "Responda todas as perguntas usando as opções apresentadas."
            status = 400

        else:
            for questao in questoes:
                campo = f"questao_{questao['id']}"
                valores = request.form.getlist(campo)

                alternativas_validas = {
                    str(alternativa["id"])
                    for alternativa in questao["alternativas"]
                }

                if (
                    len(valores) != 1
                    or valores[0] not in alternativas_validas
                ):
                    erro = (
                        "Cada pergunta deve receber uma única "
                        "alternativa válida."
                    )
                    status = 400
                    break

                respostas[questao["id"]] = int(valores[0])

            if erro is None:
                if not current_app.config.get("SECRET_KEY"):
                    abort(
                        503,
                        description="A configuração da sessão está pendente.",
                    )

                try:
                    resultado = corrigir_respostas(
                        quiz_id,
                        questoes,
                        respostas,
                    )

                    tentativa_id = salvar_tentativa(
                        quiz_id,
                        respostas,
                        resultado,
                        token_envio,
                    )

                except psycopg.Error:
                    erro = (
                        "Não foi possível salvar sua tentativa. "
                        "Tente novamente."
                    )
                    status = 503

                else:
                    session["ultima_tentativa_quiz"] = tentativa_id

                    return redirect(
                        url_for("quizzes.exibir_resultado"),
                        code=303,
                    )

    return render_template(
        "quizzes/responder.html",
        quiz=quiz,
        questoes=questoes,
        erro=erro,
        mensagem=mensagem,
        respostas=respostas,
        token_envio=token_envio,
    ), status

def corrigir_respostas(quiz_id, questoes, respostas):
    with conectar_banco() as conexao:
        gabarito = conexao.execute(
            """
            SELECT
                questao.id AS questao_id,
                questao.explicacao,
                alternativa.id AS alternativa_id,
                alternativa.texto AS texto_correto
            FROM public.questoes AS questao
            JOIN public.alternativas AS alternativa
                ON alternativa.questao_id = questao.id
            WHERE questao.quiz_id = %s
              AND alternativa.correta = TRUE
            ORDER BY questao.ordem
            """,
            (quiz_id,),
        ).fetchall()

    gabarito_por_questao = {
        registro["questao_id"]: registro
        for registro in gabarito
    }

    ids_esperados = {
        questao["id"]
        for questao in questoes
    }

    if (
        len(gabarito) != len(questoes)
        or set(gabarito_por_questao) != ids_esperados
        or any(
            len(questao["alternativas"]) != 4
            for questao in questoes
        )
    ):
        abort(
            503,
            description="Este quiz está indisponível no momento.",
        )

    pontuacao = 0
    detalhes = []

    for questao in questoes:
        resposta_correta = gabarito_por_questao[questao["id"]]
        alternativa_escolhida_id = respostas[questao["id"]]

        alternativas_por_id = {
            alternativa["id"]: alternativa
            for alternativa in questao["alternativas"]
        }

        alternativa_escolhida = alternativas_por_id[
            alternativa_escolhida_id
        ]

        acertou = (
            alternativa_escolhida_id
            == resposta_correta["alternativa_id"]
        )

        if acertou:
            pontuacao += 1

        detalhes.append(
            {
                "ordem": questao["ordem"],
                "enunciado": questao["enunciado"],
                "resposta_escolhida": alternativa_escolhida["texto"],
                "resposta_correta": resposta_correta["texto_correto"],
                "explicacao": resposta_correta["explicacao"],
                "acertou": acertou,
            }
        )

    return {
        "pontuacao": pontuacao,
        "total_questoes": len(questoes),
        "detalhes": detalhes,
    }

def salvar_tentativa(quiz_id, respostas, resultado, token_envio):
    with conectar_banco() as conexao:
        tentativa = conexao.execute(
            """
            INSERT INTO public.tentativas_quiz (
                quiz_id,
                pontuacao,
                total_questoes,
                token_envio
            )
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (token_envio) DO NOTHING
            RETURNING id
            """,
            (
                quiz_id,
                resultado["pontuacao"],
                resultado["total_questoes"],
                token_envio,
            ),
        ).fetchone()

        if tentativa is None:
            tentativa_existente = conexao.execute(
                """
                SELECT id
                FROM public.tentativas_quiz
                WHERE token_envio = %s
                  AND quiz_id = %s
                """,
                (
                    token_envio,
                    quiz_id,
                ),
            ).fetchone()

            if tentativa_existente is None:
                abort(
                    409,
                    description="Não foi possível identificar a tentativa.",
                )

            return tentativa_existente["id"]

        tentativa_id = tentativa["id"]

        for questao_id, alternativa_id in respostas.items():
            conexao.execute(
                """
                INSERT INTO public.respostas_tentativa_quiz (
                    tentativa_id,
                    questao_id,
                    alternativa_id
                )
                VALUES (%s, %s, %s)
                """,
                (
                    tentativa_id,
                    questao_id,
                    alternativa_id,
                ),
            )

    return tentativa_id

@quizzes.get("/resultado")
def exibir_resultado():
    tentativa_id = session.get("ultima_tentativa_quiz")

    if tentativa_id is None:
        return redirect(url_for("quizzes.listar_quizzes"))

    with conectar_banco() as conexao:
        tentativa = conexao.execute(
            """
            SELECT
                tentativa.id,
                tentativa.quiz_id,
                tentativa.pontuacao,
                tentativa.total_questoes,
                quiz.titulo
            FROM public.tentativas_quiz AS tentativa
            JOIN public.quizzes AS quiz
                ON quiz.id = tentativa.quiz_id
            WHERE tentativa.id = %s
            """,
            (tentativa_id,),
        ).fetchone()

        if tentativa is None:
            abort(404)

        detalhes = conexao.execute(
            """
            SELECT
                questao.ordem,
                questao.enunciado,
                escolhida.texto AS resposta_escolhida,
                correta.texto AS resposta_correta,
                questao.explicacao,
                (escolhida.id = correta.id) AS acertou
            FROM public.respostas_tentativa_quiz AS resposta
            JOIN public.questoes AS questao
                ON questao.id = resposta.questao_id
            JOIN public.alternativas AS escolhida
                ON escolhida.id = resposta.alternativa_id
                AND escolhida.questao_id = questao.id
            JOIN public.alternativas AS correta
                ON correta.questao_id = questao.id
                AND correta.correta = TRUE
            WHERE resposta.tentativa_id = %s
              AND questao.quiz_id = %s
            ORDER BY questao.ordem
            """,
            (
                tentativa_id,
                tentativa["quiz_id"],
            ),
        ).fetchall()

    if len(detalhes) != tentativa["total_questoes"]:
        abort(
            503,
            description="Não foi possível apresentar o resultado completo.",
        )

    quiz = {
        "id": tentativa["quiz_id"],
        "titulo": tentativa["titulo"],
    }

    resultado = {
        "pontuacao": tentativa["pontuacao"],
        "total_questoes": tentativa["total_questoes"],
        "detalhes": detalhes,
    }

    pagina = current_app.make_response(
        render_template(
            "quizzes/resultado.html",
            quiz=quiz,
            resultado=resultado,
        )
    )

    pagina.headers["Cache-Control"] = "no-store"

    return pagina