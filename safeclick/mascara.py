TELAS_EMAIL = {
    "contas": "Contas",
    "auditoria": "Auditoria",
    "perfil": "Alterar perfil",
    "exclusao": "Excluir conta",
    "autenticador": "Redefinir autenticador",
}


def mascarar_email(email):
    if not email:
        return ""
    if "@" not in email:
        return "***"
    usuario, dominio = email.rsplit("@", 1)
    return f"{usuario[:1]}***@{dominio}"
