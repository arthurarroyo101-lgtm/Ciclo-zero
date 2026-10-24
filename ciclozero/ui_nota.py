"""Aba "📷 Nota fiscal" da interface: foto da nota -> conferência -> estoque -> alerta do agente.

Fica separada do app.py para não conflitar com o trabalho de interface (João).
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from . import nota_fiscal as nf
from .db import conectar

EXEMPLO = Path(__file__).resolve().parent.parent / "docs" / "exemplos" / "nota_exemplo_ceasa.png"


def _reais(v) -> str:
    return "—" if v is None else f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def render(obter_agente) -> None:
    """obter_agente: função sem argumentos que devolve o agente (ou None se não houver chave)."""
    st.subheader("📷 Entrada de mercadoria pela nota fiscal")
    st.caption("Tire uma foto da nota do fornecedor. O agente lê os itens, associa ao seu cadastro e sugere a "
               "validade. Você confere e confirma: **nada entra no estoque sem a sua confirmação.**")

    origem = st.radio("Origem da nota", ["Enviar foto", "Câmera", "Nota de exemplo (demo)"], horizontal=True,
                      label_visibility="collapsed")
    imagem, mime = None, "image/png"
    if origem == "Enviar foto":
        arq = st.file_uploader("Foto ou print da nota", type=["png", "jpg", "jpeg", "webp"])
        if arq:
            imagem, mime = arq.getvalue(), arq.type or "image/jpeg"
    elif origem == "Câmera":
        foto = st.camera_input("Fotografe a nota")
        if foto:
            imagem, mime = foto.getvalue(), "image/jpeg"
    elif EXEMPLO.exists():
        imagem = EXEMPLO.read_bytes()

    if imagem:
        c1, c2 = st.columns([1, 2])
        c1.image(imagem, caption="Nota enviada", width="stretch")
        with c2:
            if st.button("🔎 Ler nota com IA", type="primary"):
                with st.status("Lendo a nota...", expanded=True) as status:
                    status.write("👁️ modelo de visão extraindo fornecedor, itens e valores")
                    try:
                        dados = nf.ler_nota(imagem, mime)
                    except nf.LeituraFalhou as e:
                        status.update(label="Não consegui ler a nota", state="error")
                        st.error(str(e))
                        return
                    status.write(f"✔️ {len(dados['itens'])} itens lidos em {dados['segundos']} s ({dados['modelo']})")
                    status.write("🔗 associando itens ao cadastro e sugerindo validade")
                    st.session_state.nota_dados = dados
                    st.session_state.nota_linhas = nf.conciliar(dados)
                    st.session_state.pop("nota_resultado", None)
                    status.update(label="Nota lida — confira abaixo", state="complete", expanded=False)

    dados = st.session_state.get("nota_dados")
    if not dados:
        return

    st.divider()
    v = dados["verificacao"]
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Fornecedor", dados.get("fornecedor") or "—")
    m2.metric("Nota nº", dados.get("numero") or "—")
    m3.metric("Total da nota", _reais(v["total_nota"]))
    m4.metric("Soma dos itens", _reais(v["soma_itens"]))
    if v["confiavel"]:
        st.success("✅ Leitura verificada: a soma dos itens confere com o total da nota.")
    else:
        st.warning("⚠️ Confira com atenção antes de lançar: " + "; ".join(v["problemas"] or ["leitura incerta"]))

    with conectar() as conn:
        nomes = [r["nome"] for r in conn.execute("SELECT nome FROM produtos ORDER BY nome")]
    df = pd.DataFrame(st.session_state.nota_linhas)
    editado = st.data_editor(
        df, hide_index=True, width="stretch", key="editor_nota",
        column_config={
            "lancar": st.column_config.CheckboxColumn("Lançar?"),
            "descricao_nota": st.column_config.TextColumn("Na nota", disabled=True),
            "produto": st.column_config.SelectboxColumn("Produto no estoque", options=[""] + nomes),
            "quantidade": st.column_config.NumberColumn("Qtd", min_value=0.0, step=0.1),
            "unidade": st.column_config.TextColumn("Un", disabled=True),
            "validade": st.column_config.TextColumn("Validade (DD/MM/AAAA)"),
            "custo_unitario": st.column_config.NumberColumn("Custo un.", format="R$ %.2f", disabled=True),
            "confianca": st.column_config.ProgressColumn("Confiança", min_value=0.0, max_value=1.0, format="%.0f%%"),
            "avisos": st.column_config.TextColumn("Avisos", disabled=True),
        })
    faltando = [r["descricao_nota"] for r in editado.to_dict("records") if r["lancar"] and not r["produto"]]
    if faltando:
        st.info("Itens sem produto correspondente não serão lançados: " + ", ".join(faltando) +
                ". Cadastre-os pelo chat do agente (ex.: \"cadastra o produto Manteiga...\").")

    if st.button("✅ Confirmar e lançar no estoque", type="primary"):
        linhas = [r for r in editado.to_dict("records") if r["lancar"] and r["produto"]]
        resultado = nf.registrar_nota(linhas, dados)
        st.session_state.nota_resultado = resultado
        agente = obter_agente()
        if agente and resultado["lancados"]:
            with st.status("O agente está avaliando o risco desta compra...", expanded=True) as status:
                agente.ao_passo = status.write
                st.session_state.nota_analise = agente.perguntar(nf.mensagem_para_agente(dados, resultado))
                status.update(label="Análise concluída", state="complete", expanded=False)
        else:
            st.session_state.pop("nota_analise", None)

    resultado = st.session_state.get("nota_resultado")
    if resultado:
        if resultado["lancados"]:
            st.success(f"📦 {len(resultado['lancados'])} lote(s) lançado(s): " +
                       ", ".join(f"{r['quantidade']:g} {r['produto']} (validade {r['validade'][8:10]}/{r['validade'][5:7]})"
                                 for r in resultado["lancados"]))
        for r in resultado["recusados"]:
            st.error(f"{r.get('produto')}: {r.get('erro')}")
        analise = st.session_state.get("nota_analise")
        if analise:
            with st.chat_message("assistant"):
                st.markdown(analise["resposta"])
