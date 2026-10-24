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

from . import relogio, tools
from .db import conectar

INTERVALO_S = 4.0          # uma "passada no caixa" a cada ~4 s
MOTIVO = "simulação ao vivo"
# a reposição automática só começa depois de alguns minutos ligada, para não "roubar" da rotina diária
# os pedidos que ela cria na demo (o roteiro roda a rotina ~1 min depois de ligar a loja ao vivo)
PEDIDOS_AUTOMATICOS_APOS_S = 180
MIN_POR_PASSO = (6, 12)    # cada passo anda 6–12 min do dia da loja: um dia (7h–20h) leva ~6 min de verdade
ENTREGA_APOS_H = 3         # pedido aprovado só chega depois de ~3 h do dia da loja (não na hora)


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
        """Um momento da loja (~5 a 10 min do dia simulado): quase sempre um cliente no caixa; às vezes chega
        mercadoria, sai fornada, algo estraga ou se paga uma conta. Às 20h a loja fecha e o dia vira."""
        if relogio.avancar(random.randint(MIN_POR_PASSO[0], MIN_POR_PASSO[1])):
            return [self._fechar_dia()]
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
        alerta = {"hora": relogio.hora().strftime("%H:%M"), "origem": origem, "produto": item["produto"],
                  "unidade": item["unidade"], "quantidade": qtd, "media_dia": round(media, 1),
                  "validade_dias": validade_dias, "sobra": arred(sobra), "ideal": arred(ideal),
                  "excesso_rs": round(sobra * custo, 2)}
        self.alertas.appendleft(alerta)
        with conectar() as conn:
            conn.execute("INSERT INTO log_agente (sessao, passo, tipo, conteudo) VALUES (?,?,?,?)",
                         ("ao_vivo", 0, "alerta_excesso", json.dumps({**alerta, "data": relogio.hoje().isoformat()},
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
        ev = {"hora": relogio.hora().strftime("%H:%M"), "tipo": tipo, "produto": nome,
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
        """Fornecedor entrega: primeiro os pedidos que o dono APROVOU (certos, sem excesso);
        senão, uma compra avulsa de algo que está acabando (às vezes exagerada)."""
        aprovados = [p for p in tools.listar_pedidos("aprovado") if not p.get("recebido_em")
                     and self._horas_desde(p.get("aprovado_em")) >= ENTREGA_APOS_H]
        if aprovados and random.random() < 0.6:
            p = aprovados[-1]  # o mais antigo
            r = tools.receber_pedido(p["id"])
            if r.get("ok"):
                return self._registrar("recebido", f"pedido #{p['id']} {p['fornecedor']}", len(r["itens_recebidos"]),
                                       "item(ns)", r["valor_rs"])
        return self._chegada_avulsa()

    def _chegada_avulsa(self) -> dict | None:
        """Compra avulsa (sem o Ciclo Zero) de um produto que está acabando."""
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
        validade = (relogio.hoje() + timedelta(days=int(dias))).strftime("%d/%m/%Y")
        if tools.registrar_entrada(item["produto"], qtd, validade).get("ok"):
            ev = self._registrar("chegada", item["produto"], qtd, item["unidade"], qtd * self._preco(item["produto"])[0])
            ev["excesso"] = self._avaliar_excesso(item, qtd, int(dias), "compra")
            return ev
        return None

    @staticmethod
    def _horas_desde(iso: str | None) -> float:
        if not iso:
            return 0.0
        try:
            return (relogio.agora() - datetime.fromisoformat(iso)).total_seconds() / 3600
        except ValueError:
            return 0.0

    def _fechar_dia(self) -> dict:
        """20h: fecha o caixa, guarda o resumo do dia, vira para o dia seguinte e baixa o que venceu."""
        fin = tools.financeiro_do_dia()
        dia = relogio.hoje()
        resumo = {"data": dia.strftime("%d/%m"), "vendas_rs": fin.get("vendas_rs", 0), "lucro_rs": fin.get("lucro_rs", 0),
                  "caixa_rs": fin.get("caixa_rs", 0), "perdas_rs": fin.get("perdas_rs", 0),
                  "n_vendas": vendas_de_hoje()["vendas"]}
        relogio.virar_dia(resumo)
        novo = relogio.hoje().isoformat()
        jogado = 0.0
        with conectar() as conn:
            vencidos = conn.execute(
                "SELECT p.nome, SUM(l.quantidade) q, p.preco_custo c FROM lotes l JOIN produtos p ON p.id=l.produto_id "
                "WHERE l.quantidade > 0 AND l.validade < ? GROUP BY p.id", (novo,)).fetchall()
        for v in vencidos:
            r = tools.registrar_saida(v["nome"], round(v["q"], 2), "perda", "venceu no fechamento (" + MOTIVO + ")")
            if r.get("ok"):
                jogado += v["q"] * v["c"]
        ev = self._registrar("fechamento", f"Dia {resumo['data']} fechado", resumo["n_vendas"], "vendas",
                             resumo["vendas_rs"])
        ev["vencido_rs"] = round(jogado, 2)
        return ev

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
        validade = (relogio.hoje() + timedelta(days=int(proprios[item["produto"]]))).strftime("%d/%m/%Y")
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
        agora = relogio.agora()
        with conectar() as conn:
            conn.execute("INSERT INTO despesas (data, hora, categoria, descricao, valor) VALUES (?,?,?,?,?)",
                         (relogio.hoje().isoformat(), agora.strftime("%H:%M:%S"), categoria, MOTIVO, valor))
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
    hoje = relogio.hoje().isoformat()
    with conectar() as conn:
        r = conn.execute("SELECT COUNT(*) n, COALESCE(SUM(valor),0) v, COALESCE(SUM(quantidade),0) q "
                         "FROM movimentacoes WHERE tipo='venda' AND data=?", (hoje,)).fetchone()
    return {"vendas": r["n"], "faturamento_rs": round(r["v"], 2), "itens": round(r["q"], 1)}


def financeiro_do_dia() -> dict:
    return tools.financeiro_do_dia()


# ------------------------------------------------------------------ interface
def _reais(v: float) -> str:
    txt = f"R$ {abs(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return ("−" + txt) if v < 0 else txt


_CARTOES_HTML = """
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Archivo:wdth,wght@62..125,700..900&family=Atkinson+Hyperlegible:wght@400;700&display=swap" rel="stylesheet">
<style>
  /* Etiquetas de gôndola (docs/DESIGN.md): valor grande, "R$" pequeno, cantos de etiqueta */
  :root { --tinta:#1D2B22; --tinta2:#4F5E54; --folha:#2F6B3B; --etiqueta:#F6D23C; --tomate:#C8402B;
          --linha:#D9DED6; --fundo:#FFFFFF; }
  html, body { margin:0; padding:0; background:transparent; color:var(--tinta);
               font-family:"Atkinson Hyperlegible", system-ui, sans-serif; }
  .grade { display:grid; grid-template-columns:repeat(6, minmax(0,1fr)); gap:10px; padding:2px; }
  .tag { position:relative; background:var(--fundo); border:1.5px solid var(--linha); border-radius:6px;
         padding:9px 12px 8px; min-width:0; }
  .tag.destaque { background:var(--etiqueta); border-color:#D9B51F; }
  .tag.destaque::before { content:""; position:absolute; right:10px; top:9px; width:9px; height:9px;
                          border-radius:50%; background:#fff; border:1.5px solid #C9A616; }  /* furo da etiqueta */
  .rotulo { font-size:13px; color:var(--tinta2); white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
  .tag.destaque .rotulo { color:var(--tinta); font-weight:700; }
  .valor { font-family:"Archivo", "Atkinson Hyperlegible", sans-serif; font-weight:800; font-stretch:85%;
           font-size:clamp(20px, 2.7vw, 34px); line-height:1.15; white-space:nowrap;
           font-variant-numeric:tabular-nums; letter-spacing:-.01em; }
  .valor .rs { font-size:.5em; font-weight:700; vertical-align:.55em; margin-right:2px; }
  .valor.negativo { color:var(--tomate); }
  .nota { font-size:12px; color:var(--tinta2); margin-top:1px; min-height:16px; }
  .delta { font-size:12px; font-weight:700; margin-top:1px; min-height:16px; opacity:0; transition:opacity .3s; }
  .delta.mostra { opacity:1; }
  .bom { color:var(--folha); } .ruim { color:var(--tomate); }
  .pisca-bom { color:var(--folha) !important; } .pisca-ruim { color:var(--tomate) !important; }
  @media (prefers-reduced-motion: reduce) { .delta { transition:none; } }
</style>
<div class="grade" id="g"></div>
<script>
const CARTOES = __DADOS__;
const reduz = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
const num = new Intl.NumberFormat('pt-BR', {minimumFractionDigits:2, maximumFractionDigits:2});
const valorHTML = (c, v) => {
  if (c.tipo !== 'reais') return Math.round(v).toLocaleString('pt-BR');
  const sinal = v < 0 ? '−' : '';
  return `${sinal}<span class="rs">R$</span>${num.format(Math.abs(v))}`;
};
const g = document.getElementById('g');
CARTOES.forEach((c, i) => {
  const d = c.para - c.de;
  let cls = '', txt = '';
  if (Math.abs(d) > 1e-9) {
    const melhorou = c.menor_melhor ? d < 0 : d > 0;
    cls = melhorou ? 'bom' : 'ruim';
    txt = (d > 0 ? '+' : '−') + (c.tipo === 'reais' ? 'R$ ' + num.format(Math.abs(d)) : Math.abs(Math.round(d)));
  }
  g.insertAdjacentHTML('beforeend',
    `<div class="tag ${c.destaque ? 'destaque' : ''}" role="group" aria-label="${c.rotulo}">
       <div class="rotulo">${c.rotulo}</div>
       <div class="valor" id="v${i}">${valorHTML(c, reduz ? c.para : c.de)}</div>
       ${c.nota ? `<div class="nota">${c.nota}</div>` : `<div class="delta ${cls}" id="d${i}">${txt || '&nbsp;'}</div>`}
     </div>`);
});
const t0 = performance.now(), DUR = reduz ? 0 : 1100;
const ease = t => 1 - Math.pow(1 - t, 3);
function quadro(agora) {
  const p = DUR ? Math.min(1, (agora - t0) / DUR) : 1;
  CARTOES.forEach((c, i) => {
    const el = document.getElementById('v' + i);
    el.innerHTML = valorHTML(c, c.de + (c.para - c.de) * ease(p));
    if (p < 1 && c.para !== c.de) el.classList.add((c.menor_melhor ? c.para < c.de : c.para > c.de) ? 'pisca-bom' : 'pisca-ruim');
    if (p >= 1) el.classList.remove('pisca-bom', 'pisca-ruim');
    el.classList.toggle('negativo', c.tipo === 'reais' && c.para < 0 && p >= 1 && !c.destaque);
  });
  if (p < 1) requestAnimationFrame(quadro);
}
requestAnimationFrame(quadro);
setTimeout(() => CARTOES.forEach((c, i) => { const d = document.getElementById('d' + i); if (d) d.classList.add('mostra'); }), 150);
</script>
"""


def _cartoes(cartoes: list[dict]) -> None:
    """Cartões com contagem animada do valor anterior até o atual (≈1 s)."""
    import json as _json

    import streamlit.components.v1 as components
    import streamlit as st
    tema = "light"  # o app usa tema claro fixo (.streamlit/config.toml) — melhor no projetor
    html = _CARTOES_HTML.replace("__DADOS__", _json.dumps(cartoes, ensure_ascii=False)).replace("__TEMA__", tema)
    components.html(html, height=112)


def intervalo() -> int | None:
    """Intervalo de atualização das abas de dados: 3 s com a loja ao vivo ligada; parado se desligada."""
    return 3 if simulador().ativo else None  # mesmo ritmo do painel do topo


def tabela_movimento():
    """Últimos lançamentos da simulação (para a aba Dashboard)."""
    import pandas as pd
    nomes = {"venda": "🛒 Venda (entra no caixa)", "chegada": "🚚 Compra recebida (sai do caixa)",
             "producao": "🍞 Produção (insumos saem do caixa)", "despesa": "💸 Despesa paga",
             "excesso": "🚨 Em excesso (vai sobrar)", "recebido": "📦 Pedido aprovado recebido (sai do caixa)",
             "perda": "🗑️ Perda (estragou)", "pedido": "📝 Pedido automático (rascunho)",
             "fechamento": "🔒 Fechamento do dia"}
    linhas = [{"hora": e["hora"],
               "lançamento": nomes.get(e.get("tipo"), e.get("tipo")) + (" · 🚨 EXCESSO" if e.get("excesso") else ""),
               "item": e["produto"],
               "qtd": f"{e['quantidade']:g} {e['unidade']}", "valor": _reais(e.get("valor", 0))}
              for e in simulador().eventos]
    return pd.DataFrame(linhas)


def render_alertas_excesso(maximo: int = 3) -> None:
    """O problema, mostrado na hora em que acontece: compra/produção acima do que a loja vende antes de vencer."""
    import streamlit as st
    for a in list(simulador().alertas)[:maximo]:
        u = a["unidade"]
        verbo = "Saíram do forno" if a["origem"] == "producao" else "Chegaram"
        st.warning(
            f"**{a['hora']}: {verbo.lower()} {a['quantidade']:g} {u} de {a['produto']}** — a loja vende ~{a['media_dia']:g} {u}/dia "
            f"e vence em {a['validade_dias']} dia(s): **~{a['sobra']:g} {u} vão para o lixo "
            f"({_reais(a['excesso_rs']).replace('$', chr(92) + '$')})**. "
            + (f"Com o Ciclo Zero, o {'plano de produção' if a['origem'] == 'producao' else 'pedido'} sugerido seria "
               f"**{a['ideal']:g} {u}**." if a["ideal"] > 0 else
               f"Com o Ciclo Zero, **não {'precisava produzir' if a['origem'] == 'producao' else 'precisava comprar'} "
               f"agora**: já havia estoque suficiente."), icon=":material/warning:")


def controles() -> None:
    """Botão liga/desliga na barra lateral."""
    import streamlit as st
    sim = simulador()
    ligado = st.toggle("Loja ao vivo", value=sim.ativo,
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

        fech = relogio.ultimo_fechamento()
        ontem = ""
        if fech:
            ontem = (f"<span class='cz-ontem'>Dia {fech['data']}: vendeu {_reais(fech['vendas_rs'])}, "
                     f"lucro {_reais(fech['lucro_rs'])}</span>")
        if sim.ativo:
            st.markdown("<div class='cz-relogio'><span class='cz-aovivo'><span class='cz-pulso'></span>Ao vivo</span>"
                        f"<span class='cz-hora'>{relogio.rotulo()}</span><small>fecha às {relogio.FECHA_H}h</small>"
                        + ("<small>(dia acelerado: ~6 min)</small>" if st.session_state.get("tecnico") else "")
                        + ontem + "</div>", unsafe_allow_html=True)
        else:
            st.markdown(f"<div class='cz-relogio'><span class='cz-hora'>{relogio.rotulo()}</span>{ontem}</div>",
                        unsafe_allow_html=True)
        if fech and st.session_state.get("_fech_visto") != fech["data"]:
            if "_fech_visto" in st.session_state:
                st.toast(f"Loja fechada. Dia {fech['data']}: vendeu {_reais(fech['vendas_rs'])}, "
                         f"lucro {_reais(fech['lucro_rs'])}. Começa um novo dia.", icon=":material/storefront:")
            st.session_state["_fech_visto"] = fech["data"]
        de = lambda k: anterior.get(k, atual[k])
        _cartoes([
            {"rotulo": "Vendas hoje", "tipo": "reais", "de": de("fat"), "para": atual["fat"]},
            {"rotulo": "Caixa do dia", "tipo": "reais", "de": de("caixa"), "para": atual["caixa"]},
            {"rotulo": "Lucro do dia", "tipo": "reais", "de": de("lucro"), "para": atual["lucro"]},
            {"rotulo": "Lotes em risco", "tipo": "int", "de": de("lotes"), "para": atual["lotes"],
             "menor_melhor": True},
            {"rotulo": "Vai para o lixo", "tipo": "reais", "de": de("perda"), "para": atual["perda"],
             "menor_melhor": True, "destaque": True},
            {"rotulo": "Jogado fora (mês)", "tipo": "reais", "de": perdas["total_perdas_rs"],
             "para": perdas["total_perdas_rs"], "nota": perdas["perdas_sobre_faturamento"].replace(".", ",") + " do faturamento"},
        ])
        if sim.ativo and sim.eventos and st.session_state.get("tecnico"):
            icone = {"venda": "🛒", "chegada": "🚚", "perda": "🗑️", "pedido": "📝", "producao": "🍞", "despesa": "💸", "fechamento": "🔒",
                     "recebido": "📦"}
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
