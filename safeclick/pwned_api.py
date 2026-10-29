import re

import requests
from requests.exceptions import RequestException

URL_PWNED_PASSWORDS = "https://api.pwnedpasswords.com/range/"


class ServicoSenhasIndisponivel(RuntimeError):
    """A consulta externa não pôde ser concluída com segurança."""


def consultar_prefixo_senha(prefixo):
    """Consulta somente os cinco primeiros caracteres de um hash SHA-1."""
    if not isinstance(prefixo, str) or not re.fullmatch(
        r"[A-Fa-f0-9]{5}", prefixo
    ):
        raise ValueError("Informe um prefixo válido de cinco caracteres.")

    prefixo = prefixo.upper()

    try:
        with requests.get(
            URL_PWNED_PASSWORDS + prefixo,
            headers={
                "User-Agent": "SafeClick-Verificador-Senhas/1.0",
                "Add-Padding": "true",
            },
            timeout=(3.05, 10),
            allow_redirects=False,
        ) as resposta:
            
            if resposta.status_code != 200:
                raise ServicoSenhasIndisponivel(
                    "Não foi possível consultar a base de senhas agora."
                )

            texto = resposta.text
    except RequestException:
        raise ServicoSenhasIndisponivel(
            "Não foi possível consultar a base de senhas agora."
        ) from None

    linhas = texto.splitlines()

    
    if not linhas or any(
        re.fullmatch(r"[A-Fa-f0-9]{35}:[0-9]{1,15}", linha) is None
        for linha in linhas
    ):
        raise ServicoSenhasIndisponivel(
            "A base de senhas retornou uma resposta inválida."
        )

    
    return "\r\n".join(linhas).upper()