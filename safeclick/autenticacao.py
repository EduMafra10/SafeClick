import secrets

from flask import (
    Blueprint,
    abort,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from flask_login import current_user, login_required, login_user, logout_user
from psycopg import Error
from psycopg.errors import UniqueViolation
from werkzeug.security import check_password_hash, generate_password_hash
from safeclick.auditoria_db import registrar_evento
from safeclick.limites import permitir_tentativa

from safeclick.formularios import (
    FormularioCadastro,
    FormularioLogin,
    FormularioMFA,
    FormularioConfigurarMFA,
    FormularioSair,
)

from safeclick.logins_db import buscar_login_pendente, iniciar_login_pendente
from safeclick.mfa import (
    ErroMFA,
    configurar_autenticador,
    confirmar_autenticador,
)

from safeclick.sessoes import Usuario, criar_sessao, revogar_sessao
from safeclick.usuarios_db import (
    buscar_mfa_por_usuario,
    buscar_usuario_por_email,
    criar_usuario,
)

autenticacao = Blueprint("autenticacao", __name__)

# tambem realiza a comparacao com de hash quando o email nao existe
_HASH_LOGIN = generate_password_hash(secrets.token_urlsafe(32), method="scrypt")


def _registrar_falha_login(etapa, motivo, usuario_id=None):
    # Registra a etapa e o motivo sem guardar dados informados no formulário.
    registrar_evento(
        usuario_id=usuario_id,
        evento="login.falha",
        resultado="falha",
        recurso_tipo="autenticacao",
        detalhes={"etapa": etapa, "motivo": motivo},
    )

@autenticacao.after_request
def evitar_cache_autenticacao(resposta):
    resposta.headers["Cache-Control"] = "no-store"
    return resposta

@autenticacao.route("/cadastro", methods=["GET", "POST"])
def cadastro():
    formulario = FormularioCadastro()
    erro = None
    status = 200

    # valida os campos e o token CSRF antes de gravar no banco
    if formulario.validate_on_submit():
        try:
            criar_usuario(
                formulario.nome.data,
                formulario.email.data,
                formulario.senha.data,
            )
        except UniqueViolation:
            formulario.email.errors.append(
                "Não foi possível usar este e-mail. Confira os dados informados"
            )
            status = 409
        except (Error, RuntimeError):
            erro = "Não foi possível concluir o cadastro. Tente novamente em instantes"
            status = 503
        else:
            # o redirecionamento evita reenviar o cadastro se atualizarem a pagina
            flash("Cadastro realizado com sucesso!", "sucesso")
            return redirect(url_for("autenticacao.cadastro"), code=303)
    
    elif request.method == "POST":
        status = 400

    return render_template(
        "autenticacao/cadastro.html",
        formulario = formulario,
        erro = erro,
    ), status

@autenticacao.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("simulacoes.conta_bloqueada"))

    formulario = FormularioLogin()
    erro = None
    status = 200

    if formulario.validate_on_submit():
        session.pop("login_pendente", None)
        try:
            if not permitir_tentativa("login", formulario.email.data, 5):
                _registrar_falha_login("senha", "limite_tentativas")
                return render_template(
                    "autenticacao/login.html",
                    formulario=formulario,
                    erro="Muitas tentativas. Aguarde cinco minutos e tente novamente.",
                ), 429

            usuario = buscar_usuario_por_email(formulario.email.data)
            senha_hash = usuario["senha_hash"] if usuario else _HASH_LOGIN
            senha_valida = check_password_hash(
                senha_hash,
                formulario.senha.data,
            )

            if usuario is None or not senha_valida:
                _registrar_falha_login("senha", "credenciais_invalidas")
                erro = "E-mail ou senha inválidos."
                status = 401
            else:
                token = iniciar_login_pendente(usuario["id"])

                if token is None:
                    _registrar_falha_login("senha", "limite_tentativas", usuario["id"])
                    erro = "Aguarde alguns minutos e tente entrar novamente."
                    status = 429
                else:
                    # guarda somente a pendencia, o usuário ainda não esta autenticado
                    session.clear()
                    session["login_pendente"] = token

                    return redirect(
                        url_for("autenticacao.autenticador"),
                        code=303,
                    )

        except (Error, RuntimeError, ValueError):
            erro = "Não foi possível iniciar o login. Tente novamente em instantes."
            status = 503

    elif request.method == "POST":
        status = 400

    return render_template(
        "autenticacao/login.html",
        formulario=formulario,
        erro=erro,
    ), status


def _tela_autenticador(
    formulario=None,
    erro=None,
    status=200,
    configuracao=None,
):
    token = session.get("login_pendente")

    try:
        pendencia = buscar_login_pendente(token)
        usuario = (
            buscar_mfa_por_usuario(pendencia["usuario_id"])
            if pendencia
            else None
        )
    except (Error, RuntimeError):
        abort(
            503,
            description="Não foi possível verificar o login. Tente novamente em instantes.",
        )

    if pendencia is None or usuario is None:
        session.pop("login_pendente", None)
        flash(
            "Informe novamente seu e-mail e sua senha para continuar.",
            "aviso",
        )
        return redirect(url_for("autenticacao.login"), code=303)

    formulario_configuracao = FormularioConfigurarMFA(prefix="configurar")
    formulario_configuracao.fator_anterior.data = (
        usuario["mfa_fator_sid"] or ""
    )

    return render_template(
        "autenticacao/autenticador.html",
        formulario=formulario if formulario is not None else FormularioMFA(),
        formulario_configuracao=formulario_configuracao,
        usuario=usuario,
        configuracao=configuracao,
        erro=erro,
        limite_atingido=pendencia["tentativas"] >= 5,
    ), status


@autenticacao.route("/login/autenticador", methods=["GET", "POST"])
def autenticador():
    if current_user.is_authenticated:
        return redirect(url_for("simulacoes.conta_bloqueada"))

    formulario = FormularioMFA()

    if formulario.validate_on_submit():
        usuario_id_pendente = None
        try:
            pendencia = buscar_login_pendente(session.get("login_pendente"))
            if pendencia is not None:
                usuario_id_pendente = pendencia["usuario_id"]

            usuario = confirmar_autenticador(
                session.get("login_pendente"),
                formulario.codigo.data,
            )

            if usuario is not None:
                token_sessao = criar_sessao(usuario["id"])

        except ErroMFA as erro:
            if erro.status < 500:
                try:
                    _registrar_falha_login(
                        "autenticador", "codigo_ou_prazo_rejeitado", usuario_id_pendente
                    )
                except (Error, RuntimeError):
                    abort(503, description="Não foi possível registrar a tentativa de login.")
            return _tela_autenticador(
                formulario,
                str(erro),
                erro.status,
            )
        except (Error, RuntimeError):
            return _tela_autenticador(
                formulario,
                "Não foi possível verificar o código. Tente novamente em instantes.",
                503,
            )

        if usuario is None:
            flash(
                "Autenticador ativado. Aguarde o próximo código do aplicativo para entrar.",
                "aviso",
            )
            return redirect(
                url_for("autenticacao.autenticador"),
                code=303,
            )

        session.clear()
        session["sessao_token"] = token_sessao
        login_user(Usuario(usuario), remember=False, fresh=True)

        flash("Login realizado com sucesso!", "sucesso")

        return redirect(url_for("simulacoes.conta_bloqueada"), code=303)

    return _tela_autenticador(
        formulario,
        status=400 if request.method == "POST" else 200,
    )


@autenticacao.post("/login/autenticador/configurar")
def configurar_mfa():
    if current_user.is_authenticated:
        return redirect(url_for("simulacoes.conta_bloqueada"))

    formulario = FormularioConfigurarMFA(prefix="configurar")

    if not formulario.validate_on_submit():
        return _tela_autenticador(
            erro="Recarregue a página e tente configurar novamente.",
            status=400,
        )

    try:
        configuracao = configurar_autenticador(
            session.get("login_pendente"),
            formulario.fator_anterior.data,
        )
    except ErroMFA as erro:
        return _tela_autenticador(
            erro=str(erro),
            status=erro.status,
        )
    except (Error, RuntimeError):
        return _tela_autenticador(
            erro="Não foi possível configurar o autenticador. Tente novamente em instantes.",
            status=503,
        )

    return _tela_autenticador(configuracao=configuracao)

@autenticacao.app_context_processor
def disponibilizar_formulario_saida():
    if current_user.is_authenticated:
        return {"formulario_saida": FormularioSair()}
    return {}

@autenticacao.post("/sair")
@login_required
def sair():
    formulario = FormularioSair()

    if not formulario.validate_on_submit():
        abort(
            400,
            description="Recarregue a página e tente sair novamente.",
        )

    try:
        revogar_sessao()
    except (Error, RuntimeError):
        abort(
            503,
            description="Não foi possível sair. Tente novamente em instantes.",
        )

    session.clear()
    logout_user()
    flash("Você saiu da sua conta.", "sucesso")

    return redirect(url_for("autenticacao.login"), code=303)
