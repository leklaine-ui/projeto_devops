


import os
import sqlite3

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DADOS_DIR = os.path.join(BASE_DIR, "dados")
BANCO = os.path.join(DADOS_DIR, "mensagens.db")


def criar_banco():
    os.makedirs(DADOS_DIR, exist_ok=True)

    conexao = sqlite3.connect(BANCO)
    cursor = conexao.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS mensagens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario TEXT NOT NULL DEFAULT "anonimo",
            mensagem TEXT NOT NULL
        )
    """)

    cursor.execute("PRAGMA table_info(mensagens)")
    colunas = [linha[1] for linha in cursor.fetchall()]

    if "usuario" not in colunas:
        cursor.execute("ALTER TABLE mensagens ADD COLUMN usuario TEXT NOT NULL DEFAULT 'anonimo'")

    conexao.commit()
    conexao.close()


if __name__ == "__main__":
    criar_banco()
    print("Banco criado com sucesso")





