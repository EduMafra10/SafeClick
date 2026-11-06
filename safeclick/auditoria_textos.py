
CATEGORIAS = {
    "acesso": "Acesso e conta",
    "aprendizado": "Aprendizado",
    "administracao": "Administração",
    "integracoes": "Serviços externos",
}

EVENTOS = {
    "usuario.cadastrado": ("Conta criada", "acesso"),
    "termo.aceito": ("Termos de Uso aceitos", "acesso"),
    "login.sucesso": ("Login concluído", "acesso"),
    "login.falha": ("Login recusado", "acesso"),
    "logout.realizado": ("Saiu da conta", "acesso"),
    "usuario.senha_redefinida": ("Senha redefinida", "acesso"),
    "acesso.negado": ("Acesso negado", "acesso"),
    "conteudo.visualizado": ("Conteúdo aberto", "aprendizado"),
    "conteudo.concluido": ("Conteúdo concluído", "aprendizado"),
    "quiz.concluido": ("Quiz respondido", "aprendizado"),
    "simulacao.concluida": ("Simulação respondida", "aprendizado"),
    "desafio_senha.concluido": ("Desafio de senhas concluído", "aprendizado"),
    "simulacao.criada": ("Simulação criada", "administracao"),
    "catalogo.criado": ("Rascunho criado", "administracao"),
    "catalogo.editado": ("Rascunho editado", "administracao"),
    "catalogo.publicado": ("Item publicado", "administracao"),
    "catalogo.despublicado": ("Item despublicado", "administracao"),
    "catalogo.removido": ("Item removido do catálogo", "administracao"),
    "catalogo.excluido": ("Rascunho excluído", "administracao"),
    "catalogo.restaurado": ("Item restaurado", "administracao"),
    "auditoria.consultada": ("Auditoria consultada", "administracao"),
    "api.consultada": ("Consulta a serviço externo", "integracoes"),
}


EVENTOS_ANTIGOS = {
    "mfa.reconfiguracao_administrativa": ("Autenticador reiniciado pelo administrador", "administracao"),
    "mfa.reconfiguracao_concluida": ("Autenticador configurado novamente", "acesso"),
}

RESULTADOS = {"sucesso": "Sucesso", "falha": "Falha", "negado": "Negado"}

MOTIVOS_LOGIN = {
    "email_nao_cadastrado": "E-mail não cadastrado",
    "senha_incorreta": "Senha incorreta",
    "credenciais_invalidas": "E-mail ou senha incorretos",
    "limite_tentativas": "Bloqueado por excesso de tentativas",
    "tentativa_indisponivel": "Tentativa expirada ou já utilizada",
    "codigo_ou_prazo_rejeitado": "Código do autenticador recusado ou prazo encerrado",
}

ETAPAS_LOGIN = {"senha": "senha", "autenticador": "código do autenticador"}

SERVICOS = {
    "twilio_verify": "Twilio (verificação em duas etapas)",
    "pwned_passwords": "Have I Been Pwned (senhas vazadas)",
}

OPERACOES = {
    "criar_fator_totp": "gerar o QR Code do autenticador",
    "validar_ativacao_totp": "ativar o autenticador",
    "validar_codigo_totp": "conferir o código do login",
    "consultar_fator_totp": "consultar a situação do autenticador",
    "remover_fator_totp": "remover autenticador não ativado",
    "consultar_prefixo": "consultar vazamentos (desafio de senhas)",
}

ERROS_TWILIO = {
    "configuracao_ausente": "configuração do Twilio ausente no servidor (.env)",
    "credenciais_recusadas": "credenciais do Twilio recusadas",
    "limite_twilio": "limite de uso do Twilio atingido",
    "servico_indisponivel": "Twilio fora do ar",
    "recusado_pelo_twilio": "pedido recusado pelo Twilio",
    "sem_conexao": "sem conexão com o Twilio",
    "falha_inesperada": "erro inesperado",
}

AREAS = {
    "quizzes": "Quizzes",
    "simulacoes": "Simulações",
    "conteudos": "Conteúdos",
    "paginas": "Páginas",
    "painel": "Meu progresso",
    "senhas": "Laboratório de senhas",
    "administracao": "Administração",
    "administracao.catalogo": "Gestão de conteúdo",
    "auditoria": "Auditoria",
}

RECURSOS = {
    "quiz": "Quiz",
    "pagina": "Página",
    "tentativa_quiz": "Tentativa de quiz",
    "tentativa_simulacao": "Tentativa de simulação",
    "simulacao": "Simulação",
    "conteudo": "Conteúdo",
    "desafio_senha": "Partida do desafio",
    "usuario": "Conta",
    "aceite_termos": "Aceite",
    "sessao": "Sessão",
}


def titulo_evento(evento):
    return (EVENTOS.get(evento) or EVENTOS_ANTIGOS.get(evento) or (evento, None))[0]


def categoria_evento(evento):
    categoria = (EVENTOS.get(evento) or EVENTOS_ANTIGOS.get(evento) or (None, None))[1]
    return CATEGORIAS.get(categoria, "Outros")


def eventos_da_categoria(categoria):
    return {
        evento
        for evento, (_, cat) in {**EVENTOS, **EVENTOS_ANTIGOS}.items()
        if cat == categoria
    }


def opcoes_de_filtro():
    """Grupos do campo "Evento": [(categoria, rótulo, [(evento, título), ...]), ...]."""
    grupos = []
    for chave, rotulo in CATEGORIAS.items():
        eventos = sorted(
            (evento, titulo) for evento, (titulo, cat) in EVENTOS.items() if cat == chave
        )
        grupos.append((chave, rotulo, sorted(eventos, key=lambda item: item[1])))
    return grupos


def _legivel(valor):
    return str(valor).replace("_", " ").replace("-", " ")


def descrever_detalhes(evento, detalhes, recurso_tipo=None, recurso_id=None):
    
    detalhes = dict(detalhes or {})
    frases = []

    if evento == "login.falha":
        motivo = detalhes.pop("motivo", None)
        etapa = detalhes.pop("etapa", None)
        if motivo:
            frases.append(MOTIVOS_LOGIN.get(motivo, _legivel(motivo)))
        if etapa:
            frases.append(f"Etapa: {ETAPAS_LOGIN.get(etapa, _legivel(etapa))}")

    elif evento == "api.consultada":
        servico = detalhes.pop("servico", None)
        operacao = detalhes.pop("operacao", None)
        if servico:
            frases.append(SERVICOS.get(servico, _legivel(servico)))
        if operacao:
            frases.append(f"Ação: {OPERACOES.get(operacao, _legivel(operacao))}")
        erro = detalhes.pop("erro", None)
        if erro:
            frases.append(f"Motivo: {ERROS_TWILIO.get(erro, _legivel(erro))}")
        codigo = detalhes.pop("codigo_twilio", None)
        if codigo:
            frases.append(f"Código Twilio: {codigo}")

    elif evento in ("quiz.concluido", "desafio_senha.concluido"):
        acertos = detalhes.pop("pontuacao", detalhes.pop("acertos", None))
        total = detalhes.pop("total_questoes", detalhes.pop("total", None))
        quiz_id = detalhes.pop("quiz_id", None)
        if quiz_id is not None:
            frases.append(f"Quiz nº {quiz_id}")
        if acertos is not None and total is not None:
            frases.append(f"Acertou {acertos} de {total}")

    elif evento == "simulacao.concluida":
        simulacao = detalhes.pop("simulacao", None)
        opcao = detalhes.pop("opcao", None)
        detalhes.pop("versao_id", None)
        if simulacao:
            frases.append(f"Cenário: {_legivel(simulacao)}")
        if opcao:
            frases.append(f"Escolha: {_legivel(opcao)}")

    elif evento == "simulacao.criada":
        identificador = detalhes.pop("identificador", None)
        estado = detalhes.pop("estado", None)
        if identificador:
            frases.append(f"Identificador: {identificador}")
        if estado:
            frases.append(f"Situação: {_legivel(estado)}")

    elif evento == "acesso.negado":
        area = detalhes.pop("area", None) or recurso_tipo
        if area:
            frases.append(f"Área: {AREAS.get(area, _legivel(area))}")
        recurso_tipo = None

    elif evento == "termo.aceito":
        versao = detalhes.pop("versao", None)
        if versao:
            frases.append(f"Versão {versao}")

    # Qualquer informação que não tenha tradução aparece como "chave: valor".
    for chave, valor in detalhes.items():
        frases.append(f"{_legivel(chave).capitalize()}: {valor}")

    if recurso_tipo in RECURSOS and recurso_id:
        frases.append(f"{RECURSOS[recurso_tipo]} nº {recurso_id}")

    return frases


def explicar_sem_usuario(evento, detalhes):
    
    detalhes = detalhes or {}
    motivo = detalhes.get("motivo")
    if evento == "login.falha" and motivo in ("email_nao_cadastrado", "limite_tentativas"):
        return "Visitante não identificado"
    if evento == "login.falha" and detalhes.get("etapa") == "autenticador":
        return "Conta não identificada (tentativa expirada ou registro antigo)"
    if evento in ("login.falha", "api.consultada"):
        return "Não registrado (anterior à atualização)"
    return "Sem conta associada"
