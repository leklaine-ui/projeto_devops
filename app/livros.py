import os
import uuid
from io import BytesIO

from flask import Blueprint, current_app, jsonify, request
from PIL import Image, UnidentifiedImageError

from app.livros_db import conectar_banco, criar_tabelas_livros

from app.corretor_texto import corrigir_texto, ErroCorretor

livros_bp = Blueprint("livros", __name__)

criar_tabelas_livros()


@livros_bp.route("/api/livros", methods=["GET"])
def listar_livros():
    with conectar_banco() as conexao:
        livros = conexao.execute("""
            SELECT id, titulo, autor, descricao,
                   introducao, conclusao, epilogo, capa,
                   criado_em, atualizado_em
            FROM livros
            ORDER BY atualizado_em DESC, id DESC
        """).fetchall()

    return jsonify([dict(livro) for livro in livros])


@livros_bp.route("/api/livros", methods=["POST"])
def criar_livro():
    dados = request.get_json(silent=True) or {}
    titulo = dados.get("titulo", "").strip()
    autor = dados.get("autor", "").strip()
    descricao = dados.get("descricao", "").strip()

    introducao = dados.get("introducao", "")
    conclusao = dados.get("conclusao", "")
    epilogo = dados.get("epilogo", "")

    if not all(isinstance(campo, str) for campo in (
        introducao, conclusao, epilogo
    )):
        return jsonify({
            "erro": "Introdução, conclusão e epílogo devem ser textos."
        }), 400

    if not titulo:
        return jsonify({
            "erro": "O título do livro é obrigatório."
        }), 400

    with conectar_banco() as conexao:
        cursor = conexao.execute("""
            INSERT INTO livros (
                titulo, autor, descricao,
                introducao, conclusao, epilogo
            )
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            titulo, autor, descricao,
            introducao, conclusao, epilogo
        ))

        livro_id = cursor.lastrowid
        livro = conexao.execute("""
            SELECT id, titulo, autor, descricao,
                   introducao, conclusao, epilogo, capa,
                   criado_em, atualizado_em
            FROM livros
            WHERE id = ?
        """, (livro_id,)).fetchone()

    return jsonify(dict(livro)), 201


@livros_bp.route("/api/livros/<int:livro_id>", methods=["GET"])
def obter_livro(livro_id):
    with conectar_banco() as conexao:
        livro = conexao.execute("""
            SELECT id, titulo, autor, descricao,
                   introducao, conclusao, epilogo, capa,
                   criado_em, atualizado_em
            FROM livros
            WHERE id = ?
        """, (livro_id,)).fetchone()

        if livro is None:
            return jsonify({"erro": "Livro não encontrado."}), 404

        capitulos = conexao.execute("""
            SELECT id, livro_id, titulo, conteudo, ordem,
                   criado_em, atualizado_em
            FROM capitulos
            WHERE livro_id = ?
            ORDER BY ordem, id
        """, (livro_id,)).fetchall()

    resultado = dict(livro)
    resultado["capitulos"] = [dict(capitulo) for capitulo in capitulos]
    return jsonify(resultado)


@livros_bp.route(
    "/api/livros/<int:livro_id>/capitulos",
    methods=["POST"]
)
def criar_capitulo(livro_id):
    dados = request.get_json(silent=True) or {}
    titulo = dados.get("titulo", "").strip()
    conteudo = dados.get("conteudo", "")
    ordem = dados.get("ordem", 1)

    if not titulo:
        return jsonify({
            "erro": "O título do capítulo é obrigatório."
        }), 400

    if not isinstance(conteudo, str):
        return jsonify({
            "erro": "O conteúdo do capítulo deve ser texto."
        }), 400

    if isinstance(ordem, bool) or not isinstance(ordem, int) or ordem < 1:
        return jsonify({
            "erro": "A ordem deve ser um número inteiro positivo."
        }), 400

    with conectar_banco() as conexao:
        livro = conexao.execute(
            "SELECT id FROM livros WHERE id = ?",
            (livro_id,)
        ).fetchone()

        if livro is None:
            return jsonify({"erro": "Livro não encontrado."}), 404

        cursor = conexao.execute("""
            INSERT INTO capitulos (livro_id, titulo, conteudo, ordem)
            VALUES (?, ?, ?, ?)
        """, (livro_id, titulo, conteudo, ordem))

        capitulo = conexao.execute("""
            SELECT id, livro_id, titulo, conteudo, ordem,
                   criado_em, atualizado_em
            FROM capitulos
            WHERE id = ?
        """, (cursor.lastrowid,)).fetchone()

        conexao.execute("""
            UPDATE livros
            SET atualizado_em = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (livro_id,))

    return jsonify(dict(capitulo)), 201


@livros_bp.route("/api/capitulos/<int:capitulo_id>", methods=["PUT"])
def atualizar_capitulo(capitulo_id):
    dados = request.get_json(silent=True) or {}

    with conectar_banco() as conexao:
        capitulo = conexao.execute(
            "SELECT * FROM capitulos WHERE id = ?",
            (capitulo_id,)
        ).fetchone()

        if capitulo is None:
            return jsonify({"erro": "Capítulo não encontrado."}), 404

        titulo = dados.get("titulo", capitulo["titulo"])
        conteudo = dados.get("conteudo", capitulo["conteudo"])
        ordem = dados.get("ordem", capitulo["ordem"])

        if not isinstance(titulo, str) or not titulo.strip():
            return jsonify({
                "erro": "O título do capítulo é obrigatório."
            }), 400

        if not isinstance(conteudo, str):
            return jsonify({
                "erro": "O conteúdo do capítulo deve ser texto."
            }), 400

        if isinstance(ordem, bool) or not isinstance(ordem, int) or ordem < 1:
            return jsonify({
                "erro": "A ordem deve ser um número inteiro positivo."
            }), 400

        conexao.execute("""
            UPDATE capitulos
            SET titulo = ?, conteudo = ?, ordem = ?,
                atualizado_em = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (titulo.strip(), conteudo, ordem, capitulo_id))

        conexao.execute("""
            UPDATE livros
            SET atualizado_em = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (capitulo["livro_id"],))

        atualizado = conexao.execute(
            "SELECT * FROM capitulos WHERE id = ?",
            (capitulo_id,)
        ).fetchone()

    return jsonify(dict(atualizado))

@livros_bp.route("/api/livros/<int:livro_id>", methods=["PUT"])
def atualizar_livro(livro_id):
    dados = request.get_json(silent=True) or {}

    with conectar_banco() as conexao:
        livro = conexao.execute(
            "SELECT * FROM livros WHERE id = ?",
            (livro_id,)
        ).fetchone()

        if livro is None:
            return jsonify({"erro": "Livro não encontrado."}), 404

        titulo = dados.get("titulo", livro["titulo"])
        autor = dados.get("autor", livro["autor"])
        descricao = dados.get("descricao", livro["descricao"])
        introducao = dados.get("introducao", livro["introducao"])
        conclusao = dados.get("conclusao", livro["conclusao"])
        epilogo = dados.get("epilogo", livro["epilogo"])

        if not isinstance(titulo, str) or not titulo.strip():
            return jsonify({
                "erro": "O título do livro é obrigatório."
            }), 400

        if not all(isinstance(campo, str) for campo in (
            autor, descricao, introducao, conclusao, epilogo
        )):
            return jsonify({
                "erro": "Os campos do livro devem ser textos."
            }), 400

        conexao.execute("""
            UPDATE livros
            SET titulo = ?, autor = ?, descricao = ?,
                introducao = ?, conclusao = ?, epilogo = ?,
                atualizado_em = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (
            titulo.strip(), autor.strip(), descricao.strip(),
            introducao, conclusao, epilogo, livro_id
        ))

        atualizado = conexao.execute(
            "SELECT * FROM livros WHERE id = ?",
            (livro_id,)
        ).fetchone()

    return jsonify(dict(atualizado))

@livros_bp.route(
    "/api/capitulos/corrigir-texto",
    methods=["POST"],
)
def corrigir_texto_capitulo():
    dados = request.get_json(silent=True)

    if not isinstance(dados, dict):
        return jsonify({
            "erro": "Envie um objeto JSON válido."
        }), 400

    texto = dados.get("texto")

    if not isinstance(texto, str):
        return jsonify({
            "erro": "O conteúdo deve ser um texto."
        }), 400

    try:
        resultado = corrigir_texto(texto)
    except ValueError as erro:
        return jsonify({"erro": str(erro)}), 400
    except ErroCorretor as erro:
        return jsonify({"erro": str(erro)}), 503

    return jsonify(resultado), 200

@livros_bp.route(
    "/api/livros/<int:livro_id>/capa",
    methods=["POST"],
)
def enviar_capa_livro(livro_id):
    arquivo = request.files.get("capa")

    if arquivo is None or not arquivo.filename:
        return jsonify({"erro": "Envie uma imagem de capa."}), 400

    tamanho_maximo = 5 * 1024 * 1024
    conteudo = arquivo.stream.read(tamanho_maximo + 1)

    if not conteudo:
        return jsonify({"erro": "O arquivo está vazio."}), 400

    if len(conteudo) > tamanho_maximo:
        return jsonify({
            "erro": "A imagem deve ter no máximo 5 MB."
        }), 400

    with conectar_banco() as conexao:
        livro = conexao.execute(
            "SELECT id FROM livros WHERE id = ?",
            (livro_id,),
        ).fetchone()

        if livro is None:
            return jsonify({"erro": "Livro não encontrado."}), 404

    try:
        imagem = Image.open(BytesIO(conteudo))
        formato = imagem.format
        imagem.verify()

        formatos_permitidos = {
            "JPEG": ("jpg", "JPEG"),
            "PNG": ("png", "PNG"),
            "WEBP": ("webp", "WEBP"),
        }

        if formato not in formatos_permitidos:
            return jsonify({
                "erro": "Formato inválido. Use JPEG, PNG ou WEBP."
            }), 400

        imagem = Image.open(BytesIO(conteudo))

        if imagem.width > 12000 or imagem.height > 12000:
            return jsonify({
                "erro": "As dimensões da imagem são muito grandes."
            }), 400

        if imagem.width * imagem.height > 40000000:
            return jsonify({
                "erro": "A resolução da imagem é muito grande."
            }), 400

        extensao, formato_saida = formatos_permitidos[formato]

        if formato_saida == "JPEG":
            imagem = imagem.convert("RGB")

        nome_arquivo = f"{uuid.uuid4().hex}.{extensao}"
        caminho_relativo = f"capas/{nome_arquivo}"

        pasta_capas = current_app.config.get("CAPAS_DIR")
        if not pasta_capas:
            pasta_capas = os.path.join(
                current_app.static_folder,
                "capas",
            )

        os.makedirs(pasta_capas, exist_ok=True)
        caminho_completo = os.path.join(
            pasta_capas,
            nome_arquivo,
        )

        imagem.save(caminho_completo, format=formato_saida)

    except (
        UnidentifiedImageError,
        OSError,
        ValueError,
        Image.DecompressionBombError,
    ):
        return jsonify({"erro": "O arquivo enviado não é uma imagem válida."}), 400

    with conectar_banco() as conexao:
        conexao.execute(
            """
            UPDATE livros
            SET capa = ?, atualizado_em = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (caminho_relativo, livro_id),
        )

    return jsonify({
        "mensagem": "Capa enviada com sucesso.",
        "capa": caminho_relativo,
    }), 200
