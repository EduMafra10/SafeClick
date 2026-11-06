from functools import wraps

from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user
from flask_wtf import FlaskForm
from psycopg import Error, errors

from safeclick import catalogo_admin_db as db
from safeclick.catalogo_validacao import (
    CANAIS, MAX_ALTERNATIVAS, MAX_QUESTOES, SECOES, DadosInvalidos,
    estrutura_json, html_do_texto, validar,
)


catalogo = Blueprint("catalogo", __name__, url_prefix="/catalogo")
ESTADOS = {
    "rascunho": "Rascunho",
    "publicada": "Publicado",
    "arquivada": "Despublicado",
    "removida": "Removido",
}
ACOES = {
    "publicar": ("Publicar", "Esta versão ficará disponível aos usuários."),
    "despublicar": ("Despublicar", "O item sai do catálogo. O histórico de atividades será preservado."),
    "remover": ("Remover", "Um rascunho nunca publicado e sem histórico é excluído. Um item com histórico sai do catálogo e pode ser restaurado."),
    "restaurar": ("Restaurar", "O item volta à gestão como despublicado. Publique quando estiver pronto."),
}
TEXTOS_SIMULACAO = ("tipo", "resumo", "assunto", "origem", "chamada", "mensagem", "sinais")
PRODUTO = ("nome", "preco_anterior", "preco_atual")


def _proteger_operacao(funcao):
    @wraps(funcao)
    def executar(secao, *args, **kwargs):
        if secao not in SECOES:
            abort(404)
        try:
            return funcao(secao, *args, **kwargs)
        except db.ItemNaoEncontrado:
            abort(404)
        except PermissionError:
            abort(403)
        except (errors.UndefinedTable, errors.UndefinedColumn):
            return render_template(
                "administracao/aviso_catalogo.html",
                mensagem="A gestão de conteúdo precisa da migração adicionar_gestao_catalogo.sql no banco usado pelo site.",
            ), 503
        except (Error, RuntimeError) as erro:
            current_app.logger.warning("Falha na gestão do catálogo (%s)", type(erro).__name__)
            return render_template(
                "administracao/aviso_catalogo.html",
                mensagem="Não foi possível concluir a operação. Confira o item antes de tentar novamente.",
            ), 503
    return executar


def _url_publica(secao, item):
    if item["estado"] != "publicada":
        return None
    if secao == "quizzes":
        return url_for("quizzes.exibir_quiz", quiz_id=item["id"])
    endpoints = {"conteudos": "conteudos.detalhe", "paginas": "paginas.detalhe", "simulacoes": "simulacoes.executar"}
    return url_for(endpoints[secao], slug=item["slug"])


def _revisao():
    valor = request.form.get("revisao", "")
    if not valor.isascii() or not valor.isdecimal() or not 1 <= len(valor) <= 10:
        raise DadosInvalidos("Reabra o item e tente novamente.")
    return int(valor)


def _validar_formulario(formulario, campos):
    if (
        set(request.form) != campos | {"csrf_token"}
        or any(len(request.form.getlist(nome)) != 1 for nome in request.form)
        or request.files
        or not formulario.validate_on_submit()
    ):
        raise DadosInvalidos("O formulário é inválido ou expirou. Recarregue a página e tente novamente.")


def _campos(secao):
    if secao == "quizzes":
        return {"titulo", "estrutura"}
    if secao == "simulacoes":
        return {"titulo", "estrutura", *TEXTOS_SIMULACAO, *("produto_" + c for c in PRODUTO)}
    return {"titulo", "corpo"}


def _ler_dados(secao):
    dados = {"titulo": request.form["titulo"]}
    if secao == "quizzes":
        dados["questoes"] = estrutura_json(request.form["estrutura"])
    elif secao == "simulacoes":
        dados.update({campo: request.form[campo] for campo in TEXTOS_SIMULACAO})
        dados["produto"] = {campo: request.form["produto_" + campo] for campo in PRODUTO}
        dados["opcoes"] = estrutura_json(request.form["estrutura"])
    else:
        dados["corpo"] = request.form["corpo"]
    return dados


def _opcoes_tela(dados):
    opcoes = dados.get("opcoes", [])
    if isinstance(opcoes, dict):
        return [opcoes[chave] for chave in dados.get("ordem_opcoes", opcoes) if chave in opcoes]
    return [a for a in opcoes[:MAX_ALTERNATIVAS] if isinstance(a, dict)] if isinstance(opcoes, list) else []


def _questoes_tela(dados):
    questoes = []
    for questao in dados.get("questoes", [])[:MAX_QUESTOES]:
        if not isinstance(questao, dict):
            continue
        opcoes = questao.get("alternativas")
        opcoes = opcoes[:MAX_ALTERNATIVAS] if isinstance(opcoes, list) else []
        questoes.append({**questao, "alternativas": [a for a in opcoes if isinstance(a, dict)]})
    return questoes


@catalogo.get("/<secao>")
@_proteger_operacao
def listar(secao):
    estado = request.args.get("estado", "")
    busca = request.args.get("busca", "").strip()[:100]
    pagina_texto = request.args.get("pagina", "1")
    if estado and estado not in ESTADOS:
        abort(400, description="Filtro de estado inválido.")
    if not pagina_texto.isascii() or not pagina_texto.isdecimal() or not 1 <= len(pagina_texto) <= 6:
        abort(400, description="Página inválida.")
    pagina = max(1, int(pagina_texto))
    itens, total = db.listar_itens(secao, estado=estado, busca=busca, pagina=pagina)
    ultima = max(1, (total + 19) // 20)
    if pagina > ultima:
        return redirect(url_for(".listar", secao=secao, estado=estado, busca=busca, pagina=ultima))
    return render_template(
        "administracao/catalogo.html", secao=secao, secoes=SECOES, estados=ESTADOS, estado=estado,
        busca=busca, pagina=pagina, ultima=ultima, itens=itens, total=total, url_publica=_url_publica,
    )


@catalogo.route("/<secao>/novo", methods=["GET", "POST"])
@catalogo.route("/<secao>/<int:item_id>/editar", methods=["GET", "POST"])
@_proteger_operacao
def editar(secao, item_id=None):
    request.max_content_length = 1024 * 1024
    formulario = FlaskForm()
    item = db.obter_item(secao, item_id) if item_id is not None else None
    if item and item["estado"] == "removida":
        abort(409, description="Restaure o item antes de editar.")

    dados = item["dados"] if item else {}
    slug = item["slug"] if item else ""
    if not item and secao == "quizzes":
        dados = {"questoes": [{"alternativas": [{}, {}]}]}
    if not item and secao == "simulacoes":
        dados = {"opcoes": [{}, {}]}

    mensagem, status = None, 200
    revisao = item["revisao"] if item else None
    if request.method == "POST":
        try:
            campos = _campos(secao) | ({"revisao"} if item else ({"slug"} if secao != "quizzes" else set()))
            _validar_formulario(formulario, campos)
            if item:
                revisao = _revisao()
            else:
                slug = request.form.get("slug", "")
            dados = _ler_dados(secao)
            salvo = db.salvar_rascunho(
                current_user.id, secao, dados, slug=slug, item_id=item_id, revisao=revisao,
            )
        except DadosInvalidos as erro:
            mensagem, status = str(erro), 400
        except db.EdicaoConflitante as erro:
            mensagem, status = str(erro), 409
        else:
            flash("Rascunho salvo. A publicação não foi alterada.", "administracao_sucesso")
            return redirect(url_for(".editar", secao=secao, item_id=salvo), code=303)

    return render_template(
        "administracao/editor_catalogo.html", formulario=formulario, secoes=SECOES,
        secao=secao, estados=ESTADOS, item=item, revisao=revisao, dados=dados, slug=slug,
        canais=CANAIS, questoes=_questoes_tela(dados) if secao == "quizzes" else [],
        opcoes=_opcoes_tela(dados) if secao == "simulacoes" else [],
        mensagem=mensagem, max_questoes=MAX_QUESTOES, max_alternativas=MAX_ALTERNATIVAS,
    ), status


@catalogo.get("/<secao>/<int:item_id>/previa")
@_proteger_operacao
def previa(secao, item_id):
    item = db.obter_item(secao, item_id)
    dados = item["dados"]
    corpo = None
    if secao in {"conteudos", "paginas"}:
        corpo = html_do_texto(dados.get("corpo", "")) if item["rascunho"] else item["texto"]
    return render_template(
        "administracao/previa_catalogo.html", secao=secao, secoes=SECOES, item=item,
        dados=dados, corpo=corpo, opcoes=_opcoes_tela(dados) if secao == "simulacoes" else [],
        url_publica=_url_publica(secao, item),
    )


@catalogo.route("/<secao>/<int:item_id>/<any(publicar,despublicar,remover,restaurar):acao>", methods=["GET", "POST"])
@_proteger_operacao
def confirmar(secao, item_id, acao):
    request.max_content_length = 8192
    formulario = FlaskForm()
    item = db.obter_item(secao, item_id)
    mensagem, status = None, 200
    if request.method == "POST":
        try:
            _validar_formulario(formulario, {"revisao"})
            db.alterar_publicacao(current_user.id, secao, item_id, _revisao(), acao)
        except DadosInvalidos as erro:
            mensagem, status = str(erro), 400
        except db.EdicaoConflitante as erro:
            mensagem, status = str(erro), 409
        else:
            flash({
                "publicar": "Item publicado e disponível aos usuários.",
                "despublicar": "Item despublicado. O histórico foi mantido.",
                "remover": "Item removido da gestão ativa.",
                "restaurar": "Item restaurado como despublicado.",
            }[acao], "administracao_sucesso")
            estado = "arquivada" if acao == "restaurar" else ""
            return redirect(url_for(".listar", secao=secao, estado=estado), code=303)
    elif acao == "publicar" and item["rascunho"]:
        try:
            validar(secao, item["dados"], publicar=True)
        except DadosInvalidos as erro:
            mensagem = str(erro)
    return render_template(
        "administracao/confirmar_catalogo.html", formulario=formulario, secao=secao, secoes=SECOES,
        item=item, acao=acao, rotulo=ACOES[acao][0], explicacao=ACOES[acao][1], mensagem=mensagem,
    ), status
