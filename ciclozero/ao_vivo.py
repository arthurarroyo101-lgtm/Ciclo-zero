"""Loja "ao vivo": simulador de vendas do caixa + painel que se atualiza sozinho.

Num comércio real, as vendas chegariam do PDV/caixa o dia inteiro. Para a demo, este simulador
gera, em ritmo acelerado: vendas (~72%), compras recebidas (~7%, 30% delas exageradas), fornadas da padaria (~7%,
validade curta), perdas (~5%), despesas pagas (~5%: energia, gás, embalagens...) e pedidos automáticos (~4%).
Caixa e lucro sobem E descem, como num dia real. As vendas são realistas (proporcionais à média de cada produto, baixando do lote que vence primeiro,
nunca deixando estoque negativo) usando a MESMA ferramenta do agente (tools.registrar_saida).
Tudo marcado como simulação (motivo "simulação ao vivo") e desligado por padrão.

Uso na interface: ao_vivo.controles() na barra lateral e ao_vivo.painel() no topo.
Uso no terminal (sem interface):  python -m ciclozero.ao_vivo
"""
from __future__ import annotations

import json
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
        self.eventos: deque = deque(maxlen=12)
        self.alertas: deque = deque(maxlen=6)   # compras/produções em excesso flagradas   # últimas vendas, para o letreiro
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
        if sorteio < 0.04 and time.time() - self.ligado_em > PEDIDOS_AUTOMATICOS_APOS_S:
            ev = self._solicitar_reposicao()
        elif sorteio < 0.11:
            ev = self._chegada()
        elif sorteio < 0.18:
            ev = self._producao()
        elif sorteio < 0.23:
            ev = self._perda()
        elif sorteio < 0.28:
            ev = self._despesa()
        else:
            return self._venda()
        return [ev] if ev else self._venda()

    def _avaliar_excesso(self, item: dict, qtd: float, validade_dias: int, origem: str) -> dict | None:
        """O problema que o Ciclo Zero resolve: comprar/produzir mais do que dá para vender antes de vencer.
        Compara o que entrou com o que a loja consegue vender até a validade e com o que o agente sugeriria."""
        media, saldo_antes = item["media_vendas_dia"], item["saldo"]
        if media <= 0:
            return None
        vende_ate_vencer = media * max(validade_dias, 1)
        sobra = min(qtd, max(0.0, saldo_antes + qtd - vende_ate_vencer))
        custo, _ = self._preco(item["produto"])
        if sobra < max(0.25 * qtd, 0.5) or sobra * custo < 15:  # ignora excesso pequeno (poluiria a tela)
            return None
        dias_ideal = 1 if origem == "producao" else min(validade_dias, tools.COBERTURA_DIAS + 2)
        ideal = max(0.0, media * dias_ideal - saldo_antes)
        arred = (lambda v: round(v, 1)) if item["unidade"] == "kg" else (lambda v: float(round(v)))
        alerta = {"hora": datetime.now().strftime("%H:%M:%S"), "origem": origem, "produto": item["produto"],
                  "unidade": item["unidade"], "quantidade": qtd, "media_dia": round(media, 1),
                  "validade_dias": validade_dias, "sobra": arred(sobra), "ideal": arred(ideal),
                  "excesso_rs": round(sobra * custo, 2)}
        self.alertas.appendleft(alerta)
        with conectar() as conn:
            conn.execute("INSERT INTO log_agente (sessao, passo, tipo, conteudo) VALUES (?,?,?,?)",
                         ("ao_vivo", 0, "alerta_excesso", json.dumps({**alerta, "data": date.today().isoformat()},
                                                                     ensure_ascii=False)))
        return alerta

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
        faltando = [i for i in itens if i["saldo"] < max(i["estoque_minimo"], i["media_vendas_dia"] * 3)
                    and i["produto"] not in self._producao_propria()]  # pão/bolo saem do forno (ver _producao)
        if not faltando:
            return None
        item = random.choice(faltando)
        with conectar() as conn:
            dias = conn.execute("SELECT COALESCE(validade_padrao_dias, 7) d FROM produtos WHERE nome=?",
                                (item["produto"],)).fetchone()["d"]
        # 70% compra certa (2–4 dias de venda); 30% compra exagerada (6–10 dias) -> gera risco de sobra
        dias_cobertos = random.uniform(1.5, 3) if random.random() < 0.7 else random.uniform(5, 8)
        qtd = max(1.0, round(item["media_vendas_dia"] * dias_cobertos, 1 if item["unidade"] == "kg" else 0))
        validade = (date.today() + timedelta(days=int(dias))).strftime("%d/%m/%Y")
        if tools.registrar_entrada(item["produto"], qtd, validade).get("ok"):
            ev = self._registrar("chegada", item["produto"], qtd, item["unidade"], qtd * self._preco(item["produto"])[0])
            ev["excesso"] = self._avaliar_excesso(item, qtd, int(dias), "compra")
            return ev
        return None

    @staticmethod
    def _producao_propria() -> set[str]:
        with conectar() as conn:
            return {r["nome"] for r in conn.execute("SELECT nome FROM produtos WHERE fornecedor='Produção própria'")}

    def _producao(self) -> dict | None:
        """Fornada da padaria: pão/bolo de validade curta entram no estoque (custo de insumos sai do caixa)."""
        itens = [i for i in tools.consultar_estoque()["itens"] if i["categoria"] == "Padaria"]
        with conectar() as conn:
            proprios = {r["nome"]: r["validade_padrao_dias"] for r in conn.execute(
                "SELECT nome, COALESCE(validade_padrao_dias,1) validade_padrao_dias FROM produtos "
                "WHERE fornecedor='Produção própria'")}
        itens = [i for i in itens if i["produto"] in proprios]
        if not itens:
            return None
        item = random.choice(itens)
        # às vezes o padeiro exagera na fornada (produção acima da venda = sobra no fim do dia)
        fator = random.uniform(0.4, 0.8) if random.random() < 0.7 else random.uniform(1.0, 1.6)
        qtd = max(1.0, round(item["media_vendas_dia"] * fator, 1 if item["unidade"] == "kg" else 0))
        validade = (date.today() + timedelta(days=int(proprios[item["produto"]]))).strftime("%d/%m/%Y")
        if tools.registrar_entrada(item["produto"], qtd, validade).get("ok"):
            ev = self._registrar("producao", item["produto"], qtd, item["unidade"], qtd * self._preco(item["produto"])[0])
            ev["excesso"] = self._avaliar_excesso(item, qtd, int(proprios[item["produto"]]), "producao")
            return ev
        return None

    DESPESAS = [("Energia elétrica", 60, 220), ("Gás do forno", 40, 140), ("Embalagens", 15, 70),
                ("Frete de fornecedor", 25, 90), ("Manutenção", 40, 180), ("Diarista/limpeza", 80, 120)]

    def _despesa(self) -> dict:
        """Conta paga no caixa (sai dinheiro, não sai produto)."""
        categoria, minimo, maximo = random.choice(self.DESPESAS)
        valor = round(random.uniform(minimo, maximo), 2)
        agora = datetime.now()
        with conectar() as conn:
            conn.execute("INSERT INTO despesas (data, hora, categoria, descricao, valor) VALUES (?,?,?,?,?)",
                         (date.today().isoformat(), agora.strftime("%H:%M:%S"), categoria, MOTIVO, valor))
        return self._registrar("despesa", categoria, 1, "pagamento", valor)

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
    """Fechamento do dia a partir das movimentações e despesas.

    - Caixa do dia  = entradas (vendas) − saídas (compras/produção pagas + despesas). Pode ser negativo.
    - Lucro do dia  = lucro bruto (vendas − custo do que foi vendido − perdas) − despesas operacionais.
    Compras não são "prejuízo": viram estoque. Por isso caixa e lucro andam diferentes num dia de muita compra.
    """
    hoje = date.today().isoformat()
    with conectar() as conn:
        r = conn.execute(
            """SELECT
                 COALESCE(SUM(CASE WHEN m.tipo='venda' THEN m.valor END),0)                       AS vendas,
                 COALESCE(SUM(CASE WHEN m.tipo='venda' THEN m.quantidade*p.preco_custo END),0)    AS custo_vendas,
                 COALESCE(SUM(CASE WHEN m.tipo='entrada' THEN m.valor END),0)                     AS compras,
                 COALESCE(SUM(CASE WHEN m.tipo='perda' THEN m.valor END),0)                       AS perdas,
                 COUNT(CASE WHEN m.tipo='venda' THEN 1 END)                                        AS n_vendas
               FROM movimentacoes m JOIN produtos p ON p.id=m.produto_id WHERE m.data=?""", (hoje,)).fetchone()
        despesas = conn.execute("SELECT COALESCE(SUM(valor),0) v FROM despesas WHERE data=?", (hoje,)).fetchone()["v"]
        pend = conn.execute("SELECT COUNT(*) n, COALESCE(SUM(valor_estimado),0) v FROM pedidos WHERE status='rascunho'"
                            ).fetchone()
        excessos = [json.loads(x["conteudo"]) for x in conn.execute(
            "SELECT conteudo FROM log_agente WHERE tipo='alerta_excesso'")]
    excessos = [e for e in excessos if e.get("data") == hoje]
    vendas, custo, compras, perdas = r["vendas"], r["custo_vendas"], r["compras"], r["perdas"]
    lucro_bruto = vendas - custo - perdas
    lucro = lucro_bruto - despesas
    saidas = compras + despesas
    return {"vendas_rs": round(vendas, 2), "custo_vendas_rs": round(custo, 2), "compras_rs": round(compras, 2),
            "despesas_rs": round(despesas, 2), "perdas_rs": round(perdas, 2), "saidas_caixa_rs": round(saidas, 2),
            "caixa_rs": round(vendas - saidas, 2), "lucro_bruto_rs": round(lucro_bruto, 2), "lucro_rs": round(lucro, 2),
            "margem": (lucro / vendas) if vendas else 0.0, "n_vendas": r["n_vendas"],
            "ticket_medio_rs": round(vendas / r["n_vendas"], 2) if r["n_vendas"] else 0.0,
            "pedidos_pendentes": pend["n"], "pedidos_pendentes_rs": round(pend["v"], 2),
            "excesso_rs": round(sum(e["excesso_rs"] for e in excessos), 2), "n_excessos": len(excessos)}


# ------------------------------------------------------------------ interface
def _reais(v: float) -> str:
    txt = f"R$ {abs(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return ("−" + txt) if v < 0 else txt


_CARTOES_HTML = """
<style>
  :root { --fundo:#ffffff; --borda:#e3e7ea; --texto:#1f2328; --sub:#5f6368; }
  @media (prefers-color-scheme: dark) { :root.auto { --fundo:#1b1f24; --borda:#30363d; --texto:#f0f3f6; --sub:#9aa4ae; } }
  :root.dark { --fundo:#1b1f24; --borda:#30363d; --texto:#f0f3f6; --sub:#9aa4ae; }
  html, body { margin:0; padding:0; background:transparent; font-family:"Source Sans Pro","Source Sans 3",system-ui,sans-serif; }
  .grade { display:grid; grid-template-columns:repeat(6, minmax(0,1fr)); gap:10px; }
  .cartao { background:var(--fundo); border:1px solid var(--borda); border-radius:12px; padding:10px 12px; min-width:0; }
  .rotulo { color:var(--sub); font-size:14px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
  .valor { color:var(--texto); font-size:clamp(16px, 2.0vw, 28px); font-weight:700; line-height:1.25; font-variant-numeric:tabular-nums;
           white-space:nowrap; transition:color .4s; }
  .delta { font-size:13px; font-weight:600; border-radius:999px; padding:1px 8px; display:inline-block; margin-top:2px;
           opacity:0; transition:opacity .3s; }
  .delta.mostra { opacity:1; }
  .bom { color:#1a7f37; background:rgba(46,160,67,.15); } .ruim { color:#cf222e; background:rgba(248,81,73,.15); }
  .neutro { color:var(--sub); background:transparent; opacity:1; }
  .pisca-bom { color:#2ea043 !important; } .pisca-ruim { color:#f85149 !important; }
  .negativo { color:#cf222e; }
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
    el.classList.toggle('negativo', c.tipo === 'reais' && c.para < 0 && p >= 1);
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
    """Intervalo de atualização das abas de dados: 3 s com a loja ao vivo ligada; parado se desligada."""
    return 3 if simulador().ativo else None  # mesmo ritmo do painel do topo


def tabela_movimento():
    """Últimos lançamentos da simulação (para a aba Dashboard)."""
    import pandas as pd
    nomes = {"venda": "🛒 Venda (entra no caixa)", "chegada": "🚚 Compra recebida (sai do caixa)",
             "producao": "🍞 Produção (insumos saem do caixa)", "despesa": "💸 Despesa paga",
             "excesso": "🚨 Em excesso (vai sobrar)",
             "perda": "🗑️ Perda (estragou)", "pedido": "📝 Pedido automático (rascunho)"}
    linhas = [{"hora": e["hora"],
               "lançamento": nomes.get(e.get("tipo"), e.get("tipo")) + (" · 🚨 EXCESSO" if e.get("excesso") else ""),
               "item": e["produto"],
               "qtd": f"{e['quantidade']:g} {e['unidade']}", "valor": _reais(e.get("valor", 0))}
              for e in simulador().eventos]
    return pd.DataFrame(linhas)


def render_alertas_excesso() -> None:
    """O problema, mostrado na hora em que acontece: compra/produção acima do que a loja vende antes de vencer."""
    import streamlit as st
    for a in list(simulador().alertas)[:3]:
        u = a["unidade"]
        verbo = "Saíram do forno" if a["origem"] == "producao" else "Chegaram"
        st.warning(
            f"🚨 **{a['hora']} · {verbo} {a['quantidade']:g} {u} de {a['produto']}** — a loja vende ~{a['media_dia']:g} {u}/dia "
            f"e vence em {a['validade_dias']} dia(s): **~{a['sobra']:g} {u} vão para o lixo "
            f"({_reais(a['excesso_rs']).replace('$', chr(92) + '$')})**. "
            + (f"Com o Ciclo Zero, o {'plano de produção' if a['origem'] == 'producao' else 'pedido'} sugerido seria "
               f"**{a['ideal']:g} {u}**." if a["ideal"] > 0 else
               f"Com o Ciclo Zero, **não {'precisava produzir' if a['origem'] == 'producao' else 'precisava comprar'} "
               f"agora**: já havia estoque suficiente."))


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
        fin = financeiro_do_dia()
        anterior = st.session_state.get("_painel_anterior", {})
        atual = {"lotes": len(risco["lotes_em_risco"]), "em_risco": vencendo["valor_total_em_risco"],
                 "perda": risco["resumo"]["perda_total_sem_acao_rs"], "fat": hoje["faturamento_rs"],
                 "vendas": hoje["vendas"], "caixa": fin["caixa_rs"], "lucro": fin["lucro_rs"]}

        if sim.ativo:
            st.markdown("🟢 **Loja ao vivo** — *simulação de vendas do caixa; números atualizando em tempo real*")
        de = lambda k: anterior.get(k, atual[k])
        _cartoes([
            {"rotulo": "Vendas hoje", "tipo": "reais", "de": de("fat"), "para": atual["fat"]},
            {"rotulo": "Caixa do dia", "tipo": "reais", "de": de("caixa"), "para": atual["caixa"]},
            {"rotulo": "Lucro do dia", "tipo": "reais", "de": de("lucro"), "para": atual["lucro"]},
            {"rotulo": "Lotes em risco · 5 dias", "tipo": "int", "de": de("lotes"), "para": atual["lotes"],
             "menor_melhor": True},
            {"rotulo": "Perda se nada for feito", "tipo": "reais", "de": de("perda"), "para": atual["perda"],
             "menor_melhor": True},
            {"rotulo": "Perdas · 30 dias", "tipo": "reais", "de": perdas["total_perdas_rs"],
             "para": perdas["total_perdas_rs"], "nota": perdas["perdas_sobre_faturamento"].replace(".", ",") + " do faturamento"},
        ])
        if sim.ativo and sim.eventos:
            icone = {"venda": "🛒", "chegada": "🚚", "perda": "🗑️", "pedido": "📝", "producao": "🍞", "despesa": "💸"}
            st.caption("Movimento: " + " · ".join(
                f"{'🚨' if e.get('excesso') else icone.get(e.get('tipo'), '🛒')} {e['hora']} {e['quantidade']:g} {e['unidade']} {e['produto']}"
                for e in list(sim.eventos)[:5]) + "  ·  🛒 venda  🍞 produção  🚚 chegada  💸 despesa  🗑️ estragou  📝 pedido")
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
