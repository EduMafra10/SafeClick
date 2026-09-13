from flask import Blueprint, abort, render_template, request

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
        
        erro = None
    mensagem = None
    respostas = {}
    status = 200


    if request.method == "POST":
        campos_esperados = {
            f"questao_{questao['id']}"
            for questao in questoes
        }

        if len(questoes) != 5:
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
                mensagem = "As cinco respostas foram recebidas."

    return render_template(
        "quizzes/responder.html",
        quiz=quiz,
        questoes=questoes,
        erro=erro,
        mensagem=mensagem,
        respostas=respostas,
    ), status