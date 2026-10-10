import os
import sqlite3

from app.banco import BANCO


def conectar_banco():
    """Abre uma conexão com o banco de dados da aplicação."""
    os.makedirs(os.path.dirname(BANCO), exist_ok=True)
    conexao = sqlite3.connect(BANCO)
    conexao.row_factory = sqlite3.Row
    conexao.execute("PRAGMA foreign_keys = ON")
    return conexao


def criar_tabelas_livros():
    """Cria as tabelas de livros e capítulos sem alterar as mensagens."""
    with conectar_banco() as conexao:
        conexao.execute("""
            CREATE TABLE IF NOT EXISTS livros (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                titulo TEXT NOT NULL,
                autor TEXT NOT NULL DEFAULT '',
                descricao TEXT NOT NULL DEFAULT '',
                criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                atualizado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conexao.execute("""
            CREATE TABLE IF NOT EXISTS capitulos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                livro_id INTEGER NOT NULL,
                titulo TEXT NOT NULL,
                conteudo TEXT NOT NULL DEFAULT '',
                ordem INTEGER NOT NULL DEFAULT 1,
                criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                atualizado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (livro_id)
                    REFERENCES livros(id)
                    ON DELETE CASCADE
            )
        """)

        conexao.execute("""
            CREATE INDEX IF NOT EXISTS idx_capitulos_livro_ordem
            ON capitulos (livro_id, ordem)
        """)
