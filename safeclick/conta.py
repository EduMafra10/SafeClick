from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user
from flask_wtf import FlaskForm
from psycopg import Error
from wtforms import PasswordField, StringField
from wtforms.validators import AnyOf, DataRequired, EqualTo, Length, ValidationError

from safeclick import conta_db
from safeclick.emails import enviar_email
from safeclick.modelo_email import montar_email
from safeclick.formularios import limpar_texto
from safeclick.icones_perfil import ICONES
from safeclick.limites import permitir_tentativa
from safeclick.painel import FUSO_BRASILIA
from safeclick.politica_senha import problema_senha
from safeclick.privacidade import VERSAO_POLITICA, VERSAO_TERMOS
from safeclick.recuperacao import _agendar
from safeclick.sessoes import exigir_perfis, hash_sessao_atual

ENDPOINT_EXCLUSAO = "exclusao_conta.excluir"


conta = Blueprint("conta", __name__, url_prefix="/conta")
conta.record_once(lambda estado: estado.app.jinja_env.globals.update(icones_perfil=ICONES))


class FormularioNome(FlaskForm):
    nome = StringField("Nome completo", filters=[limpar_texto], validators=[
        DataRequired(message="Informe o seu nome."),
        Length(max=100, message="Use até 100 caracteres no nome."),
    ])


class FormularioIcone(FlaskForm):
    icone = StringField(validators=[AnyOf(["iniciais", *ICONES], message="Escolha um dos ícones da lista.")])


class FormularioSenha(FlaskForm):
    senha_atual = PasswordField("Senha atual", validators=[
        DataRequired(message="Informe a sua senha atual."),
        Length(max=128, message="A senha informada é muito longa."),
    ])
    nova_senha = PasswordField("Nova senha", validators=[
        DataRequired(message="Informe a nova senha."),
        Length(min=15, max=128, message="Use uma senha com 15 a 128 caracteres."),
    ])
    confirmar_senha = PasswordField("Confirmar nova senha", validators=[
        DataRequired(message="Confirme a nova senha."),
        EqualTo("nova_senha", message="As senhas precisam ser iguais."),
    ])

    def validate_nova_senha(self, campo):
        problema = problema_senha(campo.data, getattr(current_user, "nome", None), getattr(current_user, "email", None))
        if problema:
            raise ValidationError(problema)


@conta.before_request
@exigir_perfis("usuario", "administrador")
def verificar_acesso_conta():
    request.max_content_length = 8 * 1024


@conta.after_request
def proteger_resposta_conta(resposta):
    resposta.headers["Cache-Control"] = "no-store"
    return resposta


def _id():
    return int(current_user.id)


def _sessao():
    sessao = hash_sessao_atual()
    if sessao is None:
        abort(401)
    return sessao


def _campos_validos(formulario, campos):
    return set(request.form) == {"csrf_token", *campos} and formulario.validate_on_submit()


def _pagina(status=200, *, formulario_nome=None, formulario_senha=None, erro_senha=None, erro=None):
    try:
        dados = conta_db.buscar_conta(_id(), _sessao())
    except conta_db.ContaIndisponivel:
        abort(404)
    except (Error, RuntimeError):
        abort(503, description="Não foi possível carregar sua conta agora. Tente novamente em instantes.")
    formulario_nome = formulario_nome or FormularioNome(data={"nome": dados["nome"]})
    aceite_em = dados["aceito_em"].astimezone(FUSO_BRASILIA) if dados["aceito_em"] else None
    endereco_exclusao = url_for(ENDPOINT_EXCLUSAO) if ENDPOINT_EXCLUSAO else None
    return render_template(
        "conta/minha_conta.html", dados=dados, icones=ICONES,
        formulario_nome=formulario_nome, formulario_icone=FormularioIcone(),
        formulario_senha=formulario_senha or FormularioSenha(), formulario_sessoes=FlaskForm(),
        erro_senha=erro_senha, erro=erro, versao_politica=VERSAO_POLITICA, versao_termos=VERSAO_TERMOS,
        aceite_em=aceite_em, endereco_exclusao=endereco_exclusao,
    ), status


@conta.get("/")
def exibir():
    return _pagina()


@conta.post("/nome")
def salvar_nome():
    formulario = FormularioNome()
    if not _campos_validos(formulario, {"nome"}):
        return _pagina(400, formulario_nome=formulario)
    try:
        conta_db.atualizar_nome(_id(), formulario.nome.data)
    except (Error, RuntimeError):
        current_app.logger.exception("Falha ao salvar o nome")
        return _pagina(503, formulario_nome=formulario, erro="Não foi possível salvar agora. Nada foi alterado.")
    flash("Perfil atualizado.", "conta_sucesso")
    return redirect(url_for("conta.exibir"), code=303)


@conta.post("/icone")
def salvar_icone():
    formulario = FormularioIcone()
    if not _campos_validos(formulario, {"icone"}):
        return _pagina(400, erro="Escolha um dos ícones da lista.")
    escolhido = formulario.icone.data
    try:
        conta_db.atualizar_icone(_id(), None if escolhido == "iniciais" else escolhido)
    except (Error, RuntimeError):
        current_app.logger.exception("Falha ao salvar o ícone")
        return _pagina(503, erro="Não foi possível trocar o ícone agora. Nada foi alterado.")
    flash("Ícone atualizado.", "conta_sucesso")
    return redirect(url_for("conta.exibir"), code=303)


def _avisar_troca_de_senha(email):
    texto, html = montar_email(
        "Segurança da conta",
        "Sua senha foi alterada",
        ["A senha da sua conta no SafeClick foi alterada pela página Minha conta. "
         "As outras sessões abertas foram encerradas."],
        aviso=("Não foi você?", "Use a opção \"Esqueci minha senha\" na tela de login e fale com a equipe "
               "pelo canal informado na Política de Privacidade."),
    )
    enviar_email(email, "SafeClick - Sua senha foi alterada", texto, html=html)


@conta.post("/senha")
def trocar_senha():
    formulario = FormularioSenha()
    if not _campos_validos(formulario, {"senha_atual", "nova_senha", "confirmar_senha"}):
        return _pagina(400, formulario_senha=formulario)
    if formulario.nova_senha.data == formulario.senha_atual.data:
        return _pagina(400, formulario_senha=formulario, erro_senha="A nova senha precisa ser diferente da atual.")
    try:
        if not permitir_tentativa("troca_senha", str(_id()), 5):
            return _pagina(429, formulario_senha=formulario,
                           erro_senha="Muitas tentativas. Aguarde cinco minutos e tente novamente.")
        email = conta_db.trocar_senha(_id(), formulario.senha_atual.data, formulario.nova_senha.data, _sessao())
    except conta_db.SenhaAtualIncorreta:
        return _pagina(400, formulario_senha=formulario, erro_senha="A senha atual está incorreta.")
    except (Error, RuntimeError, ValueError):
        current_app.logger.exception("Falha ao trocar a senha")
        return _pagina(503, formulario_senha=formulario,
                       erro_senha="Não foi possível trocar a senha agora. Nada foi alterado.")
    if not _agendar(_avisar_troca_de_senha, email):
        current_app.logger.error("Aviso de troca de senha nao agendado.")
    flash("Senha alterada. As outras sessões foram encerradas.", "conta_sucesso")
    return redirect(url_for("conta.exibir"), code=303)


@conta.post("/sessoes")
def encerrar_sessoes():
    formulario = FlaskForm()
    if not _campos_validos(formulario, set()):
        return _pagina(400, erro="O formulário expirou. Recarregue a página e tente novamente.")
    try:
        encerradas = conta_db.encerrar_outras_sessoes(_id(), _sessao())
    except (Error, RuntimeError):
        current_app.logger.exception("Falha ao encerrar sessões")
        return _pagina(503, erro="Não foi possível encerrar as sessões agora.")
    if encerradas:
        flash(f"{encerradas} {'sessão encerrada' if encerradas == 1 else 'sessões encerradas'}.", "conta_sucesso")
    else:
        flash("Não havia outras sessões abertas.", "conta_sucesso")
    return redirect(url_for("conta.exibir"), code=303)
