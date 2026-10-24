"""Loja "ao vivo": simulador de vendas do caixa + painel que se atualiza sozinho.

Num comércio real, as vendas chegariam do PDV/caixa o dia inteiro. Para a demo, este simulador
gera vendas realistas (proporcionais à média de cada produto, baixando do lote que vence primeiro,
nunca deixando estoque negativo) usando a MESMA ferramenta do agente (tools.registrar_saida).
Tudo marcado como simulação (motivo "simulação ao vivo") e desligado por padrão.

Uso na interface: ao_vivo.controles() na barra lateral e ao_vivo.painel() no topo.
Uso no terminal (sem interface):  python -m ciclozero.ao_vivo
"""
from __future__ import annotations

import random
import threading
import time
from collections import deque
from datetime import date, datetime

from . import tools
from .db import conectar

INTERVALO_S = 4.0          # uma "passada no caixa" a cada ~4 s
MOTIVO = "simulação ao vivo"


class Simulador:
    def __init__(self):
        self._thread: threading.Thread | None = None
        self._parar = threading.Event()
        self.eventos: deque = deque(maxlen=8)   # últimas vendas, para o letreiro
        self.vendas_sessao = 0

    @property
    def ativo(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    def iniciar(self) -> None:
        if self.ativo:
            return
        self._parar.clear()
        self._thread = threading.Thread(target=self._laco, daemon=True, name="ciclozero-ao-vivo")
        self._thread.start()

    def parar(self) -> None:
        self._parar.set()
        if self._thread:
            self._thread.join(timeout=INTERVALO_S + 2)

    def _laco(self) -> None:
        while not self._parar.is_set():
            try:
                self.passo()
            except Exception:
                pass  # simulação nunca derruba o app
            self._parar.wait(INTERVALO_S * random.uniform(0.6, 1.4))

    def passo(self) -> list[dict]:
        """Um cliente passa no caixa: 1 a 3 produtos, escolhidos pelo quanto cada um costuma vender."""
        itens = [i for i in tools.consultar_estoque()["itens"] if i["saldo"] > 0 and i["media_vendas_dia"] > 0]
        if not itens:
            return []
        pesos = [i["media_vendas_dia"] for i in itens]
        escolhidos = {i["produto"]: i for i in random.choices(itens, weights=pesos, k=random.randint(1, 3))}
        vendidos = []
        for nome, item in escolhidos.items():
            if item["unidade"] == "kg":
                qtd = round(random.uniform(0.2, 1.5), 1)
            else:
                qtd = float(random.randint(1, 3))
            qtd = min(qtd, item["saldo"])
            if qtd <= 0:
                continue
            r = tools.registrar_saida(nome, qtd, "venda", MOTIVO)
            if r.get("ok"):
                ev = {"hora": datetime.now().strftime("%H:%M:%S"), "produto": nome, "quantidade": qtd,
                      "unidade": item["unidade"]}
                self.eventos.appendleft(ev)
                self.vendas_sessao += 1
                vendidos.append(ev)
        return vendidos


_SIM = Simulador()  # um por processo do app


def simulador() -> Simulador:
    return _SIM


def vendas_de_hoje() -> dict:
    hoje = date.today().isoformat()
    with conectar() as conn:
        r = conn.execute("SELECT COUNT(*) n, COALESCE(SUM(valor),0) v, COALESCE(SUM(quantidade),0) q "
                         "FROM movimentacoes WHERE tipo='venda' AND data=?", (hoje,)).fetchone()
    return {"vendas": r["n"], "faturamento_rs": round(r["v"], 2), "itens": round(r["q"], 1)}


# ------------------------------------------------------------------ interface
def _reais(v: float) -> str:
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def controles() -> None:
    """Botão liga/desliga na barra lateral."""
    import streamlit as st
    sim = simulador()
    ligado = st.toggle("🟢 Loja ao vivo (simulação de vendas)", value=sim.ativo,
                       help="Simula vendas chegando do caixa a cada poucos segundos, como num dia de loja aberta. "
                            "Os números do painel se atualizam sozinhos.")
    if ligado and not sim.ativo:
        sim.iniciar()
    elif not ligado and sim.ativo:
        sim.parar()


def painel() -> None:
    """Indicadores do topo. Com a simulação ligada, atualizam a cada 3 s sem recarregar a página."""
    import streamlit as st

    @st.fragment(run_every=3 if simulador().ativo else None)
    def _painel():
        sim = simulador()
        risco = tools.analisar_risco_desperdicio()
        vencendo = tools.listar_produtos_vencendo(3)
        perdas = tools.relatorio_desperdicio(30)
        hoje = vendas_de_hoje()
        anterior = st.session_state.get("_painel_anterior", {})
        atual = {"lotes": len(risco["lotes_em_risco"]), "em_risco": vencendo["valor_total_em_risco"],
                 "perda": risco["resumo"]["perda_total_sem_acao_rs"], "fat": hoje["faturamento_rs"],
                 "vendas": hoje["vendas"]}

        def delta(chave, dinheiro=True):
            if chave not in anterior or anterior[chave] == atual[chave]:
                return None
            d = atual[chave] - anterior[chave]
            return (("+" if d > 0 else "−") + _reais(abs(d))[3:]) if dinheiro else f"{d:+g}"

        if sim.ativo:
            st.markdown("🟢 **Loja ao vivo** — *simulação de vendas do caixa; números atualizando em tempo real*")
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Vendas hoje", _reais(hoje["faturamento_rs"]), delta("fat"))
        c2.metric("Lotes em risco (5 dias)", atual["lotes"], delta("lotes", False), delta_color="inverse")
        c3.metric("R$ em risco (3 dias)", _reais(atual["em_risco"]), delta("em_risco"), delta_color="inverse")
        c4.metric("Perda projetada sem ação", _reais(atual["perda"]), delta("perda"), delta_color="inverse")
        c5.metric("Perdas últimos 30 dias", _reais(perdas["total_perdas_rs"]),
                  perdas["perdas_sobre_faturamento"] + " do faturamento", delta_color="off")
        if sim.ativo and sim.eventos:
            st.caption("🧾 Últimas vendas: " + " · ".join(
                f"{e['hora']} {e['quantidade']:g} {e['unidade']} {e['produto']}" for e in list(sim.eventos)[:5]))
        st.session_state["_painel_anterior"] = atual

    _painel()


if __name__ == "__main__":
    print("Loja ao vivo (simulação). Ctrl+C para parar.")
    s = simulador()
    try:
        while True:
            for ev in s.passo():
                print(f"{ev['hora']}  venda: {ev['quantidade']:g} {ev['unidade']} {ev['produto']}")
            print(f"   hoje: {vendas_de_hoje()}")
            time.sleep(INTERVALO_S)
    except KeyboardInterrupt:
        pass
