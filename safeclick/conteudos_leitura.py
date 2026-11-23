import math
import re

from markupsafe import Markup

TEMAS = {
    "phishing": ("anzol", "ambar"),
    "protecao-de-senhas": ("chave", "verde"),
    "golpes-por-mensagem": ("conversa", "azul"),
    "falso-conhecido-e-pix": ("pix", "roxo"),
    "compras-online-seguras": ("sacola", "ambar"),
    "verificacao-em-duas-etapas": ("escudo", "verde"),
    "vazamento-de-dados": ("alerta", "azul"),
    "privacidade-e-dados-pessoais": ("olho", "roxo"),
    "codigos-maliciosos-e-atualizacoes": ("dispositivo", "verde"),
}
PADRAO = ("livro", "verde")
EXTRA = re.compile(r'<p class="conteudos-(pratique|fonte)">(.*?)</p>', re.S)
FONTE = re.compile(r'\s*<p class="conteudos-fonte">(.*?)</p>', re.S)
TITULO = re.compile(r"<h3[^>]*>(.*?)</h3>", re.S)
PARAGRAFO = re.compile(r"<p>(.*?)</p>", re.S)


def _texto_puro(html):
    return Markup(html).striptags()


def resumo(texto, limite=110):
    achado = PARAGRAFO.search(EXTRA.sub("", texto or ""))
    frase = _texto_puro(achado.group(1)) if achado else ""
    primeira = re.split(r"(?<=[.!?])\s", frase)[0]
    if len(primeira) <= limite + 30:
        return primeira
    if len(frase) <= limite:
        return frase
    return frase[:limite].rsplit(" ", 1)[0].rstrip(",;:") + "…"


def minutos(texto):
    palavras = len(_texto_puro(texto or "").split())
    return max(1, math.ceil(palavras / 200))


def tema(slug):
    icone, cor = TEMAS.get(slug, PADRAO)
    return {"icone": icone, "cor": cor}


def cartao(conteudo):
    texto = conteudo.get("texto") or ""
    return dict(conteudo, **tema(conteudo.get("slug")), resumo=resumo(texto),
                minutos=minutos(texto), topicos=len(TITULO.findall(texto)))


def dividir(texto):
    texto = texto or ""
    fontes = [Markup(f.strip()) for f in FONTE.findall(texto)]
    partes = TITULO.split(FONTE.sub("", texto))
    topicos = [{"titulo": _texto_puro(partes[i]), "html": Markup(partes[i + 1].strip())}
               for i in range(1, len(partes) - 1, 2)]
    return {"introducao": Markup(partes[0].strip()), "topicos": topicos, "fontes": fontes}
