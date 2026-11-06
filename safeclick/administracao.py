from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user
from flask_wtf import FlaskForm
from psycopg import Error

from safeclick import contas_db
from safeclick.painel import FUSO_BRASILIA
from safeclick.sessoes import exigir_perfis
from safeclick.twilio_api import remover_fator_totp
from safeclick.catalogo_admin import catalogo
from safeclick.catalogo_validacao import SECOES
from safeclick.formularios_administracao import FormularioNovoCenario
from safeclick.simulacoes_db import (
    SimulacaoDuplicada,
    criar_rascunho_simulacao,
    listar_simulacoes_administrativas,
)


administracao = Blueprint("administracao", __name__, url_prefix="/administracao")
administracao.register_blueprint(catalogo)

ESTADOS = {
    "rascunho": "Rascunho",
    "publicada": "Publicado",
    "arquivada": "Arquivado",
}

TIPOS = {
    "email": "E-mail",
    "sms": "SMS",
    "conversa": "Conversa",
    "loja": "Loja",
}


@administracao.before_request
@exigir_perfis("administrador")
def verificar_acesso_administracao():
    
    return None


@administracao.get("/")
def inicio():
    return render_template("administracao/inicio_catalogo.html", secoes=SECOES)


@administracao.get("/simulacoes")
def listar_simulacoes():
    if (
        set(request.args) - {"estado", "pagina"}
        or any(len(request.args.getlist(campo)) != 1 for campo in request.args)
    ):
        abort(400, description="Filtros inválidos.")

    estado = request.args.get("estado", "")
    pagina_texto = request.args.get("pagina", "1")
    if estado and estado not in ESTADOS:
        abort(400, description="Estado inválido.")
    if (
        not 1 <= len(pagina_texto) <= 7
        or not pagina_texto.isascii()
        or not pagina_texto.isdecimal()
        or not 1 <= int(pagina_texto) <= 1000000
    ):
        abort(400, description="Página inválida.")

    pagina = int(pagina_texto)
    por_pagina = 20
    try:
        registros, total = listar_simulacoes_administrativas(
            estado=estado, pagina=pagina, por_pagina=por_pagina
        )
    except (Error, RuntimeError):
        abort(503, description="Não foi possível carregar os cenários agora. Tente novamente em instantes.")

    ultima_pagina = max(1, (total + por_pagina - 1) // por_pagina)
    if pagina > ultima_pagina:
        abort(404, description="Página não encontrada.")

    return render_template(
        "administracao/simulacoes.html",
        registros=registros,
        total=total,
        estado=estado,
        estados=ESTADOS,
        tipos=TIPOS,
        pagina=pagina,
        ultima_pagina=ultima_pagina,
    )


@administracao.route("/simulacoes/novo", methods=["GET", "POST"])
def novo_cenario():
    request.max_content_length = 16384
    formulario = FormularioNovoCenario()
    erro = None
    status = 200

    if request.method == "POST":
        permitidos = {"csrf_token", "titulo", "slug", "tipo", "resumo"}
        if (
            set(request.form) != permitidos
            or any(len(request.form.getlist(campo)) != 1 for campo in permitidos)
            or request.files
        ):
            erro = "Confira os campos e envie o formulário novamente."
            status = 400
        elif not formulario.validate_on_submit():
            erro = "Confira os campos indicados. Se a sessão do formulário expirou, recarregue a página."
            status = 400
        else:
            try:
                criar_rascunho_simulacao(
                    current_user.id,
                    titulo=formulario.titulo.data,
                    slug=formulario.slug.data,
                    tipo=formulario.tipo.data,
                    resumo=formulario.resumo.data,
                )
            except SimulacaoDuplicada:
                formulario.slug.errors.append("Já existe um cenário com esse endereço. Escolha outro.")
                erro = "Escolha outro endereço para o cenário."
                status = 409
            except PermissionError:
                abort(403, description="Você não tem permissão para cadastrar cenários.")
            except (Error, RuntimeError, ValueError):
                erro = "Não foi possível confirmar o cadastro. Consulte a listagem antes de tentar novamente."
                status = 503
            else:
                flash("Cenário salvo como rascunho. Ele ainda não aparece no catálogo dos usuários.", "administracao_sucesso")
                return redirect(url_for("administracao.listar_simulacoes", estado="rascunho"), code=303)

    return render_template(
        "administracao/novo_cenario.html", formulario=formulario, erro=erro
    ), status


POR_PAGINA_CONTAS = 20


def _situacao_autenticador(conta):
    if conta["autenticador_ativo"]:
        return "ativo", "Ativo"
    if conta["tem_autenticador"]:
        return "pendente", "QR Code gerado, ainda não ativado"
    return "sem", "Não configurado"


def _preparar_conta(conta):
    situacao, rotulo = _situacao_autenticador(conta)
    return {
        **conta,
        "criado_em": conta["criado_em"].astimezone(FUSO_BRASILIA),
        "situacao": situacao,
        "situacao_rotulo": rotulo,
        "propria": conta["id"] == int(current_user.id),
    }


@administracao.get("/contas")
def listar_contas():
    if (
        set(request.args) - {"busca", "pagina"}
        or any(len(request.args.getlist(campo)) != 1 for campo in request.args)
    ):
        abort(400, description="Filtros inválidos.")

    busca = request.args.get("busca", "").strip()[:100]
    pagina_texto = request.args.get("pagina", "1")
    if not (1 <= len(pagina_texto) <= 7 and pagina_texto.isascii() and pagina_texto.isdecimal()):
        abort(400, description="Página inválida.")
    pagina = int(pagina_texto)
    if not 1 <= pagina <= 1000000:
        abort(400, description="Página inválida.")

    try:
        contas, total = contas_db.listar_contas(busca=busca, pagina=pagina, por_pagina=POR_PAGINA_CONTAS)
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