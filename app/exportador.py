import subprocess
from pathlib import Path

from app.livros_db import conectar_banco


def obter_livro(livro_id):
    """Busca um livro e seus capítulos."""
    with conectar_banco() as conexao:
        livro = conexao.execute(
            """
            SELECT id, titulo, autor, descricao
            FROM livros
            WHERE id = ?
            """,
            (livro_id,),
        ).fetchone()

        if livro is None:
            return None

        capitulos = conexao.execute(
            """
            SELECT titulo, conteudo, ordem
            FROM capitulos
            WHERE livro_id = ?
            ORDER BY ordem, id
            """,
            (livro_id,),
        ).fetchall()

    resultado = dict(livro)
    resultado["capitulos"] = [dict(c) for c in capitulos]
    return resultado


def gerar_markdown(livro):
    """Converte os dados de um livro em Markdown."""
    linhas = [f"# {livro['titulo']}", ""]

    if livro["autor"]:
        linhas.extend([f"**Autor:** {livro['autor']}", ""])

    if livro["descricao"]:
        linhas.extend([livro["descricao"], ""])

    for capitulo in livro["capitulos"]:
        linhas.extend([
            f"## {capitulo['titulo']}",
            "",
            capitulo["conteudo"].strip(),
            "",
        ])

    return "\n".join(linhas).rstrip() + "\n"


def exportar_markdown(livro_id, destino):
    """Salva o livro em um arquivo Markdown."""
    livro = obter_livro(livro_id)

    if livro is None:
        raise ValueError(f"Livro {livro_id} não encontrado.")

    caminho = Path(destino)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(gerar_markdown(livro), encoding="utf-8")
    return caminho


def exportar_pdf(livro_id, destino):
    """Exporta o livro para PDF usando Pandoc e XeLaTeX."""
    livro = obter_livro(livro_id)

    if livro is None:
        raise ValueError(f"Livro {livro_id} não encontrado.")

    caminho = Path(destino)
    caminho.parent.mkdir(parents=True, exist_ok=True)

    comando = [
        "pandoc",
        "--from=markdown",
        "--pdf-engine=xelatex",
        "--metadata",
        f"title={livro['titulo']}",
        "--metadata",
        f"author={livro['autor']}",
        "-o",
        str(caminho),
    ]

    try:
        processo = subprocess.run(
            comando,
            input=gerar_markdown(livro),
            text=True,
            capture_output=True,
            check=False,
        )
    except FileNotFoundError as erro:
        raise RuntimeError(
            "Pandoc não encontrado. Verifique a instalação."
        ) from erro

    if processo.returncode != 0:
        detalhe = processo.stderr.strip() or "Erro desconhecido."
        raise RuntimeError(f"Falha ao gerar PDF: {detalhe}")

    return caminho
