"""Configuração do SafeClick por variáveis de ambiente.

Os valores secretos ficam somente no .env (ou no painel da hospedagem).
O arquivo .env.example mostra o formato esperado de cada variável.
"""
import os

AMBIENTES = ("desenvolvimento", "producao")

# trechos dos valores de exemplo do .env.example
MARCAS_DE_EXEMPLO = ("troque-", "ACxxxxxxxx", "VAxxxxxxxx", "USUARIO:SENHA", "ep-exemplo")


def _texto(nome, padrao=None):
    valor = os.environ.get(nome, "").strip()
    return valor or padrao


def _inteiro(nome, padrao):
    valor = _texto(nome)
    if valor is None:
        return padrao
    try:
        return int(valor)
    except ValueError:
        raise RuntimeError(f"A variável {nome} precisa ser um número inteiro.") from None


def _booleano(nome, padrao=False):
    valor = _texto(nome)
    if valor is None:
        return padrao
    if valor.lower() not in ("true", "false"):
        raise RuntimeError(f"A variável {nome} aceita somente true ou false.")
    return valor.lower() == "true"


def carregar_configuracao():
    
    ambiente = _texto("APP_ENV", "desenvolvimento").lower()
    if ambiente not in AMBIENTES:
        raise RuntimeError("A variável APP_ENV aceita somente desenvolvimento ou producao.")
    producao = ambiente == "producao"

    config = {
        # aplicação
        "APP_ENV": ambiente,
        "SECRET_KEY": _texto("SECRET_KEY"),
        "APP_BASE_URL": _texto("APP_BASE_URL", "http://127.0.0.1:5000").rstrip("/"),
        "AVALIACOES_ATIVAS": _booleano("AVALIACOES_ATIVAS"),
        # banco de dados
        "DATABASE_URL": _texto("DATABASE_URL"),
        # Twilio Verify (segundo fator do login)
        "TWILIO_ACCOUNT_SID": _texto("TWILIO_ACCOUNT_SID"),
        "TWILIO_AUTH_TOKEN": _texto("TWILIO_AUTH_TOKEN"),
        "TWILIO_VERIFY_SERVICE_SID": _texto("TWILIO_VERIFY_SERVICE_SID"),
        # e-mail (recuperação de senha)
        "SMTP_HOST": _texto("SMTP_HOST", "smtp.gmail.com"),
        "SMTP_PORT": _inteiro("SMTP_PORT", 587),
        "SMTP_USER": _texto("SMTP_USER", ""),
        "SMTP_PASSWORD": _texto("SMTP_PASSWORD", ""),
        "SMTP_FROM_NAME": _texto("SMTP_FROM_NAME", "SafeClick"),
        "SUPORTE_EMAIL": _texto("SUPORTE_EMAIL", "safeclickpfc@gmail.com"),
        # cookie de sessão
        "SESSION_COOKIE_HTTPONLY": True,
        "SESSION_COOKIE_SAMESITE": "Lax",
        "SESSION_COOKIE_SECURE": True if producao else _booleano("SESSION_COOKIE_SECURE", False),
    }

    # em desenvolvimento, o banco é conferido ao conectar (flask verificar-banco)
    obrigatorias = ["SECRET_KEY"]
    if producao:
        obrigatorias += [
            "DATABASE_URL",
            "TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", "TWILIO_VERIFY_SERVICE_SID",
            "SMTP_USER", "SMTP_PASSWORD",
        ]
    faltando = [nome for nome in obrigatorias if not config[nome]]
    if faltando:
        raise RuntimeError(
            "Configure no .env as variáveis obrigatórias: " + ", ".join(faltando)
        )

    if producao:
        com_exemplo = [
            nome for nome, valor in config.items()
            if isinstance(valor, str) and any(marca in valor for marca in MARCAS_DE_EXEMPLO)
        ]
        if com_exemplo:
            raise RuntimeError(
                "Troque os valores de exemplo do .env.example: " + ", ".join(com_exemplo)
            )
        if len(config["SECRET_KEY"]) < 32:
            raise RuntimeError("Em produção, a SECRET_KEY precisa ter pelo menos 32 caracteres.")
        if not config["APP_BASE_URL"].startswith("https://"):
            raise RuntimeError("Em produção, o APP_BASE_URL precisa começar com https://.")

    return config
