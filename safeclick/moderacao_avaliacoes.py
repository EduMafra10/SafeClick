from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user
from flask_wtf import FlaskForm
from psycopg import Error

from safeclick import avaliacoes_db as db
from safeclick.avaliacoes import pagina_atual
from safeclick.sessoes import exigir_perfis

moderacao_avaliacoes = Blueprint('moderacao_avaliacoes', __name__, url_prefix='/administracao/avaliacoes/comentarios')


@moderacao_avaliacoes.before_request
@exigir_perfis('administrador')
def verificar_acesso():
    request.max_content_length = 4096


@moderacao_avaliacoes.get('')
def listar():
    pagina = pagina_atual()
    estado = request.args.get('estado', '')
    if estado not in {'', 'pendente', 'aprovada', 'rejeitada', 'nao_solicitada'}:
        abort(400)
    try:
        itens, total = db.listar_gestao(pagina, estado)
    except (Error, RuntimeError):
        return render_template('avaliacoes/indisponivel.html'), 503
    return render_template('administracao/comentarios_avaliacoes.html', itens=itens, total=total, pagina=pagina,
                           estado=estado, formulario=FlaskForm(), secoes={}, secao='avaliacoes')


@moderacao_avaliacoes.route('/<any(conteudo,quiz):tipo>/<int:item_id>/<int:autor_id>/<any(aprovar,ocultar):acao>', methods=['GET', 'POST'])
def confirmar(tipo, item_id, autor_id, acao):
    formulario = FlaskForm()
    # Busca somente a avaliação escolhida, evitando copiar dados de outros autores.
    try:
        with db.conectar_banco() as conexao:
            item = conexao.execute('WITH avaliacoes AS (' + db.BASE_AVALIACOES + """ )
                SELECT tipo,item_id,titulo,usuario_id,comentario,revisao,publicar_comentario,aviso_versao
                FROM avaliacoes WHERE tipo=%s AND item_id=%s AND usuario_id=%s AND conta_ativa
            """, (tipo, item_id, autor_id)).fetchone()
        if not item or item['aviso_versao'] != db.VERSAO_AVISO or not item['publicar_comentario']:
            abort(404)
        if request.method == 'POST':
            if (set(request.form) != {'csrf_token', 'revisao', 'confirmar'}
                    or request.files
                    or any(len(request.form.getlist(c)) != 1 for c in request.form)
                    or request.form.get('confirmar') != '1'
                    or not request.form.get('revisao', '').isascii()
                    or not request.form.get('revisao', '').isdigit()
                    or not formulario.validate_on_submit()):
                abort(400)
            db.moderar_comentario(int(current_user.id), tipo, item_id, autor_id, int(request.form['revisao']), acao)
            flash('Moderação registrada. A consulta pública já reflete a decisão.', 'avaliacao')
            return redirect(url_for('moderacao_avaliacoes.listar'), code=303)
    except ValueError as erro:
        return render_template('administracao/moderar_avaliacao.html', item=item, acao=acao, formulario=formulario, erro=str(erro)), 409
    except PermissionError:
        abort(403)
    except (Error, RuntimeError):
        return render_template('avaliacoes/indisponivel.html'), 503
    return render_template('administracao/moderar_avaliacao.html', item=item, acao=acao, formulario=formulario)
