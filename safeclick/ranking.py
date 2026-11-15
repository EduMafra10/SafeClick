from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user
from flask_wtf import FlaskForm
from psycopg import Error
from wtforms import BooleanField, HiddenField

from safeclick import ranking_db as db
from safeclick.avaliacoes import pagina_atual
from safeclick.limites import permitir_tentativa
from safeclick.sessoes import exigir_perfis

ranking = Blueprint('ranking', __name__, url_prefix='/ranking')


class FormularioParticipacao(FlaskForm):
    aviso_versao = HiddenField(default=db.VERSAO_AVISO)
    participar = BooleanField('Quero publicar minha pontuação no ranking com um pseudônimo gerado pelo SafeClick.', default=False)
    maior_de_idade = BooleanField('Declaro ter 18 anos ou mais.', default=False)


@ranking.after_request
def proteger_resposta(resposta):
    resposta.headers['Cache-Control'] = 'no-store'
    resposta.headers['X-Robots-Tag'] = 'noindex, nofollow'
    return resposta


@ranking.get('/')
def listar():
    pagina = pagina_atual()
    try:
        itens, total = db.buscar_ranking(pagina)
    except (Error, RuntimeError):
        return render_template('ranking/lista.html', itens=[], total=0, pagina=pagina, erro=True), 503
    return render_template('ranking/lista.html', itens=itens, total=total, pagina=pagina)


@ranking.get('/privacidade')
def privacidade():
    return render_template('ranking/privacidade.html', versao=db.VERSAO_AVISO)


@ranking.route('/participacao', methods=['GET', 'POST'])
@exigir_perfis('usuario', 'administrador')
def participacao():
    request.max_content_length = 4096
    formulario = FormularioParticipacao()
    try:
        preferencia = db.buscar_preferencia(int(current_user.id))
        if request.method == 'POST':
            if (not set(request.form) <= {'csrf_token','aviso_versao','participar','maior_de_idade'}
                    or request.files
                    or any(len(request.form.getlist(c)) != 1 for c in request.form)
                    or any(request.form.get(c) not in (None,'1') for c in ('participar','maior_de_idade'))
                    or not formulario.validate_on_submit()
                    or request.form.get('aviso_versao') != db.VERSAO_AVISO
                    or formulario.participar.data and not formulario.maior_de_idade.data):
                return render_template('ranking/participacao.html', formulario=formulario, preferencia=preferencia,
                                       erro='Confira as opções de participação e a confirmação de idade.'), 400
            if not permitir_tentativa('ranking.participacao', int(current_user.id), 10):
                abort(429, description='Aguarde alguns minutos antes de alterar a participação novamente.')
            db.alterar_participacao(int(current_user.id), formulario.participar.data, formulario.maior_de_idade.data)
            flash('Participação atualizada. Você pode sair do ranking a qualquer momento.', 'avaliacao')
            return redirect(url_for('ranking.participacao'), code=303)
    except PermissionError as erro:
        abort(403, description=str(erro))
    except (Error, RuntimeError):
        return render_template('ranking/participacao.html', formulario=formulario, preferencia=None,
                               erro='Não foi possível atualizar a participação. Tente novamente em instantes.'), 503
    if request.method == 'GET':
        formulario.participar.data = bool(preferencia)
        formulario.maior_de_idade.data = bool(preferencia)
    return render_template('ranking/participacao.html', formulario=formulario, preferencia=preferencia)
