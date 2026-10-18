
import os

import requests

import unicodedata

URL_PADRAO = "https://api.languagetool.org/v2/check"
TEMPO_LIMITE = 10
TAMANHO_MAXIMO = 20000


def _sem_acentos(texto):
    return "".join(
        caractere
        for caractere in unicodedata.normalize("NFD", texto)
        if unicodedata.category(caractere) != "Mn"
    )


def _classificar_categoria(item, trecho_original, sugestoes):
    regra = item.get("rule", {})
    if not isinstance(regra, dict):
        regra = {}

    categoria = regra.get("category", {})
    if not isinstance(categoria, dict):
        categoria = {}

    categoria_id = str(categoria.get("id", "")).upper()
    tipo = str(regra.get("issueType", "")).lower()
    regra_id = str(regra.get("id", "")).upper()

    if (
        "WORD_REPEAT_BEGINNING" in regra_id
        or "REPETITION" in regra_id
    ):
        return "repeticao"

    if categoria_id == "PUNCTUATION" or tipo == "punctuation":
        return "pontuacao"

    if categoria_id == "GRAMMAR" or tipo == "grammar":
        return "gramatica"

    diferenca_so_de_acentos = any(
        isinstance(sugestao, str)
        and sugestao != trecho_original
        and trecho_original.isalpha()
        and sugestao.isalpha()
        and _sem_acentos(sugestao).casefold()
        == _sem_acentos(trecho_original).casefold()
        for sugestao in sugestoes
    )

    if diferenca_so_de_acentos:
        return "acentuacao"

    if any(
        palavra in regra_id
        for palavra in ("ACENT", "ACCENT", "DIACRITIC")
    ):
        return "acentuacao"

    if categoria_id == "TYPOS" or tipo in {
        "misspelling",
        "typographical",
    }:
        return "ortografia"

    if (
        categoria_id in {"STYLE", "REDUNDANCY"}
        or tipo == "style"
    ):
        return "estilo"

    return "outro"


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

        valores_sugeridos = [
            sugestao["value"]
            for sugestao in substituicoes
            if isinstance(sugestao, dict)
            and isinstance(sugestao.get("value"), str)
        ]

        trecho_original = ""
        offset = item.get("offset")
        comprimento = item.get("length")

        if (
            isinstance(offset, int)
            and isinstance(comprimento, int)
            and offset >= 0
            and comprimento > 0
            and offset + comprimento <= len(texto)
        ):
            trecho_original = texto[offset:offset + comprimento]

        categoria = _classificar_categoria(
            item,
            trecho_original,
            valores_sugeridos,
        )

        sugestoes.append(
            {
                "mensagem": item.get("message", ""),
                "trecho": contexto.get("text", ""),
                "offset": item.get("offset"),
                "comprimento": item.get("length"),
                "categoria": categoria,
                "sugestoes": valores_sugeridos,
            }
        )


    return {
        "texto_original": texto,
        "quantidade": len(sugestoes),
        "sugestoes": sugestoes,
    }
