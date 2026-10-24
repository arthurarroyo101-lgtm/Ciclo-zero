"""Aba "📷 Nota fiscal" da interface: foto da nota -> conferência -> estoque -> alerta do agente.

Fica separada do app.py para não conflitar com o trabalho de interface (João).
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from . import nota_fiscal as nf
from .db import conectar

EXEMPLOS = Path(__file__).resolve().parent.parent / "docs" / "exemplos"


def _reais(v) -> str:
    return "—" if v is None else f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def render(obter_agente) -> None:
    """obter_agente: função sem argumentos que devolve o agente (ou None se não houver chave)."""
    st.markdown("""<style>
      .st-key-cz_nota_recibo { background:#EFE6D6; border:1.5px solid #D8C9AE; border-radius:6px; padding:14px 18px; }
      .st-key-cz_nota_recibo [data-testid="stMetricValue"] { font-family:"Archivo", sans-serif; font-weight:800;
                                                            font-stretch:85%; font-variant-numeric:tabular-nums; }
    </style>""", unsafe_allow_html=True)
    st.subheader("Entrada de mercadoria pela nota fiscal")
    st.caption("Fotografe a nota do fornecedor. O Ciclo Zero lê os itens, encontra cada um no seu estoque e "
               "sugere a validade. Você confere e lança: nada entra no estoque sem a sua confirmação.")

    n_aprendidos = nf.aprendidos()
    if n_aprendidos:
        st.caption(f"Esta loja já ensinou **{n_aprendidos}** descrições de nota ao sistema — "
                   "cada confirmação ou correção é lembrada na próxima nota.")
    exemplos = sorted(EXEMPLOS.glob("nota_exemplo_*.png"))
    opcoes = ["Enviar foto", "Câmera"] + [f"Exemplo: {e.stem.replace('nota_exemplo_', '').title()}" for e in exemplos]
    origem = st.radio("Origem da nota", opcoes, horizontal=True, label_visibility="collapsed")
    imagem, mime = None, "image/png"
    if origem == "Enviar foto":
        arq = st.file_uploader("Foto ou print da nota", type=["png", "jpg", "jpeg", "webp"])
        if arq:
            imagem, mime = arq.getvalue(), arq.type or "image/jpeg"
    elif origem == "Câmera":
        foto = st.camera_input("Fotografe a nota")
        if foto:
            imagem, mime = foto.getvalue(), "image/jpeg"
    else:
        escolhido = exemplos[opcoes.index(origem) - 2]
        imagem = escolhido.read_bytes()

    if imagem:
        c1, c2 = st.columns([1, 2])
        c1.image(imagem, caption="Nota enviada", width="stretch")
        with c2:
            opcoes_metodo = {"Automático": "auto", "Visão (Gemini)": "visao_gemini",
                             "OCR local + IA de texto": "ocr"}
            if not nf.ocr_disponivel():
                opcoes_metodo.pop("OCR local + IA de texto")
            escolha = st.radio("Como ler", list(opcoes_metodo), horizontal=True,
                               help="Automático: tenta a visão do Gemini e, se falhar, o OCR local (Tesseract) "
                                    "+ IA de texto. O OCR roda no seu computador.")
            if st.button("Ler nota", type="primary", icon=":material/document_scanner:"):
                with st.status("Lendo a nota...", expanded=True) as status:
                    status.write("Lendo a nota: fornecedor, itens e valores" +
                                 (" (OCR local + IA de texto)" if opcoes_metodo[escolha] == "ocr" else ""))
                    try:
                        dados = nf.ler_nota(imagem, mime, opcoes_metodo[escolha])
                    except nf.LeituraFalhou as e:
                        status.update(label="Não consegui ler a nota", state="error")
                        st.error(str(e))
                        return
                    status.write(f"{len(dados['itens'])} itens lidos em {dados['segundos']} s ({dados['modelo']})")
                    status.write("Associando itens ao cadastro e sugerindo validade")
                    st.session_state.nota_dados = dados
                    st.session_state.nota_linhas = nf.conciliar(dados)
                    st.session_state.pop("nota_resultado", None)
                    status.update(label="Nota lida. Confira abaixo.", state="complete", expanded=False)

    dados = st.session_state.get("nota_dados")
    if not dados:
        return

    v = dados["verificacao"]
    with st.container(key="cz_nota_recibo"):
        st.markdown(f"#### {dados.get('fornecedor') or 'Fornecedor não identificado'}")
        st.caption(f"Nota nº {dados.get('numero') or 'não identificado'}"
                   + (f", emitida em {dados['data_emissao']}" if dados.get("data_emissao") else ""))
        m1, m2 = st.columns(2)
        m1.metric("Total da nota", _reais(v["total_nota"]))
        m2.metric("Soma dos itens lidos", _reais(v["soma_itens"]))
        if v["confiavel"]:
            st.success("Leitura conferida: a soma dos itens bate com o total da nota.")
        else:
            st.warning("Confira antes de lançar: " + "; ".join(v["problemas"] or ["leitura incerta"]))

    with conectar() as conn:
        nomes = [r["nome"] for r in conn.execute("SELECT nome FROM produtos ORDER BY nome")]
    df = pd.DataFrame(st.session_state.nota_linhas)
    # exibição no padrão brasileiro (a quantidade continua número para poder editar)
    SEM = "(não cadastrado)"
    df["produto"] = df["produto"].fillna("").replace("", SEM)
    df["custo_unitario"] = df["custo_unitario"].map(lambda v: "" if v is None or pd.isna(v) else _reais(v))
    df["confianca"] = (df["confianca"].fillna(0) * 100).round().astype(int)
    editado = st.data_editor(
        df, hide_index=True, width="stretch", key="editor_nota",
        column_config={
            "lancar": st.column_config.CheckboxColumn("Lançar?"),
            "descricao_nota": st.column_config.TextColumn("Na nota", disabled=True),
            "produto": st.column_config.SelectboxColumn("Produto no estoque", options=[SEM] + nomes),
            "quantidade": st.column_config.NumberColumn("Qtd", min_value=0.0, step=0.1, format="%g"),
            "unidade": st.column_config.TextColumn("Un", disabled=True),
            "validade": st.column_config.TextColumn("Validade (DD/MM/AAAA)"),
            "custo_unitario": st.column_config.TextColumn("Custo un.", disabled=True),
            "confianca": st.column_config.ProgressColumn("Confiança", min_value=0, max_value=100, format="%d%%"),
            "origem": st.column_config.TextColumn("Como associou", disabled=True),
            "avisos": st.column_config.TextColumn("Avisos", disabled=True),
        })
    editado["produto"] = editado["produto"].replace(SEM, "")
    faltando = [r["descricao_nota"] for r in editado.to_dict("records") if r["lancar"] and not r["produto"]]
    if faltando:
        st.info("Itens sem produto correspondente não serão lançados: " + ", ".join(faltando) +
                ". Cadastre-os pelo chat do agente (ex.: \"cadastra o produto Manteiga...\").")

    if st.button("Lançar no estoque", type="primary", icon=":material/move_to_inbox:"):
        linhas = [r for r in editado.to_dict("records") if r["lancar"] and r["produto"]]
        resultado = nf.registrar_nota(linhas, dados)
        st.session_state.nota_resultado = resultado
        agente = obter_agente()
        if agente and resultado["lancados"]:
            with st.status("Verificando se esta compra vai sobrar...", expanded=True) as status:
                agente.ao_passo = status.write
                st.session_state.nota_analise = agente.perguntar(nf.mensagem_para_agente(dados, resultado))
                status.update(label="Verificação concluída", state="complete", expanded=False)
        else:
            st.session_state.pop("nota_analise", None)

    resultado = st.session_state.get("nota_resultado")
    if resultado:
        if resultado["lancados"]:
            n = len(resultado["lancados"])
            st.success(f"{n} {'lote entrou' if n == 1 else 'lotes entraram'} no estoque.", icon=":material/check_circle:")
            st.dataframe(pd.DataFrame([{"Produto": r["produto"], "Quantidade": f"{r['quantidade']:g}",
                                        "Validade": f"{r['validade'][8:10]}/{r['validade'][5:7]}"}
                                       for r in resultado["lancados"]]), hide_index=True, width="content")
        for r in resultado["recusados"]:
            st.error(f"{r.get('produto')}: {r.get('erro')}")
        analise = st.session_state.get("nota_analise")
        if analise:
            with st.chat_message("assistant"):
                from .ui_agente import md_seguro
                st.markdown(md_seguro(analise["resposta"]))
