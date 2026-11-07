import secrets

from flask import Blueprint, current_app, jsonify, render_template, request, session
from flask_login import current_user
from flask_wtf import FlaskForm
from psycopg import Error

from safeclick.auditoria_db import registrar_evento
from safeclick.desafio_senhas import (
    SENHAS_EXEMPLO,
    TOTAL_RODADAS,
    contagem_em_cache,
    escolha_correta,
    guardar_contagem,
    senhas_da_rodada,
    sortear_partida,
)
from safeclick.desafios_senha_db import salvar_desafio_senha
from safeclick.formularios import FormularioRespostaDesafio
from safeclick.limites import permitir_tentativa
from safeclick.pwned_api import (
    ServicoSenhasIndisponivel,
    contar_vazamentos,
)
from safeclick.sessoes import exigir_perfis


senhas = Blueprint("senhas", __name__, url_prefix="/laboratorio-senhas")


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


@senhas.get("/")
def pagina():
    
    return render_template("laboratorio_senhas.html", formulario=FlaskForm())


# ---------- Desafio "Qual vazou mais?" ----------

def _formato_invalido(campos):
    
    return bool(
        request.args
        or request.mimetype != "application/x-www-form-urlencoded"
        or set(request.form) != campos
        or any(len(request.form.getlist(campo)) != 1 for campo in campos)
    )


def _obter_contagem(senha):
    """Busca no cache; se não tiver, consulta a API e registra na auditoria."""
    quantidade = contagem_em_cache(senha)
    if quantidade is not None:
        return quantidade

    try:
        quantidade = contar_vazamentos(senha)
    except ServicoSenhasIndisponivel:
        _registrar_consulta("falha")
        raise

    _registrar_consulta("sucesso")
    guardar_contagem(senha, quantidade)
    return quantidade


def _proxima_rodada(partida):
    numero = len(partida["respostas"]) + 1
    return {
        "rodada": numero,
        "total": TOTAL_RODADAS,
        "opcoes": senhas_da_rodada(partida["pares"][numero - 1]),
    }


@senhas.post("/desafio/iniciar")
def iniciar_desafio():
    if _formato_invalido({"csrf_token"}):
        return jsonify(erro="Formato de requisição inválido."), 400

    if not FlaskForm().validate_on_submit():
        return jsonify(erro="Recarregue a página e tente novamente."), 400

    try:
        permitido = permitir_tentativa("desafio_senha", str(current_user.id), 10)
    except (Error, RuntimeError):
        return jsonify(erro="Não foi possível iniciar o desafio agora."), 503

    if not permitido:
        resposta = jsonify(erro="Muitas partidas seguidas. Aguarde cinco minutos.")
        resposta.status_code = 429
        resposta.headers["Retry-After"] = "300"
        return resposta

    
    partida = {
        "token": secrets.token_urlsafe(32),
        "pares": sortear_partida(),
        "respostas": [],
    }
    session["desafio_senha"] = partida
    return jsonify(_proxima_rodada(partida))


@senhas.post("/desafio/responder")
def responder_desafio():
    if _formato_invalido({"escolha", "rodada", "csrf_token"}):
        return jsonify(erro="Formato de requisição inválido."), 400

    formulario = FormularioRespostaDesafio()
    if not formulario.validate_on_submit():
        return jsonify(erro="Recarregue a página e tente novamente."), 400

    partida = session.get("desafio_senha")
    if not partida or len(partida.get("respostas", [])) >= TOTAL_RODADAS:
        return jsonify(erro="Inicie uma nova partida."), 409

    numero = len(partida["respostas"]) + 1
    if formulario.rodada.data != numero:
        return jsonify(erro="Essa rodada já foi respondida. Continue a partida."), 409

    opcoes = senhas_da_rodada(partida["pares"][numero - 1])
    try:
        contagens = [_obter_contagem(senha) for senha in opcoes]
    except ServicoSenhasIndisponivel:
        return jsonify(erro="A base de vazamentos está indisponível. Tente novamente."), 503

    escolha = int(formulario.escolha.data)
    respostas = partida["respostas"] + [escolha_correta(contagens, escolha)]
    acertos = sum(respostas)
    proxima = final = None

    if len(respostas) == TOTAL_RODADAS:
        try:
            salvar_desafio_senha(int(current_user.id), acertos, TOTAL_RODADAS, partida["token"])
        except (Error, RuntimeError):
            
            return jsonify(erro="Não foi possível salvar o resultado. Tente responder novamente."), 503
        session.pop("desafio_senha", None)
        final = {"acertos": acertos, "total": TOTAL_RODADAS}
    else:
        partida = dict(partida, respostas=respostas)
        session["desafio_senha"] = partida
        proxima = _proxima_rodada(partida)

    return jsonify(
        rodada=numero,
        total=TOTAL_RODADAS,
        escolha=escolha,
        correta=respostas[-1],
        acertos=acertos,
        resultado=[
            {"senha": senha, "vazamentos": quantidade, "licao": SENHAS_EXEMPLO[senha]}
            for senha, quantidade in zip(opcoes, contagens)
        ],
        proxima=proxima,
        final=final,
    )