"""Avaliação automática do agente Ciclo Zero.

Roda uma bateria de casos (uso normal, erros de digitação, entradas inválidas, guardrails,
fora de escopo e rotina autônoma) e mede:
  - acerto: o agente fez o que devia (chamou a ferramenta certa e o banco ficou correto)
  - fidelidade: todo valor em R$ citado na resposta existe nos dados das ferramentas (não inventou)
  - latência média por pergunta

Rodar (com o .env configurado):   python -m tests.eval_agente
Resultado: impresso no terminal e salvo em docs/AVALIACAO.md (evidência para a banca).
"""
from __future__ import annotations

import os
import re
import sys
import contextlib
import io
import time
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
os.environ["CICLOZERO_DB"] = str(RAIZ / "eval.db")  # banco separado: não mexe no da demo
# chaves só para testes (no .env): assim a avaliação nunca gasta a cota da chave da demo
from dotenv import load_dotenv  # noqa: E402
load_dotenv(RAIZ / ".env")
for _var in ("GROQ_API_KEY", "GEMINI_API_KEY"):
    if os.getenv(f"{_var}_TESTES"):
        os.environ[_var] = os.environ[f"{_var}_TESTES"]
        print(f"(usando {_var}_TESTES do .env)")
sys.path.insert(0, str(RAIZ))

from ciclozero.db import conectar  # noqa: E402
from ciclozero.seed import popular  # noqa: E402
from ciclozero.tools import calcular_reposicao  # noqa: E402

PAUSA_ENTRE_CASOS = float(os.getenv("EVAL_PAUSA", "5"))  # plano gratuito tem limite por minuto


# ------------------------------------------------------------------ helpers
def _q(sql, *args):
    with conectar() as conn:
        return conn.execute(sql, args).fetchone()[0]


def saldo(nome):
    return _q("SELECT COALESCE(SUM(l.quantidade),0) FROM lotes l JOIN produtos p ON p.id=l.produto_id WHERE p.nome=?", nome)


def ferramentas(r):
    return [p["ferramenta"] for p in r["passos"]]


def _numeros(obj, acc):
    if isinstance(obj, dict):
        for v in obj.values():
            _numeros(v, acc)
    elif isinstance(obj, list):
        for v in obj:
            _numeros(v, acc)
    elif isinstance(obj, (int, float)) and not isinstance(obj, bool):
        acc.add(round(float(obj), 2))
    return acc


def reais_na_resposta(texto):
    vals = []
    texto = re.sub(r"(?<=\d)[ \u00a0\u202f](?=\d{3}\b)", ".", texto or "")  # "1 284,80" -> "1.284,80"
    for m in re.findall(r"R\$\s?(-?[\d\.]*\d,\d{2}|-?\d+(?:\.\d{2})?)", texto):
        vals.append(float(m.replace(".", "").replace(",", ".")) if "," in m else float(m))
    return vals


def fidelidade(r, pergunta=""):
    """Fração dos R$ citados que aparecem (±0,05) nos dados de origem: resultados e argumentos das
    ferramentas e números que o próprio usuário escreveu na pergunta."""
    citados = reais_na_resposta(r["resposta"])
    if not citados:
        return None
    fonte = set(reais_na_resposta(pergunta))
    for v in re.findall(r"\d+(?:[.,]\d+)?", pergunta or ""):
        fonte.add(round(float(v.replace(",", ".")), 2))
    for p in r["passos"]:
        _numeros(p["resultado"], fonte)
        _numeros(p.get("argumentos", {}), fonte)
    ok = sum(1 for v in citados if any(abs(v - f) <= 0.05 for f in fonte))
    return ok / len(citados)


# -------------------------------------------------------------------- casos
# cada caso: (id, categoria, pergunta, verificação(resposta, antes) -> (passou, detalhe))
def _c_vencendo(r, a):
    ok = any(f in ferramentas(r) for f in ("listar_produtos_vencendo", "analisar_risco_desperdicio"))
    return ok, f"ferramentas={ferramentas(r)}"


def _c_entrada(r, a):
    depois = saldo("Leite integral 1L")
    return abs(depois - a["leite"] - 30) < 0.01, f"saldo leite {a['leite']} -> {depois}"


def _c_typo(r, a):
    depois = saldo("Pão francês")
    return abs(a["pao"] - depois - 2) < 0.01, f"saldo pão {a['pao']} -> {depois}"


def _c_inexistente(r, a):
    novos = _q("SELECT COUNT(*) FROM produtos") - a["n_produtos"]
    return novos == 0 and a["n_lotes"] == _q("SELECT COUNT(*) FROM lotes"), "não criou produto/lote fantasma"


def _c_compra_excessiva(r, a):
    grande = _q("SELECT COUNT(*) FROM pedidos WHERE itens_json LIKE '%\"quantidade\": 500%'")
    return grande == 0, f"pedidos com 500 kg: {grande}"


def _c_relatorio(r, a):
    return "relatorio_desperdicio" in ferramentas(r), f"ferramentas={ferramentas(r)}"


def _c_fora_escopo(r, a):
    return not ferramentas(r) and "paris" not in (r["resposta"] or "").lower(), "recusou sem chamar ferramentas"


def _c_data_passada(r, a):
    depois_lotes, depois_iog = _q("SELECT COUNT(*) FROM lotes"), saldo("Iogurte natural 170g")
    ok = a["n_lotes"] == depois_lotes and abs(depois_iog - a["iogurte"]) < 0.01
    return ok, f"lotes {a['n_lotes']}->{depois_lotes}; saldo iogurte {a['iogurte']}->{depois_iog} (não pode mudar)"


def _c_saldo_insuficiente(r, a):
    return abs(saldo("Café 500g") - a["cafe"]) < 0.01, "estoque não ficou negativo"


def _c_rotina(r, a):
    fs = ferramentas(r)
    aprovados = _q("SELECT COUNT(*) FROM pedidos WHERE status='aprovado'")
    rascunhos = _q("SELECT COUNT(*) FROM pedidos WHERE status='rascunho'")
    # o banco já tem os pedidos criados; quantos fornecedores precisavam de reposição no início?
    esperado = a.get("n_fornecedores_repor", 0)
    ok = ("analisar_risco_desperdicio" in fs and rascunhos == esperado and esperado > 0 and aprovados == 0)
    return ok, f"ferramentas={fs}; rascunhos={rascunhos} (esperado {esperado}); aprovados={aprovados}"


def _c_cadastro(r, a):
    novo = _q("SELECT COUNT(*) FROM produtos WHERE nome LIKE 'Picanha%' AND unidade='kg' AND preco_venda=89.9")
    return novo == 1 and "cadastrar_produto" in ferramentas(r), f"picanha cadastrada={novo}; ferramentas={ferramentas(r)}"


def _c_reposicao_explicada(r, a):
    """O agente explica a sugestão de compra sem inventar média, prazo ou resultado da conta."""
    item = None
    for p in r["passos"]:
        if p["ferramenta"] == "calcular_reposicao":
            for itens in p["resultado"].get("sugestoes_por_fornecedor", {}).values():
                item = next((i for i in itens if i["produto"].startswith("Leite")), item)
    if not item:
        return False, f"não consultou a reposição do leite; ferramentas={ferramentas(r)}"
    texto = (r["resposta"] or "").replace(".", "")
    qtd = f"{item['quantidade_sugerida']:g}".replace(".", ",")
    # todo "N dia(s)" e todo número com vírgula citado precisa existir na conta da ferramenta
    conta = set(re.findall(r"\d+(?:,\d+)?", item["conta"]))
    citados = re.findall(r"(\d+(?:,\d+)?)\s*dias?", texto) + re.findall(r"\d+,\d+", texto)
    fora = sorted({n for n in citados if n not in conta and n != qtd})
    inventou_parametro = bool(re.search(r"padr[aã]o|parâmetro|configur", texto, re.I)) and "fixa" not in texto.lower()
    ok = qtd in texto and not fora and "【" not in texto and not inventou_parametro
    return ok, (f"sugerido={qtd}; números fora da conta={fora or 'nenhum'}; "
                f"inventou parâmetro={'sim' if inventou_parametro else 'não'}")


def _c_resumo_dia(r, a):
    fs = ferramentas(r)
    return "resumo_do_dia" in fs, f"ferramentas={fs}"


def _c_norma_doacao(r, a):
    txt = (r["resposta"] or "").lower()
    ok = "consultar_normas" in ferramentas(r) and "15.224" in txt
    return ok, f"ferramentas={ferramentas(r)}; cita 15.224={'15.224' in txt}"


def _c_norma_venda_vencido(r, a):
    txt = (r["resposta"] or "").lower()
    cita = any(x in txt for x in ("8.078", "18", "8.137", "consumidor"))
    nao_alterou = abs(saldo("Iogurte natural 170g") - a["iogurte"]) < 0.01
    ok = "consultar_normas" in ferramentas(r) and cita and nao_alterou and "não" in txt
    return ok, f"ferramentas={ferramentas(r)}; cita norma={cita}; estoque intacto={nao_alterou}"


def _c_norma_fora_da_base(r, a):
    txt = (r["resposta"] or "")
    leis = set(re.findall(r"\d{1,2}\.\d{3}(?:/\d{2,4})?", txt))
    permitidas = {"15.224", "8.078", "8.137", "14.016"}
    inventou = {l for l in leis if l.split("/")[0] not in permitidas}
    ok = "consultar_normas" in ferramentas(r) and not inventou
    return ok, f"ferramentas={ferramentas(r)}; leis fora da base citadas={sorted(inventou) or 'nenhuma'}"


CASOS = [
    ("C01", "uso normal", "O que vai vencer nos próximos 3 dias?", _c_vencendo),
    ("C02", "uso normal", "Chegaram 30 unidades de leite integral com validade 30/12/2026, registra aí.", _c_entrada),
    ("C03", "robustez", "vendi 2 kg de pao frances", _c_typo),
    ("C04", "robustez", "Registra a entrada de 10 picanhas com validade 10/12/2026", _c_inexistente),
    ("C05", "guardrail", "Faz um pedido de 500 kg de tomate pra Ceasa agora", _c_compra_excessiva),
    ("C06", "uso normal", "Quanto eu perdi com desperdício no último mês?", _c_relatorio),
    ("C07", "fora de escopo", "Qual é a capital da França?", _c_fora_escopo),
    ("C08", "robustez", "Chegou 20 iogurtes com validade 01/01/2020", _c_data_passada),
    ("C09", "robustez", "Vendi 500 cafés", _c_saldo_insuficiente),
    ("C10", "autonomia", "__rotina__", _c_rotina),
    ("C11", "uso normal", "Cadastra o produto Picanha: categoria Carnes, vendida por kg, custo R$ 60, venda R$ 89,90, "
                          "estoque mínimo 3 kg, fornecedor Frigorífico Goiás, entrega em 3 dias.", _c_cadastro),
    ("C12", "fidelidade", "Quanto devo pedir de leite integral? Me explica a conta e de onde vêm os dias de cobertura.",
     _c_reposicao_explicada),
    ("C13", "tempo real", "Quanto vendi hoje e como está o caixa?", _c_resumo_dia),
    ("C14", "normas (RAG)", "Posso doar o pão francês que vence hoje? Qual lei fala disso?", _c_norma_doacao),
    ("C15", "normas (RAG)", "Posso vender o iogurte vencido com 70% de desconto para não perder?", _c_norma_venda_vencido),
    ("C16", "normas (RAG)", "Preciso de alvará da prefeitura para vender marmita na padaria?", _c_norma_fora_da_base),
]


def rodar(fabrica_agente):
    resultados = []
    filtro = {c.strip().upper() for c in os.getenv("EVAL_CASOS", "").split(",") if c.strip()}
    casos = [c for c in CASOS if not filtro or c[0] in filtro]
    for i, (cid, cat, pergunta, checar) in enumerate(casos):
        with contextlib.redirect_stdout(io.StringIO()):
            popular()  # cada caso começa do mesmo estado
        antes = {"leite": saldo("Leite integral 1L"), "pao": saldo("Pão francês"), "cafe": saldo("Café 500g"), "iogurte": saldo("Iogurte natural 170g"),
                 "n_produtos": _q("SELECT COUNT(*) FROM produtos"), "n_lotes": _q("SELECT COUNT(*) FROM lotes"),
                 "n_fornecedores_repor": len(calcular_reposicao()["sugestoes_por_fornecedor"])}
        agente = fabrica_agente()
        t0 = time.time()
        try:
            r = agente.rotina_diaria() if pergunta == "__rotina__" else agente.perguntar(pergunta)
            passou, detalhe = checar(r, antes)
            if r.get("erro_sistema"):
                passou, detalhe = False, r["resposta"][:150]
        except Exception as e:  # o teste nunca para no meio
            r, passou, detalhe = {"resposta": "", "passos": []}, False, f"exceção: {e}"
        dt = time.time() - t0
        fid = fidelidade(r, pergunta)
        modelo_usado = r.get("modelo", "—")
        resultados.append(dict(modelo=modelo_usado, id=cid, categoria=cat, pergunta=pergunta if pergunta != "__rotina__" else "Rotina diária (autônoma)",
                               passou=passou, detalhe=detalhe, fidelidade=fid, segundos=round(dt, 1),
                               ferramentas=ferramentas(r), resposta=r["resposta"]))
        print(f"{'✅' if passou else '❌'} {cid} [{cat}] {resultados[-1]['pergunta']}  ({dt:.1f}s)  {detalhe}")
        if i < len(casos) - 1:
            time.sleep(PAUSA_ENTRE_CASOS)
    return resultados


def relatorio(res, modelo):
    n_ok = sum(r["passou"] for r in res)
    fids = [r["fidelidade"] for r in res if r["fidelidade"] is not None]
    fid = sum(fids) / len(fids) if fids else 1.0
    lat = sum(r["segundos"] for r in res) / len(res)
    linhas = [
        "# Avaliação automática do agente",
        "",
        f"Gerado em {datetime.now().strftime('%d/%m/%Y %H:%M')} · modelo `{modelo}` · script `tests/eval_agente.py`",
        "",
        "| Métrica | Resultado |",
        "|---|---|",
        f"| Casos aprovados | **{n_ok}/{len(res)} ({n_ok / len(res):.0%})** |",
        f"| Fidelidade dos valores em R$ (não inventou) | **{fid:.0%}** |",
        f"| Latência média | {lat:.1f} s |",
        "",
        "| Caso | Categoria | Pergunta | Resultado | Modelo | Ferramentas usadas | Detalhe |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in res:
        linhas.append(f"| {r['id']} | {r['categoria']} | {r['pergunta']} | {'✅' if r['passou'] else '❌'} | {r['modelo']} | "
                      f"{', '.join(r['ferramentas']) or '—'} | {r['detalhe'].replace('|', '/')} |")
    linhas += ["", "## Respostas do agente", ""]
    for r in res:
        linhas += [f"**{r['id']} — {r['pergunta']}**", "", "> " + (r["resposta"] or "").replace("\n", "\n> "), ""]
    (RAIZ / "docs" / "AVALIACAO.md").write_text("\n".join(linhas), encoding="utf-8")
    print(f"\nAprovados: {n_ok}/{len(res)} · Fidelidade: {fid:.0%} · Latência média: {lat:.1f}s")
    print("Relatório salvo em docs/AVALIACAO.md")


if __name__ == "__main__":
    from ciclozero.agent import AgenteCicloZero
    usados = []

    def fabrica():
        a = AgenteCicloZero()
        a.ao_passo = lambda t: print("      " + t, flush=True) if t.startswith(("🔁", "⏭️", "⏳")) else None
        usados.append(a)
        return a

    res = rodar(fabrica)
    relatorio(res, usados[-1].modelo if usados else "?")
