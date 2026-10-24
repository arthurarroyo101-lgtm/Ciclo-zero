"""Ferramentas (function calling) que o agente pode usar.

Regras de projeto:
- Toda ferramenta devolve um dict serializável em JSON. Erros voltam como {"erro": ...}
  em vez de exceção, para o agente poder se corrigir (ex.: produto com nome errado).
- Os números que o agente cita SEMPRE vêm daqui: o modelo não calcula nem inventa.
- Ações irreversíveis/caras (comprar) só geram RASCUNHO; um humano aprova na interface.
"""
from __future__ import annotations

import difflib
import json
import unicodedata
from datetime import date, datetime, timedelta

from .db import conectar

JANELA_VENDAS_DIAS = 14      # histórico usado para média de vendas
COBERTURA_DIAS = 5           # quantos dias de venda um pedido deve cobrir
DESCONTO_MAX = 0.5           # guardrail: nunca sugerir mais que 50% de desconto


# ----------------------------------------------------------------- utilitários
def _hoje() -> date:
    return date.today()


def _norm(txt: str) -> str:
    txt = unicodedata.normalize("NFKD", txt or "").encode("ascii", "ignore").decode()
    return " ".join(txt.lower().split())


def _resolver_produto(conn, nome: str):
    """Acha o produto pelo nome (tolerante a acento/maiúscula/erro de digitação)."""
    linhas = conn.execute("SELECT * FROM produtos").fetchall()
    por_nome = {_norm(r["nome"]): r for r in linhas}
    alvo = _norm(nome)
    if alvo in por_nome:
        return por_nome[alvo], None
    contem = [r for k, r in por_nome.items() if alvo and (alvo in k or k in alvo)]
    if len(contem) == 1:
        return contem[0], None
    parecidos = difflib.get_close_matches(alvo, por_nome.keys(), n=3, cutoff=0.6)
    if len(parecidos) == 1 and not contem:
        return por_nome[parecidos[0]], None
    sugestoes = [r["nome"] for r in contem] or [por_nome[p]["nome"] for p in parecidos]
    return None, {"erro": f"Produto '{nome}' não encontrado ou ambíguo.", "sugestoes": sugestoes}


def _saldo(conn, produto_id: int) -> float:
    r = conn.execute("SELECT COALESCE(SUM(quantidade),0) s FROM lotes WHERE produto_id=?", (produto_id,)).fetchone()
    return round(r["s"], 3)


def _media_vendas_dia(conn, produto_id: int) -> float:
    inicio = (_hoje() - timedelta(days=JANELA_VENDAS_DIAS)).isoformat()
    r = conn.execute(
        "SELECT COALESCE(SUM(quantidade),0) s FROM movimentacoes WHERE produto_id=? AND tipo='venda' AND data>=?",
        (produto_id, inicio),
    ).fetchone()
    return round(r["s"] / JANELA_VENDAS_DIAS, 2)


def _dias_para_vencer(validade: str | None) -> int | None:
    if not validade:
        return None
    return (date.fromisoformat(validade) - _hoje()).days


def _baixar_fefo(conn, produto_id: int, quantidade: float) -> list[dict]:
    """Consome lotes do que vence primeiro (First Expired, First Out)."""
    restante, consumidos = quantidade, []
    lotes = conn.execute(
        "SELECT * FROM lotes WHERE produto_id=? AND quantidade>0 ORDER BY validade IS NULL, validade, id",
        (produto_id,),
    ).fetchall()
    for lote in lotes:
        if restante <= 0:
            break
        usar = min(lote["quantidade"], restante)
        conn.execute("UPDATE lotes SET quantidade=quantidade-? WHERE id=?", (usar, lote["id"]))
        consumidos.append({"lote": lote["id"], "validade": lote["validade"], "quantidade": usar})
        restante -= usar
    conn.execute("DELETE FROM lotes WHERE quantidade<=0.0001")
    return consumidos


# ------------------------------------------------------------------ ferramentas
def consultar_estoque(produto: str = "") -> dict:
    """Consulta o estoque atual. Sem 'produto', lista todos os produtos.

    Args:
        produto: nome do produto (opcional). Deixe vazio para ver o estoque completo.

    Returns:
        Saldo, unidade, validade mais próxima, média de vendas por dia e se está abaixo do mínimo.
    """
    with conectar() as conn:
        if produto:
            p, erro = _resolver_produto(conn, produto)
            if erro:
                return erro
            prods = [p]
        else:
            prods = conn.execute("SELECT * FROM produtos ORDER BY nome").fetchall()
        itens = []
        for p in prods:
            saldo = _saldo(conn, p["id"])
            prox = conn.execute(
                "SELECT MIN(validade) v FROM lotes WHERE produto_id=? AND quantidade>0", (p["id"],)
            ).fetchone()["v"]
            itens.append({
                "produto": p["nome"],
                "categoria": p["categoria"],
                "saldo": saldo,
                "unidade": p["unidade"],
                "validade_mais_proxima": prox,
                "dias_para_vencer": _dias_para_vencer(prox),
                "media_vendas_dia": _media_vendas_dia(conn, p["id"]),
                "estoque_minimo": p["estoque_minimo"],
                "abaixo_do_minimo": saldo < p["estoque_minimo"],
            })
        return {"data": _hoje().isoformat(), "itens": itens}


def registrar_entrada(produto: str, quantidade: float, validade: str) -> dict:
    """Registra a chegada de mercadoria (novo lote) no estoque.

    Args:
        produto: nome do produto já cadastrado.
        quantidade: quantidade recebida (maior que zero), na unidade do produto.
        validade: data de validade no formato AAAA-MM-DD.
    """
    if quantidade is None or quantidade <= 0:
        return {"erro": "A quantidade precisa ser maior que zero."}
    try:
        val = date.fromisoformat(validade)
    except (TypeError, ValueError):
        return {"erro": "Validade inválida. Use o formato AAAA-MM-DD."}
    if val < _hoje():
        return {"erro": f"A validade {validade} já passou; confirme a data com o usuário."}
    with conectar() as conn:
        p, erro = _resolver_produto(conn, produto)
        if erro:
            return erro
        hoje = _hoje().isoformat()
        conn.execute("INSERT INTO lotes (produto_id, quantidade, validade, data_entrada) VALUES (?,?,?,?)",
                     (p["id"], quantidade, validade, hoje))
        conn.execute("INSERT INTO movimentacoes (produto_id, tipo, quantidade, valor, data, motivo) VALUES (?,?,?,?,?,?)",
                     (p["id"], "entrada", quantidade, quantidade * p["preco_custo"], hoje, "recebimento"))
        return {"ok": True, "produto": p["nome"], "quantidade": quantidade, "validade": validade,
                "saldo_atual": _saldo(conn, p["id"])}


def registrar_saida(produto: str, quantidade: float, tipo: str = "venda", motivo: str = "") -> dict:
    """Registra uma saída do estoque, consumindo primeiro os lotes que vencem antes (FEFO).

    Args:
        produto: nome do produto.
        quantidade: quantidade que saiu (maior que zero).
        tipo: 'venda', 'perda' (vencido/estragado) ou 'doacao'.
        motivo: explicação curta (opcional), ex.: 'vencido', 'doado ao banco de alimentos'.
    """
    if tipo not in ("venda", "perda", "doacao"):
        return {"erro": "tipo deve ser 'venda', 'perda' ou 'doacao'."}
    if quantidade is None or quantidade <= 0:
        return {"erro": "A quantidade precisa ser maior que zero."}
    with conectar() as conn:
        p, erro = _resolver_produto(conn, produto)
        if erro:
            return erro
        saldo = _saldo(conn, p["id"])
        if quantidade > saldo:
            return {"erro": f"Saldo insuficiente: há {saldo} {p['unidade']} de {p['nome']}."}
        lotes = _baixar_fefo(conn, p["id"], quantidade)
        preco = p["preco_venda"] if tipo == "venda" else p["preco_custo"]
        conn.execute("INSERT INTO movimentacoes (produto_id, tipo, quantidade, valor, data, motivo) VALUES (?,?,?,?,?,?)",
                     (p["id"], tipo, quantidade, round(quantidade * preco, 2), _hoje().isoformat(), motivo))
        return {"ok": True, "produto": p["nome"], "tipo": tipo, "quantidade": quantidade,
                "lotes_consumidos": lotes, "saldo_atual": _saldo(conn, p["id"])}


def listar_produtos_vencendo(dias: int = 3) -> dict:
    """Lista lotes que vencem nos próximos 'dias' dias (inclui os já vencidos).

    Args:
        dias: horizonte em dias (padrão 3).
    """
    limite = (_hoje() + timedelta(days=int(dias))).isoformat()
    with conectar() as conn:
        rows = conn.execute(
            """SELECT l.id lote, p.nome, l.quantidade, p.unidade, l.validade, p.preco_custo
               FROM lotes l JOIN produtos p ON p.id=l.produto_id
               WHERE l.quantidade>0 AND l.validade IS NOT NULL AND l.validade<=? ORDER BY l.validade""",
            (limite,),
        ).fetchall()
    itens = [{"lote": r["lote"], "produto": r["nome"], "quantidade": r["quantidade"], "unidade": r["unidade"],
              "validade": r["validade"], "dias_para_vencer": _dias_para_vencer(r["validade"]),
              "valor_em_risco": round(r["quantidade"] * r["preco_custo"], 2)} for r in rows]
    return {"horizonte_dias": dias, "itens": itens,
            "valor_total_em_risco": round(sum(i["valor_em_risco"] for i in itens), 2)}


def analisar_risco_desperdicio(dias: int = 5) -> dict:
    """Projeta, lote a lote, quanto NÃO será vendido antes de vencer e recomenda uma ação.

    Compara a quantidade de cada lote com a média de vendas diária até a validade.
    Ações possíveis: 'ok', 'promocao' (com desconto sugerido), 'doacao' ou 'descartar' (já vencido).

    Args:
        dias: considera lotes que vencem em até 'dias' dias (padrão 5).
    """
    limite = (_hoje() + timedelta(days=int(dias))).isoformat()
    with conectar() as conn:
        lotes = conn.execute(
            """SELECT l.id, l.produto_id, l.quantidade, l.validade, p.nome, p.unidade, p.preco_custo, p.preco_venda
               FROM lotes l JOIN produtos p ON p.id=l.produto_id
               WHERE l.quantidade>0 AND l.validade IS NOT NULL AND l.validade<=? ORDER BY l.validade""",
            (limite,),
        ).fetchall()
        resultado, vendavel_ate = [], {}
        for l in lotes:
            dias_rest = _dias_para_vencer(l["validade"])
            media = _media_vendas_dia(conn, l["produto_id"])
            # lotes do mesmo produto que vencem antes "consomem" a demanda primeiro (FEFO)
            ja_usada = vendavel_ate.get(l["produto_id"], 0.0)
            # o dia de hoje conta: um lote que vence hoje ainda pode ser vendido hoje
            demanda = max(0.0, media * (dias_rest + 1) - ja_usada) if dias_rest >= 0 else 0.0
            vende = min(l["quantidade"], demanda)
            vendavel_ate[l["produto_id"]] = ja_usada + vende
            sobra = round(l["quantidade"] - vende, 2)
            perda_rs = round(sobra * l["preco_custo"], 2)
            if dias_rest < 0:
                acao, desconto = "descartar", 0
            elif sobra <= 0:
                acao, desconto = "ok", 0
            elif dias_rest <= 0 or (dias_rest == 1 and sobra / l["quantidade"] > 0.5):
                acao, desconto = "doacao", 0
            else:
                # desconto proporcional à fração que sobraria, limitado pelo guardrail
                frac = sobra / l["quantidade"]
                desconto = round(min(DESCONTO_MAX, 0.15 + 0.5 * frac), 2)
                acao = "promocao"
            item = {"lote": l["id"], "produto": l["nome"], "quantidade": l["quantidade"], "unidade": l["unidade"],
                    "validade": l["validade"], "dias_para_vencer": dias_rest, "media_vendas_dia": media,
                    "projecao_sobra": max(sobra, 0), "perda_estimada_rs": max(perda_rs, 0), "acao": acao}
            if acao == "promocao":
                item["desconto_sugerido"] = f"{int(desconto * 100)}%"
                item["preco_promocional"] = round(l["preco_venda"] * (1 - desconto), 2)
                item["abaixo_do_custo"] = item["preco_promocional"] < l["preco_custo"]
            resultado.append(item)
    em_risco = [r for r in resultado if r["acao"] != "ok"]
    return {"data": _hoje().isoformat(), "lotes_analisados": len(resultado), "lotes_em_risco": em_risco,
            "perda_evitavel_rs": round(sum(r["perda_estimada_rs"] for r in em_risco if r["acao"] != "descartar"), 2)}


def calcular_reposicao() -> dict:
    """Calcula o que precisa ser comprado, por fornecedor, sem gerar excesso que vire desperdício.

    Quantidade sugerida = média de vendas/dia x (prazo de entrega + dias de cobertura) - saldo atual,
    respeitando o estoque mínimo. Produtos com sobra projetada não entram.
    """
    with conectar() as conn:
        prods = conn.execute("SELECT * FROM produtos").fetchall()
        por_forn: dict[str, list] = {}
        for p in prods:
            saldo = _saldo(conn, p["id"])
            media = _media_vendas_dia(conn, p["id"])
            alvo = max(media * (p["prazo_entrega_dias"] + COBERTURA_DIAS), p["estoque_minimo"])
            precisa = round(alvo - saldo, 1)
            if precisa > 0 and (saldo < p["estoque_minimo"] or saldo < media * p["prazo_entrega_dias"] * 1.5):
                por_forn.setdefault(p["fornecedor"] or "sem fornecedor", []).append({
                    "produto": p["nome"], "saldo": saldo, "media_vendas_dia": media,
                    "quantidade_sugerida": precisa, "unidade": p["unidade"],
                    "custo_estimado": round(precisa * p["preco_custo"], 2),
                })
    return {"cobertura_dias": COBERTURA_DIAS, "sugestoes_por_fornecedor": por_forn}


def criar_pedido_compra(fornecedor: str, produtos: list[str], quantidades: list[float], justificativa: str) -> dict:
    """Cria um RASCUNHO de pedido de compra. O pedido só é enviado depois que o dono aprova na tela.

    Use somente depois de calcular_reposicao(). Quantidades acima de 2x a sugestão são bloqueadas.

    Args:
        fornecedor: nome do fornecedor.
        produtos: lista com os nomes dos produtos.
        quantidades: lista de quantidades, na mesma ordem de 'produtos'.
        justificativa: por que este pedido é necessário (curto).
    """
    if not produtos or len(produtos) != len(quantidades):
        return {"erro": "'produtos' e 'quantidades' devem ter o mesmo tamanho e não podem ser vazios."}
    sugestoes = {}
    for itens in calcular_reposicao()["sugestoes_por_fornecedor"].values():
        for i in itens:
            sugestoes[i["produto"]] = i["quantidade_sugerida"]
    with conectar() as conn:
        itens, total = [], 0.0
        for nome, qtd in zip(produtos, quantidades):
            p, erro = _resolver_produto(conn, nome)
            if erro:
                return erro
            if qtd <= 0:
                return {"erro": f"Quantidade inválida para {p['nome']}."}
            limite = 2 * sugestoes.get(p["nome"], p["estoque_minimo"] or 0)
            if limite and qtd > limite:
                return {"erro": f"Guardrail: {qtd} de {p['nome']} é mais que o dobro do sugerido ({limite / 2}). "
                                f"Comprar demais gera desperdício."}
            itens.append({"produto": p["nome"], "quantidade": qtd, "unidade": p["unidade"],
                          "custo": round(qtd * p["preco_custo"], 2)})
            total += qtd * p["preco_custo"]
        cur = conn.execute(
            "INSERT INTO pedidos (fornecedor, itens_json, valor_estimado, status, justificativa, criado_em) VALUES (?,?,?,?,?,?)",
            (fornecedor, json.dumps(itens, ensure_ascii=False), round(total, 2), "rascunho", justificativa,
             datetime.now().isoformat(timespec="seconds")),
        )
        return {"ok": True, "pedido_id": cur.lastrowid, "status": "rascunho (aguardando aprovação do dono)",
                "fornecedor": fornecedor, "itens": itens, "valor_estimado": round(total, 2)}


def relatorio_desperdicio(dias: int = 30) -> dict:
    """Resumo de perdas e doações no período, em quantidade e em R$ (custo).

    Args:
        dias: tamanho do período em dias (padrão 30).
    """
    inicio = (_hoje() - timedelta(days=int(dias))).isoformat()
    with conectar() as conn:
        rows = conn.execute(
            """SELECT p.nome, m.tipo, SUM(m.quantidade) q, SUM(m.valor) v
               FROM movimentacoes m JOIN produtos p ON p.id=m.produto_id
               WHERE m.tipo IN ('perda','doacao') AND m.data>=? GROUP BY p.nome, m.tipo ORDER BY v DESC""",
            (inicio,),
        ).fetchall()
        vendas = conn.execute("SELECT COALESCE(SUM(valor),0) v FROM movimentacoes WHERE tipo='venda' AND data>=?",
                              (inicio,)).fetchone()["v"]
    perdas = [dict(produto=r["nome"], quantidade=r["q"], valor_rs=round(r["v"], 2)) for r in rows if r["tipo"] == "perda"]
    doacoes = [dict(produto=r["nome"], quantidade=r["q"], valor_rs=round(r["v"], 2)) for r in rows if r["tipo"] == "doacao"]
    total_perdas = round(sum(p["valor_rs"] for p in perdas), 2)
    return {"periodo_dias": dias, "perdas": perdas, "doacoes": doacoes, "total_perdas_rs": total_perdas,
            "total_doado_rs": round(sum(d["valor_rs"] for d in doacoes), 2), "faturamento_rs": round(vendas, 2),
            "perdas_sobre_faturamento": f"{(total_perdas / vendas * 100) if vendas else 0:.1f}%"}


# Ferramentas expostas ao agente (a aprovação de pedidos NÃO está aqui: é só humana)
FERRAMENTAS = [
    consultar_estoque,
    registrar_entrada,
    registrar_saida,
    listar_produtos_vencendo,
    analisar_risco_desperdicio,
    calcular_reposicao,
    criar_pedido_compra,
    relatorio_desperdicio,
]


# --------------------------------------------- funções só da interface (humano)
def listar_pedidos(status: str | None = None) -> list[dict]:
    with conectar() as conn:
        q = "SELECT * FROM pedidos" + (" WHERE status=?" if status else "") + " ORDER BY id DESC"
        rows = conn.execute(q, (status,) if status else ()).fetchall()
    return [dict(r, itens=json.loads(r["itens_json"])) for r in rows]


def decidir_pedido(pedido_id: int, aprovar: bool) -> None:
    with conectar() as conn:
        conn.execute("UPDATE pedidos SET status=? WHERE id=?", ("aprovado" if aprovar else "recusado", pedido_id))
