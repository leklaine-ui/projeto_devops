
from app.servidor_web import app


def test_aplicacao():
    cliente = app.test_client()

    resposta = cliente.get("/")

    assert resposta.status_code == 200


def test_health():
    cliente = app.test_client()

    resposta = cliente.get("/health")

    assert resposta.status_code == 200

    dados = resposta.get_json()

    assert dados["status"] == "ok"


def test_api():
    cliente = app.test_client()

    resposta = cliente.get("/api")

    assert resposta.status_code == 200

    dados = resposta.get_json()

    assert dados["projeto"] == "projeto_devops"
    assert dados["aplicacao"] == "Flask"
    assert dados["ambiente"] == "Linux"
    assert dados["status"] == "online"


def test_enviar_mensagem():
    cliente = app.test_client()

    resposta = cliente.post(
        "/api/mensagem",
        json={
            "mensagem": "Teste automatizado"
        }
    )

    assert resposta.status_code == 200

    dados = resposta.get_json()

    assert dados["mensagem_recebida"] == "Teste automatizado"
    assert dados["status"] == "recebida"
    assert dados["salva_no_banco"] is True


def test_listar_mensagens():
    cliente = app.test_client()

    cliente.post(
        "/api/mensagem",
        json={
            "mensagem": "Mensagem para testar o histórico"
        }
    )

    resposta = cliente.get("/api/mensagens")

    assert resposta.status_code == 200

    dados = resposta.get_json()

    assert isinstance(dados, list)

    mensagens = [
        item["mensagem"]
        for item in dados
    ]

    assert "Mensagem para testar o histórico" in mensagens


def test_mensagem_vazia():
    cliente = app.test_client()

    resposta = cliente.post(
        "/api/mensagem",
        json={
            "mensagem": ""
        }
    )

    assert resposta.status_code == 400

    dados = resposta.get_json()

    assert dados["status"] == "erro"
    assert dados["salva_no_banco"] is False
