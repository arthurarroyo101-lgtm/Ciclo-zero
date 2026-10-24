"""Banco de dados SQLite do Ciclo Zero.

Tabelas:
- produtos: cadastro (preços, estoque mínimo, fornecedor, prazo de entrega)
- lotes: cada entrada de mercadoria com sua validade (permite FEFO)
- movimentacoes: entradas, vendas, perdas, doações e promoções (histórico)
- pedidos: pedidos de compra gerados pelo agente (ficam em RASCUNHO até um humano aprovar)
- log_agente: rastreio de cada passo do agente (observabilidade)
"""
import os
import sqlite3
from pathlib import Path

DB_PATH = Path(os.getenv("CICLOZERO_DB", Path(__file__).resolve().parent.parent / "ciclozero.db"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS produtos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT UNIQUE NOT NULL,
    categoria TEXT,
    unidade TEXT DEFAULT 'un',
    preco_custo REAL DEFAULT 0,
    preco_venda REAL DEFAULT 0,
    estoque_minimo REAL DEFAULT 0,
    fornecedor TEXT,
    prazo_entrega_dias INTEGER DEFAULT 2,
    validade_padrao_dias INTEGER DEFAULT 7
);
CREATE TABLE IF NOT EXISTS lotes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    produto_id INTEGER NOT NULL REFERENCES produtos(id),
    quantidade REAL NOT NULL,
    validade TEXT,
    data_entrada TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS movimentacoes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    produto_id INTEGER NOT NULL REFERENCES produtos(id),
    tipo TEXT NOT NULL CHECK (tipo IN ('entrada','venda','perda','doacao','ajuste')),
    quantidade REAL NOT NULL,
    valor REAL DEFAULT 0,
    data TEXT NOT NULL,
    motivo TEXT
);
CREATE TABLE IF NOT EXISTS pedidos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fornecedor TEXT NOT NULL,
    itens_json TEXT NOT NULL,
    valor_estimado REAL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'rascunho' CHECK (status IN ('rascunho','aprovado','recusado')),
    justificativa TEXT,
    criado_em TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS apelidos (
    descricao TEXT PRIMARY KEY,      -- descrição da nota normalizada (ex.: "leite uht integral 1l cx")
    produto_id INTEGER NOT NULL REFERENCES produtos(id),
    fornecedor TEXT,
    vezes INTEGER DEFAULT 1,
    atualizado_em TEXT DEFAULT (datetime('now','localtime'))
);
CREATE TABLE IF NOT EXISTS log_agente (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sessao TEXT,
    passo INTEGER,
    tipo TEXT,          -- usuario | ferramenta | resposta | erro
    conteudo TEXT,
    criado_em TEXT DEFAULT (datetime('now','localtime'))
);
"""


def conectar() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, timeout=15, check_same_thread=False)  # simulação ao vivo escreve em paralelo
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def criar_tabelas() -> None:
    with conectar() as conn:
        conn.executescript(SCHEMA)
        # migração: bancos criados antes da leitura de nota fiscal não têm a validade padrão
        colunas = {r["name"] for r in conn.execute("PRAGMA table_info(produtos)")}
        if "validade_padrao_dias" not in colunas:
            conn.execute("ALTER TABLE produtos ADD COLUMN validade_padrao_dias INTEGER DEFAULT 7")
