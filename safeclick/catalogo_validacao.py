import json
import re
from html import escape
from html.parser import HTMLParser


SECOES = {
    "conteudos": "Conteúdos educativos",
    "quizzes": "Quizzes",
    "simulacoes": "Simulações",
    "paginas": "Páginas",
}
CANAIS = {
    "email": "E-mail fictício",
    "sms": "SMS fictício",
    "conversa": "Conversa fictícia",
    "loja": "Loja virtual fictícia",
}
MAX_QUESTOES = 20
MAX_ALTERNATIVAS = 8


class DadosInvalidos(ValueError):
    """Dados que podem ser corrigidos no editor."""


def estrutura_json(texto):
    try:
        dados = json.loads(texto)
    except (TypeError, ValueError, RecursionError):
        raise DadosInvalidos("Não foi possível ler os itens. Recarregue o editor e tente novamente.") from None
    if not isinstance(dados, list):
        raise DadosInvalidos("A lista de itens é inválida.")
    return dados


def _objeto(valor):
    if not isinstance(valor, dict):
        raise DadosInvalidos("Um dos itens do editor é inválido.")
    return valor


def _texto(valor, limite, campo, obrigatorio=False):
    if not isinstance(valor, str) or "\x00" in valor or len(valor) > limite:
        raise DadosInvalidos(f"{campo}: use até {limite} caracteres válidos.")
    valor = valor.replace("\r\n", "\n").strip()
    if obrigatorio and not valor:
        raise DadosInvalidos(f"{campo}: preencha este campo antes de continuar.")
    return valor


def validar_slug(secao, slug):
    limite = 80 if secao == "simulacoes" else 50
    slug = _texto(slug, limite, "Endereço", True)
    if not re.fullmatch(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*", slug):
        raise DadosInvalidos("Use um endereço sem espaços ou acentos, como golpes-por-mensagem.")
    return slug


def _lista(itens, limite):
    if not isinstance(itens, list) or len(itens) > limite:
        raise DadosInvalidos(f"Use no máximo {limite} itens nesta lista.")
    return itens


def _bool(valor):
    if type(valor) is not bool:
        raise DadosInvalidos("A seleção da alternativa é inválida.")
    return valor


def validar(secao, dados, *, publicar=False):
    """Valida limites ao salvar e exige itens completos para publicar."""
    titulo = _texto(dados.get("titulo", ""), 120 if secao == "simulacoes" else 150, "Título", True)
    if secao in {"conteudos", "paginas"}:
        return {"titulo": titulo, "corpo": _texto(dados.get("corpo", ""), 16000, "Texto", publicar)}
    if secao == "quizzes":
        questoes = []
        for numero, questao in enumerate(_lista(dados.get("questoes", []), MAX_QUESTOES), 1):
            questao = _objeto(questao)
            alternativas = [
                {
                    "texto": _texto(_objeto(opcao).get("texto", ""), 500, f"Pergunta {numero}, alternativa {ordem}", publicar),
                    "correta": _bool(opcao.get("correta", False)),
                }
                for ordem, opcao in enumerate(_lista(questao.get("alternativas", []), MAX_ALTERNATIVAS), 1)
            ]
            if publicar and (len(alternativas) < 2 or sum(a["correta"] for a in alternativas) != 1):
                raise DadosInvalidos(f"Pergunta {numero}: informe pelo menos duas alternativas e marque exatamente uma correta.")
            questoes.append({
                "enunciado": _texto(questao.get("enunciado", ""), 1000, f"Enunciado da pergunta {numero}", publicar),
                "explicacao": _texto(questao.get("explicacao", ""), 1200, f"Explicação da pergunta {numero}", publicar),
                "alternativas": alternativas,
            })
        if publicar and not questoes:
            raise DadosInvalidos("Adicione pelo menos uma pergunta antes de publicar.")
        return {"titulo": titulo, "questoes": questoes}

    tipo = dados.get("tipo")
    if not isinstance(tipo, str) or tipo not in CANAIS:
        raise DadosInvalidos("Selecione um formato de simulação válido.")
    cenario = {
        "titulo": titulo, "tipo": tipo, "canal": CANAIS[tipo],
        "resumo": _texto(dados.get("resumo", ""), 300, "Resumo", publicar),
        "assunto": _texto(dados.get("assunto", ""), 180, "Assunto", publicar),
        "origem": _texto(dados.get("origem", ""), 180, "Remetente ou origem", publicar),
        "chamada": _texto(dados.get("chamada", ""), 140, "Chamada"),
    }
    for chave, rotulo, limite in (("mensagem", "Mensagem", 5000), ("sinais", "Sinais de risco", 3000)):
        valor = dados.get(chave, [])
        if isinstance(valor, list):
            valor = "\n".join(_texto(linha, limite, rotulo) for linha in _lista(valor, 30))
        linhas = [linha.strip() for linha in _texto(valor, limite, rotulo, publicar).splitlines() if linha.strip()]
        cenario[chave] = _lista(linhas, 30)

    opcoes = dados.get("opcoes", [])
    if isinstance(opcoes, dict):
        opcoes = [opcoes[chave] for chave in dados.get("ordem_opcoes", opcoes) if chave in opcoes]
    cenario["opcoes"] = {}
    for numero, opcao in enumerate(_lista(opcoes, MAX_ALTERNATIVAS), 1):
        opcao = _objeto(opcao)
        cenario["opcoes"][f"opcao_{numero}"] = {
            "texto": _texto(opcao.get("texto", ""), 500, f"Alternativa {numero}", publicar),
            "consequencia": _texto(opcao.get("consequencia", ""), 1200, f"Consequência da alternativa {numero}", publicar),
            "explicacao": _texto(opcao.get("explicacao", ""), 1200, f"Explicação da alternativa {numero}", publicar),
            "segura": _bool(opcao.get("segura", False)),
        }
    cenario["ordem_opcoes"] = list(cenario["opcoes"])
    if publicar and (
        len(cenario["opcoes"]) < 2
        or {a["segura"] for a in cenario["opcoes"].values()} != {True, False}
    ):
        raise DadosInvalidos("Inclua pelo menos uma escolha segura e uma de risco.")
    if tipo == "loja":
        produto = _objeto(dados.get("produto") or {})
        produto = {
            "nome": _texto(produto.get("nome", ""), 120, "Nome do produto"),
            "preco_anterior": _texto(produto.get("preco_anterior", ""), 40, "Preço anterior"),
            "preco_atual": _texto(produto.get("preco_atual", ""), 40, "Preço anunciado"),
        }
        if any(produto.values()):
            if publicar and not all(produto.values()):
                raise DadosInvalidos("Preencha os três campos do produto ou deixe todos vazios.")
            cenario["produto"] = produto
    return cenario


class _TextoLegado(HTMLParser):
    blocos = {"p", "div", "section", "h1", "h2", "h3", "h4", "br", "li", "ul", "ol"}

    def __init__(self):
        super().__init__()
        self.partes = []

    def handle_starttag(self, tag, attrs):
        if tag in self.blocos:
            self.partes.append("\n")

    def handle_endtag(self, tag):
        if tag in self.blocos:
            self.partes.append("\n")

    def handle_data(self, data):
        self.partes.append(data)


def texto_do_html(html):
    parser = _TextoLegado()
    parser.feed(html)
    return re.sub(r"\n{3,}", "\n\n", "".join(parser.partes)).strip()


def html_do_texto(texto):
    """Texto do editor vira HTML escapado, inclusive na prévia."""
    paragrafos = re.split(r"\n[ \t]*\n", texto)
    return "".join(
        "<p>" + escape(paragrafo.strip()).replace("\n", "<br>\n") + "</p>"
        for paragrafo in paragrafos if paragrafo.strip()
    )
