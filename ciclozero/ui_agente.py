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


# ------------------------------------------------------------------ boas-vindas e estilo

CSS = """
<style>
/* caixa de mensagem do agente: maior, com borda verde e sombra para chamar atenção */
[data-testid="stChatInput"] {
    border: 2px solid #2E7D32 !important;
    border-radius: 16px !important;
    box-shadow: 0 6px 22px rgba(46, 125, 50, .18) !important;
    background: #FFFFFF !important;
    padding: 4px 6px !important;
}
[data-testid="stChatInput"] textarea {
    font-size: 1.08rem !important;
    min-height: 3.2rem !important;
}
[data-testid="stChatInput"] textarea::placeholder { color: #5F7F61 !important; opacity: 1 !important; }
[data-testid="stChatInput"]:focus-within { box-shadow: 0 6px 26px rgba(46, 125, 50, .32) !important; }
.cz-pergunta { font-size: 1.15rem; font-weight: 700; color: #1B5E20; margin: .6rem 0 .25rem; }

/* barra lateral */
.cz-boasvindas { font-size: 1.05rem; line-height: 1.45; margin-bottom: .2rem; }
.cz-boasvindas b { color: #1B5E20; }
.cz-marca { display: flex; align-items: center; gap: .55rem; margin: .6rem 0 .9rem; }
.cz-marca img { width: 44px; height: 44px; object-fit: contain; }
.cz-marca .cz-icone { font-size: 2.3rem; line-height: 1; }
.cz-marca .cz-nome { font-size: 1.7rem; font-weight: 800; color: #1B5E20; letter-spacing: -.01em; }
.cz-dor { background: #F1F8F1; border-left: 4px solid #2E7D32; border-radius: 10px;
          padding: .8rem .9rem; margin-bottom: 1rem; }
.cz-dor h4 { margin: 0 0 .35rem; font-size: 1rem; color: #1B5E20; }
.cz-dor p { margin: 0; font-size: .9rem; line-height: 1.45; color: #2F3B30; }
</style>
"""

TEXTO_DOR = (
    "Sem um bom controle, produtos podem vencer, faltar quando seus clientes precisam ou ficar parados "
    "ocupando espaço e dinheiro. Acompanhe o que entra e sai, confira as quantidades e fique atento às "
    "datas de validade para reduzir perdas e manter seu estoque sempre organizado."
)


def aplicar_estilo() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


def nome_usuario(padrao: str = "usuário") -> str:
    """Nome de quem está usando: login do Streamlit (se configurado) ou o nome digitado na barra lateral."""
    try:
        if st.user.is_logged_in and st.user.get("name"):
            return str(st.user.get("name")).split()[0]
    except Exception:  # login não configurado nesta instalação
        pass
    return (st.session_state.get("nome_usuario") or "").strip() or padrao


def _logo_html() -> str:
    """Usa assets/logo.png se existir; senão, o símbolo ♻️."""
    import base64
    from pathlib import Path

    for nome in ("logo.png", "logo.jpg", "logo.svg"):
        arq = Path(__file__).resolve().parent.parent / "assets" / nome
        if arq.exists():
            tipo = "svg+xml" if arq.suffix == ".svg" else arq.suffix[1:].replace("jpg", "jpeg")
            dados = base64.b64encode(arq.read_bytes()).decode()
            return f"<img src='data:image/{tipo};base64,{dados}' alt='Ciclo Zero'>"
    return "<span class='cz-icone'>♻️</span>"


def cabecalho_lateral() -> None:
    """Boas-vindas com o nome da pessoa, marca do Ciclo Zero e o porquê do controle de estoque."""
    from html import escape

    nome = escape(nome_usuario())
    st.markdown(
        f"<div class='cz-boasvindas'>Bem-vindo, <b>{nome}</b>!<br>"
        "Sou o agente que te ajuda no controle de estoque.</div>"
        f"<div class='cz-marca'>{_logo_html()}<span class='cz-nome'>Ciclo Zero</span></div>"
        f"<div class='cz-dor'><h4>Controle de estoque sem complicação</h4><p>{TEXTO_DOR}</p></div>",
        unsafe_allow_html=True,
    )
