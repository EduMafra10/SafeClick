from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user
from flask_wtf import FlaskForm
from psycopg import Error
from wtforms import BooleanField, HiddenField, RadioField, TextAreaField
from wtforms.validators import InputRequired, Length, ValidationError

from safeclick.avaliacoes_db import buscar_atividade, salvar_avaliacao
from safeclick.db import conectar_banco
from safeclick.sessoes import exigir_perfis
from safeclick import avaliacoes_db as db
from safeclick.limites import permitir_tentativa
from safeclick.avaliacoes_config import VERSAO_AVISO


avaliacoes = Blueprint("avaliacoes", __name__, url_prefix="/avaliacoes")
LIMITE_COMENTARIO = 500


class FormularioAvaliacao(FlaskForm):
    aviso_versao = HiddenField(default=VERSAO_AVISO)
    publicar_nota = BooleanField('Incluir minha nota na média pública.', default=False)
    publicar_comentario = BooleanField('Enviar meu comentário para publicação sem meu nome, após moderação.', default=False)
    maior_de_idade = BooleanField('Declaro ter 18 anos ou mais para compartilhar publicamente.', default=False)
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
def verificar_acesso():
    livres = {'avaliacoes.publicas', 'avaliacoes.detalhe_publico', 'avaliacoes.resumo_publico', 'avaliacoes.privacidade'}
    controles = {'avaliacoes.minhas', 'avaliacoes.excluir', 'avaliacoes.retirar'}
    if not current_app.config["AVALIACOES_ATIVAS"] and request.endpoint not in controles | {'avaliacoes.privacidade'}:
        abort(404)
    request.max_content_length = 16 * 1024
    if request.endpoint not in livres:
        return exigir_perfis('usuario', 'administrador')(lambda: None)()


@avaliacoes.after_request
def proteger_resposta(resposta):
    resposta.headers['Cache-Control'] = 'no-store'
    resposta.headers['X-Robots-Tag'] = 'noindex, nofollow'
    return resposta


def pagina_atual():
    valores = request.args.getlist('pagina')
    if len(valores) > 1 or valores and (len(valores[0]) > 5 or not valores[0].isascii() or not valores[0].isdigit()):
        abort(400, description='Página inválida.')
    pagina = int(valores[0]) if valores else 1
    if not 1 <= pagina <= 10000:
        abort(400, description='Página inválida.')
    return pagina


@avaliacoes.get('/privacidade')
def privacidade():
    return render_template('avaliacoes/privacidade.html', versao=VERSAO_AVISO)


@avaliacoes.get('/publicas')
def publicas():
    pagina = pagina_atual()
    tipo = request.args.get('tipo', '')
    busca = request.args.get('busca', '').strip()
    if tipo not in {'', 'quiz', 'conteudo'} or len(busca) > 100 or '\x00' in busca:
        abort(400)
    try:
        itens, total = db.listar_publicas(tipo=tipo, busca=busca, pagina=pagina)
    except (Error, RuntimeError):
        return render_template('avaliacoes/publicas.html', erro=True, itens=[], total=0, pagina=pagina, tipo=tipo, busca=busca), 503
    return render_template('avaliacoes/publicas.html', itens=itens, total=total, pagina=pagina, tipo=tipo, busca=busca)


@avaliacoes.get('/publicas/<any(conteudo,quiz):tipo>/<int:item_id>')
@avaliacoes.get('/publicas/<any(conteudo,quiz):tipo>/<int:item_id>/resumo', endpoint='resumo_publico')
def detalhe_publico(tipo, item_id):
    pagina = pagina_atual()
    try:
        dados = db.detalhar_publicas(tipo, item_id, pagina)
    except (Error, RuntimeError):
        return render_template('avaliacoes/indisponivel.html'), 503
    if dados is None:
        abort(404)
    atividade, resumo, comentarios = dados
    modelo = 'avaliacoes/_resumo.html' if request.endpoint == 'avaliacoes.resumo_publico' else 'avaliacoes/publica.html'
    return render_template(modelo, atividade=atividade, resumo=resumo, comentarios=comentarios, tipo=tipo, pagina=pagina)


@avaliacoes.route('/minhas', methods=['GET'])
def minhas():
    try:
        itens = db.listar_minhas(int(current_user.id))
    except (Error, RuntimeError):
        return render_template('avaliacoes/indisponivel.html'), 503
    return render_template('avaliacoes/minhas.html', itens=itens, formulario=FlaskForm())


@avaliacoes.post('/minhas/<any(conteudo,quiz):tipo>/<int:item_id>/excluir')
def excluir(tipo, item_id):
    formulario = FlaskForm()
    if (set(request.form) != {'csrf_token'} or len(request.form.getlist('csrf_token')) != 1
            or request.files or not formulario.validate_on_submit()):
        abort(400)
    try:
        if not db.excluir_avaliacao(int(current_user.id), tipo, item_id):
            abort(404)
    except (Error, RuntimeError):
        return render_template('avaliacoes/indisponivel.html'), 503
    flash('Avaliação excluída. A nota e o comentário não aparecem mais na consulta pública.', 'avaliacao')
    return redirect(url_for('avaliacoes.minhas'), code=303)


@avaliacoes.post('/minhas/<any(conteudo,quiz):tipo>/<int:item_id>/retirar')
def retirar(tipo, item_id):
    formulario = FlaskForm()
    if (set(request.form) != {'csrf_token'} or len(request.form.getlist('csrf_token')) != 1
            or request.files or not formulario.validate_on_submit()):
        abort(400)
    try:
        if not db.retirar_publicacao(int(current_user.id),tipo,item_id):
            abort(404)
    except (Error, RuntimeError):
        return render_template('avaliacoes/indisponivel.html'),503
    flash('Publicação retirada. Sua avaliação permanece privada.','avaliacao')
    return redirect(url_for('avaliacoes.minhas'),code=303)


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
                campos = {"csrf_token", "nota", "comentario", 'aviso_versao', 'publicar_nota', 'publicar_comentario', 'maior_de_idade'}
                notificado = 'aviso_versao' in request.form
                publico = formulario.publicar_nota.data or formulario.publicar_comentario.data
                valido = (
                    set(request.form) <= campos
                    and all(len(request.form.getlist(nome)) == 1 for nome in request.form)
                    and not request.files
                    and formulario.validate_on_submit()
                    and all(request.form.get(nome) in (None, '1') for nome in ('publicar_nota','publicar_comentario','maior_de_idade'))
                    and (not notificado or formulario.aviso_versao.data == VERSAO_AVISO)
                    and (not publico or notificado and formulario.maior_de_idade.data)
                    and (not formulario.publicar_comentario.data or formulario.publicar_nota.data and bool(formulario.comentario.data.strip()))
                )
                if valido:
                    if notificado and not permitir_tentativa('avaliacao', usuario_id, 20):
                        abort(429, description='Aguarde alguns minutos antes de enviar outra avaliação.')
                    opcoes = ({'publicar_nota': formulario.publicar_nota.data,
                               'publicar_comentario': formulario.publicar_comentario.data,
                               'maior_de_idade': formulario.maior_de_idade.data,
                               'aviso_versao': VERSAO_AVISO} if notificado else {})
                    salvar_avaliacao(
                        conexao, tipo, usuario_id, atividade["id"], int(formulario.nota.data),
                        formulario.comentario.data.strip() or None,
                        **opcoes,
                    )
            else:
                formulario.nota.data = str(atividade["nota"]) if atividade["nota"] is not None else None
                formulario.comentario.data = atividade["comentario"] or ""
                for nome in ('publicar_nota','publicar_comentario','maior_de_idade'):
                    getattr(formulario, nome).data = bool(atividade.get(nome))
    except PermissionError:
        abort(403, description='Sua conta não está disponível para enviar avaliações.')
    except (Error, RuntimeError):
        abort(503, description="Não foi possível acessar a avaliação agora. Tente novamente em instantes.")

    if valido:
        flash("Avaliação salva. Você pode atualizá-la a qualquer momento enquanto a atividade estiver publicada.", "avaliacao")
        return redirect(request.path, code=303)
    return render_template(
        "avaliacoes/formulario.html", atividade=atividade, formulario=formulario, tipo=tipo,
        voltar=voltar, envio_invalido=enviando, limite_comentario=LIMITE_COMENTARIO,
    ), 400 if enviando else 200
