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
    "consultar_estoque": "Consultando o estoque",
    "cadastrar_produto": "Cadastrando o produto",
    "registrar_entrada": "Registrando a chegada de mercadoria",
    "registrar_saida": "Registrando a saída",
    "listar_produtos_vencendo": "Verificando o que vence em breve",
    "analisar_risco_desperdicio": "Analisando o risco de desperdício, lote a lote",
    "calcular_reposicao": "Calculando quanto comprar",
    "criar_pedidos_sugeridos": "Montando os pedidos de compra",
    "criar_pedido_compra": "Montando um pedido de compra",
    "relatorio_desperdicio": "Levantando as perdas do período",
}

_FERRAMENTA = re.compile(r"^🔧\s*(\w+)\((.*)\)\s*$", re.S)
_PENSANDO = re.compile(r"^🧠\s*passo\s*(\d+)", re.I)


def nome_amigavel(ferramenta: str) -> str:
    return NOMES_FERRAMENTAS.get(ferramenta, f"Usando {ferramenta.replace('_', ' ')}")


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
        return "Decidindo o próximo passo…" if m.group(1) != "1" else "Entendendo o pedido…"
    return texto  # trocas de modelo/provedor: mantém o aviso original (mostra a robustez)


# ------------------------------------------------------------------ etiquetas e pedidos
CLASSE_ACAO = {"Promoção": "promo", "Doação": "doacao", "Descarte": "descarte"}

# Plano por lote: bloco quieto (DESIGN.md reserva a "etiqueta de gôndola" ao topo e ao alerta de excesso).
# A cor aparece só no selo da ação: amarelo = olhe aqui (promoção), verde = ação (doação), vermelho = problema.


def _quando(dias: int) -> str:
    if dias < 0:
        return "Já vencido"
    return {0: "Vence hoje", 1: "Vence amanhã"}.get(dias, f"Vence em {dias} dias")


def _etiqueta_lote(lote: dict) -> str:
    from html import escape

    acao = NOME_ACAO.get(lote.get("acao"), lote.get("acao", ""))
    u = escape(str(lote.get("unidade", "")))
    sobra = num(lote.get("sobra_projetada", 0))
    if acao == "Promoção":
        valor = reais(float(lote.get("preco_promocional", 0) or 0))
        detalhe = f"{escape(str(lote.get('desconto_sugerido', '')))} de desconto nas {sobra} {u} que sobrariam."
        if lote.get("receita_recuperada_rs"):
            detalhe += f" Recupera {reais(lote['receita_recuperada_rs'])}."
    elif acao == "Doação":
        valor = f"{num(lote.get('quantidade_para_doar', lote.get('sobra_projetada', 0)))} {u}"
        detalhe = "Doar para um banco de alimentos ou ONG parceira."
    else:
        valor = "Retirar"
        detalhe = f"Tirar {sobra} {u} da venda."
    return (
        "<div class='cz-lote'>"
        f"<div class='cz-lote-topo'><span class='cz-selo cz-{CLASSE_ACAO.get(acao, 'descarte')}'>{escape(acao)}</span>"
        f"<span>{_quando(int(lote.get('dias_para_vencer', 0)))}</span></div>"
        f"<div class='cz-produto'>{escape(str(lote.get('produto', '')))}</div>"
        f"<div class='cz-valor'>{valor}</div>"
        f"<div class='cz-detalhe'>{detalhe}</div>"
        f"<div class='cz-lixo'>Vai para o lixo: {reais(lote.get('perda_sem_acao_rs', 0))}</div>"
        "</div>"
    )


def _bloco_pedido(p: dict) -> str:
    from html import escape

    itens = p.get("itens") or []
    linhas = "".join(
        f"<li><span>{escape(str(i.get('produto', '')))}</span><b>{num(i.get('quantidade', 0))}</b></li>" for i in itens)
    return (
        "<div class='cz-pedido'>"
        f"<div class='cz-pedido-topo'><b>{escape(str(p.get('fornecedor', '')))}</b>"
        f"<span>Pedido {p.get('pedido_id', '?')}, esperando sua aprovação</span></div>"
        f"<ul>{linhas}</ul>"
        f"<div class='cz-pedido-total'><span>A pagar</span><b>{reais(p.get('valor_estimado', 0))}</b></div>"
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
        k1.markdown("<span class='cz-neg'></span>", unsafe_allow_html=True)  # risco em vermelho
        k1.metric("Vai para o lixo se nada for feito", reais(r.get("perda_total_sem_acao_rs", 0)))
        k2.metric("Recuperado com promoções", reais(r.get("receita_recuperada_com_promocoes_rs", 0)))
        k3.metric("Vai para doação, a preço de custo", reais(r.get("custo_dos_itens_para_doacao_rs", 0)))
        lotes = sorted(risco.get("lotes_em_risco", []), key=lambda x: (x.get("dias_para_vencer", 0),
                                                                        -x.get("perda_sem_acao_rs", 0)))
        if lotes:
            st.markdown("#### O que fazer com cada lote")
            _grade([_etiqueta_lote(l) for l in lotes], "cz-lotes")
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
/* Sistema visual: docs/DESIGN.md (cores, fontes, escala 14/16/20/26/36, cantos 6/8px) */
@import url('https://fonts.googleapis.com/css2?family=Archivo:wdth,wght@62..125,200..800&family=Manrope:wght@300;400;500;600;700&display=swap');

:root {
    --tinta: #1D2B22;
    --tinta-2: #4F5E54;
    --folha: #2F6B3B;
    --etiqueta: #F6D23C;
    --tomate: #C8402B;
    --papel: #EFE6D6;
    --linha: #D9DED6;
    --branco: #FFFFFF;
}

/* Texto: Manrope no app todo (mesmo sistema da landing) (não aplicar em span: ícones do Streamlit têm fonte própria) */
html, body, .stApp, .stMarkdown, .stMarkdown p, .stMarkdown li, h1, h2, h3, h4, h5,
label, button, input, textarea, [data-testid="stMetricLabel"], [data-testid="stCaptionContainer"],
.stTabs button p {
    font-family: "Manrope", system-ui, sans-serif !important;
}
.stApp { color: var(--tinta); background: var(--branco); font-size: 16px; }
.stMarkdown p, .stMarkdown li { max-width: 75ch; }
h3 { font-size: 26px !important; } h4 { font-size: 20px !important; } h5 { font-size: 16px !important; }
h1, h2, h3, h4, h5 { color: var(--tinta) !important; }
[data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] p { color: var(--tinta-2) !important; font-size: 14px; }

/* Valores em R$ e números grandes: Archivo leve (sistema da landing), algarismos tabulares */
[data-testid="stMetricValue"], [data-testid="stMetricValue"] div, .cz-valor, .cz-pedido-total b, .cz-pedido li b {
    font-family: "Archivo", "Arial Narrow", sans-serif !important;
    font-weight: 500 !important; font-stretch: 100%; font-variant-numeric: tabular-nums;
}
[data-testid="stMetricValue"] { font-size: 36px !important; color: var(--tinta); }

/* Vermelho só significa problema: valor negativo ou de risco (marcador .cz-neg na coluna, app.py) */
[data-testid="stColumn"]:has(.cz-neg) [data-testid="stMetricValue"],
[data-testid="column"]:has(.cz-neg) [data-testid="stMetricValue"] { color: var(--tomate) !important; }
.cz-neg { display: none; }

/* Amarelo só significa "olhe aqui": alerta de compra em excesso (st.warning) como etiqueta */
[data-testid="stAlertContainer"]:has([data-testid="stAlertContentWarning"]),
div[data-baseweb="notification"]:has([data-testid="stAlertContentWarning"]) {
    background: var(--etiqueta) !important; color: var(--tinta) !important; border-radius: 6px !important;
}
[data-testid="stAlertContentWarning"], [data-testid="stAlertContentWarning"] p { color: var(--tinta) !important; }

/* Verde é marca e ação: botões primários, aba ativa, foco */
button { border-radius: 8px !important; }
button[kind="primary"], [data-testid="stBaseButton-primary"] {
    background: var(--folha) !important; border-color: var(--folha) !important; color: var(--branco) !important;
}
.stTabs [aria-selected="true"] p { color: var(--folha) !important; font-weight: 700; }
button:focus-visible, input:focus-visible, textarea:focus-visible, [role="tab"]:focus-visible {
    outline: 3px solid var(--folha) !important; outline-offset: 2px;
}

/* Quieto: sem sombra, sem cartão decorativo */
[data-testid="stVerticalBlockBorderWrapper"] { box-shadow: none !important; border-color: var(--linha) !important; }
[data-testid="stSidebar"] { background: linear-gradient(180deg, #EEF5EF 0%, #DCEADF 100%) !important;
                            border-right: 1px solid #C9DCCD; }
/* na barra lateral verde-clara, caixas e botões ficam brancos para destacar */
[data-testid="stSidebar"] [data-testid="stExpander"] details, [data-testid="stSidebar"] [data-testid="stBaseButton-secondary"] {
    background: var(--branco) !important; border-color: #C9DCCD !important; }
[data-testid="stSidebar"] .cz-dor { border-top-color: #C9DCCD; }

/* Caixa de mensagem: onde o dono fala com o agente */
[data-testid="stChatInput"] {
    border: 2px solid var(--folha) !important; border-radius: 8px !important;
    background: var(--branco) !important; padding: 4px 6px !important;
}
[data-testid="stChatInput"] textarea { font-size: 16px !important; min-height: 3.2rem !important; }
[data-testid="stChatInput"] textarea::placeholder { color: var(--tinta-2) !important; opacity: 1 !important; }
.cz-pergunta { font-size: 20px; font-weight: 700; color: var(--tinta); margin: .8rem 0 .1rem; }

/* Plano por lote: blocos quietos, alinhados à esquerda; a cor vive só no selo da ação */
.cz-lotes { display: grid; grid-template-columns: repeat(auto-fill, minmax(230px, 1fr)); gap: 12px;
            margin: .4rem 0 1.2rem; }
.cz-lote { background: var(--branco); border: 1px solid var(--linha); border-radius: 4px; padding: 12px 14px;
           color: var(--tinta); }
.cz-lote-topo { display: flex; justify-content: space-between; align-items: center; gap: 8px;
                font-size: 14px; color: var(--tinta-2); }
.cz-selo { border-radius: 6px; padding: 1px 8px; font-weight: 700; font-size: 14px; }
.cz-promo { background: var(--etiqueta); color: var(--tinta); }
.cz-doacao { background: var(--folha); color: var(--branco); }
.cz-descarte { background: var(--tomate); color: var(--branco); }
.cz-produto { font-size: 16px; font-weight: 700; margin: 8px 0 2px; }
.cz-valor { font-size: 26px; line-height: 1.15; }
.cz-detalhe { color: var(--tinta-2); font-size: 14px; line-height: 1.45; margin-top: 4px; }
.cz-lixo { color: var(--tomate); font-size: 14px; margin-top: 8px; padding-top: 8px; border-top: 1px solid var(--linha); }

/* Pedidos: fundo de recibo (papel) */
.cz-pedidos { display: grid; grid-template-columns: repeat(auto-fill, minmax(230px, 1fr)); gap: 12px;
              margin: .4rem 0 1rem; }
.cz-pedido { background: var(--papel); border-radius: 4px; padding: 12px 14px; color: var(--tinta); }
.cz-pedido-topo { display: flex; flex-direction: column; margin-bottom: 6px; }
.cz-pedido-topo span { color: var(--tinta-2); font-size: 14px; }
.cz-pedido ul { list-style: none; margin: 0; padding: 0; }
.cz-pedido li { display: flex; justify-content: space-between; gap: 8px; padding: 3px 0; }
.cz-pedido li b { font-weight: 700 !important; }
.cz-pedido-total { display: flex; justify-content: space-between; align-items: baseline;
                   border-top: 1px dashed var(--tinta-2); margin-top: 6px; padding-top: 6px; }
.cz-pedido-total b { font-size: 20px; }

/* Barra lateral: boas-vindas, marca e o porquê */
.cz-boasvindas { font-size: 16px; line-height: 1.45; color: var(--tinta); }
.cz-marca { display: flex; align-items: center; gap: .5rem; margin: .9rem 0 1rem; }
.cz-marca img { width: 44px; height: 44px; object-fit: contain; }
.cz-marca .cz-icone { font-size: 2rem; line-height: 1; }
.cz-marca .cz-nome { font-size: 26px; font-weight: 700; color: var(--folha); }
.cz-dor { border-top: 1px solid var(--linha); padding-top: .8rem; margin-bottom: 1rem; }
.cz-dor h4 { margin: 0 0 .35rem; font-size: 16px !important; color: var(--tinta); }
.cz-dor p { margin: 0; font-size: 14px; line-height: 1.5; color: var(--tinta-2); }

/* Movimento: só para mostrar o que mudou ou que está vivo */
button { transition: background-color .15s ease, border-color .15s ease, transform .08s ease; }
button:active { transform: translateY(1px); }
[data-testid="stBaseButton-secondary"]:hover { border-color: var(--folha) !important; color: var(--folha) !important; }
[data-testid="stBaseButton-primary"]:hover { background: #255830 !important; border-color: #255830 !important; }
button [data-testid="stIconMaterial"] { font-size: 1.15em; }
/* Navegação principal como botões grandes (não abas): borda, ícone e texto legíveis; o ativo fica cheio de verde */
.stTabs [role="tablist"], .stTabs [data-baseweb="tab-list"] {
    gap: 10px; flex-wrap: wrap; padding: 4px 2px 8px; height: auto !important; overflow: visible !important;
}
.stTabs [role="tablist"]::before, .stTabs [role="tablist"]::after { display: none !important; }
.stTabs [data-baseweb="tab-highlight"], .stTabs [data-baseweb="tab-border"] { display: none !important; }
.stTabs [role="tab"] {
    min-height: 52px; padding: 0 22px !important; border: 1.5px solid var(--linha) !important; border-radius: 10px !important;
    background: var(--branco) !important; transition: background-color .15s ease, border-color .15s ease, transform .08s ease;
}
.stTabs [role="tab"] p { font-size: 17px !important; font-weight: 600 !important; color: var(--tinta) !important; }
.stTabs [role="tab"] [data-testid="stIconMaterial"], .stTabs [role="tab"] span[role="img"] {
    font-size: 22px !important; color: var(--folha); margin-right: 6px; vertical-align: -5px !important; }
.stTabs [role="tab"], .stTabs [role="tab"]:focus { box-shadow: none !important; outline: none; }
.stTabs [role="tab"]::after, .stTabs [role="tab"]::before,
.stTabs [role="tab"] > div:not([data-testid="stMarkdownContainer"]) { display: none !important; }  /* barrinha de aba */
.stTabs [role="tab"]:focus-visible { outline: 3px solid var(--etiqueta) !important; outline-offset: 2px; }
.stTabs [role="tab"]:hover { border-color: var(--folha) !important; background: #F3F7F3 !important; }
.stTabs [role="tab"]:active { transform: translateY(1px); }
.stTabs [aria-selected="true"] { background: var(--folha) !important; border-color: var(--folha) !important; }
.stTabs [aria-selected="true"] p, .stTabs [aria-selected="true"] [data-testid="stIconMaterial"],
.stTabs [aria-selected="true"] span[role="img"] { color: var(--branco) !important; }
.stTabs [aria-selected="true"]:hover { background: #255830 !important; }
.stTabs [data-baseweb="tab-panel"] { padding-top: 18px; }
.cz-aovivo { display: inline-flex; align-items: center; gap: 8px; font-size: 14px; font-weight: 700; color: var(--folha); }
.cz-aovivo small { font-weight: 400; color: var(--tinta-2); }
.cz-relogio { display: flex; flex-wrap: wrap; align-items: baseline; gap: 6px 14px; font-size: 14px; color: var(--tinta-2); margin-bottom: 6px; }
.cz-relogio .cz-hora { font-weight: 700; color: var(--tinta); font-variant-numeric: tabular-nums; }
.cz-relogio .cz-ontem { margin-left: auto; }
.cz-pulso { width: 9px; height: 9px; border-radius: 50%; background: var(--folha); position: relative; }
.cz-pulso::after { content: ""; position: absolute; inset: 0; border-radius: 50%; background: var(--folha);
                   animation: cz-pulso 1.6s ease-out infinite; }
@keyframes cz-pulso { from { transform: scale(1); opacity: .6; } to { transform: scale(2.6); opacity: 0; } }
[data-testid="stChatMessageAvatarCustom"], [data-testid="stChatMessage"] [data-testid="stIconMaterial"] { color: var(--folha); }

/* ---- Sistema da landing aplicado ao painel (docs/DESIGN.md, "Sistema visual da landing page") ---- */
.stApp { font-weight: 400; }
h1, h2, h3, h4, h5, [data-testid="stHeading"] * { font-family: "Archivo", "Manrope", sans-serif !important; font-weight: 400 !important; letter-spacing: -.01em; }
.cz-pergunta { font-family: "Archivo", sans-serif; font-weight: 400; }
.cz-produto, .cz-pedido li b, .cz-selo { font-weight: 600 !important; }
.cz-marca .cz-nome { font-family: "Archivo", sans-serif; font-weight: 500; }
/* verde em degradê (escuro -> claro), como a hero: item ativo e botões principais */
.stTabs [aria-selected="true"], [data-testid="stBaseButton-primary"], button[kind="primary"] {
    background: linear-gradient(115deg, #1A4424 0%, #2F6B3B 55%, #4C8E58 100%) !important; border-color: #24552E !important;
}
.stTabs [aria-selected="true"]:hover, [data-testid="stBaseButton-primary"]:hover {
    background: linear-gradient(115deg, #143A1E 0%, #24552E 55%, #3F7B4A 100%) !important; }
/* faixa do relógio: uma "mini hero" verde em degradê */
.cz-relogio { background: linear-gradient(115deg, #0F2E17 0%, #1A4424 30%, #2F6B3B 65%, #79B583 100%);
              color: #DCEADF; padding: 10px 16px; border-radius: 10px; margin-bottom: 10px; }
.cz-relogio .cz-hora { color: #FFFFFF; font-weight: 600; }
.cz-relogio small, .cz-relogio .cz-ontem { color: #DCEADF; }
.cz-relogio .cz-aovivo { color: #FFFFFF; }
.cz-relogio .cz-pulso, .cz-relogio .cz-pulso::after { background: #F6D23C; }
/* alertas: amarelo de etiqueta em degradê */
[data-testid="stAlertContainer"]:has([data-testid="stAlertContentWarning"]) {
    background: linear-gradient(180deg, #FFE066 0%, #F6D23C 60%) !important; }
/* notificação (toast) animada: etiqueta amarela que entra, fica ~12 s e sai; tem X para fechar */
[data-testid="stToast"] { background: linear-gradient(180deg, #FFE066 0%, #F6D23C 60%) !important; color: #1D2B22 !important;
    border: 1px solid #C9A616 !important; border-radius: 10px !important; box-shadow: 0 14px 34px rgba(29,43,34,.28) !important;
    min-width: 320px; }
[data-testid="stToast"] p, [data-testid="stToast"] * { color: #1D2B22 !important; }
@media (prefers-reduced-motion: no-preference) {
    [data-testid="stToast"] { animation: cz-entra .45s cubic-bezier(.2,.8,.2,1) both; }
    @keyframes cz-entra { from { transform: translateY(18px) scale(.97); opacity: 0; } to { transform: none; opacity: 1; } }
}
/* aba Alertas: resumo por produto */
.cz-alertas-resumo { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 10px; margin: .5rem 0 1rem; }
.cz-alerta-grupo { background: #FFF8D6; border-left: 5px solid #F6D23C; border-radius: 6px; padding: 10px 12px;
                   display: grid; gap: 2px; font-size: 14px; color: #4F5E54; }
.cz-alerta-grupo b { color: #1D2B22; font-size: 16px; font-weight: 600; }
.cz-alerta-grupo em { font-style: normal; font-family: "Archivo", sans-serif; font-size: 22px; color: #C8402B; }

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

    nome = escape(nome_usuario(padrao=""))
    saudacao = f"Bem-vindo, <b>{nome}</b>!" if nome else "Bem-vindo!"
    st.markdown(
        f"<div class='cz-boasvindas'>{saudacao}<br>"
        "Sou o agente que te ajuda no controle de estoque.</div>"
        f"<div class='cz-marca'>{_logo_html()}<span class='cz-nome'>Ciclo Zero</span></div>"
        f"<div class='cz-dor'><h4>Controle de estoque sem complicação</h4><p>{TEXTO_DOR}</p></div>",
        unsafe_allow_html=True,
    )
