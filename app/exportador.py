import subprocess
from pathlib import Path

from app.livros_db import conectar_banco


def obter_livro(livro_id):
    """Busca um livro e seus capítulos."""
    with conectar_banco() as conexao:
        livro = conexao.execute(
            """
            SELECT id, titulo, autor, descricao,
                   introducao, conclusao, epilogo, capa
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
    """Converte os dados completos de um livro em Markdown."""
    linhas = [f"# {livro['titulo']}", ""]

    if livro.get("autor"):
        linhas.extend([f"**Autor:** {livro['autor']}", ""])

    if livro.get("descricao"):
        linhas.extend([livro["descricao"], ""])

    if livro.get("introducao"):
        linhas.extend([
            "## Introdução",
            "",
            livro["introducao"].strip(),
            "",
        ])

    for capitulo in livro["capitulos"]:
        linhas.extend([
            f"## {capitulo['titulo']}",
            "",
            (capitulo["conteudo"] or "").strip(),
            "",
        ])

    if livro.get("conclusao"):
        linhas.extend([
            "## Conclusão",
            "",
            livro["conclusao"].strip(),
            "",
        ])

    if livro.get("epilogo"):
        linhas.extend([
            "## Epílogo",
            "",
            livro["epilogo"].strip(),
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
        "--table-of-contents",
        "--metadata=toc-title=Sumário",
        "--toc-depth=2",
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
    """Exporta um livro completo para EPUB 3, incluindo sua capa."""
    import html
    import mimetypes
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
    titulo = escapar(livro.get("titulo") or "Livro sem título")
    autor = escapar(livro.get("autor") or "")
    descricao = escapar(livro.get("descricao") or "")
    identificador = f"urn:uuid:{uuid.uuid4()}"
    modificacao = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    secoes = []
    itens_indice = []

    def adicionar_secao(id_secao, nome, conteudo):
        if not conteudo:
            return

        paragrafos = re.split(r"\n\s*\n", conteudo.strip())
        texto_html = "".join(
            "<p>" + escapar(paragrafo).replace("\n", "<br />") + "</p>"
            for paragrafo in paragrafos
            if paragrafo.strip()
        )

        nome_html = escapar(nome)
        secoes.append(
            f'<section id="{id_secao}">'
            f"<h2>{nome_html}</h2>{texto_html}</section>"
        )
        itens_indice.append(
            f'<li><a href="content.xhtml#{id_secao}">'
            f"{nome_html}</a></li>"
        )

    adicionar_secao("introducao", "Introdução", livro.get("introducao", ""))

    for indice, capitulo in enumerate(livro["capitulos"], start=1):
        nome = capitulo.get("titulo") or f"Capítulo {indice}"
        adicionar_secao(
            f"capitulo-{indice}",
            nome,
            capitulo.get("conteudo") or "",
        )

    adicionar_secao("conclusao", "Conclusão", livro.get("conclusao", ""))
    adicionar_secao("epilogo", "Epílogo", livro.get("epilogo", ""))

    autor_html = f"<p>{autor}</p>" if autor else ""
    descricao_html = f"<p>{descricao}</p>" if descricao else ""

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
        '<nav epub:type="toc" id="toc"><h1>Sumário</h1><ol>'
        + "".join(itens_indice)
        + "</ol></nav></body></html>"
    )

    arquivos_epub = {}
    itens_manifesto = [
        '<item id="content" href="content.xhtml" '
        'media-type="application/xhtml+xml"/>',
        '<item id="nav" href="nav.xhtml" '
        'media-type="application/xhtml+xml" properties="nav"/>',
    ]
    itens_spine = []

    capa = (livro.get("capa") or "").strip()
    if capa:
        caminho_relativo = Path(capa)

        if caminho_relativo.is_absolute() or ".." in caminho_relativo.parts:
            raise ValueError("O caminho da capa é inválido.")

        pasta_static = Path(__file__).resolve().parent.parent / "static"
        arquivo_capa = (pasta_static / caminho_relativo).resolve()

        try:
            arquivo_capa.relative_to(pasta_static.resolve())
        except ValueError as erro:
            raise ValueError("O caminho da capa é inválido.") from erro

        if not arquivo_capa.is_file():
            raise FileNotFoundError(
                f"Imagem da capa não encontrada: {capa}"
            )

        tipo_mime, _ = mimetypes.guess_type(str(arquivo_capa))
        if tipo_mime not in ("image/jpeg", "image/png", "image/webp"):
            raise ValueError("Formato de imagem da capa não suportado.")

        nome_imagem = arquivo_capa.name
        caminho_imagem_epub = f"images/{nome_imagem}"
        id_imagem = "cover-image"

        arquivos_epub[f"OEBPS/{caminho_imagem_epub}"] = arquivo_capa.read_bytes()

        itens_manifesto.append(
            f'<item id="{id_imagem}" href="{caminho_imagem_epub}" '
            f'media-type="{tipo_mime}" properties="cover-image"/>'
        )

        pagina_capa = (
            '<?xml version="1.0" encoding="utf-8"?>'
            '<html xmlns="http://www.w3.org/1999/xhtml" lang="pt-BR">'
            "<head><title>Capa</title>"
            "<style>body{margin:0;text-align:center;}"
            "img{max-width:100%;max-height:100vh;}</style>"
            "</head><body>"
            f'<img src="{caminho_imagem_epub}" alt="Capa de {titulo}"/>'
            "</body></html>"
        )

        arquivos_epub["OEBPS/cover.xhtml"] = pagina_capa
        itens_manifesto.append(
            '<item id="cover-page" href="cover.xhtml" '
            'media-type="application/xhtml+xml"/>'
        )
        itens_spine.append('<itemref idref="cover-page"/>')

    itens_spine.append('<itemref idref="content"/>')

    metadados_autor = (
        f"<dc:creator>{autor}</dc:creator>" if autor else ""
    )
    metadados_descricao = (
        f"<dc:description>{descricao}</dc:description>"
        if descricao else ""
    )

    pacote_opf = (
        '<?xml version="1.0" encoding="utf-8"?>'
        '<package xmlns="http://www.idpf.org/2007/opf" '
        'xmlns:dc="http://purl.org/dc/elements/1.1/" '
        'xmlns:dcterms="http://purl.org/dc/terms/" '
        'version="3.0" unique-identifier="book-id" xml:lang="pt-BR">'
        "<metadata>"
        f'<dc:identifier id="book-id">{identificador}</dc:identifier>'
        f"<dc:title>{titulo}</dc:title>"
        "<dc:language>pt-BR</dc:language>"
        f"{metadados_autor}{metadados_descricao}"
        f'<meta property="dcterms:modified">{modificacao}</meta>'
        "</metadata>"
        "<manifest>"
        + "".join(itens_manifesto)
        + "</manifest><spine>"
        + "".join(itens_spine)
        + "</spine></package>"
    )

    container_xml = (
        '<?xml version="1.0" encoding="utf-8"?>'
        '<container xmlns="urn:oasis:names:tc:opendocument:xmlns:container" '
        'version="1.0"><rootfiles><rootfile '
        'full-path="OEBPS/content.opf" '
        'media-type="application/oebps-package+xml"/>'
        "</rootfiles></container>"
    )

    with zipfile.ZipFile(caminho, "w") as arquivo_epub:
        arquivo_epub.writestr(
            "mimetype",
            "application/epub+zip",
            compress_type=zipfile.ZIP_STORED,
        )
        arquivo_epub.writestr("META-INF/container.xml", container_xml)
        arquivo_epub.writestr("OEBPS/content.opf", pacote_opf)
        arquivo_epub.writestr("OEBPS/content.xhtml", conteudo_xhtml)
        arquivo_epub.writestr("OEBPS/nav.xhtml", navegacao_xhtml)

        for nome, conteudo in arquivos_epub.items():
            arquivo_epub.writestr(nome, conteudo)

    return caminho
