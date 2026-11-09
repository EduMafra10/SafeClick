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
from safeclick.auditoria_db import registrar_evento
from safeclick.catalogo_validacao import MAX_ALTERNATIVAS, MAX_QUESTOES
from safeclick.navegacao_atividades import PROXIMO_QUIZ
from safeclick.sessoes import exigir_perfis
from flask_login import current_user


quizzes = Blueprint(
    "quizzes",
    __name__,
    url_prefix="/quizzes",
)


class QuizAlterado(ValueError):
    pass


@quizzes.before_request
@exigir_perfis("usuario", "administrador")
def verificar_acesso_quizzes():
    return None


@quizzes.get("/")
def listar_quizzes():
    # Lista os quizzes cadastrados no banco.
    with conectar_banco() as conexao:
        registros = conexao.execute(
            """
            SELECT c.id, q.titulo, q.formato,
                   (SELECT COUNT(*) FROM public.questoes WHERE quiz_id = q.id) AS total_questoes
            FROM public.catalogo_quizzes AS c
            JOIN public.quizzes AS q ON q.id = c.versao_publicada_id
            WHERE c.estado = 'publicada'
            ORDER BY c.id
            """
        ).fetchall()

    return render_template(
        "quizzes/lista.html",
        quizzes=registros,
    )


@quizzes.route("/<int:quiz_id>", methods=["GET", "POST"])
def exibir_quiz(quiz_id):
    # Exibe as perguntas e processa o envio das respostas.
    with conectar_banco() as conexao:
        quiz = conexao.execute(
            f"""
            SELECT item.id, publicada.id AS versao_id, publicada.titulo, publicada.formato,
                {PROXIMO_QUIZ}
            FROM public.catalogo_quizzes AS item
            JOIN public.quizzes AS publicada ON publicada.id = item.versao_publicada_id
            WHERE item.id = %s AND item.estado = 'publicada'
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
            (quiz["versao_id"],),
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
            (quiz["versao_id"],),
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

    # Cada abertura do quiz recebe um código vinculado à sessão.
    chave_token = str(quiz_id)
    formularios = session.get("formularios_quiz", {})

    if request.method == "GET":
        formularios.pop(chave_token, None)
        formularios[chave_token] = {"token": secrets.token_hex(32), "versao": quiz["versao_id"]}
        session["formularios_quiz"] = dict(list(formularios.items())[-8:])

    registro_formulario = formularios.get(chave_token, {})
    token_envio = registro_formulario.get("token")

    erro = None
    mensagem = None
    respostas = {}
    status = 200


    if request.method == "POST":
        # Aceita apenas o token e uma alternativa válida por pergunta.
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

        elif registro_formulario.get("versao") != quiz["versao_id"]:
            erro = "Este quiz foi atualizado. Volte à lista e abra o quiz novamente."
            status = 409

        elif not 1 <= len(questoes) <= MAX_QUESTOES:
            erro = "Este quiz está indisponível no momento."
            status = 503

        elif set(request.form.keys()) != campos_esperados:
            erro = "Responda todas as perguntas usando as opções apresentadas."
            status = 400

        else:
            cartoes_usados = set()
            for questao in questoes:
                campo = f"questao_{questao['id']}"
                valores = request.form.getlist(campo)

                alternativas_validas = {
                    str(alternativa["id"]): alternativa
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

                if quiz["formato"] == "oficina":
                    cartao = alternativas_validas[valores[0]]["texto"]
                    if cartao in cartoes_usados:
                        erro = "Encaixe cada cartão em um único trecho do guia."
                        status = 400
                        break
                    cartoes_usados.add(cartao)

                respostas[questao["id"]] = int(valores[0])

            if erro is None:
                if not current_app.config.get("SECRET_KEY"):
                    abort(
                        503,
                        description="A configuração da sessão está pendente.",
                    )

                try:
                    resultado = corrigir_respostas(
                        quiz["versao_id"],
                        questoes,
                        respostas,
                    )

                    tentativa_id = salvar_tentativa(
                        current_user.id,
                        quiz["versao_id"],
                        respostas,
                        resultado,
                        token_envio,
                    )

                except QuizAlterado:
                    erro = "Este quiz mudou de publicação. Volte à lista para continuar."
                    status = 409
                except psycopg.Error:
                    erro = (
                        "Não foi possível salvar sua tentativa. "
                        "Tente novamente."
                    )
                    status = 503

                else:
                    session["ultima_tentativa_quiz"] = tentativa_id

                    # O redirecionamento evita reenvio ao atualizar o resultado.
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
    # Calcula os acertos pelo gabarito e prepara as explicações.
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
            not 2 <= len(questao["alternativas"]) <= MAX_ALTERNATIVAS
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


def salvar_tentativa(usuario_id, quiz_id, respostas, resultado, token_envio):
    with conectar_banco() as conexao:
        tentativa = conexao.execute(
            """
            INSERT INTO public.tentativas_quiz (
                usuario_id,
                quiz_id,
                pontuacao,
                total_questoes,
                token_envio
            )
            SELECT %s, %s, %s, %s, %s
            FROM public.catalogo_quizzes
            WHERE versao_publicada_id = %s AND estado = 'publicada'
            FOR SHARE
            ON CONFLICT (token_envio) DO NOTHING
            RETURNING id, (
                SELECT catalogo_id FROM public.quizzes WHERE id = tentativas_quiz.quiz_id
            ) AS catalogo_id
            """,
            (
                usuario_id,
                quiz_id,
                resultado["pontuacao"],
                resultado["total_questoes"],
                token_envio,
                quiz_id,
            ),
        ).fetchone()

        if tentativa is None:
            tentativa_existente = conexao.execute(
                """
                SELECT id
                FROM public.tentativas_quiz
                WHERE token_envio = %s
                  AND quiz_id = %s
                  AND usuario_id = %s
                """,
                (
                    token_envio,
                    quiz_id,
                    usuario_id,
                ),
            ).fetchone()

            if tentativa_existente is None:
                raise QuizAlterado()

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

        registrar_evento(
            usuario_id=usuario_id,
            evento="quiz.concluido",
            resultado="sucesso",
            recurso_tipo="tentativa_quiz",
            recurso_id=tentativa_id,
            detalhes={
                "quiz_id": tentativa["catalogo_id"],
                "pontuacao": resultado["pontuacao"],
                "total_questoes": resultado["total_questoes"],
            },
            conexao=conexao,
        )

    return tentativa_id


@quizzes.get("/guia")
def exibir_guia():
    with conectar_banco() as conexao:
        paginas = conexao.execute(
            """
            SELECT DISTINCT ON (quiz.catalogo_id)
                tentativa.id, quiz.titulo, tentativa.pontuacao, tentativa.total_questoes
            FROM public.tentativas_quiz AS tentativa
            JOIN public.quizzes AS quiz ON quiz.id = tentativa.quiz_id
            WHERE tentativa.usuario_id = %s AND quiz.formato = 'oficina'
            ORDER BY quiz.catalogo_id, tentativa.id DESC
            """,
            (current_user.id,),
        ).fetchall()
    return render_template("quizzes/guia.html", paginas=paginas)


@quizzes.get("/resultado")
@quizzes.get("/resultado/<int:tentativa_id>")
def exibir_resultado(tentativa_id=None):
    # Mostra a última tentativa associada à sessão do navegador.
    if tentativa_id is None:
        tentativa_id = session.get("ultima_tentativa_quiz")

    if tentativa_id is None:
        return redirect(url_for("quizzes.listar_quizzes"))

    with conectar_banco() as conexao:
        tentativa = conexao.execute(
            f"""
            SELECT
                tentativa.id,
                tentativa.quiz_id,
                tentativa.pontuacao,
                tentativa.total_questoes,
                quiz.titulo,
                quiz.formato,
                item.id AS catalogo_id,
                item.estado = 'publicada' AS pode_repetir,
                {PROXIMO_QUIZ}
            FROM public.tentativas_quiz AS tentativa
            JOIN public.quizzes AS quiz
                ON quiz.id = tentativa.quiz_id
            JOIN public.catalogo_quizzes AS item
                ON item.id = quiz.catalogo_id
            LEFT JOIN public.quizzes AS publicada
                ON publicada.id = item.versao_publicada_id
            WHERE tentativa.id = %s
              AND tentativa.usuario_id = %s
            """,
            (tentativa_id, current_user.id),
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
                (escolhida.id = correta.id) AS acertou,
                (
                    SELECT jsonb_agg(jsonb_build_object(
                        'ordem', opcao.ordem,
                        'texto', opcao.texto,
                        'correta', opcao.correta,
                        'explicacao', opcao.explicacao
                    ) ORDER BY opcao.ordem)
                    FROM public.alternativas AS opcao
                    WHERE opcao.questao_id = questao.id AND opcao.explicacao <> ''
                ) AS alternativas_comentadas
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
        "id": tentativa["catalogo_id"],
        "titulo": tentativa["titulo"],
        "formato": tentativa["formato"],
        "pode_repetir": tentativa["pode_repetir"],
        "proxima_referencia": tentativa["proxima_referencia"],
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
            tentativa_id=tentativa["id"],
        )
    )

    pagina.headers["Cache-Control"] = "no-store"

    return pagina
