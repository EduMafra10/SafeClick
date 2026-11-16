"""Liga cada sinal de risco ao trecho da mensagem em que ele aparece."""
import re

ALVOS = {
    "remetente": "origem",
    "assunto": "assunto",
    "botão": "chamada",
    "botao": "chamada",
    "produto": "produto",
}
_PREFIXO = re.compile(r"^\[\s*([^\]]{1,20}?)\s*\]\s*(\S.*)$")
_PARAGRAFO = re.compile(r"par[aá]grafo\s*(\d{1,2})")


def separar_pistas(sinais):
    """Devolve os textos dos sinais e, para cada trecho marcado, os números dos sinais."""
    if isinstance(sinais, str):
        sinais = [linha.strip() for linha in sinais.splitlines() if linha.strip()]
    textos, marcas = [], {}
    for numero, sinal in enumerate(sinais or [], start=1):
        texto, alvo = sinal, None
        prefixo = _PREFIXO.match(sinal)
        if prefixo:
            chave = prefixo.group(1).lower()
            paragrafo = _PARAGRAFO.fullmatch(chave)
            alvo = f"paragrafo-{int(paragrafo.group(1))}" if paragrafo else ALVOS.get(chave)
            if alvo:
                texto = prefixo.group(2)
        textos.append(texto)
        if alvo:
            marcas.setdefault(alvo, []).append(numero)
    return textos, marcas
