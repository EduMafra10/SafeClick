from flask import Blueprint, Response, current_app, jsonify, render_template, request
from flask_login import current_user
from psycopg import Error

from safeclick.auditoria_db import registrar_evento
from safeclick.formularios import FormularioConsultaSenha
from safeclick.limites import permitir_tentativa
from safeclick.pwned_api import (
    ServicoSenhasIndisponivel,
    consultar_prefixo_senha,
)
from safeclick.sessoes import exigir_perfis


senhas = Blueprint("senhas", __name__, url_prefix="/verificar-senha")


@senhas.before_request
@exigir_perfis("usuario", "administrador")
def verificar_acesso_senhas():
    request.max_content_length = 4096


@senhas.after_request
def proteger_resposta_senhas(resposta):
    resposta.headers["Cache-Control"] = "no-store"
    resposta.headers["Referrer-Policy"] = "no-referrer"
    resposta.headers["X-Content-Type-Options"] = "nosniff"
    return resposta


@senhas.errorhandler(413)
def rejeitar_consulta_grande(erro):
    return jsonify(erro="A consulta enviada é muito grande."), 413


def _registrar_consulta(resultado):
    try:
        registrar_evento(
            usuario_id=current_user.id,
            evento="api.consultada",
            resultado=resultado,
            recurso_tipo="api",
            detalhes={
                "servico": "pwned_passwords",
                "operacao": "consultar_prefixo",
            },
        )
    except (Error, RuntimeError):
        current_app.logger.warning("Falha ao registrar consulta de senhas na auditoria")


@senhas.post("/consultar")
def consultar():
    
    campos = {"prefixo", "csrf_token"}
    if (
        request.args
        or request.mimetype != "application/x-www-form-urlencoded"
        or set(request.form) != campos
        or any(len(request.form.getlist(campo)) != 1 for campo in campos)
    ):
        return jsonify(erro="Formato de consulta inválido."), 400

    formulario = FormularioConsultaSenha()
    if not formulario.validate_on_submit():
        return jsonify(erro="Recarregue a página e tente novamente."), 400

    try:
        permitido = permitir_tentativa("consulta_senha", str(current_user.id), 5)
    except (Error, RuntimeError):
        return jsonify(erro="Não foi possível iniciar a consulta agora."), 503

    if not permitido:
        resposta = jsonify(erro="Limite de consultas atingido. Aguarde cinco minutos.")
        resposta.status_code = 429
        resposta.headers["Retry-After"] = "300"
        return resposta

    try:
        texto = consultar_prefixo_senha(formulario.prefixo.data)
    except ServicoSenhasIndisponivel:
        _registrar_consulta("falha")
        return jsonify(erro="A consulta está indisponível. Tente novamente mais tarde."), 503

    _registrar_consulta("sucesso")
    return Response(texto, mimetype="text/plain")

@senhas.get("/")
def pagina():
    return render_template(
        "verificar_senha.html",
        formulario=FormularioConsultaSenha(),
    )