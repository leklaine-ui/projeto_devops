
import os

import requests

URL_PADRAO = "https://api.languagetool.org/v2/check"
TEMPO_LIMITE = 10
TAMANHO_MAXIMO = 20000


class ErroCorretor(RuntimeError):
    """Erro ao consultar o serviço local de correção."""


def corrigir_texto(texto):
    if not isinstance(texto, str):
        raise ValueError("O conteúdo deve ser um texto.")

    if not texto.strip():
        raise ValueError("Digite um texto para corrigir.")

    if len(texto.encode("utf-8")) > TAMANHO_MAXIMO:
        raise ValueError("O texto excede o limite de 20 KB.")

    url = os.environ.get("LANGUAGETOOL_URL", URL_PADRAO)

    try:
        resposta = requests.post(
            url,
            data={"text": texto, "language": "pt-BR"},
            timeout=TEMPO_LIMITE,
        )
        resposta.raise_for_status()
        dados = resposta.json()
    except (requests.RequestException, ValueError) as erro:
        raise ErroCorretor(
            "O corretor local está indisponível ou retornou "
            "uma resposta inválida."
        ) from erro

    if not isinstance(dados, dict):
        raise ErroCorretor("Resposta inválida do corretor local.")

    correspondencias = dados.get("matches")

    if not isinstance(correspondencias, list):
        raise ErroCorretor("Resposta inválida do corretor local.")

    sugestoes = []

    for item in correspondencias:
        if not isinstance(item, dict):
            continue

        contexto = item.get("context", {})
        substituicoes = item.get("replacements", [])

        if not isinstance(contexto, dict):
            contexto = {}

        if not isinstance(substituicoes, list):
            substituicoes = []

        sugestoes.append(
            {
                "mensagem": item.get("message", ""),
                "trecho": contexto.get("text", ""),
                "offset": item.get("offset"),
                "comprimento": item.get("length"),
                "sugestoes": [
                    sugestao["value"]
                    for sugestao in substituicoes
                    if isinstance(sugestao, dict)
                    and isinstance(sugestao.get("value"), str)
                ],
            }
        )

    return {
        "texto_original": texto,
        "quantidade": len(sugestoes),
        "sugestoes": sugestoes,
    }
