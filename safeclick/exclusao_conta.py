import re

from flask import Blueprint, current_app, flash, redirect, render_template, request, session, url_for
from flask_login import current_user, logout_user
from flask_wtf import FlaskForm
from psycopg import Error
from werkzeug.security import check_password_hash
from wtforms import BooleanField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Length

from safeclick.emails import enviar_email
from safeclick.modelo_email import montar_email
from safeclick.exclusao_conta_db import (
    ContaJaExcluida,
    agendar_exclusao,
    aplicar_prazos,
    buscar_dados_exclusao,
    desvincular_autenticador,
    gerar_novo_link,
    reativar_conta,
    registrar_recusa,
)
from safeclick.limites import permitir_tentativa
from safeclick.recuperacao import _base_publica
from safeclick.sessoes import exigir_perfis
from safeclick.twilio_api import remover_fator_totp


exclusao_conta = Blueprint("exclusao_conta", __name__, url_prefix="/conta")

reativacao_conta = Blueprint("reativacao_conta", __name__)

INDISPONIVEL = "Não foi possível excluir a conta agora. Nada foi alterado. Tente novamente em instantes."


class FormularioExcluirConta(FlaskForm):
    senha = PasswordField(
        "Senha atual",
        validators=[
            DataRequired(message="Informe sua senha atual para confirmar."),
            Length(max=128, message="A senha informada é muito longa."),
        ],
    )
    ciente = BooleanField(
        "Entendo que, depois de 30 dias, a exclusão é definitiva e não pode ser desfeita.",
        default=False,
        false_values=(False, "false", "", "0", "off", "no"),
        validators=[DataRequired(message="Marque a caixa para confirmar que entendeu.")],
    )
    enviar = SubmitField("Excluir minha conta")


class FormularioReativarConta(FlaskForm):
    senha = PasswordField(
        "Senha",
        validators=[
            DataRequired(message="Informe sua senha para reativar a conta."),
            Length(max=128, message="A senha informada é muito longa."),
        ],
    )
    enviar = SubmitField("Reativar minha conta")


def concluir_exclusoes_vencidas():
    try:
        aplicar_prazos()
    except (Error, RuntimeError):
        current_app.logger.exception("Falha ao concluir as exclusões vencidas")


def _link_reativacao(token):
    return f"{_base_publica()}{url_for('reativacao_conta.reativar')}#token={token}"


def _montar_link(dados, assunto, abertura):
    return montar_email(
        "Exclusão de conta",
        assunto.removeprefix("SafeClick - "),
        [abertura,
         f"Depois de {dados['excluir_em']}, seu nome e sua senha serão apagados de vez e a conta "
         "não poderá mais ser recuperada. Seu e-mail ficará guardado por mais 6 meses, "
         "visível só para a administração, e depois também será apagado.",
         f"Se mudar de ideia, abra o link abaixo até {dados['excluir_em']} "
         "e confirme com a sua senha para reativar a conta."],
        botao=("Reativar conta", _link_reativacao(dados["token"])),
        aviso=("Não pediu a exclusão?", "Reative a conta pelo link e troque a sua senha."),
    )


def _enviar_link(dados, assunto, abertura):
    try:
        texto, html = _montar_link(dados, assunto, abertura)
        enviar_email(dados["email"], assunto, texto, html=html)
    except Exception:
        current_app.logger.error("Link de reativação não enviado.")
        return False
    return True


def avisar_conta_agendada(usuario_id):
    dados = gerar_novo_link(usuario_id)
    if dados is None:
        return None

    enviado = _enviar_link(
        dados,
        "SafeClick - Link para reativar sua conta",
        "Recebemos uma tentativa de entrar na sua conta do SafeClick, que está com a "
        f"exclusão marcada para {dados['excluir_em']}. Se não foi você, reative a conta "
        "e troque a sua senha.",
    )
    if not enviado:
        return (
            f"Esta conta está com a exclusão marcada para {dados['excluir_em']}, mas não "
            "conseguimos enviar o link de reativação agora. Tente entrar de novo em instantes.",
            503,
        )
    return (
        f"Esta conta está com a exclusão marcada para {dados['excluir_em']}. Enviamos para o "
        "seu e-mail um link para reativá-la. Confira também o spam.",
        403,
    )


@exclusao_conta.before_request
@exigir_perfis("usuario", "administrador")
def verificar_acesso():
    return None


@exclusao_conta.route("/excluir", methods=["GET", "POST"])
def excluir():
    formulario = FormularioExcluirConta()
    erro = None
    status = 200

    if request.method == "POST":
        if not formulario.validate_on_submit():
            status = 400
        else:
            erro, status, dados = _tentar_excluir(int(current_user.id), formulario.senha.data)
            if erro is None:
                enviado = _enviar_link(
                    dados,
                    f"SafeClick - Sua conta será excluída em {dados['excluir_em']}",
                    "Recebemos o pedido de exclusão da sua conta no SafeClick. "
                    "O acesso foi encerrado em todos os dispositivos.",
                )
                session.clear()
                logout_user()
                aviso = (
                    "Enviamos para o seu e-mail um link para reativá-la, caso mude de ideia."
                    if enviado else
                    "Não conseguimos enviar o e-mail agora: se mudar de ideia, entre com seu "
                    "e-mail e sua senha para receber o link de reativação."
                )
                flash(
                    f"Sua conta foi desativada e será excluída em {dados['excluir_em']}. {aviso}",
                    "sucesso",
                )
                return redirect(url_for("autenticacao.login"), code=303)

    return render_template("conta/excluir.html", formulario=formulario, erro=erro), status


def _tentar_excluir(usuario_id, senha):
    try:
        if not permitir_tentativa("exclusao_conta", usuario_id, 5):
            return "Muitas tentativas. Aguarde 5 minutos e tente novamente.", 429, None
        conta = buscar_dados_exclusao(usuario_id)
    except (Error, RuntimeError):
        current_app.logger.exception("Falha ao preparar a exclusão da conta")
        return INDISPONIVEL, 503, None

    if conta is None:
        return "Esta conta já foi excluída.", 409, None

    if not check_password_hash(conta["senha_hash"], senha):
        _registrar_recusa(usuario_id, "senha_incorreta")
        return "Senha incorreta. Sua conta não foi excluída.", 400, None

    if conta["unico_administrador"]:
        _registrar_recusa(usuario_id, "unico_administrador")
        return (
            "Você é o único administrador do SafeClick. Antes de excluir a conta, "
            "outra pessoa precisa receber o perfil de administrador.",
            409,
            None,
        )

    if conta["mfa_fator_sid"]:
        try:
            remover_fator_totp(conta["mfa_identidade"], conta["mfa_fator_sid"], usuario_id=usuario_id)
        except RuntimeError:
            current_app.logger.warning("Fator não removido na Twilio (conta %s)", usuario_id)
            return (
                "Não foi possível desvincular o aplicativo autenticador agora. "
                "Sua conta não foi excluída. Tente novamente em instantes.",
                503,
                None,
            )

    try:
        dados = agendar_exclusao(usuario_id)
    except ContaJaExcluida:
        return "Esta conta já foi excluída.", 409, None
    except (Error, RuntimeError):
        current_app.logger.exception("Falha ao excluir a conta %s", usuario_id)
        if conta["mfa_fator_sid"]:
            try:
                desvincular_autenticador(usuario_id)
            except (Error, RuntimeError):
                current_app.logger.exception("Falha ao desvincular o autenticador da conta %s", usuario_id)
            return (
                "Não foi possível concluir a exclusão e sua conta continua ativa. "
                "O aplicativo autenticador foi desvinculado: no próximo login, configure-o de novo "
                "ou peça ajuda ao administrador.",
                503,
                None,
            )
        return INDISPONIVEL, 503, None

    return None, 200, dados


def _registrar_recusa(usuario_id, motivo):
    try:
        registrar_recusa(usuario_id, motivo)
    except (Error, RuntimeError):
        current_app.logger.exception("Falha ao registrar a recusa da exclusão")


@reativacao_conta.after_request
def proteger_resposta(resposta):
    resposta.headers["Cache-Control"] = "no-store"
    resposta.headers["Referrer-Policy"] = "no-referrer"
    resposta.headers["X-Robots-Tag"] = "noindex, nofollow"
    return resposta


@reativacao_conta.route("/reativar-conta", methods=["GET", "POST"])
def reativar():
    formulario = FormularioReativarConta()
    erro = None
    status = 200
    link_invalido = False
    token = request.form.get("token_reativacao", "") if request.method == "POST" else ""
    if not re.fullmatch(r"[A-Za-z0-9_-]{43}", token):
        token = ""

    if formulario.validate_on_submit():
        try:
            ip = request.remote_addr or "desconhecido"
            if not (
                permitir_tentativa("reativacao_ip", ip, 5)
                and permitir_tentativa("reativacao_link", token, 5)
            ):
                erro = "Muitas tentativas. Aguarde 5 minutos e tente novamente."
                status = 429
            else:
                concluir_exclusoes_vencidas()
                resultado = reativar_conta(token, formulario.senha.data)
                if resultado is None:
                    link_invalido = True
                elif resultado.get("senha_incorreta"):
                    erro = "Senha incorreta. A conta continua desativada."
                    status = 400
                else:
                    _avisar_reativacao(resultado["email"])
                    session.clear()
                    flash(
                        "Sua conta foi reativada! Entre com seu e-mail e sua senha. Como o "
                        "aplicativo autenticador foi desvinculado, você vai configurá-lo de novo.",
                        "sucesso",
                    )
                    return redirect(url_for("autenticacao.login"), code=303)
        except (Error, RuntimeError):
            current_app.logger.exception("Falha ao reativar a conta")
            erro = "Não foi possível reativar a conta agora. Tente novamente em instantes."
            status = 503
    elif request.method == "POST":
        status = 400

    if link_invalido:
        token = ""
        erro = (
            "Este link é inválido, já foi usado ou o prazo de 30 dias acabou. "
            "Se ainda estiver no prazo, entre com seu e-mail e senha para receber um novo link."
        )
        status = 400

    return render_template(
        "conta/reativar.html",
        formulario=formulario,
        erro=erro,
        token_reativacao=token,
        link_invalido=link_invalido,
    ), status


def _avisar_reativacao(email):
    try:
        texto, html = montar_email(
            "Sua conta",
            "Sua conta foi reativada",
            ["Sua conta do SafeClick foi reativada e não será mais excluída. "
             "Para entrar, use seu e-mail e sua senha. Como o aplicativo autenticador foi "
             "desvinculado na exclusão, o sistema vai pedir para configurá-lo de novo."],
            aviso=("Não foi você?", "Troque sua senha pela opção \"Esqueci minha senha\" e fale com "
                   "a equipe pelo canal informado na Política de Privacidade."),
        )
        enviar_email(email, "SafeClick - Sua conta foi reativada", texto, html=html)
    except Exception:
        current_app.logger.error("Aviso de conta reativada não enviado.")
