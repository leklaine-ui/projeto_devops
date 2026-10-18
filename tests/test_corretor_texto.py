
import pytest
import requests

from app.corretor_texto import (
    ErroCorretor,
    corrigir_texto,
)


class RespostaFalsa:
    def __init__(self, dados):
        self.dados = dados

    def raise_for_status(self):
        pass

    def json(self):
        return self.dados


def test_corrigir_texto_com_sugestoes(monkeypatch):
    def post_falso(url, data, timeout):
        assert data["text"] == "Ola mundo"
        assert data["language"] == "pt-BR"
        assert timeout == 10

        return RespostaFalsa(
            {
                "matches": [
                    {
                        "message": "Possível erro ortográfico",
                        "context": {"text": "Ola mundo"},
                        "offset": 0,
                        "length": 3,
                        "replacements": [
                            {"value": "Olá"},
                            {"value": "Ola!"},
                        ],
                    }
                ]
            }
        )

    monkeypatch.setattr(
        "app.corretor_texto.requests.post",
        post_falso,
    )

    resultado = corrigir_texto("Ola mundo")

    assert resultado["texto_original"] == "Ola mundo"
    assert resultado["quantidade"] == 1
    assert resultado["sugestoes"][0]["mensagem"] == (
        "Possível erro ortográfico"
    )
    assert resultado["sugestoes"][0]["trecho"] == "Ola mundo"
    assert resultado["sugestoes"][0]["offset"] == 0
    assert resultado["sugestoes"][0]["comprimento"] == 3
    assert resultado["sugestoes"][0]["sugestoes"] == [
        "Olá",
        "Ola!",
    ]


@pytest.mark.parametrize(
    "texto",
    [
        None,
        123,
        [],
    ],
)
def test_rejeita_conteudo_que_nao_e_texto(texto):
    with pytest.raises(ValueError, match="deve ser um texto"):
        corrigir_texto(texto)


@pytest.mark.parametrize("texto", ["", "   ", "\n\t"])
def test_rejeita_texto_vazio(texto):
    with pytest.raises(ValueError, match="Digite um texto"):
        corrigir_texto(texto)


def test_rejeita_texto_maior_que_limite():
    texto = "a" * 20001

    with pytest.raises(ValueError, match="20 KB"):
        corrigir_texto(texto)


def test_rejeita_resposta_sem_matches(monkeypatch):
    monkeypatch.setattr(
        "app.corretor_texto.requests.post",
        lambda *args, **kwargs: RespostaFalsa({}),
    )

    with pytest.raises(ErroCorretor, match="Resposta inválida"):
        corrigir_texto("Olá mundo")


def test_trata_falha_de_conexao(monkeypatch):
    def post_falso(*args, **kwargs):
        raise requests.ConnectionError("Serviço indisponível")

    monkeypatch.setattr(
        "app.corretor_texto.requests.post",
        post_falso,
    )

    with pytest.raises(ErroCorretor, match="indisponível"):
        corrigir_texto("Olá mundo")


def test_ignora_itens_invalidos_e_normaliza_campos(monkeypatch):
    monkeypatch.setattr(
        "app.corretor_texto.requests.post",
        lambda *args, **kwargs: RespostaFalsa(
            {
                "matches": [
                    None,
                    {
                        "message": "Erro encontrado",
                        "context": None,
                        "replacements": [
                            None,
                            {"value": "Correção"},
                            {"value": 123},
                        ],
                    },
                ]
            }
        ),
    )

    resultado = corrigir_texto("Texto de teste")

    assert resultado["quantidade"] == 1
    assert resultado["sugestoes"][0]["trecho"] == ""
    assert resultado["sugestoes"][0]["sugestoes"] == [
        "Correção"
    ]


@pytest.mark.parametrize(
    "item, original, sugestoes, esperado",
    [
        (
            {"rule": {"category": {"id": "TYPOS"}}},
            "caza",
            ["casa"],
            "ortografia",
        ),
        (
            {"rule": {"category": {"id": "GRAMMAR"}}},
            "as pessoa",
            ["as pessoas"],
            "gramatica",
        ),
        (
            {"rule": {"category": {"id": "PUNCTUATION"}}},
            "Olá mundo",
            ["Olá, mundo"],
            "pontuacao",
        ),
        (
            {"rule": {"category": {"id": "TYPOS"}}},
            "Ola",
            ["Olá"],
            "acentuacao",
        ),
        (
            {"rule": {}},
            "caza",
            ["casa"],
            "outro",
        ),
        (
            {
                "rule": {
                    "id": "PORTUGUESE_WORD_REPEAT_BEGINNING_RULE",
                    "category": {"id": "STYLE"},
                    "issueType": "style",
                }
            },
            "Livre",
            [],
            "repeticao",
        ),
        (
            {
                "rule": {
                    "id": "PT_WORDINESS_REPLACE_AINDA_ESTÁ",
                    "category": {"id": "REDUNDANCY"},
                    "issueType": "style",
                }
            },
            "ainda está",
            ["continua"],
            "estilo",
        ),
    ],
)
def test_classifica_categorias(
    item,
    original,
    sugestoes,
    esperado,
):
    from app.corretor_texto import _classificar_categoria

    assert _classificar_categoria(
        item,
        original,
        sugestoes,
    ) == esperado
