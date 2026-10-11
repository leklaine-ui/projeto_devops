
import runpy
import sqlite3

from app import banco


def test_main_executado_como_programa(capsys):
    runpy.run_path("app/main.py", run_name="__main__")

    resultado = capsys.readouterr()
    assert "Aplicação DevOps funcionando!" in resultado.out


def test_banco_executado_como_programa(
    capsys, monkeypatch, tmp_path
):
    caminho_original = banco.BANCO
    caminho_temporario = str(tmp_path / "teste.db")
    conectar_original = sqlite3.connect

    def conectar_seguro(caminho, *args, **kwargs):
        if str(caminho) == str(caminho_original):
            caminho = caminho_temporario

        return conectar_original(caminho, *args, **kwargs)

    monkeypatch.setattr(sqlite3, "connect", conectar_seguro)

    runpy.run_path("app/banco.py", run_name="__main__")

    resultado = capsys.readouterr()
    assert "Banco criado com sucesso" in resultado.out

    conexao = conectar_original(caminho_temporario)
    tabelas = conexao.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()
    conexao.close()

    assert ("mensagens",) in tabelas


def test_mensagem_sem_json():
    from app.servidor_web import app

    cliente = app.test_client()
    resposta = cliente.post("/api/mensagem", json={})

    assert resposta.status_code == 400
    assert resposta.get_json()["status"] == "erro"



def test_servidor_web_executado_como_programa(monkeypatch):
    from flask.app import Flask

    chamadas = {}

    def run_falso(self, **kwargs):
        chamadas.update(kwargs)

    monkeypatch.setattr(Flask, "run", run_falso)

    runpy.run_path("app/servidor_web.py", run_name="__main__")

    assert chamadas["host"] == "0.0.0.0"
    assert chamadas["port"] == 5000
