"""Peças visuais da aba do agente (João Paulo).

- passo_amigavel(): traduz o progresso técnico do agente ("🔧 calcular_reposicao({...})")
  para uma frase que a banca e o dono do comércio entendem.
- render_plano(): mostra o resultado da análise de risco e dos pedidos em cartões coloridos,
  com os números lidos direto do resultado das ferramentas (nada vem do texto do modelo).
"""
from __future__ import annotations

import ast
import re

import streamlit as st

from .graficos import CORES_ACAO, NOME_ACAO, num, reais

NOMES_FERRAMENTAS = {
    "consultar_estoque": "📦 Consultando o estoque",
    "cadastrar_produto": "🆕 Cadastrando o produto",
    "registrar_entrada": "📥 Registrando a chegada de mercadoria",
    "registrar_saida": "📤 Registrando a saída",
    "listar_produtos_vencendo": "⏰ Verificando o que vence em breve",
    "analisar_risco_desperdicio": "⏳ Analisando o risco de desperdício, lote a lote",
    "calcular_reposicao": "🧮 Calculando quanto comprar",
    "criar_pedidos_sugeridos": "🧾 Montando os pedidos de compra",
    "criar_pedido_compra": "🧾 Montando um pedido de compra",
    "relatorio_desperdicio": "📊 Levantando as perdas do período",
}

_FERRAMENTA = re.compile(r"^🔧\s*(\w+)\((.*)\)\s*$", re.S)
_PENSANDO = re.compile(r"^🧠\s*passo\s*(\d+)", re.I)


def nome_amigavel(ferramenta: str) -> str:
    return NOMES_FERRAMENTAS.get(ferramenta, f"🔧 Usando {ferramenta.replace('_', ' ')}")


def _detalhe(args_txt: str) -> str:
    """Pega o produto ou fornecedor dos argumentos, quando houver, para dar contexto."""
    try:
        args = ast.literal_eval(args_txt) if args_txt.strip() else {}
    except (ValueError, SyntaxError):
        return ""
    if not isinstance(args, dict):
        return ""
    for chave in ("produto", "fornecedor", "nome"):
        if args.get(chave):
            return f" — {args[chave]}"
    if args.get("produtos"):
        return " — " + ", ".join(map(str, args["produtos"]))
    return ""


def passo_amigavel(texto: str) -> str:
    """Converte uma mensagem de progresso do agente em linguagem simples."""
    m = _FERRAMENTA.match(texto or "")
    if m:
        return nome_amigavel(m.group(1)) + _detalhe(m.group(2)) + "…"
    m = _PENSANDO.match(texto or "")
    if m:
        return "🧠 Decidindo o próximo passo…" if m.group(1) != "1" else "🧠 Entendendo o pedido…"
    return texto  # trocas de modelo/provedor: mantém o aviso original (mostra a robustez)


# ------------------------------------------------------------------ cartões

def _selo(acao: str, cor: str | None = None) -> str:
    cor = cor or CORES_ACAO.get(acao, "#9AA0A6")
    return (f"<span style='background:{cor};color:#fff;padding:2px 10px;border-radius:999px;"
            f"font-size:0.78rem;font-weight:600;letter-spacing:.02em'>{acao}</span>")


def _quando(dias: int) -> str:
    if dias < 0:
        return "já vencido"
    return {0: "vence hoje", 1: "vence amanhã"}.get(dias, f"vence em {dias} dias")


def _cartao_lote(lote: dict) -> None:
    acao = NOME_ACAO.get(lote.get("acao"), lote.get("acao", ""))
    u = lote.get("unidade", "")
    with st.container(border=True):
        st.markdown(f"{_selo(acao)}&nbsp;&nbsp;<b>{lote.get('produto', '')}</b>", unsafe_allow_html=True)
        st.caption(f"{_quando(int(lote.get('dias_para_vencer', 0)))} · "
                   f"sobra prevista {num(lote.get('sobra_projetada', 0))} {u}")
        if acao == "Promoção":
            st.markdown(f"**{lote.get('desconto_sugerido', '')} de desconto** → "
                        f"{reais(lote.get('preco_promocional', 0))}")
            if lote.get("receita_recuperada_rs"):
                st.caption(f"recupera {reais(lote['receita_recuperada_rs'])} em vendas")
        elif acao == "Doação":
            st.markdown(f"**Doar {num(lote.get('quantidade_para_doar', lote.get('sobra_projetada', 0)))} {u}**")
            st.caption("banco de alimentos ou ONG parceira")
        elif acao == "Descarte":
            st.markdown("**Retirar da venda e descartar**")
        st.caption(f"perda se nada for feito: {reais(lote.get('perda_sem_acao_rs', 0))}")


def _cartao_pedido(p: dict) -> None:
    with st.container(border=True):
        st.markdown(f"{_selo('Rascunho', '#5F6368')}&nbsp;&nbsp;<b>Pedido #{p.get('pedido_id', '?')}</b>",
                    unsafe_allow_html=True)
        st.markdown(f"**{p.get('fornecedor', '')}** · {reais(p.get('valor_estimado', 0))}")
        itens = p.get("itens") or []
        if itens:
            st.caption(" · ".join(f"{i.get('produto')}: {num(i.get('quantidade', 0))}" for i in itens))
        st.caption("aguardando sua aprovação na aba 🧾 Pedidos")


def tem_plano(passos: list[dict]) -> bool:
    return any(p.get("ferramenta") in ("analisar_risco_desperdicio", "criar_pedidos_sugeridos") for p in passos or [])


def render_plano(passos: list[dict]) -> None:
    """Cartões com o plano de ação por lote e os pedidos criados, a partir dos resultados das ferramentas."""
    risco = next((p["resultado"] for p in reversed(passos)
                  if p.get("ferramenta") == "analisar_risco_desperdicio" and "lotes_em_risco" in p.get("resultado", {})),
                 None)
    pedidos = next((p["resultado"] for p in reversed(passos)
                    if p.get("ferramenta") == "criar_pedidos_sugeridos" and "pedidos" in p.get("resultado", {})), None)

    if risco:
        r = risco.get("resumo", {})
        k1, k2, k3 = st.columns(3)
        k1.metric("Perda se nada for feito", reais(r.get("perda_total_sem_acao_rs", 0)))
        k2.metric("Recuperado com promoções", reais(r.get("receita_recuperada_com_promocoes_rs", 0)))
        k3.metric("Vai para doação (custo)", reais(r.get("custo_dos_itens_para_doacao_rs", 0)))
        lotes = sorted(risco.get("lotes_em_risco", []), key=lambda x: (x.get("dias_para_vencer", 0),
                                                                        -x.get("perda_sem_acao_rs", 0)))
        if lotes:
            st.markdown("##### Plano de ação por lote")
            for i in range(0, len(lotes), 3):
                for col, lote in zip(st.columns(3), lotes[i:i + 3]):
                    with col:
                        _cartao_lote(lote)
        else:
            st.success("Nenhum lote em risco nos próximos dias.")

    if pedidos:
        criados = [p for p in pedidos.get("pedidos", []) if p.get("ok")]
        if criados:
            st.markdown(f"##### Pedidos de compra · {reais(pedidos.get('valor_total_rs', 0))} no total")
            for i in range(0, len(criados), 3):
                for col, p in zip(st.columns(3), criados[i:i + 3]):
                    with col:
                        _cartao_pedido(p)
        else:
            st.info("Nenhuma reposição necessária agora.")
