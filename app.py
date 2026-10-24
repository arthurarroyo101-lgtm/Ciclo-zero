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


def marcar_risco(col, ativo: bool = True) -> None:
    """Pinta de vermelho (#C8402B) o st.metric desta coluna: valor negativo ou de risco."""
    if ativo:
        col.markdown("<span class='cz-neg'></span>", unsafe_allow_html=True)


def reais(v: float) -> str:
    txt = f"R$ {abs(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return ("−" + txt) if v < 0 else txt


@st.cache_resource
def get_agente(chave: str | None):
    from ciclozero.agent import AgenteCicloZero
    return AgenteCicloZero(api_key=chave or None)


ui_agente.aplicar_estilo()

with st.sidebar:
    ui_agente.cabecalho_lateral()
    tem_env = bool(os.getenv("GEMINI_API_KEY") or os.getenv("GROQ_API_KEY"))
    chave = "" if tem_env else st.text_input("Chave do Gemini", type="password")
    from ciclozero import ao_vivo as _ao_vivo
    _ao_vivo.controles()
    tecnico = st.toggle("🔧 Modo técnico", key="tecnico", value=False,
                        help="Mostra o que é para a equipe e a banca: como o agente decidiu, fórmulas, lançamentos "
                             "detalhados e a aba Rastreio. Desligado = visão limpa do comerciante.")
    with st.expander("👤 Personalizar"):
        st.text_input("Seu nome", key="nome_usuario", placeholder="Ex.: João",
                      help="Aparece na mensagem de boas-vindas. Com login configurado, o nome vem dele.")
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
        st.info("Para conversar com o agente, coloque a chave do Gemini na barra lateral ou no arquivo .env.")
    else:
        agente = get_agente(chave)
        st.session_state.setdefault("chat", [])
        if st.button("▶️ Rodar rotina diária", type="primary",
                     help="O agente confere o que vence, monta o plano de cada lote e prepara os pedidos de compra."):
            with st.status("Conferindo a loja...", expanded=True) as status:
                agente.ao_passo = lambda t: status.write(ui_agente.passo_amigavel(t))
                r = agente.rotina_diaria()
                status.update(label="Plano de hoje pronto", state="complete", expanded=False)
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
                    with st.expander("Resumo escrito pelo agente", expanded=False):
                        st.markdown(conteudo["resposta"])
                else:
                    st.markdown(conteudo["resposta"])
                    if ui_agente.tem_plano(passos) and not conteudo.get("erro_sistema"):
                        ui_agente.render_plano(passos)
                if passos and tecnico:
                    with st.expander(f"Como o agente chegou nisso ({len(passos)} ferramenta(s))"):
                        for i, p in enumerate(passos, 1):
                            st.markdown(f"**{i}. {ui_agente.nome_amigavel(p['ferramenta'])}**  \n"
                                        f"`{p['ferramenta']}({p['argumentos']})`")
                            st.json(p["resultado"], expanded=False)
        st.markdown("<div class='cz-pergunta'>Qual a dúvida de hoje?</div>", unsafe_allow_html=True)
        st.caption("Pode perguntar do seu jeito, por exemplo: “chegaram 30 litros de leite com validade "
                   "30/10/2026”, “o que vence essa semana?” ou “quanto devo pedir de leite?”")
        if msg := st.chat_input("Qual a dúvida de hoje?"):
            st.session_state.chat.append(("user", msg))
            with st.status("Pensando...", expanded=True) as status:
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
        with st.container():
            st.markdown("#### Como está o dia" + (" (ao vivo)" if ao_vivo.simulador().ativo else ""))
            esc = lambda v: reais(v).replace("$", "\\$")
            f1, f2, f3 = st.columns(3)
            f1.metric("Vendas", reais(fin["vendas_rs"]), f"{fin['n_vendas']} vendas", delta_color="off",
                      help=f"Ticket médio {reais(fin['ticket_medio_rs'])}")
            marcar_risco(f2, fin["caixa_rs"] < 0)
            f2.metric("Caixa", reais(fin["caixa_rs"]),
                      help=f"Vendas − compras recebidas ({reais(fin['compras_rs'])}) − despesas "
                           f"({reais(fin['despesas_rs'])}). Pode fechar negativo em dia de muita compra.")
            marcar_risco(f3, fin["lucro_rs"] < 0)
            f3.metric("Lucro", reais(fin["lucro_rs"]), f"margem {fin['margem']:.0%}", delta_color="off",
                      help="Vendas − custo do que foi vendido − perdas − despesas. Compra não é prejuízo: vira estoque.")
            f4, f5, f6 = st.columns(3)
            marcar_risco(f4, fin["excesso_rs"] > 0)
            f4.metric("Comprado a mais", reais(fin["excesso_rs"]),
                      f"{fin['n_excessos']} compra(s) acima do que você vende" if fin["n_excessos"] else None,
                      delta_color="off",
                      help="O que entrou além do que a loja consegue vender antes de vencer. Se nada for feito, vira lixo.")
            f5.metric("A pagar a fornecedores", reais(fin["a_pagar_rs"]),
                      f"{fin['a_pagar_n']} pedido(s) aprovado(s)" if fin["a_pagar_n"] else None, delta_color="off",
                      help="Pedidos aprovados que ainda não chegaram. Quando chegam, entram no estoque e saem do caixa.")
            f6.metric("Pedidos para aprovar", fin["pedidos_pendentes"],
                      esc(fin["pedidos_pendentes_rs"]) if fin["pedidos_pendentes"] else None, delta_color="off")
            ao_vivo.render_alertas_excesso(maximo=2)
            if tecnico:
                st.caption("Caixa: vendas menos compras, produção e despesas. Lucro: vendas menos o custo do que foi "
                           "vendido, as perdas e as despesas. Comprado a mais: custo do que entrou além do que a loja "
                           "vende antes de vencer.")
                mov = ao_vivo.tabela_movimento()
                if not mov.empty:
                    st.markdown("##### Últimos lançamentos")
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
        with col_a:
            st.markdown("#### O que precisa de ação agora")
            if df_lotes.empty:
                st.success("Nada vai vencer na prateleira nos próximos 5 dias.")
            else:
                st.caption(f"{len(df_lotes)} lote(s) vencem em até 5 dias e não vai dar tempo de vender tudo. "
                           f"Se nada for feito, você perde **{graficos.reais(df_lotes['perda'].sum())}**.")
                st.altair_chart(graficos.grafico_lotes_em_risco(df_lotes), width="stretch")
        with col_b:
            st.markdown("#### Os 5 produtos que você mais joga fora")
            if df_top.empty:
                st.info("Nenhuma perda registrada nos últimos 30 dias.")
            else:
                lider = df_top.iloc[0]
                st.caption(f"**{lider['produto']}** sozinho responde por {lider['parcela']} "
                           f"({lider['valor_fmt']} em 30 dias).")
                st.altair_chart(graficos.grafico_top_desperdicio(df_top), width="stretch")

        with st.container():
            st.markdown("#### Vendas e perdas, dia a dia (últimos 30 dias)")
            if df_dia.empty:
                st.info("Sem movimentações no período.")
            else:
                st.caption(f"Você vendeu {graficos.reais(perdas['faturamento_rs'])} e perdeu "
                           f"{graficos.reais(perdas['total_perdas_rs'])}, o equivalente a "
                           f"{perdas['perdas_sobre_faturamento']} do que vendeu."
                           + (" Cada linha tem sua própria escala, para as perdas não sumirem no gráfico." if tecnico else ""))
                st.altair_chart(graficos.grafico_vendas_x_perdas(df_dia), width="stretch")

        with st.container():
            st.markdown("#### Onde está a perda, por categoria")
            if df_cat.empty:
                st.info("Nenhuma perda registrada nos últimos 30 dias.")
            else:
                st.caption(f"**{df_cat.iloc[0]['categoria']}** é onde você mais perde "
                           f"({df_cat.iloc[0]['valor_fmt']} em 30 dias).")
                st.altair_chart(graficos.grafico_perdas_por_categoria(df_cat), width="stretch")
    _aba_dash()

with aba_painel:
    @st.fragment(run_every=ao_vivo.intervalo())  # ao vivo: atualiza sozinho
    def _aba_estoque():
        risco = tools.analisar_risco_desperdicio()
        perdas = tools.relatorio_desperdicio(30)
        st.subheader("Perto de vencer, sem tempo de vender tudo")
        if risco["lotes_em_risco"]:
            st.dataframe(tabela(risco["lotes_em_risco"]), width="stretch", hide_index=True)
        st.subheader("Tudo o que tem na loja")
        st.dataframe(tabela(tools.consultar_estoque()["itens"]), width="stretch", hide_index=True)
    _aba_estoque()

with aba_pedidos:
    @st.fragment(run_every=ao_vivo.intervalo())  # ao vivo: atualiza sozinho
    def _aba_pedidos():
        risco = tools.analisar_risco_desperdicio()
        perdas = tools.relatorio_desperdicio(30)
        pedidos = tools.listar_pedidos()
        if not pedidos:
            st.info("Nenhum pedido por enquanto. Rode a rotina diária ou pergunte ao agente o que precisa comprar.")
        rotulo = {"rascunho": "Esperando sua aprovação", "aprovado": "Aprovado, esperando a entrega",
                  "recebido": "Recebido", "recusado": "Recusado"}
        for p in pedidos:
            estado = "recebido" if p.get("recebido_em") else p["status"]
            with st.container(border=True):
                st.markdown(f"**{p['fornecedor']}**, pedido {p['id']}: **{reais(p['valor_estimado'])}**  \n"
                            f"{rotulo.get(estado, estado)}")
                st.caption("; ".join(f"{i['produto']}, {i['quantidade']:g} {i.get('unidade', '')}".rstrip()
                                     for i in p["itens"]))
                if tecnico and p.get("justificativa"):
                    st.caption(p["justificativa"])
                if estado == "rascunho":
                    a, b = st.columns(2)
                    if a.button("✅ Aprovar pedido", key=f"ok{p['id']}", type="primary"):
                        tools.decidir_pedido(p["id"], True)
                        st.rerun()
                    if b.button("Recusar", key=f"no{p['id']}"):
                        tools.decidir_pedido(p["id"], False)
                        st.rerun()
                elif estado == "aprovado":
                    if st.button("📦 Marcar como recebido", key=f"rec{p['id']}",
                                 help="A mercadoria chegou. Ela entra no estoque e o valor sai do caixa."):
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
        st.caption(f"{m['chamadas_ferramenta']} chamadas de ferramenta, {m['erros_de_ferramenta']} com erro (o agente "
                   f"se corrigiu ou perguntou) e {m['perguntas_com_erro']} pergunta(s) sem resposta.")
        if m["por_modelo"]:
            st.dataframe(pd.DataFrame(m["por_modelo"]), width="stretch", hide_index=True)
        st.subheader("Registro passo a passo")
        st.caption("Cada passo do agente fica registrado: o que recebeu, quais ferramentas chamou e o que respondeu.")
        with conectar() as conn:
            log = pd.read_sql("SELECT sessao, passo, tipo, conteudo, criado_em FROM log_agente ORDER BY id DESC LIMIT 200", conn)
        st.dataframe(log, width="stretch", hide_index=True)
    if tecnico:  # Rastreio é só para a equipe/banca
        _aba_rastreio()
