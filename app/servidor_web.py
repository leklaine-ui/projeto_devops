import sqlite3

from flask import Flask, jsonify, request, render_template

from app.banco import BANCO, criar_banco


app = Flask(__name__, template_folder="../templates")


criar_banco()


def salvar_mensagem(texto):
    conexao = sqlite3.connect(BANCO)

    cursor = conexao.cursor()

    cursor.execute(
        "INSERT INTO mensagens (mensagem) VALUES (?)",
        (texto,)
    )

    conexao.commit()
    conexao.close()


@app.route("/", methods=["GET"])
def inicio():
    return render_template("index.html")


@app.route("/health")
def health():
    return jsonify({
        "status": "ok",
        "servico": "servidor_web",
        "versao": "1.0"
    })


@app.route("/api")
def api():
    return jsonify({
        "projeto": "projeto_devops",
        "aplicacao": "Flask",
        "ambiente": "Linux",
        "status": "online"
    })


@app.route("/api/mensagem", methods=["POST"])
def mensagem():
    dados = request.get_json()

    if not dados:
        return jsonify({
            "mensagem_recebida": None,
            "status": "erro",
            "salva_no_banco": False
        }), 400

    texto = dados.get("mensagem")

    if not texto or not texto.strip():
        return jsonify({
            "mensagem_recebida": texto,
            "status": "erro",
            "salva_no_banco": False
        }), 400

    salvar_mensagem(texto)

    return jsonify({
        "mensagem_recebida": texto,
        "status": "recebida",
        "salva_no_banco": True
    })


@app.route("/api/mensagens", methods=["GET"])
def listar_mensagens():
    conexao = sqlite3.connect(BANCO)

    cursor = conexao.cursor()

    cursor.execute("""
        SELECT id, mensagem
        FROM mensagens
        ORDER BY id DESC
    """)

    mensagens = cursor.fetchall()

    conexao.close()

    resultado = []

    for id_mensagem, texto in mensagens:
        resultado.append({
            "id": id_mensagem,
            "mensagem": texto
        })

    return jsonify(resultado)


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000
    )
