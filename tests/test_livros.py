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


def test_atualizar_livro_com_sucesso(cliente):
    livro = criar_livro(cliente).get_json()
    livro_id = livro["id"]

    resposta = cliente.put(
        f"/api/livros/{livro_id}",
        json={
            "titulo": "Livro atualizado",
            "autor": "Novo autor",
            "descricao": "Nova descrição"
        }
    )

    assert resposta.status_code == 200
    dados = resposta.get_json()
    assert dados["titulo"] == "Livro atualizado"
    assert dados["autor"] == "Novo autor"
    assert dados["descricao"] == "Nova descrição"


def test_atualizar_livro_inexistente(cliente):
    resposta = cliente.put(
        "/api/livros/999999",
        json={"titulo": "Livro inexistente"}
    )

    assert resposta.status_code == 404


def test_atualizar_livro_com_titulo_vazio(cliente):
    livro_id = criar_livro(cliente).get_json()["id"]

    resposta = cliente.put(
        f"/api/livros/{livro_id}",
        json={"titulo": "   "}
    )

    assert resposta.status_code == 400


def test_atualizar_livro_com_titulo_de_tipo_invalido(cliente):
    livro_id = criar_livro(cliente).get_json()["id"]

    resposta = cliente.put(
        f"/api/livros/{livro_id}",
        json={"titulo": 123}
    )

    assert resposta.status_code == 400


def test_atualizar_livro_com_autor_invalido(cliente):
    livro_id = criar_livro(cliente).get_json()["id"]

    resposta = cliente.put(
        f"/api/livros/{livro_id}",
        json={"autor": 123}
    )

    assert resposta.status_code == 400


def test_atualizar_livro_com_descricao_invalida(cliente):
    livro_id = criar_livro(cliente).get_json()["id"]

    resposta = cliente.put(
        f"/api/livros/{livro_id}",
        json={"descricao": 123}
    )

    assert resposta.status_code == 400


def test_atualizar_livro_preserva_campos_nao_enviados(cliente):
    livro = cliente.post(
        "/api/livros",
        json={
            "titulo": "Título original",
            "autor": "Autor original",
            "descricao": "Descrição original"
        }
    ).get_json()

    resposta = cliente.put(
        f"/api/livros/{livro['id']}",
        json={"titulo": "Título revisado"}
    )

    assert resposta.status_code == 200
    dados = resposta.get_json()
    assert dados["titulo"] == "Título revisado"
    assert dados["autor"] == "Autor original"
    assert dados["descricao"] == "Descrição original"
