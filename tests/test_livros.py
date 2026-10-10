import pytest

from app import livros_db
from app.servidor_web import app


@pytest.fixture
def cliente(tmp_path, monkeypatch):
    banco_teste = tmp_path / "livros_teste.db"
    monkeypatch.setattr(livros_db, "BANCO", str(banco_teste))

    livros_db.criar_tabelas_livros()

    app.config.update(TESTING=True)

    with app.test_client() as cliente:
        yield cliente


def criar_livro(cliente, titulo="Livro de teste"):
    return cliente.post(
        "/api/livros",
        json={"titulo": titulo, "autor": "Autor de teste"}
    )


def test_criar_e_consultar_livro(cliente):
    resposta = criar_livro(cliente)
    assert resposta.status_code == 201

    livro_id = resposta.get_json()["id"]
    consulta = cliente.get(f"/api/livros/{livro_id}")

    assert consulta.status_code == 200
    assert consulta.get_json()["titulo"] == "Livro de teste"
    assert consulta.get_json()["capitulos"] == []


def test_rejeitar_livro_sem_titulo(cliente):
    resposta = cliente.post("/api/livros", json={"titulo": "   "})
    assert resposta.status_code == 400


def test_criar_e_editar_capitulo(cliente):
    livro = criar_livro(cliente).get_json()
    livro_id = livro["id"]

    resposta = cliente.post(
        f"/api/livros/{livro_id}/capitulos",
        json={
            "titulo": "Capítulo original",
            "conteudo": "Texto original",
            "ordem": 1
        }
    )
    assert resposta.status_code == 201
    capitulo_id = resposta.get_json()["id"]

    atualizacao = cliente.put(
        f"/api/capitulos/{capitulo_id}",
        json={
            "titulo": "Capítulo revisado",
            "conteudo": "Texto atualizado",
            "ordem": 1
        }
    )

    assert atualizacao.status_code == 200
    assert atualizacao.get_json()["titulo"] == "Capítulo revisado"
    assert atualizacao.get_json()["conteudo"] == "Texto atualizado"


def test_rejeitar_titulo_vazio_em_capitulo(cliente):
    livro_id = criar_livro(cliente).get_json()["id"]

    resposta = cliente.post(
        f"/api/livros/{livro_id}/capitulos",
        json={"titulo": "   ", "conteudo": "Texto"}
    )

    assert resposta.status_code == 400


def test_livro_inexistente(cliente):
    resposta = cliente.get("/api/livros/999999")
    assert resposta.status_code == 404
