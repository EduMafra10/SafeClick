from flask import current_app


def montar_email(etiqueta, titulo, paragrafos, botao=None, aviso=None):
    """Devolve (texto, html) de um e-mail do sistema no modelo minimalista.

    botao: (rótulo, endereço); aviso: (destaque, texto).
    """
    suporte = current_app.config.get("SUPORTE_EMAIL")
    partes = ["Olá!", *paragrafos]
    if botao:
        partes.append(f"{botao[0]}:\n{botao[1]}")
    if aviso:
        partes.append(f"{aviso[0]} {aviso[1]}")
    partes.append(f"SafeClick\nMensagem automática, não responda. Suporte: {suporte}")
    html = current_app.jinja_env.get_template("emails/modelo.html").render(
        etiqueta=etiqueta, titulo=titulo, paragrafos=paragrafos,
        botao=botao, aviso=aviso, suporte=suporte,
    )
    return "\n\n".join(partes), html
