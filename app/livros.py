from flask import Blueprint, jsonify, request

from app.livros_db import conectar_banco, criar_tabelas_livros

livros_bp = Blueprint("livros", __name__)

criar_tabelas_livros()


@livros_bp.route("/api/livros", methods=["GET"])
def listar_livros():
    with conectar_banco() as conexao:
        livros = conexao.execute("""
            SELECT id, titulo, autor, descricao, criado_em, atualizado_em
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

    if not titulo:
        return jsonify({
            "erro": "O título do livro é obrigatório."
        }), 400

    with conectar_banco() as conexao:
        cursor = conexao.execute("""
            INSERT INTO livros (titulo, autor, descricao)
            VALUES (?, ?, ?)
        """, (titulo, autor, descricao))

        livro_id = cursor.lastrowid
        livro = conexao.execute("""
            SELECT id, titulo, autor, descricao, criado_em, atualizado_em
            FROM livros
            WHERE id = ?
        """, (livro_id,)).fetchone()

    return jsonify(dict(livro)), 201


@livros_bp.route("/api/livros/<int:livro_id>", methods=["GET"])
def obter_livro(livro_id):
    with conectar_banco() as conexao:
        livro = conexao.execute("""
            SELECT id, titulo, autor, descricao, criado_em, atualizado_em
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
