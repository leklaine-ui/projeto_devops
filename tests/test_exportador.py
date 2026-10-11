
import subprocess

import pytest

from app import exportador, livros_db


@pytest.fixture
def banco_teste(tmp_path, monkeypatch):
    banco = tmp_path / "livros.db"
    monkeypatch.setattr(livros_db, "BANCO", str(banco))
    monkeypatch.setattr(
        "app.exportador.conectar_banco",
        livros_db.conectar_banco,
    )

    livros_db.criar_tabelas_livros()

    with livros_db.conectar_banco() as conexao:
        cursor = conexao.execute(
            """
            INSERT INTO livros (titulo, autor, descricao)
            VALUES (?, ?, ?)
            """,
            ("Livro de teste", "Autor de teste", "Descrição de teste"),
        )
        livro_id = cursor.lastrowid

        conexao.execute(
            """
            INSERT INTO capitulos (livro_id, titulo, conteudo, ordem)
            VALUES (?, ?, ?, ?)
            """,
            (livro_id, "Capítulo 1", "Conteúdo do capítulo", 1),
        )

    return livro_id

def test_obter_livro_com_capitulos(banco_teste):
    livro = exportador.obter_livro(banco_teste)

    assert livro["titulo"] == "Livro de teste"
    assert livro["autor"] == "Autor de teste"
    assert len(livro["capitulos"]) == 1
    assert livro["capitulos"][0]["titulo"] == "Capítulo 1"


def test_obter_livro_inexistente(banco_teste):
    assert exportador.obter_livro(-1) is None


def test_gerar_markdown_completo():
    livro = {
        "titulo": "Meu Livro",
        "autor": "Minha Autora",
        "descricao": "Uma descrição.",
        "capitulos": [
            {
                "titulo": "Introdução",
                "conteudo": " Texto do capítulo ",
                "ordem": 1,
            }
        ],
    }

    markdown = exportador.gerar_markdown(livro)

    assert "# Meu Livro" in markdown
    assert "**Autor:** Minha Autora" in markdown
    assert "Uma descrição." in markdown
    assert "## Introdução" in markdown
    assert "Texto do capítulo" in markdown


def test_gerar_markdown_sem_autor_ou_descricao():
    livro = {
        "titulo": "Livro simples",
        "autor": "",
        "descricao": "",
        "capitulos": [],
    }

    markdown = exportador.gerar_markdown(livro)

    assert markdown == "# Livro simples\n"

def test_exportar_markdown_cria_arquivo(banco_teste, tmp_path):
    destino = tmp_path / "subpasta" / "livro.md"

    resultado = exportador.exportar_markdown(banco_teste, destino)

    assert resultado == destino
    assert destino.exists()
    assert "# Livro de teste" in destino.read_text(encoding="utf-8")


def test_exportar_markdown_livro_inexistente(tmp_path):
    with pytest.raises(ValueError, match="não encontrado"):
        exportador.exportar_markdown(-1, tmp_path / "livro.md")


def test_exportar_pdf_livro_inexistente(tmp_path):
    with pytest.raises(ValueError, match="não encontrado"):
        exportador.exportar_pdf(-1, tmp_path / "livro.pdf")


def test_exportar_pdf_pandoc_ausente(
    banco_teste, tmp_path, monkeypatch
):
    def pandoc_ausente(*args, **kwargs):
        raise FileNotFoundError("pandoc")

    monkeypatch.setattr(subprocess, "run", pandoc_ausente)

    with pytest.raises(RuntimeError, match="Pandoc não encontrado"):
        exportador.exportar_pdf(
            banco_teste,
            tmp_path / "livro.pdf",
        )


def test_exportar_pdf_com_falha(
    banco_teste, tmp_path, monkeypatch
):
    processo = subprocess.CompletedProcess(
        args=["pandoc"],
        returncode=1,
        stdout="",
        stderr="Erro de conversão",
    )

    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: processo,
    )

    with pytest.raises(RuntimeError, match="Erro de conversão"):
        exportador.exportar_pdf(
            banco_teste,
            tmp_path / "livro.pdf",
        )


def test_exportar_pdf_sem_detalhe_de_erro(
    banco_teste, tmp_path, monkeypatch
):
    processo = subprocess.CompletedProcess(
        args=["pandoc"],
        returncode=1,
        stdout="",
        stderr="",
    )

    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: processo,
    )

    with pytest.raises(RuntimeError, match="Erro desconhecido"):
        exportador.exportar_pdf(
            banco_teste,
            tmp_path / "livro.pdf",
        )


def test_exportar_pdf_com_sucesso(
    banco_teste, tmp_path, monkeypatch
):
    chamadas = {}

    def pandoc_simulado(comando, **kwargs):
        chamadas["comando"] = comando
        chamadas.update(kwargs)

        return subprocess.CompletedProcess(
            args=comando,
            returncode=0,
            stdout="",
            stderr="",
        )

    monkeypatch.setattr(subprocess, "run", pandoc_simulado)

    destino = tmp_path / "livro.pdf"

    resultado = exportador.exportar_pdf(banco_teste, destino)

    assert resultado == destino
    assert chamadas["comando"][0] == "pandoc"
    assert "--pdf-engine=xelatex" in chamadas["comando"]
    assert chamadas["comando"][-1] == str(destino)
    assert "# Livro de teste" in chamadas["input"]
    assert chamadas["check"] is False

