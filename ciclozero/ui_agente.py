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


# ------------------------------------------------------------------ etiquetas e pedidos
COR_TEXTO_ACAO = {"Promoção": "#8A5A06"}

# Cada lote em risco vira uma etiqueta de preço de padaria: furo, ação na cor dela,
# preço novo grande (ou quantidade a doar) e a validade como carimbo.

def _quando(dias: int) -> str:
    if dias < 0:
        return "Já vencido"
    return {0: "Vence hoje", 1: "Vence amanhã"}.get(dias, f"Vence em {dias} dias")


def _etiqueta_lote(lote: dict) -> str:
    from html import escape

    acao = NOME_ACAO.get(lote.get("acao"), lote.get("acao", ""))
    cor = CORES_ACAO.get(acao, "#5F6B62")
    texto = COR_TEXTO_ACAO.get(acao, cor)  # tom mais escuro para o texto ter contraste no branco
    u = escape(str(lote.get("unidade", "")))
    produto = escape(str(lote.get("produto", "")))
    sobra = num(lote.get("sobra_projetada", 0))
    if acao == "Promoção":
        novo = float(lote.get("preco_promocional", 0) or 0)
        destaque = f"<div class='cz-preco'><span>{reais(novo)}</span></div>"
        detalhe = f"{escape(str(lote.get('desconto_sugerido', '')))} de desconto em {sobra} {u}"
        if lote.get("receita_recuperada_rs"):
            detalhe += f", recupera {reais(lote['receita_recuperada_rs'])}"
    elif acao == "Doação":
        q = num(lote.get("quantidade_para_doar", lote.get("sobra_projetada", 0)))
        destaque = f"<div class='cz-preco'><span>{q} {u}</span></div>"
        detalhe = "Para banco de alimentos ou ONG parceira"
    else:
        destaque = "<div class='cz-preco'><span>Retirar</span></div>"
        detalhe = f"{sobra} {u} fora da venda"
    return (
        f"<div class='cz-etiqueta' style='--cor:{cor};--cor-texto:{texto}'>"
        f"<div class='cz-acao'>{escape(acao)}</div>"
        f"<div class='cz-produto'>{produto}</div>"
        f"{destaque}"
        f"<div class='cz-detalhe'>{detalhe}</div>"
        f"<div class='cz-rodape'><span class='cz-carimbo'>{_quando(int(lote.get('dias_para_vencer', 0)))}</span>"
        f"<span>sem ação, perde {reais(lote.get('perda_sem_acao_rs', 0))}</span></div>"
        f"</div>"
    )


def _bloco_pedido(p: dict) -> str:
    from html import escape

    itens = p.get("itens") or []
    linhas = "".join(
        f"<li><span>{escape(str(i.get('produto', '')))}</span><b>{num(i.get('quantidade', 0))}</b></li>" for i in itens)
    return (
        "<div class='cz-pedido'>"
        f"<div class='cz-pedido-topo'><b>{escape(str(p.get('fornecedor', '')))}</b>"
        f"<span>Pedido {p.get('pedido_id', '?')}, rascunho</span></div>"
        f"<ul>{linhas}</ul>"
        f"<div class='cz-pedido-total'><span>Total estimado</span><b>{reais(p.get('valor_estimado', 0))}</b></div>"
        "</div>"
    )


def _grade(blocos: list[str], classe: str) -> None:
    html = "".join(blocos).replace("R$ ", "R$&nbsp;")  # "R$" nunca se separa do valor na quebra de linha
    st.markdown(f"<div class='{classe}'>{html}</div>", unsafe_allow_html=True)


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
        k3.metric("Vai para doação, a preço de custo", reais(r.get("custo_dos_itens_para_doacao_rs", 0)))
        lotes = sorted(risco.get("lotes_em_risco", []), key=lambda x: (x.get("dias_para_vencer", 0),
                                                                        -x.get("perda_sem_acao_rs", 0)))
        if lotes:
            st.markdown("#### O que fazer com cada lote")
            _grade([_etiqueta_lote(l) for l in lotes], "cz-etiquetas")
        else:
            st.success("Nenhum lote corre risco de vencer antes de ser vendido.")

    if pedidos:
        criados = [p for p in pedidos.get("pedidos", []) if p.get("ok")]
        if criados:
            st.markdown("#### Pedidos de compra prontos para você aprovar")
            st.caption(f"{len(criados)} fornecedor(es), {reais(pedidos.get('valor_total_rs', 0))} no total. "
                       "Nada é comprado sem a sua aprovação na aba Pedidos.")
            _grade([_bloco_pedido(p) for p in criados], "cz-pedidos")
        else:
            st.info("Nenhuma reposição necessária agora.")


# ------------------------------------------------------------------ boas-vindas e estilo

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Atkinson+Hyperlegible:ital,wght@0,400;0,700;1,400&display=swap');

:root {
    --cz-folha: #2F6B3A;
    --cz-folha-escura: #1F4D29;
    --cz-tinta: #1F2A22;
    --cz-sub: #5F6B62;
    --cz-salvia: #EEF3EC;
    --cz-fio: #D6DED3;
}

/* Uma família só, escolhida para leitura rápida (dono do comércio) e projetor (banca).
   Não aplicar em span: os ícones do Streamlit usam uma fonte própria. */
html, body, .stApp, .stMarkdown, .stMarkdown p, .stMarkdown li, h1, h2, h3, h4, h5,
label, button, input, textarea, [data-testid="stMetricValue"], [data-testid="stMetricLabel"],
[data-testid="stCaptionContainer"], .stTabs button p {
    font-family: "Atkinson Hyperlegible", "Segoe UI", system-ui, sans-serif !important;
}
.stApp { color: var(--cz-tinta); }
h1, h2, h3, h4 { color: var(--cz-tinta); letter-spacing: -0.01em; }
[data-testid="stMetricValue"] { font-variant-numeric: tabular-nums; font-weight: 700; }

/* barra lateral em sálvia */
[data-testid="stSidebar"] { background: var(--cz-salvia); border-right: 1px solid var(--cz-fio); }

/* abas: a ativa em verde folha */
.stTabs [aria-selected="true"] p { color: var(--cz-folha) !important; font-weight: 700; }

/* foco de teclado sempre visível */
button:focus-visible, input:focus-visible, textarea:focus-visible, [role="tab"]:focus-visible {
    outline: 3px solid var(--cz-folha) !important; outline-offset: 2px;
}

/* caixa de mensagem do agente: o lugar onde o dono fala, então é a mais visível da tela */
[data-testid="stChatInput"] {
    border: 2px solid var(--cz-folha) !important;
    border-radius: 14px !important;
    background: #FFFFFF !important;
    padding: 4px 6px !important;
}
[data-testid="stChatInput"] textarea { font-size: 1.1rem !important; min-height: 3.2rem !important; }
[data-testid="stChatInput"] textarea::placeholder { color: var(--cz-sub) !important; opacity: 1 !important; }
[data-testid="stChatInput"]:focus-within { border-color: var(--cz-folha-escura) !important;
    box-shadow: 0 0 0 4px rgba(47, 107, 58, .16) !important; }
.cz-pergunta { font-size: 1.3rem; font-weight: 700; color: var(--cz-tinta); margin: .8rem 0 .1rem; }

/* etiquetas de preço (plano de ação por lote) */
.cz-etiquetas { display: grid; grid-template-columns: repeat(auto-fill, minmax(230px, 1fr)); gap: 14px;
                margin: .4rem 0 1.2rem; }
.cz-etiqueta { position: relative; background: #FFFFFF; border: 2px solid var(--cor);
               border-radius: 6px 18px 18px 6px; padding: 14px 16px 12px 34px; color: var(--cz-tinta); }
.cz-etiqueta::before { /* o furo da etiqueta */
    content: ""; position: absolute; left: 12px; top: 22px; width: 10px; height: 10px; border-radius: 50%;
    border: 2px solid var(--cor); background: var(--cz-salvia); }
.cz-acao { color: var(--cor-texto, var(--cor)); font-weight: 700; font-size: .95rem; }
.cz-produto { font-size: 1.1rem; font-weight: 700; line-height: 1.25; margin: 2px 0 6px; }
.cz-preco { display: flex; align-items: baseline; gap: 8px; flex-wrap: wrap; }
.cz-preco span { font-size: 1.9rem; font-weight: 700; line-height: 1.1; font-variant-numeric: tabular-nums; }
.cz-detalhe { color: var(--cz-sub); font-size: .92rem; line-height: 1.4; margin-top: 4px; }
.cz-rodape { display: flex; justify-content: space-between; align-items: center; gap: 8px; flex-wrap: wrap;
             border-top: 1px dashed var(--cz-fio); margin-top: 10px; padding-top: 8px;
             font-size: .85rem; color: var(--cz-sub); }
.cz-carimbo { border: 1.5px solid var(--cor); color: var(--cor-texto, var(--cor)); border-radius: 4px; padding: 0 6px;
              font-weight: 700; transform: rotate(-2deg); display: inline-block; }

/* pedidos: quietos, como uma comanda */
.cz-pedidos { display: grid; grid-template-columns: repeat(auto-fill, minmax(230px, 1fr)); gap: 14px;
              margin: .4rem 0 1rem; }
.cz-pedido { background: #FFFFFF; border: 1px solid var(--cz-fio); border-radius: 10px; padding: 12px 14px; }
.cz-pedido-topo { display: flex; flex-direction: column; margin-bottom: 6px; }
.cz-pedido-topo span { color: var(--cz-sub); font-size: .85rem; }
.cz-pedido ul { list-style: none; margin: 0; padding: 0; }
.cz-pedido li { display: flex; justify-content: space-between; gap: 8px; padding: 3px 0; font-size: .95rem; }
.cz-pedido li b { font-variant-numeric: tabular-nums; }
.cz-pedido-total { display: flex; justify-content: space-between; border-top: 1px solid var(--cz-fio);
                   margin-top: 6px; padding-top: 6px; }
.cz-pedido-total b { font-size: 1.15rem; font-variant-numeric: tabular-nums; }

/* barra lateral: boas-vindas, marca e o porquê */
.cz-boasvindas { font-size: 1.05rem; line-height: 1.45; color: var(--cz-tinta); }
.cz-marca { display: flex; align-items: center; gap: .5rem; margin: .9rem 0 1rem; }
.cz-marca img { width: 44px; height: 44px; object-fit: contain; }
.cz-marca .cz-icone { font-size: 2.2rem; line-height: 1; }
.cz-marca .cz-nome { font-size: 1.85rem; font-weight: 700; color: var(--cz-folha); letter-spacing: -.02em; }
.cz-dor { border-top: 1px solid var(--cz-fio); padding-top: .8rem; margin-bottom: 1rem; }
.cz-dor h4 { margin: 0 0 .35rem; font-size: 1.02rem; color: var(--cz-tinta); }
.cz-dor p { margin: 0; font-size: .93rem; line-height: 1.5; color: var(--cz-sub); max-width: 34ch; }

@media (prefers-reduced-motion: reduce) { * { transition: none !important; animation: none !important; } }
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
