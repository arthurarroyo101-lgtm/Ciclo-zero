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


@st.cache_resource
def get_agente(chave: str):
    from ciclozero.agent import AgenteCicloZero
    return AgenteCicloZero(api_key=chave)


with st.sidebar:
    st.title("♻️ Ciclo Zero")
    st.caption("Agente de IA contra o desperdício de alimentos no pequeno comércio")
    chave = os.getenv("GEMINI_API_KEY") or st.text_input("Chave do Gemini", type="password")
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
c2.metric("R$ em risco (3 dias)", f"R$ {vencendo['valor_total_em_risco']:.2f}")
c3.metric("Perda evitável pelo plano", f"R$ {risco['perda_evitavel_rs']:.2f}")
c4.metric("Perdas últimos 30 dias", f"R$ {perdas['total_perdas_rs']:.2f}", perdas["perdas_sobre_faturamento"] + " do faturamento",
          delta_color="off")

aba_chat, aba_painel, aba_pedidos, aba_log = st.tabs(["💬 Agente", "📦 Estoque", "🧾 Pedidos", "🔍 Rastreio"])

with aba_chat:
    if not chave:
        st.info("Informe a chave do Gemini na barra lateral (ou no arquivo .env) para conversar com o agente.")
    else:
        agente = get_agente(chave)
        st.session_state.setdefault("chat", [])
        if st.button("▶️ Rodar rotina diária (modo autônomo)", type="primary"):
            with st.spinner("O agente está analisando o estoque..."):
                r = agente.rotina_diaria()
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
        if msg := st.chat_input("Ex.: chegaram 30 litros de leite com validade 2026-10-30"):
            st.session_state.chat.append(("user", msg))
            with st.spinner("Pensando..."):
                st.session_state.chat.append(("assistant", agente.perguntar(msg)))
            st.rerun()

with aba_painel:
    st.subheader("Lotes em risco de desperdício")
    if risco["lotes_em_risco"]:
        st.dataframe(pd.DataFrame(risco["lotes_em_risco"]), width="stretch", hide_index=True)
    st.subheader("Estoque atual")
    st.dataframe(pd.DataFrame(tools.consultar_estoque()["itens"]), width="stretch", hide_index=True)

with aba_pedidos:
    pedidos = tools.listar_pedidos()
    if not pedidos:
        st.info("Nenhum pedido ainda. Rode a rotina diária ou peça ao agente para calcular a reposição.")
    for p in pedidos:
        with st.container(border=True):
            st.markdown(f"**Pedido #{p['id']} — {p['fornecedor']}** · R$ {p['valor_estimado']:.2f} · `{p['status']}`")
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
