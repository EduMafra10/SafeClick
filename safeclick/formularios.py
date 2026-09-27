from flask_wtf import FlaskForm
from wtforms import EmailField, PasswordField, StringField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, Length

def limpar_texto(valor):
    # remove espaços das extremidades de nome e email
    return valor.strip() if valor else ""

class FormularioCadastro(FlaskForm):
    nome = StringField(
        "Nome",
        filters=[limpar_texto],
        validators=[
            DataRequired(message="Informe o seu nome"),
            Length(max=100, message="Use até 100 caracteres no nome"),
        ],
    )

    email = EmailField(
        "E-mail",
        filters=[limpar_texto, str.lower],
        validators=[
            DataRequired(message="Informe o seu e-mail"),
            Length(max=254, message="Use até 254 caracteres no e-mail"),
            Email(message="Informe um e-mail válido", check_deliverability=False),
        ],
    )

    # a senha mantem exatamente os caracteres digitados, incluindo os espacos
    senha = PasswordField(
        "Senha",
        validators=[
            DataRequired(message="Informe uma senha"),
            Length(
                min=15,
                max=128,
                message="Use uma senha com 15 a 128 caracteres",
            ),
        ],
    )

    confirmar_senha = PasswordField(
        "Confirme a senha",
        validators=[
            DataRequired(message="Confirme sua senha"),
            EqualTo("senha", message="As senhas precisam ser iguais"),
        ],
    )

    enviar = SubmitField("Criar conta")