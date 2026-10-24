"""Entrada de mercadoria por FOTO da nota fiscal (multimodal).

Fluxo (ponta a ponta, com o humano só confirmando):
  1. ler_nota(foto)      -> modelo com visão extrai fornecedor, número, data, total e itens (JSON estruturado)
  2. verificar_leitura() -> confere a extração: soma dos itens x total da nota, quantidades e valores válidos
  3. conciliar()         -> associa cada item ao produto cadastrado, sugere validade (validade padrão do produto)
                            e sinaliza custo muito diferente do cadastro ou item desconhecido
  4. (tela) o dono confere/edita a tabela e confirma
  5. registrar_nota()    -> lança os lotes pelas MESMAS ferramentas do agente (com todas as validações)

Guardrails: nada entra no estoque sem confirmação; item sem produto correspondente não é lançado
(o dono cadastra antes); a leitura informa a própria confiabilidade (soma confere ou não).
"""
from __future__ import annotations

import base64
import json
import os
import re
import time
import unicodedata
from datetime import date, timedelta

from dotenv import load_dotenv

from .db import conectar

load_dotenv()

MODELOS_VISAO_GEMINI = [m.strip() for m in os.getenv(
    "GEMINI_VISION_MODELS", "gemini-flash-latest,gemini-3.8-flash,gemini-flash-lite-latest").split(",") if m.strip()]
MODELOS_VISAO_GROQ = [m.strip() for m in os.getenv(
    "GROQ_VISION_MODELS",
    "qwen/qwen3.8-27b,meta-llama/llama-4-scout-17b-16e-instruct").split(",") if m.strip()]

PROMPT_LEITURA = """Você recebe a foto de uma nota fiscal ou cupom de COMPRA de mercadorias de um pequeno comércio de alimentos.
Extraia os dados EXATAMENTE como aparecem na imagem. Não invente nada: se um campo não estiver legível, use null.
Responda SOMENTE com JSON neste formato:
{"fornecedor": str|null, "numero": str|null, "data_emissao": "DD/MM/AAAA"|null, "valor_total": number|null,
 "itens": [{"descricao": str, "quantidade": number, "unidade": str, "valor_unitario": number|null, "valor_total": number|null}]}
Números com ponto decimal (ex.: 1234.56). Unidade como está na nota (UN, KG, CX, PCT...)."""


class LeituraFalhou(Exception):
    pass


# ---------------------------------------------------------------- 1. leitura
def _extrair_json(texto: str) -> dict:
    texto = (texto or "").strip()
    m = re.search(r"\{.*\}", texto, flags=re.S)
    if not m:
        raise LeituraFalhou("o modelo não devolveu JSON")
    return json.loads(m.group(0))


def _ler_gemini(imagem: bytes, mime: str) -> tuple[dict, str]:
    from google import genai
    from google.genai import types
    chave = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not chave:
        raise LeituraFalhou("sem GEMINI_API_KEY")
    client = genai.Client(api_key=chave, http_options=types.HttpOptions(timeout=60_000))
    ultimo = ""
    for modelo in MODELOS_VISAO_GEMINI:
        try:
            resp = client.models.generate_content(
                model=modelo,
                contents=[types.Part.from_bytes(data=imagem, mime_type=mime), PROMPT_LEITURA],
                config=types.GenerateContentConfig(temperature=0, response_mime_type="application/json"))
            return _extrair_json(resp.text), f"gemini:{modelo}"
        except Exception as e:  # tenta o próximo modelo
            ultimo = str(e)[:150]
    raise LeituraFalhou(f"Gemini: {ultimo}")


def _ler_groq(imagem: bytes, mime: str) -> tuple[dict, str]:
    from openai import OpenAI
    chave = os.getenv("GROQ_API_KEY")
    if not chave:
        raise LeituraFalhou("sem GROQ_API_KEY")
    client = OpenAI(api_key=chave, base_url="https://api.groq.com/openai/v1", timeout=60, max_retries=1)
    url = f"data:{mime};base64,{base64.b64encode(imagem).decode()}"
    ultimo = ""
    for modelo in MODELOS_VISAO_GROQ:
        try:
            resp = client.chat.completions.create(
                model=modelo, temperature=0, response_format={"type": "json_object"},
                messages=[{"role": "user", "content": [{"type": "text", "text": PROMPT_LEITURA},
                                                       {"type": "image_url", "image_url": {"url": url}}]}])
            return _extrair_json(resp.choices[0].message.content), f"groq:{modelo}"
        except Exception as e:
            ultimo = str(e)[:150]
    raise LeituraFalhou(f"Groq: {ultimo}")


def ler_nota(imagem: bytes, mime: str = "image/jpeg") -> dict:
    """Lê a foto da nota com um modelo de visão (Gemini; se falhar, Groq). Devolve dados + verificação."""
    t0, erros = time.time(), []
    for leitor in (_ler_gemini, _ler_groq):
        try:
            dados, modelo = leitor(imagem, mime)
            break
        except (LeituraFalhou, json.JSONDecodeError) as e:
            erros.append(str(e))
    else:
        raise LeituraFalhou("Não consegui ler a nota: " + " | ".join(erros))
    dados.setdefault("itens", [])
    dados["modelo"] = modelo
    dados["segundos"] = round(time.time() - t0, 1)
    dados["verificacao"] = verificar_leitura(dados)
    _log_leitura(dados)
    return dados


def _log_leitura(dados: dict) -> None:
    try:
        with conectar() as conn:
            conn.execute("INSERT INTO log_agente (sessao, passo, tipo, conteudo) VALUES (?,?,?,?)",
                         ("nota", 0, "nota_fiscal", json.dumps(
                             {"modelo": dados.get("modelo"), "segundos": dados.get("segundos"),
                              "itens": len(dados.get("itens", [])), "verificacao": dados.get("verificacao")},
                             ensure_ascii=False)))
    except Exception:
        pass


# ------------------------------------------------------- 2. verificação da leitura
def _num(v) -> float | None:
    if v is None or v == "":
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip().replace("R$", "").strip()
    if "," in s:
        s = s.replace(".", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def verificar_leitura(dados: dict) -> dict:
    """Mede a qualidade da extração sem precisar de gabarito: as contas da própria nota fecham?"""
    problemas, soma = [], 0.0
    for i, item in enumerate(dados.get("itens", []), 1):
        q, vu, vt = _num(item.get("quantidade")), _num(item.get("valor_unitario")), _num(item.get("valor_total"))
        item["quantidade"], item["valor_unitario"], item["valor_total"] = q, vu, vt
        if not q or q <= 0:
            problemas.append(f"item {i}: quantidade ilegível")
        if vt is None and q and vu is not None:
            item["valor_total"] = vt = round(q * vu, 2)
        if q and vu is not None and vt is not None and abs(q * vu - vt) > max(0.05, 0.02 * vt):
            problemas.append(f"item {i}: quantidade × unitário ({q} × {vu}) não bate com o total {vt}")
        soma += vt or 0
    total = _num(dados.get("valor_total"))
    dados["valor_total"] = total
    soma = round(soma, 2)
    if total is None:
        problemas.append("total da nota ilegível")
        confere = None
    else:
        confere = abs(soma - total) <= max(0.10, 0.01 * total)
        if not confere:
            problemas.append(f"soma dos itens (R$ {soma:.2f}) diferente do total da nota (R$ {total:.2f})")
    if not dados.get("itens"):
        problemas.append("nenhum item encontrado")
    return {"soma_itens": soma, "total_nota": total, "soma_confere": confere,
            "confiavel": bool(dados.get("itens")) and confere is True and not problemas, "problemas": problemas}


# ----------------------------------------------------------- 3. conciliação
_PALAVRAS_VAZIAS = {"de", "da", "do", "com", "e", "a", "o", "un", "und", "kg", "cx", "pct", "pc", "lt", "l", "g",
                    "tipo", "uht", "integral", "natural"}


_SINONIMOS = {"mussarela": "mucarela", "muzzarela": "mucarela", "mozarela": "mucarela", "mozzarella": "mucarela",
              "dz": "duzia", "duz": "duzia", "nat": "natural", "coz": "cozido", "frances": "frances"}


def _tokens(txt: str) -> set[str]:
    txt = unicodedata.normalize("NFKD", txt or "").encode("ascii", "ignore").decode().lower()
    txt = re.sub(r"[^a-z0-9 ]", " ", txt)
    return {_SINONIMOS.get(t, t) for t in txt.split() if len(t) > 1}


def _pontuar(descricao: str, nome: str) -> float:
    """Quanto do nome do produto aparece na descrição da nota (0 a 1). Palavras-chave pesam mais."""
    nome_t, desc_t = _tokens(nome), _tokens(descricao)
    if not nome_t:
        return 0.0
    chave = nome_t - _PALAVRAS_VAZIAS or nome_t
    acerto_chave = len(chave & desc_t) / len(chave)
    acerto_total = len(nome_t & desc_t) / len(nome_t)
    # aceita prefixos (ex.: "presunt" ~ "presunto", "banan" ~ "banana")
    if acerto_chave < 1:
        parciais = sum(1 for c in chave if any(d.startswith(c[:5]) or c.startswith(d[:5]) for d in desc_t if len(d) >= 4))
        acerto_chave = max(acerto_chave, parciais / len(chave) * 0.9)
    return round(0.7 * acerto_chave + 0.3 * acerto_total, 2)


def _chave_apelido(descricao: str) -> str:
    """Descrição normalizada: a mesma linha de nota sempre gera a mesma chave."""
    txt = unicodedata.normalize("NFKD", descricao or "").encode("ascii", "ignore").decode().lower()
    return " ".join(re.sub(r"[^a-z0-9 ]", " ", txt).split())


def aprendidos() -> int:
    """Quantas descrições de nota esta loja já ensinou ao sistema (ativo próprio da loja)."""
    with conectar() as conn:
        return conn.execute("SELECT COUNT(*) FROM apelidos").fetchone()[0]


def _aprender(conn, descricao: str, produto: str, fornecedor: str | None) -> None:
    pid = conn.execute("SELECT id FROM produtos WHERE nome=?", (produto,)).fetchone()
    chave = _chave_apelido(descricao)
    if not pid or not chave:
        return
    conn.execute(
        """INSERT INTO apelidos (descricao, produto_id, fornecedor, vezes) VALUES (?,?,?,1)
           ON CONFLICT(descricao) DO UPDATE SET produto_id=excluded.produto_id, vezes=apelidos.vezes+1,
           fornecedor=COALESCE(excluded.fornecedor, apelidos.fornecedor), atualizado_em=datetime('now','localtime')""",
        (chave, pid[0], fornecedor))


def conciliar(dados: dict) -> list[dict]:
    """Uma linha por item da nota, já com o produto sugerido, quantidade, validade e custo.
    Primeiro procura no que a loja já ensinou (apelidos); se não houver, usa a semelhança de palavras."""
    with conectar() as conn:
        produtos = [dict(r) for r in conn.execute("SELECT * FROM produtos")]
        por_id = {p["id"]: p for p in produtos}
        memoria = {r["descricao"]: (por_id.get(r["produto_id"]), r["vezes"])
                   for r in conn.execute("SELECT descricao, produto_id, vezes FROM apelidos")}
    hoje = date.today()
    linhas = []
    for item in dados.get("itens", []):
        desc = str(item.get("descricao") or "")
        aprendido = memoria.get(_chave_apelido(desc))
        if aprendido and aprendido[0]:
            prod, score, origem = aprendido[0], 1.0, f"aprendido ({aprendido[1]}x)"
        else:
            ranking = sorted(((_pontuar(desc, p["nome"]), p) for p in produtos), key=lambda x: -x[0])
            score, prod = ranking[0] if ranking else (0, None)
            origem = "semelhança"
            if score < 0.5:
                prod, origem = None, "—"
        qtd, vu = item.get("quantidade"), item.get("valor_unitario")
        avisos = []
        if prod is None:
            avisos.append("produto não cadastrado: cadastre antes de lançar")
        else:
            un_nota = str(item.get("unidade") or "").strip().upper()
            if prod["unidade"] == "kg" and un_nota and un_nota not in ("KG", "KGS", "QUILO"):
                avisos.append(f"nota em {un_nota}, cadastro em kg: confira a quantidade")
            if prod["unidade"] == "un" and un_nota in ("KG",):
                avisos.append("nota em KG, cadastro em unidade: confira a quantidade")
            if vu and prod["preco_custo"] and abs(vu - prod["preco_custo"]) / prod["preco_custo"] > 0.2:
                avisos.append(f"custo R$ {vu:.2f} difere do cadastro (R$ {prod['preco_custo']:.2f})")
        validade = hoje + timedelta(days=int((prod or {}).get("validade_padrao_dias") or 7))
        linhas.append({
            "lancar": prod is not None and bool(qtd) and qtd > 0,
            "descricao_nota": desc,
            "produto": prod["nome"] if prod else "",
            "quantidade": qtd,
            "unidade": prod["unidade"] if prod else str(item.get("unidade") or ""),
            "validade": validade.strftime("%d/%m/%Y"),
            "custo_unitario": vu,
            "confianca": score,
            "origem": origem,
            "avisos": "; ".join(avisos),
        })
    return linhas


# --------------------------------------------------------------- 5. registro
def registrar_nota(linhas: list[dict], dados: dict | None = None) -> dict:
    """Lança no estoque as linhas confirmadas, usando as mesmas ferramentas (e validações) do agente."""
    from .tools import registrar_entrada
    lancados, recusados = [], []
    for ln in linhas:
        if not ln.get("lancar"):
            continue
        r = registrar_entrada(ln.get("produto") or "", float(ln.get("quantidade") or 0), str(ln.get("validade") or ""))
        (lancados if r.get("ok") else recusados).append({"produto": ln.get("produto"), **r})
        if r.get("ok") and ln.get("descricao_nota"):
            # o dono confirmou (ou corrigiu) a associação: a loja ensina o sistema
            with conectar() as conn:
                _aprender(conn, ln["descricao_nota"], r["produto"], (dados or {}).get("fornecedor"))
    try:
        with conectar() as conn:
            conn.execute("INSERT INTO log_agente (sessao, passo, tipo, conteudo) VALUES (?,?,?,?)",
                         ("nota", 1, "nota_registrada", json.dumps(
                             {"fornecedor": (dados or {}).get("fornecedor"), "numero": (dados or {}).get("numero"),
                              "lancados": len(lancados), "recusados": len(recusados)}, ensure_ascii=False)))
    except Exception:
        pass
    return {"lancados": lancados, "recusados": recusados}


def mensagem_para_agente(dados: dict, resultado: dict) -> str:
    """Texto que a tela envia ao agente depois do registro, para ele avaliar o risco da compra."""
    itens = ", ".join(f"{l['quantidade']} {l.get('produto')}" for l in resultado["lancados"])
    return (f"Recebi a nota {dados.get('numero') or ''} do fornecedor {dados.get('fornecedor') or 'não identificado'} "
            f"e os lotes já foram registrados: {itens}. Sem registrar mais nada, analise o risco de desperdício dos "
            f"próximos 5 dias e diga em até 4 linhas se algum desses produtos vai sobrar e o que fazer.")
