"""Formatação simples do editor de conteúdos.

O administrador escreve texto com algumas marcações e o sistema gera o HTML.
Tudo é escapado antes; só as marcações abaixo viram tags:

    ## Subtítulo
    - item de lista
    > destaque (caixa verde)
    **negrito**, *itálico* e [texto do link](/endereco)
    Um parágrafo que começa com "Fonte:" ou "Fontes:" vira a nota de fontes.
"""
import re
from html import escape
from html.parser import HTMLParser

_LINK = re.compile(r"\[([^\]\n]+)\]\(((?:/(?!/)|https://)[^\s)*\"'<>]*)\)")
_NEGRITO = re.compile(r"\*\*(?=\S)(.+?)(?<=\S)\*\*")
_ITALICO = re.compile(r"(?<![*\w])\*(?=[^\s*])([^*\n]+?)(?<=[^\s*])\*(?![*\w])")
_FONTE = re.compile(r"Fontes?:", re.IGNORECASE)
_PRATIQUE = "conteudos-pratique"


def _link_seguro(endereco):
    return bool(endereco) and (
        (endereco.startswith("/") and not endereco.startswith("//")) or endereco.startswith("https://")
    )


def _em_linha(texto):
    texto = escape(texto, quote=False)
    texto = _LINK.sub(r'<a href="\2">\1</a>', texto)
    texto = _NEGRITO.sub(r"<strong>\1</strong>", texto)
    return _ITALICO.sub(r"<em>\1</em>", texto)


def html_do_texto(texto):
    partes, paragrafo, lista, destaque = [], [], [], []

    def fechar():
        if paragrafo:
            classe = ' class="conteudos-fonte"' if _FONTE.match(paragrafo[0]) else ""
            partes.append(f"<p{classe}>" + "<br>\n".join(_em_linha(l) for l in paragrafo) + "</p>")
        if lista:
            partes.append("<ul>\n" + "".join(f"<li>{_em_linha(l)}</li>\n" for l in lista) + "</ul>")
        if destaque:
            partes.append(f'<p class="{_PRATIQUE}">' + "<br>\n".join(_em_linha(l) for l in destaque) + "</p>")
        paragrafo.clear()
        lista.clear()
        destaque.clear()

    for linha in texto.replace("\r\n", "\n").split("\n"):
        linha = linha.strip()
        if linha.startswith("## "):
            fechar()
            if linha[3:].strip():
                partes.append(f"<h3>{_em_linha(linha[3:].strip())}</h3>")
        elif linha.startswith("- "):
            if paragrafo or destaque:
                fechar()
            lista.append(linha[2:].strip())
        elif linha.startswith("> "):
            if paragrafo or lista:
                fechar()
            destaque.append(linha[2:].strip())
        elif linha:
            if lista or destaque:
                fechar()
            paragrafo.append(linha)
        else:
            fechar()
    fechar()
    return "\n".join(partes)


class _Leitor(HTMLParser):
    """Faz o caminho inverso, para editar conteúdos que já estão publicados."""

    titulos = {"h1", "h2", "h3", "h4", "h5", "h6"}
    blocos = {"p", "ul", "ol", "div", "section", "table", "tr"} | titulos

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.partes = []
        self.links = []
        self.prefixo = ""

    def handle_starttag(self, tag, attrs):
        atributos = dict(attrs)
        if tag in self.titulos:
            self.prefixo = ""
            self.partes.append("\n\n## ")
        elif tag == "p" and _PRATIQUE in (atributos.get("class") or "").split():
            self.prefixo = "> "
            self.partes.append("\n\n> ")
        elif tag in self.blocos:
            self.prefixo = ""
            self.partes.append("\n\n")
        elif tag == "li":
            self.partes.append("\n- ")
        elif tag == "br":
            self.partes.append("\n" + self.prefixo)
        elif tag in {"strong", "b"}:
            self.partes.append("**")
        elif tag in {"em", "i"}:
            self.partes.append("*")
        elif tag == "a":
            endereco = atributos.get("href") or ""
            self.links.append(endereco if _link_seguro(endereco) else None)
            if self.links[-1]:
                self.partes.append("[")

    def handle_endtag(self, tag):
        if tag in self.blocos:
            self.prefixo = ""
            self.partes.append("\n\n")
        elif tag in {"strong", "b"}:
            self.partes.append("**")
        elif tag in {"em", "i"}:
            self.partes.append("*")
        elif tag == "a" and self.links:
            endereco = self.links.pop()
            if endereco:
                self.partes.append(f"]({endereco})")

    def handle_data(self, data):
        self.partes.append(re.sub(r"\s+", " ", data))


def texto_do_html(html):
    leitor = _Leitor()
    leitor.feed(html or "")
    leitor.close()
    linhas = []
    for linha in "".join(leitor.partes).split("\n"):
        linha = linha.strip()
        linha = re.sub(r"^(##|-|>) +", r"\1 ", linha)
        if linha in {"##", "-", ">"}:
            linha = ""
        linhas.append(linha)
    return re.sub(r"\n{3,}", "\n\n", "\n".join(linhas)).strip()
