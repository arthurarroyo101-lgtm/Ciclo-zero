"""Automação de saída: mensagem pronta para o fornecedor e plaquinhas de promoção para a gôndola.

Nada aqui é inventado: quantidades vêm do pedido aprovado e preços vêm do cadastro + cálculo de
tools.analisar_risco_desperdicio (o mesmo que o agente usa). Não emite documento fiscal.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from html import escape
from urllib.parse import quote

from . import relogio, tools
from .db import conectar


def _reais(v: float) -> str:
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _qtd(q: float) -> str:
    return f"{q:g}".replace(".", ",")


def _saudacao() -> str:
    h = relogio.hora().hour
    return "Bom dia" if h < 12 else "Boa tarde" if h < 18 else "Boa noite"


def _prazo(produtos: list[str]) -> int:
    if not produtos:
        return 2
    with conectar() as conn:
        marcas = ",".join("?" * len(produtos))
        r = conn.execute(f"SELECT MAX(prazo_entrega_dias) p FROM produtos WHERE nome IN ({marcas})", produtos).fetchone()
    return int(r["p"] or 2)


def mensagem_fornecedor(pedido: dict, loja: str = "") -> str:
    """Texto do pedido pronto para WhatsApp/e-mail."""
    itens = pedido.get("itens", [])
    linhas = [f"- {_qtd(i['quantidade'])} {i.get('unidade', '')} de {i['produto']}".replace("  ", " ") for i in itens]
    entrega = relogio.hoje() + timedelta(days=max(1, _prazo([i["produto"] for i in itens])))
    quem = f", aqui é da {loja}" if loja else ""
    return (f"{_saudacao()}, {pedido['fornecedor']}{quem}! Segue nosso pedido nº {pedido['id']}:\n"
            + "\n".join(linhas)
            + f"\n\nConseguem entregar até {entrega.strftime('%d/%m')}? Por favor, confirmem o valor. Obrigado!")


def link_whatsapp(texto: str) -> str:
    return "https://wa.me/?text=" + quote(texto)


def plaquinhas() -> list[dict]:
    """Uma plaquinha por produto com lote em promoção (menor preço sugerido entre os lotes)."""
    risco = tools.analisar_risco_desperdicio()
    promo = [l for l in risco["lotes_em_risco"] if l.get("acao") == "promocao" and l.get("preco_promocional")]
    if not promo:
        return []
    with conectar() as conn:
        precos = {r["nome"]: r["preco_venda"] for r in conn.execute("SELECT nome, preco_venda FROM produtos")}
    por_produto: dict[str, dict] = {}
    for l in promo:
        atual = por_produto.get(l["produto"])
        if not atual or l["preco_promocional"] < atual["por"]:
            por_produto[l["produto"]] = {
                "produto": l["produto"], "unidade": l["unidade"], "de": precos.get(l["produto"], 0.0),
                "por": l["preco_promocional"], "desconto": l.get("desconto_sugerido", ""),
                "validade": f"{l['validade'][8:10]}/{l['validade'][5:7]}", "sobra": l["sobra_projetada"],
            }
    saida = []
    for p in por_produto.values():
        un = "kg" if p["unidade"] == "kg" else "un"
        p["texto"] = f"{p['produto']}: de {_reais(p['de'])} por {_reais(p['por'])}/{un} (válido até {p['validade']})"
        saida.append(p)
    return sorted(saida, key=lambda p: p["validade"])


def _html_plaquinha(p: dict) -> str:
    un = "kg" if p["unidade"] == "kg" else "un"
    inteiro, cent = f"{p['por']:.2f}".split(".")
    return (f"<div class='cz-plaq'><div class='cz-plaq-oferta'>Oferta</div>"
            f"<div class='cz-plaq-produto'>{escape(p['produto'])}</div>"
            f"<div class='cz-plaq-de'>de {_reais(p['de'])}</div>"
            f"<div class='cz-plaq-por'><span>R$</span><b>{inteiro}</b><small>,{cent}</small><em>/{un}</em></div>"
            f"<div class='cz-plaq-rodape'>Válido até {p['validade']} ou enquanto durar o estoque</div></div>")


CSS_PLAQ = """
.cz-plaqs { display: grid; grid-template-columns: repeat(auto-fill, minmax(210px, 1fr)); gap: 12px; margin: .4rem 0 .8rem; }
.cz-plaq { background: #F6D23C; color: #1D2B22; border-radius: 0 0 8px 8px; border-top: 8px solid #1D2B22;
           padding: 12px 14px 10px; font-family: "Atkinson Hyperlegible", Arial, sans-serif; break-inside: avoid; }
.cz-plaq-oferta { display: inline-block; background: #C8402B; color: #fff; font-weight: 700; font-size: 13px;
                  padding: 1px 8px; border-radius: 4px; }
.cz-plaq-produto { font-weight: 700; font-size: 18px; margin-top: 6px; line-height: 1.2; }
.cz-plaq-de { font-size: 14px; text-decoration: line-through; color: #4F5E54; margin-top: 2px; }
.cz-plaq-por { display: flex; align-items: flex-start; gap: 2px; margin-top: 6px; color: #C8402B;
               font-family: "Archivo", "Arial Narrow", sans-serif !important; font-variant-numeric: tabular-nums; }
.cz-plaq-por b { font-weight: 900 !important; font-size: 52px !important; line-height: .9; letter-spacing: -.02em; }
.cz-plaq-por span { font-weight: 800; font-size: 16px !important; margin-top: 4px; }
.cz-plaq-por small { font-weight: 900; font-size: 24px !important; line-height: 1; margin-top: 2px; }
.cz-plaq-por em { font-style: normal; font-size: 15px !important; color: #1D2B22; align-self: flex-end; margin-left: 2px; }
.cz-plaq-rodape { font-size: 12px; border-top: 1px dashed #9E8A18; margin-top: 8px; padding-top: 6px; }
"""


def pagina_impressao(lista: list[dict]) -> str:
    """HTML com todas as plaquinhas, pronto para abrir e imprimir (Ctrl+P)."""
    return ("<!doctype html><html lang='pt-BR'><head><meta charset='utf-8'><title>Plaquinhas de oferta</title>"
            "<link rel='stylesheet' href='https://fonts.googleapis.com/css2?family=Archivo:wght@900&"
            "family=Atkinson+Hyperlegible:wght@400;700&display=swap'>"
            f"<style>body{{margin:16px;background:#fff}}{CSS_PLAQ}"
            ".cz-plaqs{grid-template-columns:repeat(3,1fr)}@media print{body{margin:0}}</style></head><body>"
            f"<div class='cz-plaqs'>{''.join(_html_plaquinha(p) for p in lista)}</div></body></html>")


# ------------------------------------------------------------------ interface (Streamlit)
def render_mensagem_pedido(pedido: dict) -> None:
    """Dentro do card de um pedido aprovado: texto pronto + abrir no WhatsApp."""
    import streamlit as st
    texto = mensagem_fornecedor(pedido, (st.session_state.get("nome_loja") or "").strip())
    with st.expander("Mensagem para o fornecedor", icon=":material/chat:"):
        st.code(texto, language=None, wrap_lines=True)
        st.link_button("Abrir no WhatsApp", link_whatsapp(texto), icon=":material/send:")


def render_plaquinhas() -> None:
    """Seção de plaquinhas de oferta (aba Estoque)."""
    import streamlit as st
    lista = plaquinhas()
    st.subheader("Plaquinhas de oferta")
    if not lista:
        st.caption("Nenhum lote precisa de promoção agora.")
        return
    st.caption("Preço sugerido pelo Ciclo Zero para vender a sobra antes de vencer. "
               "Baixe, imprima e coloque na gôndola.")
    st.markdown(f"<style>{CSS_PLAQ}</style><div class='cz-plaqs'>"
                + "".join(_html_plaquinha(p) for p in lista) + "</div>", unsafe_allow_html=True)
    st.download_button("Baixar plaquinhas para imprimir", pagina_impressao(lista),
                       file_name=f"plaquinhas_{relogio.hoje().strftime('%d-%m')}.html", mime="text/html",
                       icon=":material/print:")
