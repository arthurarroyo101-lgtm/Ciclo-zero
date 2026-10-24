"""Observabilidade (LLMOps): métricas do agente a partir da tabela log_agente.

Responde à pergunta da banca: "como vocês investigariam uma resposta ruim e qual métrica indicaria degradação?"
- cada chamada ao LLM é registrada com provedor, modelo, tempo e sucesso/erro (tipo 'llm')
- cada pergunta termina com um registro 'fim' com tempo total, nº de passos e se houve erro
- cada ferramenta registra argumentos e resultado (tipo 'ferramenta')
Sinais de degradação: latência p95 subindo, taxa de erro do LLM subindo, mais trocas para modelo reserva,
mais erros de ferramenta por pergunta (modelo chamando com argumentos ruins).
"""
from __future__ import annotations

import json
from statistics import mean

from .db import conectar


def _linhas(tipo: str, limite: int = 2000) -> list[dict]:
    with conectar() as conn:
        rows = conn.execute("SELECT conteudo, criado_em FROM log_agente WHERE tipo=? ORDER BY id DESC LIMIT ?",
                            (tipo, limite)).fetchall()
    out = []
    for r in rows:
        try:
            d = json.loads(r["conteudo"])
        except (json.JSONDecodeError, TypeError):
            continue
        if isinstance(d, dict):
            d["criado_em"] = r["criado_em"]
            out.append(d)
    return out


def _p95(valores: list[float]) -> float:
    if not valores:
        return 0.0
    v = sorted(valores)
    return v[min(len(v) - 1, int(round(0.95 * (len(v) - 1))))]


def metricas_agente() -> dict:
    """Resumo de saúde do agente (últimos registros)."""
    llm = _linhas("llm")
    fins = _linhas("fim")
    ferr = _linhas("ferramenta")
    ok_llm = [c for c in llm if c.get("ok")]
    tempos_perg = [f["segundos"] for f in fins if "segundos" in f]
    por_modelo: dict[str, dict] = {}
    for c in llm:
        chave = f"{c.get('provedor')}:{c.get('modelo')}"
        m = por_modelo.setdefault(chave, {"modelo": chave, "chamadas": 0, "erros": 0, "_ms": []})
        m["chamadas"] += 1
        if c.get("ok"):
            m["_ms"].append(c.get("ms", 0))
        else:
            m["erros"] += 1
    tabela_modelos = [{"modelo": m["modelo"], "chamadas": m["chamadas"], "erros": m["erros"],
                       "taxa_erro": f"{m['erros'] / m['chamadas']:.0%}",
                       "latencia_media_s": round(mean(m["_ms"]) / 1000, 2) if m["_ms"] else None}
                      for m in por_modelo.values()]
    erros_ferr = sum(1 for f in ferr if isinstance(f.get("resultado"), dict) and "erro" in f["resultado"])
    return {
        "perguntas": len(fins),
        "latencia_media_pergunta_s": round(mean(tempos_perg), 1) if tempos_perg else 0,
        "latencia_p95_pergunta_s": round(_p95(tempos_perg), 1),
        "perguntas_com_erro": sum(1 for f in fins if f.get("erro")),
        "chamadas_llm": len(llm),
        "taxa_erro_llm": f"{(len(llm) - len(ok_llm)) / len(llm):.0%}" if llm else "0%",
        "trocas_para_reserva": sum(1 for f in fins if f.get("usou_reserva")),
        "chamadas_ferramenta": len(ferr),
        "erros_de_ferramenta": erros_ferr,
        "por_modelo": tabela_modelos,
    }
