"""Esconde dados pessoais nas listas da administração."""

# telas da administração que permitem ver o e-mail completo
TELAS_EMAIL = {
    "contas": "Contas",
    "auditoria": "Auditoria",
    "perfil": "Alterar perfil",
    "exclusao": "Excluir conta",
    "autenticador": "Redefinir autenticador",
}


def mascarar_email(email):
    """Mostra só a primeira letra e o domínio (m***@gmail.com), sem revelar o tamanho."""
    if not email:
        return ""
    if "@" not in email:
        return "***"
    usuario, dominio = email.rsplit("@", 1)
    return f"{usuario[:1]}***@{dominio}"
