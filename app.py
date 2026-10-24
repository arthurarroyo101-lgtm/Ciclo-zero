"""Interface Streamlit do Ciclo Zero (versão base — João Paulo evolui o visual).

Rodar: streamlit run app.py
"""
import os

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from ciclozero import tools
from ciclozero.db import DB_PATH, conectar, criar_tabelas

load_dotenv()
st.set_page_config(page_title="Ciclo Zero", page_icon="♻️", layout="wide")

if not DB_PATH.exists():
    from ciclozero.seed import popular
    popular()
criar_tabelas()


COLUNAS_DATA = ("validade", "validade_mais_proxima", "data", "data_entrada", "criado_em")


def tabela(linhas):
    """DataFrame com datas no padrão brasileiro."""
    df = pd.DataFrame(linhas)
    for c in COLUNAS_DATA:
        if c in df.columns:
            df[c] = df[c].map(tools.data_br)
    return df


def reais(v: float) -> str:
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


@st.cache_resource
def get_agente(chave: str | None):
    from ciclozero.agent import AgenteCicloZero
    return AgenteCicloZero(api_key=chave or None)


with st.sidebar:
    st.title("♻️ Ciclo Zero")
    st.caption("Agente de IA contra o desperdício de alimentos no pequeno comércio")
    tem_env = bool(os.getenv("GEMINI_API_KEY") or os.getenv("GROQ_API_KEY"))
    chave = "" if tem_env else st.text_input("Chave do Gemini", type="password")
    if st.button("🔄 Recriar dados de exemplo"):
        from ciclozero.seed import popular
        popular()
        st.cache_resource.clear()
        st.session_state.pop("chat", None)
        st.rerun()

risco = tools.analisar_risco_desperdicio()
vencendo = tools.listar_produtos_vencendo(3)
perdas = tools.relatorio_desperdicio(30)
c1, c2, c3, c4 = st.columns(4)
c1.metric("Lotes em risco (5 dias)", len(risco["lotes_em_risco"]))
c2.metric("R$ em risco (3 dias)", reais(vencendo["valor_total_em_risco"]))
c3.metric("Perda projetada sem ação", reais(risco["resumo"]["perda_total_sem_acao_rs"]))
c4.metric("Perdas últimos 30 dias", reais(perdas["total_perdas_rs"]), perdas["perdas_sobre_faturamento"] + " do faturamento",
          delta_color="off")

aba_chat, aba_painel, aba_pedidos, aba_log = st.tabs(["💬 Agente", "📦 Estoque", "🧾 Pedidos", "🔍 Rastreio"])

with aba_chat:
    if not (tem_env or chave):
        st.info("Informe a chave do Gemini na barra lateral (ou no arquivo .env) para conversar com o agente.")
    else:
        agente = get_agente(chave)
        st.session_state.setdefault("chat", [])
        if st.button("▶️ Rodar rotina diária (modo autônomo)", type="primary"):
            with st.status("O agente está trabalhando...", expanded=True) as status:
                agente.ao_passo = status.write
                r = agente.rotina_diaria()
                status.update(label="Rotina concluída", state="complete", expanded=False)
            st.session_state.chat.append(("user", "▶️ Rotina diária"))
            st.session_state.chat.append(("assistant", r))
        for papel, conteudo in st.session_state.chat:
            with st.chat_message(papel):
                if papel == "user":
                    st.markdown(conteudo)
                else:
                    st.markdown(conteudo["resposta"])
                    if conteudo["passos"]:
                        with st.expander(f"🔧 {len(conteudo['passos'])} ferramenta(s) usada(s)"):
                            for p in conteudo["passos"]:
                                st.markdown(f"**{p['ferramenta']}** `{p['argumentos']}`")
                                st.json(p["resultado"], expanded=False)
        if msg := st.chat_input("Ex.: chegaram 30 litros de leite com validade 30/10/2026"):
            st.session_state.chat.append(("user", msg))
            with st.status("O agente está trabalhando...", expanded=True) as status:
                agente.ao_passo = status.write
                st.session_state.chat.append(("assistant", agente.perguntar(msg)))
                status.update(label="Pronto", state="complete", expanded=False)
            st.rerun()

with aba_painel:
    st.subheader("Lotes em risco de desperdício")
    if risco["lotes_em_risco"]:
        st.dataframe(tabela(risco["lotes_em_risco"]), width="stretch", hide_index=True)
    st.subheader("Estoque atual")
    st.dataframe(tabela(tools.consultar_estoque()["itens"]), width="stretch", hide_index=True)

with aba_pedidos:
    pedidos = tools.listar_pedidos()
    if not pedidos:
        st.info("Nenhum pedido ainda. Rode a rotina diária ou peça ao agente para calcular a reposição.")
    for p in pedidos:
        with st.container(border=True):
            st.markdown(f"**Pedido #{p['id']} — {p['fornecedor']}** · {reais(p['valor_estimado'])} · `{p['status']}`")
            st.caption(p["justificativa"] or "")
            st.dataframe(pd.DataFrame(p["itens"]), hide_index=True)
            if p["status"] == "rascunho":
                a, b = st.columns(2)
                if a.button("✅ Aprovar", key=f"ok{p['id']}"):
                    tools.decidir_pedido(p["id"], True)
                    st.rerun()
                if b.button("❌ Recusar", key=f"no{p['id']}"):
                    tools.decidir_pedido(p["id"], False)
                    st.rerun()

with aba_log:
    st.caption("Cada passo do agente fica registrado: o que recebeu, quais ferramentas chamou e o que respondeu.")
    with conectar() as conn:
        log = pd.read_sql("SELECT sessao, passo, tipo, conteudo, criado_em FROM log_agente ORDER BY id DESC LIMIT 200", conn)
    st.dataframe(log, width="stretch", hide_index=True)
