"""Gráficos do dashboard do Ciclo Zero (João Paulo).

Duas camadas, para facilitar teste e manutenção:
- funções `dados_*`: transformam o retorno das ferramentas (tools.py) em DataFrames prontos;
- funções `grafico_*`: desenham os gráficos com Altair (já vem junto com o Streamlit).

Os números vêm sempre do banco, pelas mesmas ferramentas que o agente usa.
"""
from __future__ import annotations

import pandas as pd

# Cores por ação recomendada: só as do docs/DESIGN.md
CORES_ACAO = {
    "Promoção": "#F6D23C",   # etiqueta: olhe aqui
    "Doação": "#2F6B3B",     # folha: ação
    "Descarte": "#C8402B",   # tomate: problema
    "Sem risco": "#D9DED6",  # linha
}
NOME_ACAO = {"promocao": "Promoção", "doacao": "Doação", "descartar": "Descarte", "ok": "Sem risco"}
COR_VENDAS = "#2F6B3B"
COR_PERDAS = "#C8402B"


def reais(v: float) -> str:
    """1234.5 -> 'R$ 1.234,50'."""
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def num(v: float) -> str:
    """48.3 -> '48,3'; 12.0 -> '12'."""
    return f"{v:g}".replace(".", ",")


def _quando(dias: int) -> str:
    if dias < 0:
        return "vencido"
    if dias == 0:
        return "vence hoje"
    if dias == 1:
        return "vence amanhã"
    return f"vence em {dias} dias"


# ------------------------------------------------------------------ dados

def dados_perdas_por_categoria(historico: list[dict]) -> pd.DataFrame:
    """Perdas em R$ (custo) por categoria, da maior para a menor."""
    df = pd.DataFrame(historico)
    if df.empty or "tipo" not in df:
        return pd.DataFrame(columns=["categoria", "valor", "valor_fmt"])
    df = df[df["tipo"] == "perda"].groupby("categoria", as_index=False)["valor"].sum()
    df = df.sort_values("valor", ascending=False).reset_index(drop=True)
    df["valor"] = df["valor"].round(2)
    df["valor_fmt"] = df["valor"].map(reais)
    return df


def dados_vendas_x_perdas(historico: list[dict]) -> pd.DataFrame:
    """Uma linha por dia x série ('Vendas' ou 'Perdas'), em R$, sem buracos nos dias sem movimento."""
    df = pd.DataFrame(historico)
    if df.empty or "tipo" not in df:
        return pd.DataFrame(columns=["data", "serie", "valor", "valor_fmt"])
    df = df[df["tipo"].isin(["venda", "perda"])].copy()
    df["data"] = pd.to_datetime(df["data"])
    tabela = df.pivot_table(index="data", columns="tipo", values="valor", aggfunc="sum", fill_value=0.0)
    dias = pd.date_range(tabela.index.min(), tabela.index.max(), freq="D")
    tabela = tabela.reindex(dias, fill_value=0.0).rename_axis("data")
    for col in ("venda", "perda"):
        if col not in tabela:
            tabela[col] = 0.0
    tabela = tabela.rename(columns={"venda": "Vendas", "perda": "Perdas"})[["Vendas", "Perdas"]]
    longo = tabela.reset_index().melt(id_vars="data", var_name="serie", value_name="valor")
    longo["valor"] = longo["valor"].round(2)
    longo["valor_fmt"] = longo["valor"].map(reais)
    longo["data_fmt"] = longo["data"].dt.strftime("%d/%m/%Y")
    return longo


def dados_lotes_em_risco(risco: dict) -> pd.DataFrame:
    """Lotes que vencem logo, com a ação recomendada pelo agente e a perda se nada for feito."""
    lotes = risco.get("lotes_em_risco", [])
    if not lotes:
        return pd.DataFrame(columns=["rotulo", "dias", "perda", "acao", "detalhe", "perda_fmt"])
    df = pd.DataFrame(lotes)
    df["acao"] = df["acao"].map(NOME_ACAO).fillna(df["acao"])
    df["dias"] = df["dias_para_vencer"].astype(int)
    df["perda"] = df["perda_sem_acao_rs"].astype(float)
    df["perda_fmt"] = df["perda"].map(reais)
    df["rotulo"] = df["produto"] + " (lote " + df["lote"].astype(str) + ") · " + df["dias"].map(_quando)

    def detalhe(r) -> str:
        sobra = f"sobra {num(r['sobra_projetada'])} {r['unidade']}"
        if r["acao"] == "Promoção":
            return f"{sobra} · {r.get('desconto_sugerido', '')} de desconto → {reais(r.get('preco_promocional', 0))}"
        if r["acao"] == "Doação":
            return f"{sobra} · doar {num(r.get('quantidade_para_doar', r['sobra_projetada']))} {r['unidade']}"
        return sobra

    df["detalhe"] = df.apply(detalhe, axis=1)
    df = df.sort_values(["dias", "perda"], ascending=[True, False]).reset_index(drop=True)
    return df[["rotulo", "produto", "dias", "perda", "perda_fmt", "acao", "detalhe"]]


def dados_top_desperdicio(relatorio: dict, n: int = 5) -> pd.DataFrame:
    """Os n produtos com mais perda em R$ no período."""
    perdas = relatorio.get("perdas", [])
    if not perdas:
        return pd.DataFrame(columns=["produto", "valor", "quantidade", "valor_fmt"])
    df = pd.DataFrame(perdas).rename(columns={"valor_rs": "valor"})
    df = df.sort_values("valor", ascending=False).head(n).reset_index(drop=True)
    df["valor_fmt"] = df["valor"].map(reais)
    total = relatorio.get("total_perdas_rs") or df["valor"].sum()
    df["parcela"] = (df["valor"] / total * 100).round(0).astype(int).astype(str) + "% das perdas" if total else ""
    return df


# ------------------------------------------------------------------ gráficos

FONTE = "Atkinson Hyperlegible"


def _alt():
    import altair as alt  # dependência do Streamlit
    return alt


def _tema(chart):
    """Fonte e cores do docs/DESIGN.md nos eixos e legendas."""
    return chart.configure(font=FONTE).configure_axis(
        labelColor="#4F5E54", titleColor="#4F5E54", gridColor="#D9DED6", domainColor="#D9DED6", labelFontSize=13
    ).configure_legend(labelColor="#1D2B22", titleColor="#4F5E54").configure_view(stroke=None)


def grafico_perdas_por_categoria(df: pd.DataFrame):
    alt = _alt()
    return _tema((
        alt.Chart(df)
        .mark_bar(cornerRadiusEnd=4, color=COR_PERDAS)
        .encode(
            x=alt.X("valor:Q", title="Perdas (R$, custo)"),
            y=alt.Y("categoria:N", sort="-x", title=None),
            tooltip=[alt.Tooltip("categoria:N", title="Categoria"), alt.Tooltip("valor_fmt:N", title="Perdas")],
        )
        .properties(height=max(160, 38 * len(df)))
    ))


def grafico_vendas_x_perdas(df: pd.DataFrame):
    alt = _alt()
    cores = alt.Scale(domain=["Vendas", "Perdas"], range=[COR_VENDAS, COR_PERDAS])
    base = alt.Chart(df).encode(
        x=alt.X("data:T", title=None, axis=alt.Axis(format="%d/%m")),
        color=alt.Color("serie:N", scale=cores, title=None, legend=alt.Legend(orient="top")),
        tooltip=[alt.Tooltip("data_fmt:N", title="Dia"), alt.Tooltip("serie:N", title="Série"),
                 alt.Tooltip("valor_fmt:N", title="Valor")],
    )
    vendas = base.transform_filter(alt.datum.serie == "Vendas").mark_line(point=True).encode(
        y=alt.Y("valor:Q", title="Vendas (R$)", axis=alt.Axis(titleColor=COR_VENDAS)))
    perdas = base.transform_filter(alt.datum.serie == "Perdas").mark_line(point=True, strokeDash=[4, 3]).encode(
        y=alt.Y("valor:Q", title="Perdas (R$)", axis=alt.Axis(titleColor=COR_PERDAS)))
    # eixos independentes: perdas são bem menores que vendas e sumiriam na mesma escala
    return _tema(alt.layer(vendas, perdas).resolve_scale(y="independent").properties(height=300))


def grafico_lotes_em_risco(df: pd.DataFrame):
    alt = _alt()
    cores = alt.Scale(domain=list(CORES_ACAO), range=list(CORES_ACAO.values()))
    ordem = df["rotulo"].tolist()
    return _tema((
        alt.Chart(df)
        .mark_bar(cornerRadiusEnd=2, stroke="#1D2B22", strokeWidth=0.6)  # contorno: amarelo some no branco
        .encode(
            x=alt.X("perda:Q", title="Perda se nada for feito (R$, custo)"),
            y=alt.Y("rotulo:N", sort=ordem, title=None, axis=alt.Axis(labelLimit=320)),
            color=alt.Color("acao:N", scale=cores, title="Ação recomendada", legend=alt.Legend(orient="top")),
            tooltip=[alt.Tooltip("rotulo:N", title="Lote"), alt.Tooltip("acao:N", title="Ação"),
                     alt.Tooltip("detalhe:N", title="Detalhe"), alt.Tooltip("perda_fmt:N", title="Perda sem ação")],
        )
        .properties(height=max(160, 34 * len(df)))
    ))


def grafico_top_desperdicio(df: pd.DataFrame):
    alt = _alt()
    barras = (
        alt.Chart(df)
        .mark_bar(cornerRadiusEnd=4, color=COR_PERDAS)
        .encode(
            x=alt.X("valor:Q", title="Perdas no período (R$, custo)"),
            y=alt.Y("produto:N", sort="-x", title=None),
            tooltip=[alt.Tooltip("produto:N", title="Produto"), alt.Tooltip("valor_fmt:N", title="Perdas"),
                     alt.Tooltip("quantidade:Q", title="Quantidade perdida"),
                     alt.Tooltip("parcela:N", title="Participação")],
        )
    )
    rotulos = barras.mark_text(align="left", dx=4).encode(text="valor_fmt:N", color=alt.value("#888"))
    return _tema((barras + rotulos).properties(height=max(160, 38 * len(df))))