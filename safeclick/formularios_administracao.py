from flask_wtf import FlaskForm
from wtforms import SelectField, StringField, TextAreaField
from wtforms.validators import AnyOf, DataRequired, Length, Regexp, ValidationError


def limpar_texto(valor):
    return valor.strip() if isinstance(valor, str) else ""


def sem_caractere_nulo(formulario, campo):
    if "\x00" in (campo.data or ""):
        raise ValidationError("Remova o caractere inválido deste campo.")


class FormularioNovoCenario(FlaskForm):
    titulo = StringField(
        "Título do cenário",
        filters=[limpar_texto],
        validators=[DataRequired(message="Informe o título."), Length(max=120, message="Use até 120 caracteres."), sem_caractere_nulo],
        render_kw={"maxlength": 120},
    )
    slug = StringField(
        "Endereço do cenário",
        filters=[limpar_texto],
        validators=[
            DataRequired(message="Informe o endereço."),
            Length(max=80, message="Use até 80 caracteres."),
            Regexp(
                r"\A[a-z][a-z0-9]*(?:-[a-z0-9]+)*\Z",
                message="Comece com uma letra e use letras minúsculas sem acentos, números e hífens entre palavras.",
            ),
        ],
        render_kw={"maxlength": 80, "spellcheck": "false", "autocapitalize": "none"},
    )
    tipo = SelectField(
        "Tipo de cenário",
        choices=[("", "Selecione"), ("email", "E-mail"), ("sms", "SMS"),
                 ("conversa", "Conversa"), ("loja", "Loja")],
        validate_choice=False,
        validators=[
            DataRequired(message="Selecione o tipo de cenário."),
            AnyOf(["email", "sms", "conversa", "loja"], message="Selecione um tipo válido."),
        ],
    )
    resumo = TextAreaField(
        "Resumo para o catálogo",
        filters=[limpar_texto],
        validators=[DataRequired(message="Informe um resumo."), Length(max=300, message="Use até 300 caracteres."), sem_caractere_nulo],
        render_kw={"maxlength": 300, "rows": 3},
    )
