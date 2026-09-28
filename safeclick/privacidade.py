# Páginas de Política de Privacidade e Termos de Uso (LGPD)
from flask import Blueprint, render_template

privacidade = Blueprint("privacidade", __name__)

# Informações exibidas nas duas páginas.
# Ao mudar o texto de um documento, aumente a versão e atualize a vigência;
# o cadastro grava essa versão para comprovar qual texto foi aceito.
DOCUMENTOS = {
    "versao": "1.0",
    "vigencia": "28/09/2026",
    # canal que precisa funcionar de verdade (e-mail do grupo)
    "email_privacidade": "safeclick.privacidade@gmail.com",
    # integrante que responde pelo canal de privacidade
    "encarregado": "João Souza",
    # idade mínima para criar conta e usar a plataforma
    "idade_minima_conta": 16,
    "provedor_email": "a definir",
}

VERSAO_TERMOS = DOCUMENTOS["versao"]


@privacidade.get("/politica-de-privacidade")
def politica():
    return render_template("privacidade/politica.html", **DOCUMENTOS)


@privacidade.get("/termos-de-uso")
def termos():
    return render_template("privacidade/termos.html", **DOCUMENTOS)
