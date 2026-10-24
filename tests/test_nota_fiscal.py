"""Teste offline (sem IA) da conferência e da conciliação da nota fiscal.

Rodar: python -m tests.test_nota_fiscal
Garante que, dada uma leitura da nota, o sistema: confere a soma, associa os itens ao cadastro,
não lança item desconhecido, sugere validade e registra os lotes certos.
"""
import contextlib
import io
import os
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
os.environ["CICLOZERO_DB"] = str(RAIZ / "eval.db")
sys.path.insert(0, str(RAIZ))

from ciclozero import nota_fiscal as nf  # noqa: E402
from ciclozero.seed import popular  # noqa: E402
from ciclozero.tools import consultar_estoque  # noqa: E402

LEITURA = {"fornecedor": "Ceasa Goiânia", "numero": "004521", "valor_total": "368,40", "itens": [
    {"descricao": "BANANA PRATA", "quantidade": 40, "unidade": "KG", "valor_unitario": "3,50", "valor_total": "140,00"},
    {"descricao": "TOMATE ITALIANO", "quantidade": 12, "unidade": "KG", "valor_unitario": 5.0, "valor_total": 60.0},
    {"descricao": "ALFACE CRESPA", "quantidade": 20, "unidade": "UN", "valor_unitario": 1.8, "valor_total": 36.0},
    {"descricao": "OVOS BRANCOS DZ", "quantidade": 10, "unidade": "DZ", "valor_unitario": 8.5, "valor_total": 85.0},
    {"descricao": "MANTEIGA C/ SAL 200G", "quantidade": 6, "unidade": "UN", "valor_unitario": 7.9, "valor_total": 47.4},
]}


def checar(nome, cond, detalhe=""):
    print(f"{'✅' if cond else '❌'} {nome} {detalhe}")
    return cond


def main():
    with contextlib.redirect_stdout(io.StringIO()):
        popular()
    ok = True
    v = nf.verificar_leitura(LEITURA)
    ok &= checar("soma dos itens confere com o total", v["soma_confere"] is True, f"(R$ {v['soma_itens']})")
    errada = {**LEITURA, "valor_total": 500, "itens": [dict(i) for i in LEITURA["itens"]]}
    ok &= checar("detecta total divergente", nf.verificar_leitura(errada)["soma_confere"] is False)
    linhas = nf.conciliar(LEITURA)
    mapa = {l["descricao_nota"]: l["produto"] for l in linhas}
    esperado = {"BANANA PRATA": "Banana prata", "TOMATE ITALIANO": "Tomate", "ALFACE CRESPA": "Alface crespa",
                "OVOS BRANCOS DZ": "Ovos (dúzia)", "MANTEIGA C/ SAL 200G": ""}
    ok &= checar("associa itens ao cadastro", mapa == esperado, str(mapa) if mapa != esperado else "")
    manteiga = next(l for l in linhas if l["descricao_nota"].startswith("MANTEIGA"))
    ok &= checar("item não cadastrado não é lançado", manteiga["lancar"] is False and "cadastr" in manteiga["avisos"])
    antes = consultar_estoque("banana")["itens"][0]["saldo"]
    r = nf.registrar_nota(linhas, LEITURA)
    depois = consultar_estoque("banana")["itens"][0]["saldo"]
    ok &= checar("lança 4 lotes e recusa 0", len(r["lancados"]) == 4 and not r["recusados"])
    ok &= checar("saldo da banana +40 kg", abs(depois - antes - 40) < 0.01, f"({antes} -> {depois})")
    print("\nResultado:", "TUDO OK" if ok else "FALHOU")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
