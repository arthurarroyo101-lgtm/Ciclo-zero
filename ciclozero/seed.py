"""Gera dados de exemplo: uma padaria/mercadinho de bairro fictício com 30 dias de histórico.

Rodar:  python -m ciclozero.seed
Os dados são montados em torno da data de HOJE, então sempre haverá itens vencendo na demo.
"""
import random
from datetime import date, timedelta

from .db import DB_PATH, conectar, criar_tabelas

# nome, categoria, unidade, custo, venda, minimo, fornecedor, prazo_entrega, vendas/dia, validade_dias
PRODUTOS = [
    ("Pão francês", "Padaria", "kg", 9.0, 16.9, 8, "Produção própria", 0, 12, 1),
    ("Pão de forma integral", "Padaria", "un", 6.5, 11.9, 6, "Distribuidora Pão Bom", 2, 4, 6),
    ("Bolo de cenoura", "Padaria", "un", 12.0, 24.9, 2, "Produção própria", 0, 2, 3),
    ("Leite integral 1L", "Laticínios", "un", 4.2, 6.49, 24, "Laticínios Serra Dourada", 2, 18, 7),
    ("Iogurte natural 170g", "Laticínios", "un", 2.1, 3.99, 12, "Laticínios Serra Dourada", 2, 6, 10),
    ("Queijo muçarela", "Laticínios", "kg", 32.0, 54.9, 3, "Laticínios Serra Dourada", 2, 1.5, 12),
    ("Presunto cozido", "Frios", "kg", 28.0, 46.9, 2, "Frigorífico Goiás", 3, 1.2, 8),
    ("Banana prata", "Hortifruti", "kg", 3.5, 6.99, 10, "Ceasa Goiânia", 1, 8, 5),
    ("Tomate", "Hortifruti", "kg", 5.0, 8.99, 6, "Ceasa Goiânia", 1, 5, 6),
    ("Alface crespa", "Hortifruti", "un", 1.8, 3.49, 8, "Ceasa Goiânia", 1, 6, 3),
    ("Frango resfriado", "Carnes", "kg", 11.0, 18.9, 6, "Frigorífico Goiás", 3, 4, 4),
    ("Ovos (dúzia)", "Mercearia", "un", 8.5, 13.9, 10, "Granja Bela Vista", 2, 5, 21),
    ("Arroz 5kg", "Mercearia", "un", 22.0, 31.9, 6, "Atacadão Central", 3, 2, 365),
    ("Café 500g", "Mercearia", "un", 14.0, 22.9, 6, "Atacadão Central", 3, 2.5, 240),
]


def popular(seed: int = 42) -> None:
    random.seed(seed)
    if DB_PATH.exists():
        DB_PATH.unlink()
    criar_tabelas()
    hoje = date.today()
    with conectar() as conn:
        for nome, cat, un, custo, venda, minimo, forn, prazo, vpd, val in PRODUTOS:
            pid = conn.execute(
                "INSERT INTO produtos (nome, categoria, unidade, preco_custo, preco_venda, estoque_minimo, fornecedor, prazo_entrega_dias,"
                " validade_padrao_dias) VALUES (?,?,?,?,?,?,?,?,?)", (nome, cat, un, custo, venda, minimo, forn, prazo, val)).lastrowid
            # 30 dias de histórico: vendas diárias com ruído + perdas ocasionais de perecíveis
            for d in range(30, 0, -1):
                dia = (hoje - timedelta(days=d)).isoformat()
                fator = 1.3 if (hoje - timedelta(days=d)).weekday() >= 5 else 1.0  # fim de semana vende mais
                q = max(0, round(random.gauss(vpd * fator, vpd * 0.25), 1 if un == "kg" else 0))
                if q:
                    conn.execute("INSERT INTO movimentacoes (produto_id,tipo,quantidade,valor,data,motivo) VALUES (?,?,?,?,?,?)",
                                 (pid, "venda", q, round(q * venda, 2), dia, ""))
                if val <= 7 and random.random() < 0.25:
                    perda = round(vpd * random.uniform(0.2, 0.6), 1 if un == "kg" else 0) or 1
                    conn.execute("INSERT INTO movimentacoes (produto_id,tipo,quantidade,valor,data,motivo) VALUES (?,?,?,?,?,?)",
                                 (pid, "perda", perda, round(perda * custo, 2), dia, "vencido"))
            # estoque atual: um lote "antigo" (perto de vencer, às vezes em excesso) + um lote novo
            excesso = random.choice([0.6, 1.0, 1.8, 2.5])
            if val > 30:
                antigo_val = hoje + timedelta(days=random.randint(60, 200))
            else:
                antigo_val = hoje + timedelta(days=min(val - 1, random.choice([0, 1, 1, 2, 2, 3])))
            q_antigo = round(vpd * excesso * min(4, (antigo_val - hoje).days + 1), 1 if un == "kg" else 0) or 1
            conn.execute("INSERT INTO lotes (produto_id,quantidade,validade,data_entrada) VALUES (?,?,?,?)",
                         (pid, q_antigo, antigo_val.isoformat(), (hoje - timedelta(days=2)).isoformat()))
            if random.random() < 0.6:
                q_novo = round(vpd * random.uniform(1, 3), 1 if un == "kg" else 0) or 1
                conn.execute("INSERT INTO lotes (produto_id,quantidade,validade,data_entrada) VALUES (?,?,?,?)",
                             (pid, q_novo, (hoje + timedelta(days=val)).isoformat(), hoje.isoformat()))
    print(f"Banco de exemplo criado em {DB_PATH}")


if __name__ == "__main__":
    popular()
