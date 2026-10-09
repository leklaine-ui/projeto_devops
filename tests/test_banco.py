import sqlite3

from app import banco


def test_criar_banco_novo(monkeypatch, tmp_path):
    monkeypatch.setattr(banco, "DADOS_DIR", str(tmp_path))
    monkeypatch.setattr(
        banco, "BANCO", str(tmp_path / "teste.db")
    )

    banco.criar_banco()

    conexao = sqlite3.connect(banco.BANCO)
    cursor = conexao.execute("PRAGMA table_info(mensagens)")
    colunas = [linha[1] for linha in cursor.fetchall()]
    conexao.close()

    assert "id" in colunas
    assert "usuario" in colunas
    assert "mensagem" in colunas
    assert "data_hora" in colunas


def test_migrar_tabela_antiga(monkeypatch, tmp_path):
    caminho = str(tmp_path / "legado.db")

    monkeypatch.setattr(banco, "DADOS_DIR", str(tmp_path))
    monkeypatch.setattr(banco, "BANCO", caminho)

    # Simula um banco antigo sem usuario e data_hora.
    conexao = sqlite3.connect(caminho)
    conexao.execute(
        """
        CREATE TABLE mensagens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mensagem TEXT NOT NULL
        )
        """
    )
    conexao.execute(
        "INSERT INTO mensagens (mensagem) VALUES (?)",
        ("Mensagem antiga",),
    )
    conexao.commit()
    conexao.close()

    banco.criar_banco()

    conexao = sqlite3.connect(caminho)
    cursor = conexao.execute(
        "SELECT usuario, mensagem, data_hora FROM mensagens"
    )
    usuario, mensagem, data_hora = cursor.fetchone()
    conexao.close()

    assert usuario == "anonimo"
    assert mensagem == "Mensagem antiga"
    assert data_hora != ""
