from datetime import datetime

from flask import Blueprint, Response, abort, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user
from flask_wtf import FlaskForm
from psycopg import Error

from safeclick import auditoria_textos, contas_db
from safeclick.auditoria_db import registrar_evento
from safeclick.avaliacoes_db import listar_resumo_avaliacoes
from safeclick.painel import FUSO_BRASILIA
from safeclick.sessoes import exigir_perfis
from safeclick.twilio_api import remover_fator_totp
from safeclick.catalogo_admin import catalogo
from safeclick.catalogo_validacao import SECOES
from safeclick.visao_geral_excel import gerar_planilha
from safeclick.visao_geral_db import PERIODOS, buscar_visao_geral


administracao = Blueprint("administracao", __name__, url_prefix="/administracao")
administracao.register_blueprint(catalogo)

TIPO_EXCEL = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

ROTULOS_ATIVIDADE = {
    "conteudo": "Conteúdos concluídos",
    "quiz": "Quizzes respondidos",
    "simulacao": "Simulações feitas",
    "desafio": "Desafios de senha",
}


@administracao.before_request
@exigir_perfis("administrador")
def verificar_acesso_administracao():
    return None


@administracao.app_context_processor
def disponibilizar_menu_administrativo():
    return {"secoes_admin": SECOES}


def _ler_periodo():
    if set(request.args) - {"periodo"} or len(request.args.getlist("periodo")) > 1:
        abort(400, description="Filtros inválidos.")
    texto = request.args.get("periodo", "30")
    if texto not in {str(dias) for dias in PERIODOS}:
        abort(400, description="Período inválido.")
    return int(texto)


def _avaliacoes_mais_baixas():
    if not current_app.config["AVALIACOES_ATIVAS"]:
        return None
    avaliadas = [item for item in listar_resumo_avaliacoes() if item["total"]]
    return sorted(avaliadas, key=lambda item: (item["media"], item["titulo"]))[:5]


@administracao.get("/")
def inicio():
    dias = _ler_periodo()
    try:
        dados = buscar_visao_geral(dias, datetime.now(FUSO_BRASILIA).date())
        avaliacoes = _avaliacoes_mais_baixas()
    except (Error, RuntimeError):
        current_app.logger.exception("Falha ao carregar a visão geral")
        abort(503, description="Não foi possível carregar os indicadores agora. Tente novamente em instantes.")

    eventos = [
        {
            "hora": evento["criado_em"].astimezone(FUSO_BRASILIA),
            "titulo": auditoria_textos.titulo_evento(evento["evento"]),
            "resultado": evento["resultado"],
        }
        for evento in dados["ultimos_eventos"]
    ]
    grafico = {
        "dias": dados["atividades"]["por_dia"]["dias"],
        "series": [
            {"rotulo": ROTULOS_ATIVIDADE[tipo], "tipo": tipo, "valores": valores}
            for tipo, valores in dados["atividades"]["por_dia"]["series"].items()
        ],
    }
    return render_template(
        "administracao/visao_geral.html",
        dados=dados,
        periodos=PERIODOS,
        eventos=eventos,
        grafico=grafico,
        avaliacoes=avaliacoes,
        notas_baixas=sum(1 for item in avaliacoes or [] if item["media"] < 3),
        rotulos_atividade=ROTULOS_ATIVIDADE,
    )


@administracao.get("/visao-geral.xlsx")
def exportar_visao_geral():
    dias = _ler_periodo()
    agora = datetime.now(FUSO_BRASILIA)
    try:
        dados = buscar_visao_geral(dias, agora.date())
        avaliacoes = _avaliacoes_mais_baixas()
        registrar_evento(
            usuario_id=int(current_user.id),
            evento="visao_geral.exportada",
            resultado="sucesso",
            recurso_tipo="visao_geral",
            detalhes={"periodo_dias": dias},
        )
    except (Error, RuntimeError):
        current_app.logger.exception("Falha ao exportar a visão geral")
        abort(503, description="Não foi possível exportar os indicadores agora. Tente novamente em instantes.")

    conteudo = gerar_planilha(dados, ROTULOS_ATIVIDADE, SECOES, avaliacoes, agora)
    nome = f"safeclick-visao-geral-{dias}-dias-{agora:%Y-%m-%d}.xlsx"
    return Response(conteudo, mimetype=TIPO_EXCEL, headers={
        "Content-Disposition": f'attachment; filename="{nome}"',
        "Cache-Control": "no-store",
    })


@administracao.get("/avaliacoes")
def listar_avaliacoes():
    if not current_app.config["AVALIACOES_ATIVAS"]:
        abort(404)
    try:
        itens = listar_resumo_avaliacoes()
    except (Error, RuntimeError):
        abort(503, description="Não foi possível consultar as avaliações agora. Tente novamente em instantes.")
    return render_template("administracao/avaliacoes.html", secoes=SECOES, secao="avaliacoes", itens=itens)


# As telas antigas de simulações foram unificadas na gestão de conteúdo.
@administracao.get("/simulacoes")
def listar_simulacoes():
    return redirect(url_for("administracao.catalogo.listar", secao="simulacoes"), code=301)


@administracao.get("/simulacoes/novo")
def novo_cenario():
    return redirect(url_for("administracao.catalogo.editar", secao="simulacoes"), code=301)


POR_PAGINA_CONTAS = 20


def _situacao_autenticador(conta):
    if conta["autenticador_ativo"]:
        return "ativo", "Ativo"
    if conta["tem_autenticador"]:
        return "pendente", "QR Code gerado, ainda não ativado"
    return "sem", "Não configurado"


FILTROS_AUTENTICADOR = {
    "ativo": "Ativo",
    "pendente": "QR Code gerado, não ativado",
    "sem": "Não configurado",
}


def _preparar_conta(conta):
    situacao, rotulo = _situacao_autenticador(conta)
    ultimo_acesso = conta.get("ultimo_acesso")
    return {
        **conta,
        "criado_em": conta["criado_em"].astimezone(FUSO_BRASILIA),
        "ultimo_acesso": ultimo_acesso.astimezone(FUSO_BRASILIA) if ultimo_acesso else None,
        "situacao": situacao,
        "situacao_rotulo": rotulo,
        "propria": conta["id"] == int(current_user.id),
    }

@administracao.get("/contas")
def listar_contas():
    if (
        set(request.args) - {"busca", "autenticador", "pagina"}
        or any(len(request.args.getlist(campo)) != 1 for campo in request.args)
    ):
        abort(400, description="Filtros inválidos.")

    busca = request.args.get("busca", "").strip()[:100]
    autenticador = request.args.get("autenticador") or None
    if autenticador is not None and autenticador not in FILTROS_AUTENTICADOR:
        abort(400, description="Filtros inválidos.")
    pagina_texto = request.args.get("pagina", "1")
    if not (1 <= len(pagina_texto) <= 7 and pagina_texto.isascii() and pagina_texto.isdecimal()):
        abort(400, description="Página inválida.")
    pagina = int(pagina_texto)
    if not 1 <= pagina <= 1000000:
        abort(400, description="Página inválida.")

    try:
        contas, total = contas_db.listar_contas(
            busca=busca, autenticador=autenticador, pagina=pagina, por_pagina=POR_PAGINA_CONTAS
        )
    except (Error, RuntimeError):
        abort(503, description="Não foi possível carregar as contas agora. Tente novamente em instantes.")

    ultima_pagina = max(1, (total + POR_PAGINA_CONTAS - 1) // POR_PAGINA_CONTAS)
    if pagina > ultima_pagina:
        abort(404, description="Página não encontrada.")

    return render_template(
        "administracao/contas.html",
        secoes=SECOES,
        secao="contas",
        contas=[_preparar_conta(conta) for conta in contas],
        total=total,
        busca=busca,
        autenticador=autenticador,
        filtros_autenticador=FILTROS_AUTENTICADOR,
        pagina=pagina,
        ultima_pagina=ultima_pagina,
    )

@administracao.route("/contas/<int:usuario_id>/redefinir-autenticador", methods=["GET", "POST"])
def redefinir_autenticador(usuario_id):
    request.max_content_length = 4096
    formulario = FlaskForm()

    try:
        conta = contas_db.obter_conta(usuario_id)
    except (Error, RuntimeError):
        abort(503, description="Não foi possível carregar a conta agora.")
    if conta is None:
        abort(404, description="Conta não encontrada.")
    conta = _preparar_conta(conta)

    bloqueio = None
    if conta["propria"]:
        bloqueio = "Você não pode redefinir o próprio autenticador por aqui. Peça a outro administrador."
    elif conta["situacao"] == "sem":
        bloqueio = "Esta conta ainda não configurou o autenticador. Não há nada para redefinir."

    mensagem, status = bloqueio, 200
    if request.method == "POST":
        if bloqueio:
            status = 409
        elif set(request.form) != {"csrf_token"} or not formulario.validate_on_submit():
            mensagem, status = "O formulário expirou. Recarregue a página e tente novamente.", 400
        else:
            try:
                antigo = contas_db.redefinir_autenticador(int(current_user.id), usuario_id)
            except contas_db.ContaNaoEncontrada:
                abort(404, description="Conta não encontrada.")
            except contas_db.SemAutenticador as erro:
                mensagem, status = str(erro), 409
            except (Error, RuntimeError):
                current_app.logger.exception("Falha ao redefinir o autenticador")
                mensagem, status = "Não foi possível redefinir agora. Nada foi alterado.", 503
            else:
                # O banco já não aceita o aplicativo antigo; a remoção na Twilio é só limpeza.
                try:
                    remover_fator_totp(antigo["identidade"], antigo["fator_sid"], usuario_id=usuario_id)
                except RuntimeError:
                    current_app.logger.warning("Fator antigo não removido na Twilio (conta %s)", usuario_id)
                flash(
                    f"Autenticador de {conta['nome']} redefinido. No próximo login, "
                    "a pessoa vai configurar um novo aplicativo.",
                    "administracao_sucesso",
                )
                return redirect(url_for("administracao.listar_contas", busca=conta["email"]), code=303)

    return render_template(
        "administracao/redefinir_autenticador.html",
        secoes=SECOES,
        secao="contas",
        formulario=formulario,
        conta=conta,
        bloqueio=bloqueio,
        mensagem=mensagem,
    ), status



@administracao.route("/contas/<int:usuario_id>/perfil", methods=["GET", "POST"])
def alterar_perfil(usuario_id):
    request.max_content_length = 4096
    formulario = FlaskForm()

    try:
        conta = contas_db.obter_conta(usuario_id)
    except (Error, RuntimeError):
        abort(503, description="Não foi possível carregar a conta agora.")
    if conta is None:
        abort(404, description="Conta não encontrada.")
    conta = _preparar_conta(conta)
    novo_perfil = "usuario" if conta["perfil"] == "administrador" else "administrador"

    bloqueio = None
    if conta["propria"]:
        bloqueio = "Você não pode alterar o próprio perfil. Peça a outro administrador."
    elif novo_perfil == "administrador" and conta["situacao"] != "ativo":
        bloqueio = "Esta conta ainda não ativou o autenticador. Só contas com o autenticador ativo podem virar administradoras."

    mensagem, status = bloqueio, 200
    if request.method == "POST":
        if bloqueio:
            status = 409
        elif set(request.form) != {"csrf_token"} or not formulario.validate_on_submit():
            mensagem, status = "O formulário expirou. Recarregue a página e tente novamente.", 400
        else:
            try:
                contas_db.alterar_perfil(int(current_user.id), usuario_id, novo_perfil)
            except contas_db.ContaNaoEncontrada:
                abort(404, description="Conta não encontrada.")
            except contas_db.AlteracaoDePerfilRecusada as erro:
                mensagem, status = str(erro), 409
            except (Error, RuntimeError):
                current_app.logger.exception("Falha ao alterar o perfil")
                mensagem, status = "Não foi possível alterar o perfil agora. Nada foi alterado.", 503
            else:
                acao = "agora é administrador(a)" if novo_perfil == "administrador" else "voltou a ser usuário(a) comum"
                flash(f"{conta['nome']} {acao}.", "administracao_sucesso")
                return redirect(url_for("administracao.listar_contas", busca=conta["email"]), code=303)

    return render_template(
        "administracao/alterar_perfil.html",
        formulario=formulario,
        conta=conta,
        novo_perfil=novo_perfil,
        bloqueio=bloqueio,
        mensagem=mensagem,
    ), status