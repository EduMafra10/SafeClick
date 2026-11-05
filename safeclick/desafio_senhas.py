"""Regras do desafio "Qual vazou mais?" do Laboratório de senhas

As senhas abaixo são exemplos públicos e muito conhecidos. O desafio nunca
usa nada que o usuário digita: ele só escolhe qual das duas apareceu mais
"""

import secrets
import threading
import time

TOTAL_RODADAS = 5

# Cada senha de exemplo vem com a lição que ela ensina
SENHAS_EXEMPLO = {
    "123456": "Sequências numéricas são as primeiras combinações testadas por criminosos.",
    "password": "É a palavra \"senha\" em inglês: uma das primeiras tentativas em qualquer ataque.",
    "senha123": "Uma palavra comum com números no fim continua fácil de adivinhar.",
    "qwerty": "Seguir as teclas em linha no teclado cria um padrão muito conhecido.",
    "111111": "Repetir o mesmo caractere não deixa a senha mais forte.",
    "abc123": "Juntar o começo do alfabeto com números é um padrão previsível.",
    "iloveyou": "Frases famosas estão nas listas usadas para adivinhar senhas.",
    "102030": "Padrões numéricos populares no Brasil também estão nas listas de ataque.",
    "brasil": "Nomes de países e cidades são palavras de dicionário, fáceis de testar.",
    "flamengo": "Times de futebol são escolhas comuns e entram nas listas de ataque.",
    "corinthians": "Mesmo nomes longos são fracos quando são palavras conhecidas.",
    "palmeiras": "Paixões populares viram senhas populares, e senhas populares vazam mais.",
    "gabriel": "Nomes próprios estão entre as primeiras palavras testadas.",
    "princesa": "Apelidos carinhosos são previsíveis para quem tenta adivinhar.",
    "minecraft": "Nomes de jogos e séries famosos são fáceis de adivinhar.",
    "mudar123": "Senhas provisórias que nunca foram trocadas são alvos fáceis.",
}

LISTA_SENHAS = tuple(SENHAS_EXEMPLO)


_VALIDADE_CACHE = 12 * 60 * 60
_cache = {}
_trava_cache = threading.Lock()


def sortear_partida():
    
    sorteadas = secrets.SystemRandom().sample(range(len(LISTA_SENHAS)), TOTAL_RODADAS * 2)
    return [[sorteadas[i], sorteadas[i + 1]] for i in range(0, len(sorteadas), 2)]


def senhas_da_rodada(par):
    return [LISTA_SENHAS[indice] for indice in par]


def contagem_em_cache(senha):
    with _trava_cache:
        guardado = _cache.get(senha)
    if guardado and time.monotonic() - guardado[1] < _VALIDADE_CACHE:
        return guardado[0]
    return None


def guardar_contagem(senha, quantidade):
    with _trava_cache:
        _cache[senha] = (quantidade, time.monotonic())


def limpar_cache():
    with _trava_cache:
        _cache.clear()


def escolha_correta(contagens, escolha):
   
    return contagens[escolha] >= contagens[1 - escolha]