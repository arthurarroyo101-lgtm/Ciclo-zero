"""Relógio da loja: data e hora "de negócio" usadas por todo o sistema.

Sem simulação, é o relógio real. Com a "Loja ao vivo", o dia anda acelerado (abre às 7h, fecha às 20h);
ao fechar, o dia vira: os contadores diários zeram sozinhos (tudo filtra pela data de hoje()), o dia que
passou entra no histórico para análise e os lotes que venceram são baixados como perda.
O estado fica no banco (tabela config), então sobrevive a recarregar a página. Recriar os dados zera tudo.
"""
from __future__ import annotations

import json
from datetime import date, datetime, time, timedelta

from .db import conectar

ABRE_H = 7
FECHA_H = 20


def _ler(chave: str, padrao: str | None = None) -> str | None:
    with conectar() as conn:
        r = conn.execute("SELECT valor FROM config WHERE chave=?", (chave,)).fetchone()
    return r["valor"] if r else padrao


def _gravar(chave: str, valor) -> None:
    with conectar() as conn:
        conn.execute("INSERT INTO config (chave, valor) VALUES (?,?) "
                     "ON CONFLICT(chave) DO UPDATE SET valor=excluded.valor", (chave, str(valor)))


def dias_avancados() -> int:
    return int(_ler("dias_avancados", "0") or 0)


def hoje() -> date:
    return date.today() + timedelta(days=dias_avancados())


def _minutos() -> int | None:
    v = _ler("minutos_do_dia")
    return int(v) if v is not None else None


def hora() -> time:
    m = _minutos()
    if m is None:
        return datetime.now().time().replace(microsecond=0)
    return time(m // 60, m % 60)


def agora() -> datetime:
    return datetime.combine(hoje(), hora())


def avancar(minutos: int) -> bool:
    """Anda o relógio da simulação. Devolve True quando chegou a hora de fechar a loja."""
    m = _minutos()
    if m is None:  # primeira vez: começa na hora real (dentro do expediente)
        agora_real = datetime.now()
        m = min(max(agora_real.hour * 60 + agora_real.minute, ABRE_H * 60), FECHA_H * 60 - 30)
    m += minutos
    _gravar("minutos_do_dia", min(m, FECHA_H * 60))
    return m >= FECHA_H * 60


def virar_dia(resumo: dict) -> None:
    """Fecha o dia: guarda o resumo para o painel e começa o dia seguinte às 7h."""
    _gravar("ultimo_fechamento", json.dumps(resumo, ensure_ascii=False))
    _gravar("dias_avancados", dias_avancados() + 1)
    _gravar("minutos_do_dia", ABRE_H * 60)


def ultimo_fechamento() -> dict | None:
    v = _ler("ultimo_fechamento")
    return json.loads(v) if v else None


_DIAS = ["segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo"]


def rotulo() -> str:
    """Ex.: 'sábado, 24/10, 14:35'."""
    d, h = hoje(), hora()
    return f"{_DIAS[d.weekday()]}, {d.strftime('%d/%m')}, {h.strftime('%H:%M')}"
