"""Interface Streamlit do Ciclo Zero (versão base — João Paulo evolui o visual).

Rodar: streamlit run app.py
"""
import os

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from ciclozero import tools, ui_agente
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
    txt = f"R$ {abs(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return ("−" + txt) if v < 0 else txt


@st.cache_resource
def get_agente(chave: str | None):
    from ciclozero.agent import AgenteCicloZero
    return AgenteCicloZero(api_key=chave or None)


with st.sidebar:
    st.title("♻️ Ciclo Zero")
    st.caption("Agente de IA contra o desperdício de alimentos no pequeno comércio")
    tem_env = bool(os.getenv("GEMINI_API_KEY") or os.getenv("GROQ_API_KEY"))
    chave = "" if tem_env else st.text_input("Chave do Gemini", type="password")
    from ciclozero import ao_vivo as _ao_vivo
    _ao_vivo.controles()
    tecnico = st.toggle("🔧 Modo técnico", key="tecnico", value=False,
                        help="Mostra o que é para a equipe e a banca: como o agente decidiu, fórmulas, lançamentos "
                             "detalhados e a aba Rastreio. Desligado = visão limpa do comerciante.")
    if st.button("🔄 Recriar dados de exemplo"):
        from ciclozero.seed import popular
        _ao_vivo.simulador().parar()  # não escrever no banco enquanto ele é recriado
        popular()
        st.cache_resource.clear()
        st.session_state.pop("chat", None)
        st.rerun()

# indicadores do topo: atualizam sozinhos quando a "Loja ao vivo" está ligada (ciclozero/ao_vivo.py)
from ciclozero import ao_vivo
ao_vivo.painel()
risco = tools.analisar_risco_desperdicio()
vencendo = tools.listar_produtos_vencendo(3)
perdas = tools.relatorio_desperdicio(30)

_nomes_abas = ["💬 Agente", "📷 Nota fiscal", "📊 Dashboard", "📦 Estoque", "🧾 Pedidos"]
_abas = st.tabs(_nomes_abas + (["🔍 Rastreio"] if tecnico else []))
aba_chat, aba_nota, aba_dash, aba_painel, aba_pedidos = _abas[:5]
aba_log = _abas[5] if tecnico else st.empty()  # Rastreio só no modo técnico

with aba_nota:  # módulo separado (Matheus) para não conflitar com o resto da interface
    from ciclozero import ui_nota
    ui_nota.render(lambda: get_agente(chave) if (tem_env or chave) else None)

with aba_chat:
    if not (tem_env or chave):
        st.info("Informe a chave do Gemini na barra lateral (ou no arquivo .env) para conversar com o agente.")
    else:
        agente = get_agente(chave)
        st.session_state.setdefault("chat", [])
        if st.button("▶️ Rodar rotina diária (modo autônomo)", type="primary"):
            with st.status("O agente está trabalhando...", expanded=True) as status:
                agente.ao_passo = lambda t: status.write(ui_agente.passo_amigavel(t))
                r = agente.rotina_diaria()
                status.update(label="Rotina concluída", state="complete", expanded=False)
            r["rotina"] = True
            st.session_state.chat.append(("user", "▶️ Rotina diária"))
            st.session_state.chat.append(("assistant", r))
        for papel, conteudo in st.session_state.chat:
            with st.chat_message(papel, avatar="♻️" if papel == "assistant" else None):
                if papel == "user":
                    st.markdown(conteudo)
                    continue
                passos = conteudo.get("passos") or []
                if conteudo.get("rotina") and ui_agente.tem_plano(passos) and not conteudo.get("erro_sistema"):
                    # rotina: cartões primeiro (números das ferramentas), texto do agente logo abaixo
                    ui_agente.render_plano(passos)
                    with st.expander("💬 Resumo escrito pelo agente", expanded=False):
                        st.markdown(conteudo["resposta"])
                else:
                    st.markdown(conteudo["resposta"])
                    if ui_agente.tem_plano(passos) and not conteudo.get("erro_sistema"):
                        ui_agente.render_plano(passos)
                if passos and tecnico:
                    with st.expander(f"🔧 Como o agente chegou nisso ({len(passos)} ferramenta(s))"):
                        for i, p in enumerate(passos, 1):
                            st.markdown(f"**{i}. {ui_agente.nome_amigavel(p['ferramenta'])}** · "
                                        f"`{p['ferramenta']}({p['argumentos']})`")
                            st.json(p["resultado"], expanded=False)
        if msg := st.chat_input("Ex.: chegaram 30 litros de leite com validade 30/10/2026"):
            st.session_state.chat.append(("user", msg))
            with st.status("O agente está trabalhando...", expanded=True) as status:
                agente.ao_passo = lambda t: status.write(ui_agente.passo_amigavel(t))
                st.session_state.chat.append(("assistant", agente.perguntar(msg)))
                status.update(label="Pronto", state="complete", expanded=False)
            st.rerun()

with aba_dash:
    @st.fragment(run_every=ao_vivo.intervalo())  # ao vivo: atualiza sozinho
    def _aba_dash():
        risco = tools.analisar_risco_desperdicio()
        perdas = tools.relatorio_desperdicio(30)
        fin = ao_vivo.financeiro_do_dia()
        with st.container(border=True):
            st.markdown("#### 💰 Hoje" + ("  ·  🟢 ao vivo" if ao_vivo.simulador().ativo else ""))
            esc = lambda v: reais(v).replace("$", "\\$")
            f1, f2, f3 = st.columns(3)
            f1.metric("Vendas", reais(fin["vendas_rs"]), f"{fin['n_vendas']} vendas", delta_color="off",
                      help=f"Ticket médio {reais(fin['ticket_medio_rs'])}")
            f2.metric("Caixa", reais(fin["caixa_rs"]),
                      help=f"Vendas − compras recebidas ({reais(fin['compras_rs'])}) − despesas "
                           f"({reais(fin['despesas_rs'])}). Pode fechar negativo em dia de muita compra.")
            f3.metric("Lucro", reais(fin["lucro_rs"]), f"margem {fin['margem']:.0%}", delta_color="off",
                      help="Vendas − custo do que foi vendido − perdas − despesas. Compra não é prejuízo: vira estoque.")
            f4, f5, f6 = st.columns(3)
            f4.metric("🚨 Comprado em excesso", reais(fin["excesso_rs"]),
                      f"{fin['n_excessos']} compra(s) acima do que vende" if fin["n_excessos"] else None,
                      delta_color="off",
                      help="Custo do que entrou além do que a loja consegue vender antes de vencer: vai virar lixo.")
            f5.metric("A pagar a fornecedores", reais(fin["a_pagar_rs"]),
                      f"{fin['a_pagar_n']} pedido(s) aprovado(s)" if fin["a_pagar_n"] else None, delta_color="off",
                      help="Pedidos aprovados que ainda não chegaram. Quando chegam, entram no estoque e saem do caixa.")
            f6.metric("Pedidos p/ aprovar", fin["pedidos_pendentes"],
                      esc(fin["pedidos_pendentes_rs"]) if fin["pedidos_pendentes"] else None, delta_color="off")
            ao_vivo.render_alertas_excesso(maximo=2)
            if tecnico:
                st.caption("Caixa = vendas − (compras/produção + despesas) · Lucro = vendas − custo do vendido − perdas − "
                           "despesas · Excesso = custo do que entrou além do que a loja vende antes de vencer.")
                mov = ao_vivo.tabela_movimento()
                if not mov.empty:
                    st.markdown("##### Últimos lançamentos (modo técnico)")
                    st.dataframe(mov, width="stretch", hide_index=True, height=250)
        from ciclozero import graficos

        hist = tools.historico_diario(30)
        df_lotes = graficos.dados_lotes_em_risco(risco)
        df_top = graficos.dados_top_desperdicio(perdas, 5)
        df_cat = graficos.dados_perdas_por_categoria(hist)
        df_dia = graficos.dados_vendas_x_perdas(hist)

        if tecnico:
            st.caption("Todos os números saem do banco, pelas mesmas ferramentas que o agente usa. "
                       "Perdas e risco são medidos pelo custo do produto.")

        col_a, col_b = st.columns(2)
        with col_a, st.container(border=True):
            st.markdown("#### ⏳ O que precisa de ação agora")
            if df_lotes.empty:
                st.success("Nenhum lote vence nos próximos 5 dias com sobra prevista.")
            else:
                st.caption(f"{len(df_lotes)} lote(s) vencem em até 5 dias e não devem ser vendidos a tempo. "
                           f"Sem ação, a perda seria de **{graficos.reais(df_lotes['perda'].sum())}**.")
                st.altair_chart(graficos.grafico_lotes_em_risco(df_lotes), width="stretch")
        with col_b, st.container(border=True):
            st.markdown("#### 🏆 Top 5 produtos que mais geram desperdício")
            if df_top.empty:
                st.info("Sem perdas registradas nos últimos 30 dias.")
            else:
                lider = df_top.iloc[0]
                st.caption(f"**{lider['produto']}** sozinho responde por {lider['parcela']} "
                           f"({lider['valor_fmt']} em 30 dias).")
                st.altair_chart(graficos.grafico_top_desperdicio(df_top), width="stretch")

        with st.container(border=True):
            st.markdown("#### 📈 Vendas × perdas por dia (últimos 30 dias)")
            if df_dia.empty:
                st.info("Sem movimentações no período.")
            else:
                st.caption(f"Faturamento de {graficos.reais(perdas['faturamento_rs'])} e perdas de "
                           f"{graficos.reais(perdas['total_perdas_rs'])} ({perdas['perdas_sobre_faturamento']} do "
                           "faturamento). Cada eixo tem sua escala para as perdas não sumirem no gráfico.")
                st.altair_chart(graficos.grafico_vendas_x_perdas(df_dia), width="stretch")

        with st.container(border=True):
            st.markdown("#### 🗂️ Perdas por categoria")
            if df_cat.empty:
                st.info("Sem perdas registradas nos últimos 30 dias.")
            else:
                st.caption(f"**{df_cat.iloc[0]['categoria']}** é a categoria que mais perde "
                           f"({df_cat.iloc[0]['valor_fmt']} em 30 dias).")
                st.altair_chart(graficos.grafico_perdas_por_categoria(df_cat), width="stretch")
    _aba_dash()

with aba_painel:
    @st.fragment(run_every=ao_vivo.intervalo())  # ao vivo: atualiza sozinho
    def _aba_estoque():
        risco = tools.analisar_risco_desperdicio()
        perdas = tools.relatorio_desperdicio(30)
        st.subheader("Lotes em risco de desperdício")
        if risco["lotes_em_risco"]:
            st.dataframe(tabela(risco["lotes_em_risco"]), width="stretch", hide_index=True)
        st.subheader("Estoque atual")
        st.dataframe(tabela(tools.consultar_estoque()["itens"]), width="stretch", hide_index=True)
    _aba_estoque()

with aba_pedidos:
    @st.fragment(run_every=ao_vivo.intervalo())  # ao vivo: atualiza sozinho
    def _aba_pedidos():
        risco = tools.analisar_risco_desperdicio()
        perdas = tools.relatorio_desperdicio(30)
        pedidos = tools.listar_pedidos()
        if not pedidos:
            st.info("Nenhum pedido ainda. Rode a rotina diária ou peça ao agente para calcular a reposição.")
        rotulo = {"rascunho": "📝 aguardando sua aprovação", "aprovado": "✅ aprovado · aguardando entrega",
                  "recebido": "📦 recebido", "recusado": "❌ recusado"}
        for p in pedidos:
            estado = "recebido" if p.get("recebido_em") else p["status"]
            with st.container(border=True):
                st.markdown(f"**#{p['id']} · {p['fornecedor']}** · {reais(p['valor_estimado'])} · {rotulo.get(estado, estado)}")
                st.caption(" · ".join(f"{i['produto']}: {i['quantidade']:g} {i.get('unidade', '')}" for i in p["itens"]))
                if tecnico and p.get("justificativa"):
                    st.caption(p["justificativa"])
                if estado == "rascunho":
                    a, b = st.columns(2)
                    if a.button("✅ Aprovar", key=f"ok{p['id']}"):
                        tools.decidir_pedido(p["id"], True)
                        st.rerun()
                    if b.button("❌ Recusar", key=f"no{p['id']}"):
                        tools.decidir_pedido(p["id"], False)
                        st.rerun()
                elif estado == "aprovado":
                    if st.button("📦 Marcar como recebido", key=f"rec{p['id']}",
                                 help="A mercadoria chegou: entra no estoque e o valor sai do caixa."):
                        tools.receber_pedido(p["id"])
                        st.rerun()
    _aba_pedidos()

with aba_log:
    @st.fragment(run_every=ao_vivo.intervalo())  # ao vivo: atualiza sozinho
    def _aba_rastreio():
        risco = tools.analisar_risco_desperdicio()
        perdas = tools.relatorio_desperdicio(30)
        from ciclozero.metricas import metricas_agente
        m = metricas_agente()
        st.subheader("Saúde do agente")
        st.caption("Sinais de degradação: latência p95 subindo, mais erros do modelo, mais trocas para o modelo reserva "
                   "ou mais erros de ferramenta (modelo chamando com argumentos ruins).")
        k1, k2, k3, k4, k5 = st.columns(5)
        k1.metric("Perguntas", m["perguntas"])
        k2.metric("Tempo médio", f"{m['latencia_media_pergunta_s']:.1f} s".replace(".", ","))
        k3.metric("Tempo p95", f"{m['latencia_p95_pergunta_s']:.1f} s".replace(".", ","))
        k4.metric("Erro do modelo", m["taxa_erro_llm"])
        k5.metric("Usou reserva", m["trocas_para_reserva"])
        st.caption(f"{m['chamadas_ferramenta']} chamadas de ferramenta · {m['erros_de_ferramenta']} devolveram erro "
                   f"(e o agente se corrigiu ou perguntou) · {m['perguntas_com_erro']} perguntas sem resposta")
        if m["por_modelo"]:
            st.dataframe(pd.DataFrame(m["por_modelo"]), width="stretch", hide_index=True)
        st.subheader("Registro passo a passo")
        st.caption("Cada passo do agente fica registrado: o que recebeu, quais ferramentas chamou e o que respondeu.")
        with conectar() as conn:
            log = pd.read_sql("SELECT sessao, passo, tipo, conteudo, criado_em FROM log_agente ORDER BY id DESC LIMIT 200", conn)
        st.dataframe(log, width="stretch", hide_index=True)
    if tecnico:  # Rastreio é só para a equipe/banca
        _aba_rastreio()
