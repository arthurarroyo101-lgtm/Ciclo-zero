"""Loja "ao vivo": simulador de vendas do caixa + painel que se atualiza sozinho.

Num comércio real, as vendas chegariam do PDV/caixa o dia inteiro. Para a demo, este simulador
gera, em ritmo acelerado, ~80% vendas, ~12% chegadas de mercadoria (repõe o que está acabando) e ~8% perdas
(algo estraga). As vendas são realistas (proporcionais à média de cada produto, baixando do lote que vence primeiro,
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
from datetime import date, datetime, timedelta

from . import tools
from .db import conectar

INTERVALO_S = 4.0          # uma "passada no caixa" a cada ~4 s
MOTIVO = "simulação ao vivo"
# a reposição automática só começa depois de alguns minutos ligada, para não "roubar" da rotina diária
# os pedidos que ela cria na demo (o roteiro roda a rotina ~1 min depois de ligar a loja ao vivo)
PEDIDOS_AUTOMATICOS_APOS_S = 180


class Simulador:
    def __init__(self):
        self._thread: threading.Thread | None = None
        self._parar = threading.Event()
        self.eventos: deque = deque(maxlen=12)   # últimas vendas, para o letreiro
        self.vendas_sessao = 0
        self.ligado_em = 0.0

    @property
    def ativo(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    def iniciar(self) -> None:
        if self.ativo:
            return
        self._parar.clear()
        self.ligado_em = time.time()
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
        """Um momento da loja: quase sempre um cliente no caixa; às vezes chega mercadoria ou algo estraga."""
        sorteio = random.random()
        if sorteio < 0.05 and time.time() - self.ligado_em > PEDIDOS_AUTOMATICOS_APOS_S:
            ev = self._solicitar_reposicao()
        elif sorteio < 0.16:
            ev = self._chegada()
        elif sorteio < 0.23:
            ev = self._perda()
        else:
            return self._venda()
        return [ev] if ev else self._venda()

    def _solicitar_reposicao(self) -> dict | None:
        """Reposição automática: se algo está acabando, gera rascunho de pedido (o dono aprova na aba Pedidos)."""
        r = tools.criar_pedidos_sugeridos()
        if not r.get("pedidos_criados"):
            return None
        forn = ", ".join(p["fornecedor"] for p in r["pedidos"] if p.get("ok"))
        ev = self._registrar("pedido", forn, r["pedidos_criados"], "pedido(s)")
        ev["valor"] = r["valor_total_rs"]
        return ev

    def _registrar(self, tipo: str, nome: str, qtd: float, unidade: str, valor: float = 0.0) -> dict:
        ev = {"hora": datetime.now().strftime("%H:%M:%S"), "tipo": tipo, "produto": nome,
              "quantidade": qtd, "unidade": unidade, "valor": round(valor, 2)}
        self.eventos.appendleft(ev)
        self.vendas_sessao += tipo == "venda"
        return ev

    @staticmethod
    def _preco(nome: str) -> tuple[float, float]:
        with conectar() as conn:
            r = conn.execute("SELECT preco_custo, preco_venda FROM produtos WHERE nome=?", (nome,)).fetchone()
        return (r["preco_custo"], r["preco_venda"]) if r else (0.0, 0.0)

    def _venda(self) -> list[dict]:
        """Cliente no caixa: 1 a 3 produtos, escolhidos pelo quanto cada um costuma vender."""
        itens = [i for i in tools.consultar_estoque()["itens"] if i["saldo"] > 0 and i["media_vendas_dia"] > 0]
        if not itens:
            return []
        pesos = [i["media_vendas_dia"] for i in itens]
        escolhidos = {i["produto"]: i for i in random.choices(itens, weights=pesos, k=random.randint(1, 3))}
        vendidos = []
        for nome, item in escolhidos.items():
            qtd = round(random.uniform(0.2, 1.5), 1) if item["unidade"] == "kg" else float(random.randint(1, 3))
            qtd = min(qtd, item["saldo"])
            if qtd > 0 and tools.registrar_saida(nome, qtd, "venda", MOTIVO).get("ok"):
                vendidos.append(self._registrar("venda", nome, qtd, item["unidade"], qtd * self._preco(nome)[1]))
        return vendidos

    def _chegada(self) -> dict | None:
        """Fornecedor entrega um produto que está acabando (validade padrão do produto)."""
        itens = tools.consultar_estoque()["itens"]
        faltando = [i for i in itens if i["saldo"] < max(i["estoque_minimo"], i["media_vendas_dia"] * 2)]
        if not faltando:
            return None
        item = random.choice(faltando)
        with conectar() as conn:
            dias = conn.execute("SELECT COALESCE(validade_padrao_dias, 7) d FROM produtos WHERE nome=?",
                                (item["produto"],)).fetchone()["d"]
        qtd = max(1.0, round(item["media_vendas_dia"] * random.uniform(2, 4), 1 if item["unidade"] == "kg" else 0))
        validade = (date.today() + timedelta(days=int(dias))).strftime("%d/%m/%Y")
        if tools.registrar_entrada(item["produto"], qtd, validade).get("ok"):
            return self._registrar("chegada", item["produto"], qtd, item["unidade"], qtd * self._preco(item["produto"])[0])
        return None

    def _perda(self) -> dict | None:
        """Um produto estraga (pequena quantidade do lote que vence primeiro)."""
        candidatos = [i for i in tools.consultar_estoque()["itens"]
                      if i["saldo"] > 0 and i["dias_para_vencer"] is not None and i["dias_para_vencer"] <= 3]
        if not candidatos:
            return None
        item = random.choice(candidatos)
        qtd = min(item["saldo"], round(random.uniform(0.3, 1.2), 1) if item["unidade"] == "kg" else 1.0)
        if tools.registrar_saida(item["produto"], qtd, "perda", "estragou (" + MOTIVO + ")").get("ok"):
            return self._registrar("perda", item["produto"], qtd, item["unidade"], qtd * self._preco(item["produto"])[0])
        return None


_SIM = Simulador()  # um por processo do app


def simulador() -> Simulador:
    return _SIM


def vendas_de_hoje() -> dict:
    hoje = date.today().isoformat()
    with conectar() as conn:
        r = conn.execute("SELECT COUNT(*) n, COALESCE(SUM(valor),0) v, COALESCE(SUM(quantidade),0) q "
                         "FROM movimentacoes WHERE tipo='venda' AND data=?", (hoje,)).fetchone()
    return {"vendas": r["n"], "faturamento_rs": round(r["v"], 2), "itens": round(r["q"], 1)}


def financeiro_do_dia() -> dict:
    """Resultado do dia a partir das movimentações: vendas, custo do que foi vendido, lucro, compras e perdas."""
    hoje = date.today().isoformat()
    with conectar() as conn:
        r = conn.execute(
            """SELECT
                 COALESCE(SUM(CASE WHEN m.tipo='venda' THEN m.valor END),0)                       AS vendas,
                 COALESCE(SUM(CASE WHEN m.tipo='venda' THEN m.quantidade*p.preco_custo END),0)    AS custo_vendas,
                 COALESCE(SUM(CASE WHEN m.tipo='entrada' THEN m.valor END),0)                     AS compras,
                 COALESCE(SUM(CASE WHEN m.tipo='perda' THEN m.valor END),0)                       AS perdas,
                 COALESCE(SUM(CASE WHEN m.tipo='doacao' THEN m.valor END),0)                      AS doacoes,
                 COUNT(CASE WHEN m.tipo='venda' THEN 1 END)                                        AS n_vendas
               FROM movimentacoes m JOIN produtos p ON p.id=m.produto_id WHERE m.data=?""", (hoje,)).fetchone()
        pend = conn.execute("SELECT COUNT(*) n, COALESCE(SUM(valor_estimado),0) v FROM pedidos WHERE status='rascunho'"
                            ).fetchone()
    vendas, custo = r["vendas"], r["custo_vendas"]
    lucro = vendas - custo - r["perdas"]
    return {"vendas_rs": round(vendas, 2), "custo_vendas_rs": round(custo, 2), "lucro_bruto_rs": round(lucro, 2),
            "margem": (lucro / vendas) if vendas else 0.0, "compras_rs": round(r["compras"], 2),
            "perdas_rs": round(r["perdas"], 2), "n_vendas": r["n_vendas"],
            "ticket_medio_rs": round(vendas / r["n_vendas"], 2) if r["n_vendas"] else 0.0,
            "pedidos_pendentes": pend["n"], "pedidos_pendentes_rs": round(pend["v"], 2)}


# ------------------------------------------------------------------ interface
def _reais(v: float) -> str:
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


_CARTOES_HTML = """
<style>
  :root { --fundo:#ffffff; --borda:#e3e7ea; --texto:#1f2328; --sub:#5f6368; }
  @media (prefers-color-scheme: dark) { :root.auto { --fundo:#1b1f24; --borda:#30363d; --texto:#f0f3f6; --sub:#9aa4ae; } }
  :root.dark { --fundo:#1b1f24; --borda:#30363d; --texto:#f0f3f6; --sub:#9aa4ae; }
  html, body { margin:0; padding:0; background:transparent; font-family:"Source Sans Pro","Source Sans 3",system-ui,sans-serif; }
  .grade { display:grid; grid-template-columns:repeat(5, minmax(0,1fr)); gap:10px; }
  .cartao { background:var(--fundo); border:1px solid var(--borda); border-radius:12px; padding:10px 12px; min-width:0; }
  .rotulo { color:var(--sub); font-size:14px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
  .valor { color:var(--texto); font-size:clamp(18px, 2.3vw, 30px); font-weight:700; line-height:1.25; font-variant-numeric:tabular-nums;
           white-space:nowrap; transition:color .4s; }
  .delta { font-size:13px; font-weight:600; border-radius:999px; padding:1px 8px; display:inline-block; margin-top:2px;
           opacity:0; transition:opacity .3s; }
  .delta.mostra { opacity:1; }
  .bom { color:#1a7f37; background:rgba(46,160,67,.15); } .ruim { color:#cf222e; background:rgba(248,81,73,.15); }
  .neutro { color:var(--sub); background:transparent; opacity:1; }
  .pisca-bom { color:#2ea043 !important; } .pisca-ruim { color:#f85149 !important; }
</style>
<div class="grade" id="g"></div>
<script>
document.documentElement.className = "__TEMA__";
const CARTOES = __DADOS__;
const fmtR = new Intl.NumberFormat('pt-BR', {style:'currency', currency:'BRL'});
const fmt = (c, v) => c.tipo === 'reais' ? fmtR.format(v) : Math.round(v).toLocaleString('pt-BR');
const g = document.getElementById('g');
CARTOES.forEach((c, i) => {
  const d = c.para - c.de;
  let cls = 'neutro', txt = c.nota || '';
  if (Math.abs(d) > 1e-9) {
    const melhorou = c.menor_melhor ? d < 0 : d > 0;
    cls = melhorou ? 'bom' : 'ruim';
    txt = (d > 0 ? '▲ ' : '▼ ') + (c.tipo === 'reais' ? fmtR.format(Math.abs(d)) : Math.abs(Math.round(d)));
  }
  g.insertAdjacentHTML('beforeend',
    `<div class="cartao"><div class="rotulo">${c.rotulo}</div>
       <div class="valor" id="v${i}">${fmt(c, c.de)}</div>
       <div class="delta ${cls}" id="d${i}">${txt || '&nbsp;'}</div></div>`);
});
const t0 = performance.now(), DUR = 1100;
const ease = t => 1 - Math.pow(1 - t, 3);
function quadro(agora) {
  const p = Math.min(1, (agora - t0) / DUR);
  CARTOES.forEach((c, i) => {
    const el = document.getElementById('v' + i);
    el.textContent = fmt(c, c.de + (c.para - c.de) * ease(p));
    if (p < 1 && c.para !== c.de) el.classList.add((c.menor_melhor ? c.para < c.de : c.para > c.de) ? 'pisca-bom' : 'pisca-ruim');
    if (p >= 1) el.classList.remove('pisca-bom', 'pisca-ruim');
  });
  if (p < 1) requestAnimationFrame(quadro);
}
requestAnimationFrame(quadro);
setTimeout(() => CARTOES.forEach((c, i) => document.getElementById('d' + i).classList.add('mostra')), 150);
</script>
"""


def _cartoes(cartoes: list[dict]) -> None:
    """Cartões com contagem animada do valor anterior até o atual (≈1 s)."""
    import json as _json

    import streamlit.components.v1 as components
    import streamlit as st
    tema = "light"  # o app usa tema claro fixo (.streamlit/config.toml) — melhor no projetor
    html = _CARTOES_HTML.replace("__DADOS__", _json.dumps(cartoes, ensure_ascii=False)).replace("__TEMA__", tema)
    components.html(html, height=118)


def intervalo() -> int | None:
    """Intervalo de atualização das abas de dados: 4 s com a loja ao vivo ligada; parado se desligada."""
    return 4 if simulador().ativo else None


def tabela_movimento():
    """Últimos lançamentos da simulação (para a aba Dashboard)."""
    import pandas as pd
    nomes = {"venda": "🛒 Venda", "chegada": "🚚 Chegada", "perda": "🗑️ Perda", "pedido": "📝 Pedido automático"}
    linhas = [{"hora": e["hora"], "lançamento": nomes.get(e.get("tipo"), e.get("tipo")), "item": e["produto"],
               "qtd": f"{e['quantidade']:g} {e['unidade']}", "valor": _reais(e.get("valor", 0))}
              for e in simulador().eventos]
    return pd.DataFrame(linhas)


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

        if sim.ativo:
            st.markdown("🟢 **Loja ao vivo** — *simulação de vendas do caixa; números atualizando em tempo real*")
        de = lambda k: anterior.get(k, atual[k])
        _cartoes([
            {"rotulo": "Vendas hoje", "tipo": "reais", "de": de("fat"), "para": atual["fat"]},
            {"rotulo": "Lotes em risco · 5 dias", "tipo": "int", "de": de("lotes"), "para": atual["lotes"],
             "menor_melhor": True},
            {"rotulo": "R$ em risco · 3 dias", "tipo": "reais", "de": de("em_risco"), "para": atual["em_risco"],
             "menor_melhor": True},
            {"rotulo": "Perda se nada for feito", "tipo": "reais", "de": de("perda"), "para": atual["perda"],
             "menor_melhor": True},
            {"rotulo": "Perdas · 30 dias", "tipo": "reais", "de": perdas["total_perdas_rs"],
             "para": perdas["total_perdas_rs"], "nota": perdas["perdas_sobre_faturamento"].replace(".", ",") + " do faturamento"},
        ])
        if sim.ativo and sim.eventos:
            icone = {"venda": "🛒", "chegada": "🚚", "perda": "🗑️", "pedido": "📝"}
            st.caption("Movimento: " + " · ".join(
                f"{icone.get(e.get('tipo'), '🛒')} {e['hora']} {e['quantidade']:g} {e['unidade']} {e['produto']}"
                for e in list(sim.eventos)[:5]) + "  ·  🛒 venda  🚚 chegada  🗑️ estragou  📝 pedido automático")
        st.session_state["_painel_anterior"] = atual

    _painel()


if __name__ == "__main__":
    print("Loja ao vivo (simulação). Ctrl+C para parar.")
    s = simulador()
    try:
        while True:
            for ev in s.passo():
                print(f"{ev['hora']}  {ev['tipo']}: {ev['quantidade']:g} {ev['unidade']} {ev['produto']}")
            print(f"   hoje: {vendas_de_hoje()}")
            time.sleep(INTERVALO_S)
    except KeyboardInterrupt:
        pass
