"""Regras do desafio "Qual vazou mais?" do Laboratório de senhas

As senhas abaixo são exemplos públicos e muito conhecidos. O desafio nunca
usa nada que o usuário digita: ele só escolhe qual das duas apareceu mais
"""

import secrets
import threading
import time

TOTAL_RODADAS = 5

# Todas são senhas públicas e muito conhecidas, presentes na base do Have I Been Pwned.
SENHAS_EXEMPLO = {
    # Sequências e repetições numéricas
    "123456": "Sequências numéricas são as primeiras combinações testadas por criminosos.",
    "123456789": "Uma sequência mais longa continua sendo uma sequência: ela é testada logo no início.",
    "111111": "Repetir o mesmo caractere não deixa a senha mais forte.",
    "000000": "Zeros repetidos lembram senhas de fábrica e estão entre as primeiras tentativas.",
    "123123": "Repetir um bloco de números cria um padrão fácil de prever.",
    "654321": "Inverter uma sequência é um truque que os ataques já conhecem.",
    "102030": "Padrões numéricos populares no Brasil também estão nas listas de ataque.",

    # Desenhos no teclado
    "qwerty": "Seguir as teclas em linha no teclado cria um padrão muito conhecido.",
    "qwertyuiop": "Uma linha inteira do teclado é longa, mas totalmente previsível.",
    "asdfgh": "A linha do meio do teclado também está nas listas de ataque.",
    "1q2w3e4r": "Alternar números e letras vizinhos no teclado ainda forma um padrão previsível.",
    "159753": "Desenhar um X no teclado numérico é um padrão que os ataques testam.",
    "147258369": "Percorrer o teclado numérico coluna por coluna é um desenho conhecido.",

    # Palavras óbvias e truques que não funcionam
    "password": "É a palavra \"senha\" em inglês: uma das primeiras tentativas em qualquer ataque.",
    "senha": "Usar a própria palavra \"senha\" é uma das primeiras coisas que um atacante tenta.",
    "senha123": "Uma palavra comum com números no fim continua fácil de adivinhar.",
    "admin": "Nomes de usuário padrão usados como senha são testados primeiro.",
    "abc123": "Juntar o começo do alfabeto com números é um padrão previsível.",
    "mudar123": "Senhas provisórias que nunca foram trocadas são alvos fáceis.",
    "p@ssw0rd": "Trocar letras por símbolos parecidos (a por @, o por 0) é um truque que os ataques testam automaticamente.",
    "Password1": "Maiúscula no começo e número no fim cumprem a regra do cadastro, mas formam o padrão mais previsível.",

    # Futebol
    "flamengo": "Times de futebol são escolhas comuns e entram nas listas de ataque.",
    "corinthians": "Mesmo nomes longos são fracos quando são palavras conhecidas.",
    "palmeiras": "Paixões populares viram senhas populares, e senhas populares vazam mais.",
    "vasco": "Clubes de todas as regiões aparecem nas listas usadas para adivinhar senhas.",
    "cruzeiro": "Torcer por um time é público: qualquer pessoa pode descobrir e testar.",
    "gremio": "Nomes de clubes são palavras de dicionário para quem ataca senhas.",

    # Nomes, afeto e dia a dia
    "gabriel": "Nomes próprios estão entre as primeiras palavras testadas.",
    "lucas": "Seu nome ou o de alguém próximo é uma das primeiras coisas que um atacante tenta.",
    "maria": "Nomes populares no Brasil estão em listas feitas para ataques em português.",
    "princesa": "Apelidos carinhosos são previsíveis para quem tenta adivinhar.",
    "familia": "Palavras afetivas, como família e amor, são escolhas comuns e previsíveis.",
    "iloveyou": "Frases famosas estão nas listas usadas para adivinhar senhas.",
    "cachorro": "Animais de estimação e palavras do dia a dia são fáceis de adivinhar.",
    "brasil": "Nomes de países e cidades são palavras de dicionário, fáceis de testar.",

    # Cultura pop
    "minecraft": "Nomes de jogos e séries famosos são fáceis de adivinhar.",
    "naruto": "Personagens de animes e desenhos são escolhas populares e previsíveis.",
    "pokemon": "Franquias famosas estão nas listas de palavras usadas em ataques.",
    "batman": "Super-heróis são escolhas comuns no mundo inteiro.",
    "dragon": "Palavras populares em outros idiomas também estão nas listas de ataque.",
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