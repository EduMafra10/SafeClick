# Páginas de Política de Privacidade e Termos de Uso (LGPD)
from flask import Blueprint, abort, render_template, request
from psycopg import Error

from safeclick.termos_db import buscar_termos

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

# Antes de mudar esta versao, arquive o novo documento em versoes_termos.
# A pagina de termos mostra o HTML arquivado; editar termos.html sozinho nao a altera.
VERSAO_TERMOS = DOCUMENTOS["versao"]


@privacidade.get("/politica-de-privacidade")
def politica():
    return render_template("privacidade/politica.html", **DOCUMENTOS)


@privacidade.get("/termos-de-uso")
def termos():
    versao = request.args.get("versao", VERSAO_TERMOS)
    try:
        documento = buscar_termos(versao)
    except (Error, RuntimeError):
        abort(503, description="Não foi possível carregar os Termos de Uso. Tente novamente em instantes.")

    if documento is None:
        abort(404, description="Esta versão dos Termos de Uso não está disponível.")

    # Exibe o documento arquivado, o mesmo que sera vinculado ao aceite.
    dados_pagina = dict(DOCUMENTOS)
    dados_pagina.update(
        versao=documento["versao"],
        vigencia=documento["vigente_desde"].strftime("%d/%m/%Y"),
    )
    resposta = render_template(
        "privacidade/termos_publicados.html",
        conteudo_termos=documento["conteudo_html"],
        **dados_pagina,
    )
    return resposta, 200, {"Cache-Control": "no-store"}
