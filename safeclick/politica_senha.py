"""Complementa a política de senha (15 a 128 caracteres, sem regras de composição)
recusando senhas triviais, como recomenda a OWASP. A mesma regra roda em static/js/politica_senha.js."""
import re
import unicodedata

MINIMO = 15
MAXIMO = 128
# palavras que não deixam a senha mais difícil de adivinhar
OBVIAS = ("senha", "password", "safeclick", "qwerty", "admin", "brasil", "teste", "abc", "123")
SEQUENCIAS = ("abcdefghijklmnopqrstuvwxyz", "0123456789", "qwertyuiop", "asdfghjkl", "zxcvbnm")

MENSAGEM_TRIVIAL = (
    "Evite repetições, sequências e palavras óbvias, como \"senha\" ou \"123456\". "
    "Uma frase com várias palavras é mais segura."
)
MENSAGEM_PESSOAL = "Não use o seu nome ou o seu e-mail na senha."


def normalizar(texto):
    sem_acento = unicodedata.normalize("NFKD", texto or "").encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]", "", sem_acento.lower())


def _vizinhas(a, b):
    return any(a + b in s or b + a in s for s in SEQUENCIAS)


def senha_trivial(senha):
    if len(set(senha.lower())) < 5:
        return True
    nucleo = normalizar(senha)
    for palavra in OBVIAS:
        nucleo = nucleo.replace(palavra, "")
    if len(set(nucleo)) < 4:
        return True
    pares = len(nucleo) - 1
    seguidos = sum(_vizinhas(nucleo[i], nucleo[i + 1]) for i in range(pares))
    return seguidos / pares >= 0.7


def usa_dados_pessoais(senha, nome=None, email=None):
    alvo = normalizar(senha)
    partes = [normalizar(p) for p in (nome or "").split()]
    partes.append(normalizar((email or "").split("@")[0]))
    return any(len(parte) >= 4 and parte in alvo for parte in partes)


def problema_senha(senha, nome=None, email=None):
    """Devolve a mensagem do problema ou None. O tamanho é conferido pelo próprio formulário."""
    if not isinstance(senha, str) or not MINIMO <= len(senha) <= MAXIMO:
        return None
    if usa_dados_pessoais(senha, nome, email):
        return MENSAGEM_PESSOAL
    if senha_trivial(senha):
        return MENSAGEM_TRIVIAL
    return None
