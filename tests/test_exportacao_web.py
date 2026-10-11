
import pytest

from app import exportacao_web
from app.servidor_web import app


@pytest.fixture
def cliente():
    app.config["TESTING"] = True
    with app.test_client() as cliente:
        yield cliente


def test_baixar_markdown_com_sucesso(cliente, monkeypatch):
    def exportacao_falsa(livro_id, destino):
        destino.write_text(
            "# Livro de teste\n",
            encoding="utf-8",
        )
        return destino

    monkeypatch.setattr(
        exportacao_web,
        "exportar_markdown",
        exportacao_falsa,
    )

    resposta = cliente.get(
        "/api/livros/1/exportar/markdown"
    )

    assert resposta.status_code == 200
    assert resposta.mimetype == "text/markdown"
    assert b"# Livro de teste" in resposta.data


def test_baixar_markdown_livro_inexistente(cliente, monkeypatch):
    def livro_inexistente(livro_id, destino):
        raise ValueError(f"Livro {livro_id} não encontrado.")

    monkeypatch.setattr(
        exportacao_web,
        "exportar_markdown",
        livro_inexistente,
    )

    resposta = cliente.get(
        "/api/livros/999/exportar/markdown"
    )

    assert resposta.status_code == 404
    assert "não encontrado" in resposta.get_json()["erro"]


def test_baixar_pdf_com_sucesso(cliente, monkeypatch):
    def pdf_falso(livro_id, destino):
        destino.write_bytes(b"%PDF-1.4 teste")
        return destino

    monkeypatch.setattr(
        exportacao_web,
        "exportar_pdf",
        pdf_falso,
    )

    resposta = cliente.get("/api/livros/1/exportar/pdf")

    assert resposta.status_code == 200
    assert resposta.mimetype == "application/pdf"
    assert resposta.data.startswith(b"%PDF-1.4")


def test_baixar_pdf_livro_inexistente(cliente, monkeypatch):
    def livro_inexistente(livro_id, destino):
        raise ValueError(f"Livro {livro_id} não encontrado.")

    monkeypatch.setattr(
        exportacao_web,
        "exportar_pdf",
        livro_inexistente,
    )

    resposta = cliente.get("/api/livros/999/exportar/pdf")

    assert resposta.status_code == 404
    assert "não encontrado" in resposta.get_json()["erro"]


def test_baixar_pdf_com_erro_de_geracao(cliente, monkeypatch):
    def erro_pdf(livro_id, destino):
        raise RuntimeError("Falha ao gerar PDF: erro de teste")

    monkeypatch.setattr(
        exportacao_web,
        "exportar_pdf",
        erro_pdf,
    )

    resposta = cliente.get("/api/livros/1/exportar/pdf")

    assert resposta.status_code == 500
    assert "Falha ao gerar PDF" in resposta.get_json()["erro"]

