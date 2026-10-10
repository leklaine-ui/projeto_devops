import os
import tempfile
from pathlib import Path

from flask import Blueprint, jsonify, send_file

from app.exportador import exportar_markdown, exportar_pdf

exportacao_bp = Blueprint("exportacao", __name__)


def preparar_download(livro_id, formato):
    descritor, nome = tempfile.mkstemp(
        prefix=f"livro_{livro_id}_",
        suffix=f".{formato}",
    )
    os.close(descritor)
    caminho = Path(nome)

    try:
        if formato == "pdf":
            exportar_pdf(livro_id, caminho)
            mimetype = "application/pdf"
        else:
            exportar_markdown(livro_id, caminho)
            mimetype = "text/markdown; charset=utf-8"

        resposta = send_file(
            caminho,
            as_attachment=True,
            mimetype=mimetype,
        )
        resposta.call_on_close(lambda: caminho.unlink(missing_ok=True))
        return resposta

    except Exception:
        caminho.unlink(missing_ok=True)
        raise


@exportacao_bp.route(
    "/api/livros/<int:livro_id>/exportar/markdown",
    methods=["GET"],
)
def baixar_markdown(livro_id):
    try:
        return preparar_download(livro_id, "md")
    except ValueError as erro:
        return jsonify({"erro": str(erro)}), 404


@exportacao_bp.route(
    "/api/livros/<int:livro_id>/exportar/pdf",
    methods=["GET"],
)
def baixar_pdf(livro_id):
    try:
        return preparar_download(livro_id, "pdf")
    except ValueError as erro:
        return jsonify({"erro": str(erro)}), 404
    except RuntimeError as erro:
        return jsonify({"erro": str(erro)}), 500
