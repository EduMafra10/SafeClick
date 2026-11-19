from datetime import datetime

from flask import Blueprint, Response, abort, current_app, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user
from flask_wtf import FlaskForm
from psycopg import Error
from wtforms import PasswordField, TextAreaField
from wtforms.validators import DataRequired, Length

from safeclick import auditoria_textos, contas_db
from safeclick.auditoria_db import registrar_evento
from safeclick.avaliacoes_db import contar_pendentes, listar_resumo_avaliacoes
from safeclick.emails import enviar_email
from safeclick.modelo_email import montar_email
from safeclick.formularios import limpar_texto
from safeclick.limites import permitir_tentativa
from safeclick.mascara import TELAS_EMAIL
from safeclick.painel import FUSO_BRASILIA
from safeclick.recuperacao import _agendar
from safeclick.sessoes import exigir_perfis
from safeclick.twilio_api import remover_fator_totp
from safeclick.catalogo_admin import catalogo
from safeclick.catalogo_validacao import SECOES
from safeclick.visao_geral_excel import gerar_planilha
from safeclick.visao_geral_db import MINIMO_RESPOSTAS_QUESTAO, PERIODOS, buscar_visao_geral


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


def _consultar_visao_geral(dias):
    agora = datetime.now(FUSO_BRASILIA)
    dados = buscar_visao_geral(dias, agora.date(), incluir_avaliacoes=current_app.config['AVALIACOES_ATIVAS'])
    avaliadas = [item for item in dados.get('avaliacoes') or [] if item['total']]
    avaliacoes = (
        sorted(avaliadas, key=lambda item: (item['media'], item['titulo']))[:5]
        if current_app.config['AVALIACOES_ATIVAS'] else None
    )
    atualizado_em = dados.get('atualizado_em') or agora
    return dados, avaliacoes, sum(item['media'] < 3 for item in avaliadas), atualizado_em.astimezone(FUSO_BRASILIA)


@administracao.get("/")
def inicio():
    dias = _ler_periodo()
    try:
        dados, avaliacoes, notas_baixas, atualizado_em = _consultar_visao_geral(dias)
    except (Error, RuntimeError):
        current_app.logger.exception("Falha ao carregar a visão geral")
        abort(503, description="Não foi possível carregar os indicadores agora. Tente novamente em instantes.")

    contexto = _contexto_visao_geral(dados, avaliacoes, notas_baixas)
    return render_template('administracao/visao_geral.html', atualizado_em=atualizado_em, **contexto)


def _contexto_visao_geral(dados, avaliacoes, notas_baixas):
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
    return dict(dados=dados, periodos=PERIODOS, eventos=eventos, grafico=grafico, avaliacoes=avaliacoes,
                notas_baixas=notas_baixas, rotulos_atividade=ROTULOS_ATIVIDADE, minimo_respostas=MINIMO_RESPOSTAS_QUESTAO)


@administracao.get('/visao-geral/dados')
def atualizar_visao_geral():
    dias = _ler_periodo()
    try:
        dados, avaliacoes, notas_baixas, atualizado_em = _consultar_visao_geral(dias)
    except (Error, RuntimeError):
        current_app.logger.exception('Falha ao atualizar a visão geral')
        return {'erro': 'Não foi possível atualizar os indicadores.'}, 503, {'Cache-Control': 'no-store'}
    html = render_template('administracao/_visao_geral_painel.html',
                           **_contexto_visao_geral(dados, avaliacoes, notas_baixas))
    return {'html': html, 'atualizado_em': atualizado_em.isoformat(),
            'horario': atualizado_em.strftime('%d/%m/%Y às %H:%M:%S')}, 200, {'Cache-Control': 'no-store'}


@administracao.get("/visao-geral.xlsx")
def exportar_visao_geral():
    dias = _ler_periodo()
    agora = datetime.now(FUSO_BRASILIA)
    try:
        dados, avaliacoes, _, _ = _consultar_visao_geral(dias)
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


@administracao.get("/avaliacoes/pendentes")
def notificacoes_avaliacoes():
    if not current_app.config["AVALIACOES_ATIVAS"]:
        abort(404)
    try:
        total = contar_pendentes()
    except (Error, RuntimeError):
        return {"erro": "Não foi possível consultar as avaliações pendentes."}, 503, {"Cache-Control": "no-store"}
    return {"total": total}, 200, {"Cache-Control": "no-store"}


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

FILTROS_SITUACAO = {
    "ativas": "Ativas",
    "agendadas": "Exclusão agendada (30 dias)",
    "excluidas": "Excluídas",
}

FILTROS_ORDEM = {
    "recentes": "Mais recentes",
    "antigas": "Mais antigas",
    "nome": "Nome (A a Z)",
}


def _no_fuso(momento):
    return momento.astimezone(FUSO_BRASILIA) if momento else None


def _preparar_conta(conta):
    situacao, rotulo = _situacao_autenticador(conta)
    ultimo_acesso = conta.get("ultimo_acesso")
    return {
        **conta,
        "criado_em": conta["criado_em"].astimezone(FUSO_BRASILIA),
        "ultimo_acesso": ultimo_acesso.astimezone(FUSO_BRASILIA) if ultimo_acesso else None,
        "excluida_em": _no_fuso(conta.get("excluida_em")),
        "exclusao_marcada_para": _no_fuso(conta.get("exclusao_marcada_para")),
        "descartar_em": _no_fuso(conta.get("descartar_em")),
        "situacao": situacao,
        "situacao_rotulo": rotulo,
        "propria": conta["id"] == int(current_user.id),
    }


@administracao.get("/contas")
def listar_contas():
    if (
        set(request.args) - {"busca", "autenticador", "situacao", "ordem", "pagina"}
        or any(len(request.args.getlist(campo)) != 1 for campo in request.args)
    ):
        abort(400, description="Filtros inválidos.")

    busca = request.args.get("busca", "").strip()[:100]
    autenticador = request.args.get("autenticador") or None
    if autenticador is not None and autenticador not in FILTROS_AUTENTICADOR:
        abort(400, description="Filtros inválidos.")
    situacao = request.args.get("situacao") or "ativas"
    if situacao not in FILTROS_SITUACAO:
        abort(400, description="Filtros inválidos.")
    ordem = request.args.get("ordem") or "recentes"
    if ordem not in FILTROS_ORDEM:
        abort(400, description="Filtros inválidos.")
    pagina_texto = request.args.get("pagina", "1")
    if not (1 <= len(pagina_texto) <= 7 and pagina_texto.isascii() and pagina_texto.isdecimal()):
        abort(400, description="Página inválida.")
    pagina = int(pagina_texto)
    if not 1 <= pagina <= 1000000:
        abort(400, description="Página inválida.")

    try:
        contas, total = contas_db.listar_contas(
            busca=busca, autenticador=autenticador, situacao=situacao, ordem=ordem,
            pagina=pagina, por_pagina=POR_PAGINA_CONTAS,
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
        situacao=situacao,
        filtros_situacao=FILTROS_SITUACAO,
        ordem=ordem,
        filtros_ordem=FILTROS_ORDEM,
        pagina=pagina,
        ultima_pagina=ultima_pagina,
    )


@administracao.post("/contas/<int:usuario_id>/email")
def revelar_email(usuario_id):
    request.max_content_length = 4096
    tela = request.form.get("tela", "")
    if set(request.form) != {"csrf_token", "tela"} or tela not in TELAS_EMAIL or not FlaskForm().validate_on_submit():
        abort(400, description="O formulário expirou. Recarregue a página e tente novamente.")

    try:
        email = contas_db.revelar_email(int(current_user.id), usuario_id, tela)
    except (Error, RuntimeError):
        current_app.logger.exception("Falha ao revelar o e-mail")
        abort(503, description="Não foi possível mostrar o e-mail agora.")
    if email is None:
        abort(404, description="Conta não encontrada ou e-mail já descartado.")

    cabecalhos = {"Cache-Control": "no-store"}
    if request.accept_mimetypes.best == "application/json":
        return jsonify(email=email), 200, cabecalhos
    return render_template(
        "administracao/email_revelado.html",
        secoes=SECOES,
        secao="contas",
        usuario_id=usuario_id,
        email=email,
        voltar=request.referrer if (request.referrer or "").startswith(request.host_url) else None,
    ), 200, cabecalhos


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
                return redirect(url_for("administracao.listar_contas", busca=conta["id"]), code=303)

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
                return redirect(url_for("administracao.listar_contas", busca=conta["id"]), code=303)

    return render_template(
        "administracao/alterar_perfil.html",
        formulario=formulario,
        conta=conta,
        novo_perfil=novo_perfil,
        bloqueio=bloqueio,
        mensagem=mensagem,
    ), status


class FormularioExcluirAdministrador(FlaskForm):
    senha = PasswordField("Sua senha", validators=[
        DataRequired(message="Informe a sua senha para confirmar."),
        Length(max=128, message="A senha informada é muito longa."),
    ])
    motivo = TextAreaField("Motivo da exclusão", filters=[limpar_texto], validators=[
        DataRequired(message="Explique o motivo da exclusão."),
        Length(min=10, max=300, message="Escreva o motivo com 10 a 300 caracteres."),
    ])


def _avisar_conta_excluida(email):
    texto, html = montar_email(
        "Sua conta",
        "Sua conta foi excluída",
        ["Sua conta de administrador no SafeClick foi excluída por outro administrador da equipe. "
         "Seu nome, sua senha e o vínculo com o aplicativo autenticador foram apagados, e o acesso "
         "foi encerrado em todos os dispositivos.",
         "Seu e-mail fica guardado por 6 meses, visível só para a administração, e depois é apagado."],
        aviso=("Acha que foi um engano?", "Fale com a equipe pelo canal informado na Política de Privacidade."),
    )
    enviar_email(email, "SafeClick - Sua conta foi excluída", texto, html=html)


@administracao.route("/contas/<int:usuario_id>/excluir", methods=["GET", "POST"])
def excluir_conta(usuario_id):
    """Um administrador exclui a conta de outro administrador (RF16)."""
    request.max_content_length = 4096
    formulario = FormularioExcluirAdministrador()

    try:
        conta = contas_db.obter_conta(usuario_id)
    except (Error, RuntimeError):
        abort(503, description="Não foi possível carregar a conta agora.")
    if conta is None:
        abort(404, description="Conta não encontrada.")
    conta = _preparar_conta(conta)

    bloqueio = None
    if conta["propria"]:
        bloqueio = "Para excluir a sua própria conta, use Minha conta → Excluir conta."
    elif conta["perfil"] != "administrador":
        bloqueio = (
            "Só contas de administrador são excluídas por aqui. "
            "As outras pessoas excluem a própria conta em Minha conta."
        )

    mensagem, status = bloqueio, 200
    if request.method == "POST":
        if bloqueio:
            status = 409
        elif set(request.form) != {"csrf_token", "senha", "motivo"} or not formulario.validate_on_submit():
            status = 400
        else:
            administrador_id = int(current_user.id)
            try:
                if not permitir_tentativa("exclusao_admin", str(administrador_id), 5):
                    mensagem, status = "Muitas tentativas. Aguarde cinco minutos e tente novamente.", 429
                elif not contas_db.senha_confere(administrador_id, formulario.senha.data):
                    mensagem, status = "Senha incorreta. Nada foi alterado.", 400
                else:
                    antigo = contas_db.excluir_administrador(
                        administrador_id, usuario_id, formulario.motivo.data
                    )
            except contas_db.ContaNaoEncontrada:
                abort(404, description="Conta não encontrada.")
            except contas_db.ExclusaoRecusada as erro:
                mensagem, status = str(erro), 409
            except (Error, RuntimeError):
                current_app.logger.exception("Falha ao excluir a conta de administrador")
                mensagem, status = "Não foi possível excluir agora. Nada foi alterado.", 503

            if status == 200:
                if antigo["fator_sid"]:
                    try:
                        remover_fator_totp(antigo["identidade"], antigo["fator_sid"], usuario_id=usuario_id)
                    except RuntimeError:
                        current_app.logger.warning("Fator antigo não removido na Twilio (conta %s)", usuario_id)
                if not _agendar(_avisar_conta_excluida, antigo["email"]):
                    current_app.logger.error("Aviso de conta excluída não agendado.")
                flash(
                    f"A conta de {conta['nome']} foi excluída. O e-mail fica guardado por 6 meses.",
                    "administracao_sucesso",
                )
                return redirect(url_for("administracao.listar_contas", situacao="excluidas"), code=303)

    return render_template(
        "administracao/excluir_conta.html",
        formulario=formulario,
        conta=conta,
        bloqueio=bloqueio,
        mensagem=mensagem,
    ), status
