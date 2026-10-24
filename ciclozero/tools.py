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
import math
import unicodedata
from datetime import date, datetime, timedelta

from .db import conectar

JANELA_VENDAS_DIAS = 14      # histórico usado para média de vendas
COBERTURA_DIAS = 5           # quantos dias de venda um pedido deve cobrir
DESCONTO_MAX = 0.5           # guardrail: nunca sugerir mais que 50% de desconto


# ----------------------------------------------------------------- utilitários
def _hoje() -> date:
    return date.today()


def ler_data(txt: str) -> date:
    """Aceita DD/MM/AAAA (padrão brasileiro), DD/MM/AA ou AAAA-MM-DD."""
    txt = (txt or "").strip()
    for fmt in ("%d/%m/%Y", "%d/%m/%y", "%Y-%m-%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(txt, fmt).date()
        except ValueError:
            pass
    raise ValueError(txt)


def data_br(iso: str | None) -> str | None:
    """'2026-10-30' -> '30/10/2026' (para exibir)."""
    if not iso:
        return iso
    try:
        return date.fromisoformat(str(iso)[:10]).strftime("%d/%m/%Y")
    except ValueError:
        return iso


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


def _num(v: float) -> str:
    """Número no padrão brasileiro com até 2 casas: 106.333 -> '106,33'; 34.0 -> '34'."""
    return f"{round(v, 2):.2f}".rstrip("0").rstrip(".").replace(".", ",")


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
        validade: data de validade no formato DD/MM/AAAA (ex.: 30/10/2026).
    """
    if quantidade is None or quantidade <= 0:
        return {"erro": "A quantidade precisa ser maior que zero."}
    try:
        val = ler_data(validade)
    except (TypeError, ValueError):
        return {"erro": "Validade inválida. Use o formato DD/MM/AAAA."}
    if val < _hoje():
        return {"erro": f"A validade {val.strftime('%d/%m/%Y')} já passou; confirme a data com o usuário."}
    validade = val.isoformat()
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


def cadastrar_produto(nome: str, categoria: str, unidade: str, preco_custo: float, preco_venda: float,
                      estoque_minimo: float, fornecedor: str, prazo_entrega_dias: int,
                      validade_padrao_dias: int = 7) -> dict:
    """Cadastra um produto novo. Use SOMENTE com dados informados pelo usuário; se faltar algum, pergunte.

    Args:
        nome: nome do produto, ex.: 'Picanha'.
        categoria: ex.: 'Carnes', 'Padaria', 'Laticínios', 'Hortifruti', 'Frios', 'Mercearia'.
        unidade: 'kg' ou 'un'.
        preco_custo: quanto o comércio paga por unidade/kg, em R$.
        preco_venda: preço de venda por unidade/kg, em R$.
        estoque_minimo: quantidade mínima que deve ter na loja.
        fornecedor: nome do fornecedor.
        prazo_entrega_dias: dias que o fornecedor leva para entregar.
        validade_padrao_dias: quantos dias o produto costuma durar depois que chega (usado na leitura de nota fiscal).
    """
    unidade = (unidade or "").strip().lower()
    if unidade not in ("kg", "un"):
        return {"erro": "unidade deve ser 'kg' ou 'un'."}
    if not nome or not nome.strip():
        return {"erro": "nome do produto vazio."}
    if preco_custo is None or preco_venda is None or preco_custo <= 0 or preco_venda <= 0:
        return {"erro": "preço de custo e de venda precisam ser maiores que zero; pergunte ao usuário."}
    if estoque_minimo is None or estoque_minimo < 0 or prazo_entrega_dias is None or prazo_entrega_dias < 0:
        return {"erro": "estoque mínimo e prazo de entrega não podem ser negativos."}
    with conectar() as conn:
        existentes = [r["nome"] for r in conn.execute("SELECT nome FROM produtos")]
        alvo = _norm(nome)
        if alvo in {_norm(n) for n in existentes}:
            return {"erro": f"'{nome}' já está cadastrado."}
        parecidos = difflib.get_close_matches(alvo, [_norm(n) for n in existentes], n=1, cutoff=0.85)
        if parecidos:
            original = next(n for n in existentes if _norm(n) == parecidos[0])
            return {"erro": f"Já existe '{original}', muito parecido. Confirme com o usuário se é outro produto."}
        conn.execute(
            "INSERT INTO produtos (nome, categoria, unidade, preco_custo, preco_venda, estoque_minimo, fornecedor, prazo_entrega_dias,"
            " validade_padrao_dias) VALUES (?,?,?,?,?,?,?,?,?)",
            (nome.strip(), categoria, unidade, preco_custo, preco_venda, estoque_minimo, fornecedor, int(prazo_entrega_dias),
             int(validade_padrao_dias or 7)))
    aviso = "Atenção: preço de venda menor que o custo." if preco_venda < preco_custo else None
    r = {"ok": True, "produto": nome.strip(), "unidade": unidade, "margem": f"{(preco_venda / preco_custo - 1):.0%}"}
    if aviso:
        r["aviso"] = aviso
    return r


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
        if tipo == "perda" and "venc" in (motivo or "").lower():
            vencido = conn.execute(
                "SELECT COALESCE(SUM(quantidade),0) q FROM lotes WHERE produto_id=? AND validade IS NOT NULL AND validade<?",
                (p["id"], _hoje().isoformat())).fetchone()["q"]
            if quantidade > vencido:
                return {"erro": f"Só há {vencido} {p['unidade']} de {p['nome']} vencidos no estoque. Perda por "
                                f"vencimento não pode tirar produto dentro da validade. Mercadoria que chegou vencida "
                                f"não entra no estoque: devolva ao fornecedor."}
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
            sobra = l["quantidade"] - vende
            # produto vendido por unidade não tem fração: arredonda a sobra para cima
            sobra = float(math.ceil(sobra - 1e-9)) if l["unidade"] != "kg" else round(sobra, 1)
            sobra = max(sobra, 0.0)
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
            item = {"lote": l["id"], "produto": l["nome"], "quantidade_no_lote": l["quantidade"], "unidade": l["unidade"],
                    "validade": l["validade"], "dias_para_vencer": dias_rest, "media_vendas_dia": media,
                    "sobra_projetada": sobra, "perda_sem_acao_rs": perda_rs, "acao": acao}
            if acao == "promocao":
                item["desconto_sugerido"] = f"{int(desconto * 100)}%"
                item["preco_promocional"] = round(l["preco_venda"] * (1 - desconto), 2)
                item["receita_recuperada_rs"] = round(sobra * item["preco_promocional"], 2)
                item["abaixo_do_custo"] = item["preco_promocional"] < l["preco_custo"]
            if acao == "doacao":
                item["quantidade_para_doar"] = sobra
            resultado.append(item)
    em_risco = [r for r in resultado if r["acao"] != "ok"]
    soma = lambda chave, acao=None: round(sum(r.get(chave, 0) for r in em_risco if acao is None or r["acao"] == acao), 2)
    return {
        "data": _hoje().isoformat(),
        "lotes_analisados": len(resultado),
        "lotes_em_risco": em_risco,
        "resumo": {
            "qtd_lotes_em_risco": len(em_risco),
            "perda_total_sem_acao_rs": soma("perda_sem_acao_rs"),
            "receita_recuperada_com_promocoes_rs": soma("receita_recuperada_rs", "promocao"),
            "custo_dos_itens_em_promocao_rs": soma("perda_sem_acao_rs", "promocao"),
            "custo_dos_itens_para_doacao_rs": soma("perda_sem_acao_rs", "doacao"),
            "custo_ja_vencido_para_descarte_rs": soma("perda_sem_acao_rs", "descartar"),
            "lotes_por_acao": {a: sum(1 for r in em_risco if r["acao"] == a) for a in ("promocao", "doacao", "descartar")},
        },
    }


def calcular_reposicao() -> dict:
    """Calcula o que precisa ser comprado, por fornecedor, sem gerar excesso que vire desperdício.

    Quantidade sugerida = média de vendas/dia x (prazo de entrega + dias de cobertura) - saldo atual
    - o que já foi pedido, respeitando o estoque mínimo. Produtos com sobra projetada não entram.
    Cada item traz o campo 'conta' com o cálculo completo: use-o para explicar o número ao usuário.
    """
    with conectar() as conn:
        prods = conn.execute("SELECT * FROM produtos").fetchall()
        # o que já foi pedido (rascunho ou aprovado) conta como "a caminho": evita pedido duplicado
        a_caminho: dict[str, float] = {}
        for ped in conn.execute("SELECT itens_json FROM pedidos WHERE status IN ('rascunho','aprovado') "
                                "AND recebido_em IS NULL"):
            for item in json.loads(ped["itens_json"]):
                a_caminho[item["produto"]] = a_caminho.get(item["produto"], 0) + item["quantidade"]
        por_forn: dict[str, list] = {}
        for p in prods:
            saldo = _saldo(conn, p["id"])
            pedido = a_caminho.get(p["nome"], 0)
            media = _media_vendas_dia(conn, p["id"])
            prazo = p["prazo_entrega_dias"]
            pela_venda = media * (prazo + COBERTURA_DIAS)
            alvo = max(pela_venda, p["estoque_minimo"])
            bruto = alvo - saldo - pedido
            # arredonda para cima: unidade sem fração; kg com 1 casa (nunca pede menos que o necessário)
            precisa = float(math.ceil(bruto - 1e-9)) if p["unidade"] != "kg" else math.ceil(bruto * 10 - 1e-9) / 10
            if precisa > 0 and (saldo + pedido < p["estoque_minimo"] or saldo + pedido < media * prazo * 1.5):
                u = p["unidade"]
                dias_txt = "dia" if prazo == 1 else "dias"
                if pela_venda >= p["estoque_minimo"]:
                    base = (f"média de vendas {_num(media)} {u}/dia × ({prazo} {dias_txt} de entrega + {COBERTURA_DIAS} dias "
                            f"de cobertura = {prazo + COBERTURA_DIAS} dias) = {_num(pela_venda)} {u}")
                else:
                    base = f"estoque mínimo de {_num(alvo)} {u} (maior que a venda prevista de {_num(pela_venda)} {u})"
                conta = f"{base} − saldo atual {_num(saldo)} {u}"
                if pedido:
                    conta += f" − já pedido {_num(pedido)} {u}"
                conta += f" = {_num(bruto)} {u}"
                if precisa != round(bruto, 2):
                    conta += f" → {_num(precisa)} {u} (arredondado para cima)"
                item = {"produto": p["nome"], "saldo": saldo, "media_vendas_dia": media,
                        "prazo_entrega_dias": prazo, "quantidade_sugerida": precisa, "unidade": u,
                        "custo_estimado": round(precisa * p["preco_custo"], 2), "conta": conta}
                if pedido:
                    item["ja_pedido"] = pedido
                por_forn.setdefault(p["fornecedor"] or "sem fornecedor", []).append(item)
    return {"cobertura_dias": COBERTURA_DIAS,
            "regra_cobertura": (f"Regra fixa do sistema: cada pedido cobre o prazo de entrega do fornecedor mais "
                                f"{COBERTURA_DIAS} dias de vendas. Não é configurável pelo usuário nesta versão."),
            "sugestoes_por_fornecedor": por_forn}


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


def criar_pedidos_sugeridos(fornecedores: list[str] | None = None) -> dict:
    """Cria, de uma vez, um RASCUNHO de pedido para cada fornecedor com reposição necessária,
    usando exatamente as quantidades de calcular_reposicao(). O dono aprova cada pedido na tela.

    Args:
        fornecedores: opcional; limite a estes fornecedores. Vazio = todos que precisam de reposição.
    """
    sugestoes = calcular_reposicao()["sugestoes_por_fornecedor"]
    if fornecedores:
        alvo = {_norm(f) for f in fornecedores}
        sugestoes = {f: i for f, i in sugestoes.items() if _norm(f) in alvo}
    pedidos = []
    for forn, itens in sugestoes.items():
        r = criar_pedido_compra(forn, [i["produto"] for i in itens], [i["quantidade_sugerida"] for i in itens],
                                "Reposição automática: cobre o prazo de entrega + "
                                f"{COBERTURA_DIAS} dias de vendas, sem excesso.")
        pedidos.append(r if r.get("ok") else {"fornecedor": forn, **r})
    return {"pedidos_criados": len([p for p in pedidos if p.get("ok")]), "pedidos": pedidos,
            "valor_total_rs": round(sum(p.get("valor_estimado", 0) for p in pedidos), 2),
            "status": "rascunhos aguardando aprovação do dono"}


def relatorio_desperdicio(dias: int = 30) -> dict:
    """Resumo de perdas e doações no período, em quantidade e em R$ (custo).

    Args:
        dias: tamanho do período em dias (padrão 30).
    """
    inicio = (_hoje() - timedelta(days=int(dias))).isoformat()
    with conectar() as conn:
        rows = conn.execute(
            """SELECT p.nome, p.unidade, m.tipo, SUM(m.quantidade) q, SUM(m.valor) v
               FROM movimentacoes m JOIN produtos p ON p.id=m.produto_id
               WHERE m.tipo IN ('perda','doacao') AND m.data>=? GROUP BY p.nome, p.unidade, m.tipo ORDER BY v DESC""",
            (inicio,),
        ).fetchall()
        vendas = conn.execute("SELECT COALESCE(SUM(valor),0) v FROM movimentacoes WHERE tipo='venda' AND data>=?",
                              (inicio,)).fetchone()["v"]
    perdas = [dict(produto=r["nome"], quantidade=r["q"], unidade=r["unidade"], valor_rs=round(r["v"], 2))
              for r in rows if r["tipo"] == "perda"]
    doacoes = [dict(produto=r["nome"], quantidade=r["q"], unidade=r["unidade"], valor_rs=round(r["v"], 2))
               for r in rows if r["tipo"] == "doacao"]
    total_perdas = round(sum(p["valor_rs"] for p in perdas), 2)
    return {"periodo_dias": dias, "perdas": perdas, "doacoes": doacoes, "total_perdas_rs": total_perdas,
            "total_doado_rs": round(sum(d["valor_rs"] for d in doacoes), 2), "faturamento_rs": round(vendas, 2),
            "perdas_sobre_faturamento": f"{(total_perdas / vendas * 100) if vendas else 0:.1f}%"}


# Ferramentas expostas ao agente (a aprovação de pedidos NÃO está aqui: é só humana)
FERRAMENTAS = [
    consultar_estoque,
    cadastrar_produto,
    registrar_entrada,
    registrar_saida,
    listar_produtos_vencendo,
    analisar_risco_desperdicio,
    calcular_reposicao,
    criar_pedidos_sugeridos,
    criar_pedido_compra,
    relatorio_desperdicio,
]


# --------------------------------------------- funções só da interface (humano)
def historico_diario(dias: int = 30) -> list[dict]:
    """Uma linha por dia x produto x tipo (venda/perda/doacao/entrada), com quantidade e R$.
    Base para os gráficos do dashboard."""
    inicio = (_hoje() - timedelta(days=int(dias))).isoformat()
    with conectar() as conn:
        rows = conn.execute(
            """SELECT m.data, p.nome produto, p.categoria, m.tipo, SUM(m.quantidade) quantidade, SUM(m.valor) valor
               FROM movimentacoes m JOIN produtos p ON p.id=m.produto_id
               WHERE m.data>=? GROUP BY m.data, p.nome, p.categoria, m.tipo ORDER BY m.data""",
            (inicio,),
        ).fetchall()
    return [dict(r) for r in rows]


def listar_pedidos(status: str | None = None) -> list[dict]:
    with conectar() as conn:
        q = "SELECT * FROM pedidos" + (" WHERE status=?" if status else "") + " ORDER BY id DESC"
        rows = conn.execute(q, (status,) if status else ()).fetchall()
    return [dict(r, itens=json.loads(r["itens_json"])) for r in rows]


def decidir_pedido(pedido_id: int, aprovar: bool) -> None:
    with conectar() as conn:
        conn.execute("UPDATE pedidos SET status=?, aprovado_em=? WHERE id=?",
                     ("aprovado" if aprovar else "recusado",
                      datetime.now().isoformat(timespec="seconds") if aprovar else None, pedido_id))


def receber_pedido(pedido_id: int) -> dict:
    """Fornecedor entregou um pedido aprovado: os itens entram no estoque (validade padrão de cada produto)
    e o valor sai do caixa (compra paga na entrega). Só o dono/interface ou a simulação chamam."""
    with conectar() as conn:
        p = conn.execute("SELECT * FROM pedidos WHERE id=?", (pedido_id,)).fetchone()
        if not p or p["status"] != "aprovado" or p["recebido_em"]:
            return {"erro": "Pedido não está aprovado ou já foi recebido."}
        itens = json.loads(p["itens_json"])
        validades = {r["nome"]: r["v"] for r in conn.execute(
            "SELECT nome, COALESCE(validade_padrao_dias, 7) v FROM produtos")}
    lancados = []
    for i in itens:
        validade = (_hoje() + timedelta(days=int(validades.get(i["produto"], 7)))).strftime("%d/%m/%Y")
        r = registrar_entrada(i["produto"], float(i["quantidade"]), validade)
        if r.get("ok"):
            lancados.append(i["produto"])
    with conectar() as conn:
        conn.execute("UPDATE pedidos SET recebido_em=? WHERE id=?", (datetime.now().isoformat(timespec="seconds"), pedido_id))
    return {"ok": True, "pedido_id": pedido_id, "fornecedor": p["fornecedor"], "itens_recebidos": lancados,
            "valor_rs": p["valor_estimado"]}


def financeiro_do_dia() -> dict:
    """Fechamento do dia (usado pela tela e pelo agente).

    - Caixa do dia  = entradas (vendas) − saídas (compras recebidas/produção + despesas). Pode ser negativo.
    - Lucro do dia  = vendas − custo do que foi vendido − perdas − despesas. Compra não é prejuízo: vira estoque.
    - A pagar       = pedidos aprovados que ainda não chegaram (compromisso com fornecedor).
    """
    hoje = _hoje().isoformat()
    with conectar() as conn:
        r = conn.execute(
            """SELECT
                 COALESCE(SUM(CASE WHEN m.tipo='venda' THEN m.valor END),0)                       AS vendas,
                 COALESCE(SUM(CASE WHEN m.tipo='venda' THEN m.quantidade*p.preco_custo END),0)    AS custo_vendas,
                 COALESCE(SUM(CASE WHEN m.tipo='entrada' THEN m.valor END),0)                     AS compras,
                 COALESCE(SUM(CASE WHEN m.tipo='perda' THEN m.valor END),0)                       AS perdas,
                 COUNT(CASE WHEN m.tipo='venda' THEN 1 END)                                        AS n_vendas
               FROM movimentacoes m JOIN produtos p ON p.id=m.produto_id WHERE m.data=?""", (hoje,)).fetchone()
        tem_despesas = conn.execute("SELECT 1 FROM sqlite_master WHERE name='despesas'").fetchone()
        despesas = conn.execute("SELECT COALESCE(SUM(valor),0) v FROM despesas WHERE data=?", (hoje,)
                                ).fetchone()["v"] if tem_despesas else 0.0
        rasc = conn.execute("SELECT COUNT(*) n, COALESCE(SUM(valor_estimado),0) v FROM pedidos WHERE status='rascunho'"
                            ).fetchone()
        apagar = conn.execute("SELECT COUNT(*) n, COALESCE(SUM(valor_estimado),0) v FROM pedidos "
                              "WHERE status='aprovado' AND recebido_em IS NULL").fetchone()
        excessos = [json.loads(x["conteudo"]) for x in conn.execute(
            "SELECT conteudo FROM log_agente WHERE tipo='alerta_excesso'")]
    excessos = [e for e in excessos if e.get("data") == hoje]
    vendas, custo, compras, perdas = r["vendas"], r["custo_vendas"], r["compras"], r["perdas"]
    lucro_bruto = vendas - custo - perdas
    lucro = lucro_bruto - despesas
    saidas = compras + despesas
    return {"vendas_rs": round(vendas, 2), "custo_vendas_rs": round(custo, 2), "compras_rs": round(compras, 2),
            "despesas_rs": round(despesas, 2), "perdas_rs": round(perdas, 2), "saidas_caixa_rs": round(saidas, 2),
            "caixa_rs": round(vendas - saidas, 2), "lucro_bruto_rs": round(lucro_bruto, 2), "lucro_rs": round(lucro, 2),
            "margem": (lucro / vendas) if vendas else 0.0, "n_vendas": r["n_vendas"],
            "ticket_medio_rs": round(vendas / r["n_vendas"], 2) if r["n_vendas"] else 0.0,
            "pedidos_pendentes": rasc["n"], "pedidos_pendentes_rs": round(rasc["v"], 2),
            "a_pagar_n": apagar["n"], "a_pagar_rs": round(apagar["v"], 2),
            "excesso_rs": round(sum(e["excesso_rs"] for e in excessos), 2), "n_excessos": len(excessos)}


def resumo_do_dia() -> dict:
    """Resultado financeiro de HOJE, em tempo real: vendas, caixa, lucro, despesas, compras, perdas,
    compras em excesso (que vão virar lixo), pedidos aguardando aprovação e valores a pagar a fornecedores.
    Use para perguntas como "quanto vendi hoje?", "como está o caixa?", "quanto lucrei?"."""
    f = financeiro_do_dia()
    return {"data": _hoje().isoformat(), "vendas_rs": f["vendas_rs"], "numero_de_vendas": f["n_vendas"],
            "ticket_medio_rs": f["ticket_medio_rs"], "caixa_do_dia_rs": f["caixa_rs"],
            "lucro_do_dia_rs": f["lucro_rs"], "margem": f"{f['margem']:.0%}", "lucro_bruto_rs": f["lucro_bruto_rs"],
            "despesas_rs": f["despesas_rs"], "compras_recebidas_rs": f["compras_rs"], "perdas_rs": f["perdas_rs"],
            "compras_em_excesso_rs": f["excesso_rs"], "pedidos_aguardando_aprovacao": f["pedidos_pendentes"],
            "a_pagar_fornecedores_rs": f["a_pagar_rs"],
            "explicacao": "caixa = vendas − compras recebidas − despesas; lucro = vendas − custo do vendido − perdas − despesas"}


# ferramenta financeira (definida mais abaixo no arquivo) também vai para o agente
FERRAMENTAS.insert(0, resumo_do_dia)
