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


def exportar_epub(livro_id, destino):
    """Exporta um livro para EPUB 3 usando apenas a biblioteca padrão."""
    import html
    import re
    import uuid
    import zipfile
    from datetime import datetime, timezone

    livro = obter_livro(livro_id)
    if livro is None:
        raise ValueError(f"Livro {livro_id} não encontrado.")

    caminho = Path(destino)
    caminho.parent.mkdir(parents=True, exist_ok=True)

    escapar = html.escape
    titulo = escapar(livro["titulo"] or "Livro sem título")
    autor = escapar(livro["autor"] or "")
    descricao = escapar(livro["descricao"] or "")
    identificador = f"urn:uuid:{uuid.uuid4()}"
    modificacao = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    secoes = []
    itens_indice = []

    for indice, capitulo in enumerate(livro["capitulos"], start=1):
        id_capitulo = f"capitulo-{indice}"
        titulo_capitulo = escapar(
            capitulo["titulo"] or f"Capítulo {indice}"
        )
        conteudo = (capitulo["conteudo"] or "").strip()
        paragrafos = re.split(r"\n\s*\n", conteudo) if conteudo else []
        texto_html = "".join(
            "<p>" + escapar(paragrafo).replace("\n", "<br />") + "</p>"
            for paragrafo in paragrafos
        )

        secoes.append(
            f'<section id="{id_capitulo}">'
            f"<h2>{titulo_capitulo}</h2>{texto_html}</section>"
        )
        itens_indice.append(
            f'<li><a href="content.xhtml#{id_capitulo}">'
            f"{titulo_capitulo}</a></li>"
        )

    descricao_html = f"<p>{descricao}</p>" if descricao else ""
    autor_html = f"<p>{autor}</p>" if autor else ""

    conteudo_xhtml = (
        '<?xml version="1.0" encoding="utf-8"?>'
        '<html xmlns="http://www.w3.org/1999/xhtml" lang="pt-BR">'
        "<head><title>" + titulo + "</title>"
        '<meta charset="utf-8"/>'
        "<style>body{line-height:1.5;margin:5%;}"
        "h1,h2{text-align:left;}p{text-align:justify;}</style>"
        "</head><body>"
        f"<h1>{titulo}</h1>{autor_html}{descricao_html}"
        + "".join(secoes)
        + "</body></html>"
    )

    navegacao_xhtml = (
        '<?xml version="1.0" encoding="utf-8"?>'
        '<html xmlns="http://www.w3.org/1999/xhtml" '
        'xmlns:epub="http://www.idpf.org/2007/ops" lang="pt-BR">'
        "<head><title>Índice</title></head><body>"
        '<nav epub:type="toc" id="toc"><h1>Índice</h1><ol>'
        + "".join(itens_indice)
        + "</ol></nav></body></html>"
    )

    metadados_autor = f"<dc:creator>{autor}</dc:creator>" if autor else ""
    metadados_descricao = (
        f"<dc:description>{descricao}</dc:description>" if descricao else ""
    )

    pacote_opf = (
        '<?xml version="1.0" encoding="utf-8"?>'
        '<package xmlns="http://www.idpf.org/2007/opf" '
        'xmlns:dc="http://purl.org/dc/elements/1.1/" '
        'version="3.0" unique-identifier="book-id" xml:lang="pt-BR">'
        "<metadata>"
        f'<dc:identifier id="book-id">{identificador}</dc:identifier>'
        f"<dc:title>{titulo}</dc:title>"
        "<dc:language>pt-BR</dc:language>"
        f"{metadados_autor}{metadados_descricao}"
        f'<meta property="dcterms:modified">{modificacao}</meta>'
        "</metadata>"
        '<manifest>'
        '<item id="content" href="content.xhtml" '
        'media-type="application/xhtml+xml"/>'
        '<item id="nav" href="nav.xhtml" '
        'media-type="application/xhtml+xml" properties="nav"/>'
        "</manifest>"
        '<spine><itemref idref="content"/></spine>'
        "</package>"
    )

    container_xml = (
        '<?xml version="1.0" encoding="utf-8"?>'
        '<container xmlns="urn:oasis:names:tc:opendocument:xmlns:container" '
        'version="1.0"><rootfiles><rootfile '
        'full-path="OEBPS/content.opf" '
        'media-type="application/oebps-package+xml"/>'
        "</rootfiles></container>"
    )

    with zipfile.ZipFile(caminho, "w") as arquivo:
        arquivo.writestr(
            "mimetype",
            "application/epub+zip",
            compress_type=zipfile.ZIP_STORED,
        )
        arquivo.writestr("META-INF/container.xml", container_xml)
        arquivo.writestr("OEBPS/content.opf", pacote_opf)
        arquivo.writestr("OEBPS/content.xhtml", conteudo_xhtml)
        arquivo.writestr("OEBPS/nav.xhtml", navegacao_xhtml)

    return caminho
