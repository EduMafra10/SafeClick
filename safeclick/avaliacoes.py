from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user
from flask_wtf import FlaskForm
from psycopg import Error
from wtforms import RadioField, TextAreaField
from wtforms.validators import InputRequired, Length, ValidationError

from safeclick.avaliacoes_db import buscar_atividade, salvar_avaliacao
from safeclick.db import conectar_banco
from safeclick.sessoes import exigir_perfis


avaliacoes = Blueprint("avaliacoes", __name__, url_prefix="/avaliacoes")
LIMITE_COMENTARIO = 500


class FormularioAvaliacao(FlaskForm):
    nota = RadioField(
        "Quanto esta atividade ajudou você a entender o tema?",
        choices=[
            ("1", "1 · Nada útil"),
            ("2", "2 · Pouco útil"),
            ("3", "3 · Moderadamente útil"),
            ("4", "4 · Útil"),
            ("5", "5 · Muito útil"),
        ],
        validators=[InputRequired(message="Escolha uma nota de 1 a 5.")],
    )
    comentario = TextAreaField(
        "Comentário (opcional)",
        default="",
        validators=[Length(max=LIMITE_COMENTARIO, message="Use até 500 caracteres.")],
    )

    def validate_comentario(self, campo):
        if "\x00" in campo.data:
            raise ValidationError("O comentário contém um caractere inválido.")


@avaliacoes.before_request
@exigir_perfis("usuario", "administrador")
def verificar_acesso():
    if not current_app.config["AVALIACOES_ATIVAS"]:
        abort(404)


@avaliacoes.route("/conteudos/<slug>", methods=["GET", "POST"])
def conteudo(slug):
    return _editar(
        "conteudo", slug, url_for("conteudos.detalhe", slug=slug),
    )


@avaliacoes.route("/quizzes/<int:tentativa_id>", methods=["GET", "POST"])
def quiz(tentativa_id):
    return _editar(
        "quiz", tentativa_id, url_for("quizzes.exibir_resultado", tentativa_id=tentativa_id),
    )


def _editar(tipo, referencia, voltar):
    request.max_content_length = 16 * 1024
    enviando = request.method == "POST"
    usuario_id = int(current_user.id)
    try:
        with conectar_banco() as conexao:
            atividade = buscar_atividade(conexao, tipo, usuario_id, referencia, bloquear=enviando)
            if atividade is None:
                abort(404)

            formulario = FormularioAvaliacao()
            valido = False
            if enviando:
                campos = {"csrf_token", "nota", "comentario"}
                valido = (
                    set(request.form) <= campos
                    and all(len(request.form.getlist(nome)) == 1 for nome in request.form)
                    and not request.files
                    and formulario.validate_on_submit()
                )
                if valido:
                    salvar_avaliacao(
                        conexao, tipo, usuario_id, atividade["id"], int(formulario.nota.data),
                        formulario.comentario.data.strip() or None,
                    )
            else:
                formulario.nota.data = str(atividade["nota"]) if atividade["nota"] is not None else None
                formulario.comentario.data = atividade["comentario"] or ""
    except (Error, RuntimeError):
        abort(503, description="Não foi possível acessar a avaliação agora. Tente novamente em instantes.")

    if valido:
        flash("Avaliação salva. Você pode atualizá-la a qualquer momento enquanto a atividade estiver publicada.", "avaliacao")
        return redirect(request.path, code=303)
    return render_template(
        "avaliacoes/formulario.html", atividade=atividade, formulario=formulario, tipo=tipo,
        voltar=voltar, envio_invalido=enviando, limite_comentario=LIMITE_COMENTARIO,
    ), 400 if enviando else 200
