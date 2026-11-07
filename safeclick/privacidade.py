# Páginas de Política de Privacidade e Termos de Uso (LGPD)
from flask import Blueprint, abort, render_template, request
from psycopg import Error

from safeclick.documentos_db import buscar_politica, buscar_referencias
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

# A politica tambem fica arquivada no banco (versoes_politica).
# Para publicar uma nova versao, grave o documento no banco e depois mude este valor.
VERSAO_POLITICA = "1.1"


@privacidade.get("/politica-de-privacidade")
def politica():
    versao = request.args.get("versao", VERSAO_POLITICA)
    try:
        documento = buscar_politica(versao)
        referencias = buscar_referencias("politica", versao) if documento else []
    except (Error, RuntimeError):
        abort(503, description="Não foi possível carregar a Política de Privacidade. Tente novamente em instantes.")

    if documento is None:
        abort(404, description="Esta versão da Política de Privacidade não está disponível.")

    dados_pagina = dict(DOCUMENTOS)
    dados_pagina.update(
        versao=documento["versao"],
        vigencia=documento["vigente_desde"].strftime("%d/%m/%Y"),
    )
    resposta = render_template(
        "privacidade/politica_publicada.html",
        conteudo_politica=documento["conteudo_html"],
        referencias=referencias,
        **dados_pagina,
    )
    return resposta, 200, {"Cache-Control": "no-store"}


@privacidade.get("/termos-de-uso")
def termos():
    versao = request.args.get("versao", VERSAO_TERMOS)
    try:
        documento = buscar_termos(versao)
        referencias = buscar_referencias("termos", versao) if documento else []
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
        referencias=referencias,
        **dados_pagina,
    )
    return resposta, 200, {"Cache-Control": "no-store"}
