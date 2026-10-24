"""Agente Ciclo Zero: loop de raciocínio + function calling.

Fluxo:  entrada (usuário ou rotina automática)
        -> o LLM decide quais ferramentas chamar (pode encadear várias)
        -> cada chamada é validada, executada e registrada em log_agente
        -> o LLM responde usando SOMENTE os números devolvidos pelas ferramentas.

Provedores (com troca automática se um cair):
- Gemini (Google) — vários modelos em sequência (GEMINI_MODEL + GEMINI_MODELOS_RESERVA)
- Groq (gratuito, rápido, API compatível com OpenAI) — GROQ_MODELS
A ordem vem de PROVEDORES no .env (padrão: "gemini,groq"); só entra quem tiver chave.

Guardrails:
- limite de passos por pergunta (evita loop infinito e gasto de cota)
- só ferramentas da lista FERRAMENTAS podem ser executadas
- erros de ferramenta voltam ao modelo como dado, para ele se corrigir
- se o provedor cair DEPOIS de o agente já ter alterado o estoque, não repete a pergunta em outro
  provedor (evitaria lançar a mesma entrada duas vezes); avisa o usuário
- compras saem como rascunho; o humano aprova na interface
"""
from __future__ import annotations

import inspect
import json
import os
import re
import time
import uuid
from datetime import date

from dotenv import load_dotenv

from .db import conectar, criar_tabelas
from .tools import FERRAMENTAS, data_br

load_dotenv()

PROVEDORES = [p.strip().lower() for p in os.getenv("PROVEDORES", "groq,gemini").split(",") if p.strip()]
MODELO = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
MODELOS_RESERVA = [m.strip() for m in os.getenv(
    "GEMINI_MODELOS_RESERVA", "gemini-flash-latest,gemini-flash-lite-latest").split(",") if m.strip()]
NIVEL_RACIOCINIO = os.getenv("GEMINI_THINKING", "low")  # minimal | low | medium | high
GROQ_MODELS = [m.strip() for m in os.getenv(
    "GROQ_MODELS", "openai/gpt-oss-120b,openai/gpt-oss-20b,qwen/qwen3.8-27b").split(",") if m.strip()]
GROQ_RACIOCINIO = os.getenv("GROQ_REASONING", "low")  # low | medium | high (só modelos gpt-oss)
MAX_PASSOS = 8
FERRAMENTAS_QUE_ALTERAM = {"cadastrar_produto", "registrar_entrada", "registrar_saida", "criar_pedido_compra", "criar_pedidos_sugeridos"}

INSTRUCOES = """Você é o Ciclo Zero, agente de estoque de um pequeno comércio de alimentos (padaria/mercadinho).
Missão: reduzir o desperdício de alimentos sem deixar faltar produto.

Regras:
1. Todo número que você citar (quantidade, data, R$, %) deve vir de uma ferramenta. Nunca estime nem invente.
   Para explicar um cálculo, copie o campo "conta" da ferramenta. Nunca refaça contas, nunca arredonde valores
   intermediários e nunca cite prazo, média ou período que não esteja no resultado da ferramenta.
   Não descreva como as ferramentas funcionam por dentro (parâmetros, valores padrão, opções) além do que está
   escrito no resultado delas. Se perguntarem de onde vem uma regra, cite o campo da ferramenta que a explica
   (ex.: "regra_cobertura"); se ele não existir, diga que essa é uma regra do sistema.
   O cálculo cobre só o prazo de entrega + a cobertura. Se o usuário pedir outro período (ex.: um mês inteiro),
   avise que a sugestão cobre apenas esse intervalo; não a apresente como resposta para o período pedido.
2. Antes de responder sobre estoque, validade, compras, perdas, vendas, caixa ou lucro, chame a ferramenta adequada
   (dinheiro do dia: resumo_do_dia). Os dados mudam em TEMPO REAL (vendas acontecendo agora): a cada pergunta,
   consulte de novo — nunca reaproveite números de respostas anteriores da conversa.
3. Se uma ferramenta devolver "erro", leia a mensagem: corrija (ex.: use o nome sugerido) ou pergunte ao usuário.
   "Chegou", "recebi", "entregaram" = ENTRADA. Só registre saída (venda, perda, doação) quando o usuário disser que o produto saiu.
   Mercadoria que chega já vencida não entra no estoque e NÃO é perda da loja: recuse e oriente devolver ao fornecedor.
   Nunca use outra operação para contornar uma recusa (ex.: entrada vencida recusada NÃO vira perda nem doação).
   Produto que não existe: ofereça cadastrar e peça os dados que faltam (categoria, unidade, custo, venda, estoque mínimo, fornecedor, prazo). Nunca invente preço ou fornecedor.
4. Pedidos de compra: para repor o que o cálculo sugere, use criar_pedidos_sugeridos (todos os fornecedores de uma vez). Use criar_pedido_compra só quando o usuário pedir algo específico, depois de calcular_reposicao. Pedidos ficam como rascunho até o dono aprovar; deixe isso claro.
5. Para lotes em risco, priorize: promoção (vender) > doação (banco de alimentos/ONG) > descarte.
   Produto VENCIDO nunca vai para promoção nem doação: só descarte (e a ferramenta informa a base legal).
   Perguntas sobre lei, norma, regra, multa ou "posso doar/vender": chame consultar_normas e cite a norma e o
   artigo que ela devolver, com o link. NUNCA cite lei, artigo, valor de multa ou prazo que não venha da
   ferramenta. Se ela não encontrar, diga claramente que não sabe e sugira a vigilância sanitária ou um advogado.
6. Se o pedido estiver fora do seu escopo (não for sobre o estoque do comércio), diga educadamente que só ajuda com estoque e desperdício, sem responder a pergunta.
7. Datas: sempre escreva no formato brasileiro DD/MM/AAAA. Ao passar validade para ferramentas, use DD/MM/AAAA.
8. Valores em reais no formato R$ 1.234,56.
9. Responda em português do Brasil, curto e prático, como quem fala com o dono do comércio. Use listas quando houver vários itens.
Hoje é {hoje} ({dia_semana})."""

ROTINA_DIARIA = (
    "Execute a rotina diária de abertura da loja, sem pedir confirmação, no MENOR número de passos:\n"
    "Passo A: chame JUNTAS, na mesma resposta, analisar_risco_desperdicio(dias=5) e criar_pedidos_sugeridos().\n"
    "Passo B: responda com (1) o plano de ação por lote em lista curta (produto, ação, preço promocional ou quantidade "
    "para doar), (2) os pedidos criados (número, fornecedor, valor) e (3) um resumo usando EXATAMENTE os campos de "
    "'resumo' da análise: perda total se nada for feito, receita recuperada com as promoções e custo dos itens "
    "doados. Não some nem recalcule valores."
)

_FERR_POR_NOME = {f.__name__: f for f in FERRAMENTAS}
_DIAS = ["segunda-feira", "terça-feira", "quarta-feira", "quinta-feira", "sexta-feira", "sábado", "domingo"]
_ISO = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class ProvedorIndisponivel(Exception):
    """O provedor de LLM não respondeu (cota, sobrecarga, chave, rede)."""


# ------------------------------------------------------------------ utilitários
def _datas_br(obj):
    """Converte toda data ISO do resultado para DD/MM/AAAA antes de mostrar ao modelo."""
    if isinstance(obj, dict):
        return {k: _datas_br(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_datas_br(v) for v in obj]
    if isinstance(obj, str) and _ISO.match(obj):
        return data_br(obj)
    return obj


_RE_CHEGADA = re.compile(r"\b(cheg\w*|receb\w*|entreg\w*)\b", re.I)
_RE_SAIDA = re.compile(r"\b(vend\w*|perd\w*|estrag\w*|venc(eu|eram)|doa\w*|descart\w*|jog\w*|baix\w*|sa(i|iu|íram|iram))\b", re.I)


def _mensagem_so_de_chegada(texto: str) -> bool:
    """True se o usuário só falou de mercadoria chegando (sem venda/perda/doação)."""
    return bool(_RE_CHEGADA.search(texto or "")) and not _RE_SAIDA.search(texto or "")


_CAMPOS_SO_TELA = {"lote", "media_vendas_dia", "abaixo_do_custo", "lotes_consumidos", "estoque_minimo", "categoria"}


_CITACAO = re.compile(r"\s*【[^】]*】")


_MILHAR_ESPACO = re.compile(r"(R\$\s?\d{1,3})(?:[ \u00a0\u202f](\d{3}))+(,\d{2})")


def _padronizar_reais(texto: str) -> str:
    """'R$ 1 284,80' (alguns modelos usam espaço como milhar) -> 'R$ 1.284,80'."""
    def troca(m):
        bruto = m.group(0)
        prefixo, resto = bruto[:2], bruto[2:].strip()
        digitos = re.sub(r"[ \u00a0\u202f]", ".", resto.split(",")[0])
        return f"{prefixo} {digitos},{resto.split(',')[1]}"
    return _MILHAR_ESPACO.sub(troca, texto)


def _limpar_resposta(texto: str) -> str:
    """Remove marcas de citação internas (ex.: 【calcular_reposicao】) e padroniza valores em R$."""
    return _padronizar_reais(_CITACAO.sub("", texto or "").strip())


def _enxuto(obj):
    """Versão compacta do resultado para o modelo: menos tokens = resposta mais rápida."""
    if isinstance(obj, dict):
        return {k: _enxuto(v) for k, v in obj.items()
                if k not in _CAMPOS_SO_TELA and v is not None and v is not False and v != []}
    if isinstance(obj, list):
        return [_enxuto(v) for v in obj]
    if isinstance(obj, float):
        return round(obj, 2)
    return obj


def _log(sessao: str, passo: int, tipo: str, conteudo) -> None:
    if not isinstance(conteudo, str):
        conteudo = json.dumps(conteudo, ensure_ascii=False, default=str)
    with conectar() as conn:
        conn.execute("INSERT INTO log_agente (sessao, passo, tipo, conteudo) VALUES (?,?,?,?)",
                     (sessao, passo, tipo, conteudo[:4000]))


def _executar(nome: str, args: dict) -> dict:
    func = _FERR_POR_NOME.get(nome)
    if func is None:
        return {"erro": f"Ferramenta '{nome}' não existe. Disponíveis: {list(_FERR_POR_NOME)}"}
    try:
        return func(**args)
    except TypeError as e:
        return {"erro": f"Argumentos inválidos para {nome}: {e}"}
    except Exception as e:  # nunca derruba o agente
        return {"erro": f"Falha ao executar {nome}: {e}"}


def _schema_openai(func) -> dict:
    """Gera o JSON Schema de uma ferramenta (formato OpenAI/Groq) a partir da assinatura e docstring."""
    doc = inspect.getdoc(func) or ""
    descricao = doc.split("\n\nArgs:")[0].strip()
    desc_args = dict(re.findall(r"^\s{4}(\w+): (.+)$", doc, flags=re.M))
    tipos = {"str": "string", "float": "number", "int": "integer", "bool": "boolean"}
    props, obrig = {}, []
    for nome, p in inspect.signature(func).parameters.items():
        anot = str(p.annotation)
        if anot.startswith("list["):
            item = tipos.get(anot[5:-1], "string")
            sch = {"type": "array", "items": {"type": item}}
        else:
            sch = {"type": tipos.get(anot, "string")}
        if nome in desc_args:
            sch["description"] = desc_args[nome]
        props[nome] = sch
        if p.default is inspect.Parameter.empty:
            obrig.append(nome)
    return {"type": "function", "function": {"name": func.__name__, "description": descricao,
                                             "parameters": {"type": "object", "properties": props, "required": obrig}}}


# ------------------------------------------------------------------- provedores
class _Gemini:
    nome = "gemini"
    registrar = staticmethod(lambda d: None)  # substituído pelo agente (log de cada chamada)

    def __init__(self, chave: str, avisar):
        from google import genai
        from google.genai import types
        self.types = types
        self.client = genai.Client(api_key=chave, http_options=types.HttpOptions(timeout=60_000))
        self.modelo = MODELO
        self.avisar = avisar
        self.config = types.GenerateContentConfig(
            tools=FERRAMENTAS,
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
            temperature=0.2,
            thinking_config=types.ThinkingConfig(thinking_level=NIVEL_RACIOCINIO) if NIVEL_RACIOCINIO else None,
        )

    def _ajustar_raciocinio(self):
        """Modelos 3.x usam 'nível' de raciocínio; 2.x usam 'orçamento'. Alterna entre os dois."""
        t, tc = self.types, self.config.thinking_config
        if tc is None:
            return False
        if tc.thinking_level is not None:
            orc = {"minimal": 0, "low": 512, "medium": 2048}.get(NIVEL_RACIOCINIO, -1)
            self.config.thinking_config = t.ThinkingConfig(thinking_budget=orc)
        elif tc.thinking_budget is not None and NIVEL_RACIOCINIO:
            self.config.thinking_config = t.ThinkingConfig(thinking_level=NIVEL_RACIOCINIO)
        return True

    def _gerar(self, contents):
        candidatos = [self.modelo] + [m for m in MODELOS_RESERVA if m != self.modelo]
        ultimo = ""
        for modelo in candidatos:
            ajustes = 0
            tentativa = 0
            max_tent = 2 if modelo == self.modelo else 1  # reservas: uma tentativa só, para trocar rápido
            while tentativa < max_tent:
                t0 = time.time()
                try:
                    resp = self.client.models.generate_content(model=modelo, contents=contents, config=self.config)
                    self.registrar({"provedor": "gemini", "modelo": modelo, "ms": int((time.time() - t0) * 1000), "ok": True})
                    if modelo != self.modelo:
                        self.avisar(f"🔁 Gemini: usando {modelo}")
                        self.modelo = modelo
                    return resp
                except Exception as e:
                    ultimo = str(e)
                    self.registrar({"provedor": "gemini", "modelo": modelo, "ms": int((time.time() - t0) * 1000),
                                    "ok": False, "erro": ultimo[:120]})
                    if "thinking" in ultimo.lower() and ajustes < 2 and self._ajustar_raciocinio():
                        ajustes += 1
                        continue  # mesma tentativa, com a configuração de raciocínio trocada
                    if any(c in ultimo for c in ("401", "403", "API key")):
                        raise ProvedorIndisponivel(f"chave do Gemini inválida: {ultimo[:120]}")
                    if any(c in ultimo for c in ("404", "INVALID_ARGUMENT")):
                        self.avisar(f"⏭️ {modelo} não disponível")
                        break
                    self.avisar(f"⏳ {modelo} indisponível ({ultimo[:60]}...)")
                    tentativa += 1
                    time.sleep(3 * tentativa)
        raise ProvedorIndisponivel(ultimo[:200])

    def rodar(self, sistema, conversa, mensagem, chamar, avisar):
        t = self.types
        self.config.system_instruction = sistema
        contents = [t.Content(role="user" if r == "user" else "model", parts=[t.Part(text=x)]) for r, x in conversa]
        contents.append(t.Content(role="user", parts=[t.Part(text=mensagem)]))
        for passo in range(1, MAX_PASSOS + 1):
            avisar(f"🧠 passo {passo}: pensando ({self.modelo})...")
            resp = self._gerar(contents)
            conteudo = resp.candidates[0].content if resp.candidates else None
            if conteudo is None:
                raise ProvedorIndisponivel("resposta vazia do Gemini")
            contents.append(conteudo)
            chamadas = resp.function_calls or []
            if not chamadas:
                return resp.text or ""
            partes = []
            for fc in chamadas:
                resultado = chamar(fc.name, dict(fc.args or {}), passo)
                partes.append(t.Part.from_function_response(name=fc.name, response={"result": resultado}))
            contents.append(t.Content(role="user", parts=partes))
        return None


class _Groq:
    nome = "groq"
    registrar = staticmethod(lambda d: None)

    def __init__(self, chave: str, avisar):
        from openai import OpenAI
        self.client = OpenAI(api_key=chave, base_url="https://api.groq.com/openai/v1", timeout=60, max_retries=1)
        self.modelo = GROQ_MODELS[0]
        self.avisar = avisar
        self.tools = [_schema_openai(f) for f in FERRAMENTAS]

    def _gerar(self, messages):
        candidatos = [self.modelo] + [m for m in GROQ_MODELS if m != self.modelo]
        ultimo = ""
        for modelo in candidatos:
            for tentativa in range(2 if modelo == self.modelo else 1):
                t0 = time.time()
                try:
                    extra = {"reasoning_effort": GROQ_RACIOCINIO} if "gpt-oss" in modelo and GROQ_RACIOCINIO else {}
                    resp = self.client.chat.completions.create(model=modelo, messages=messages, tools=self.tools,
                                                               tool_choice="auto", temperature=0.2, **extra)
                    self.registrar({"provedor": "groq", "modelo": modelo, "ms": int((time.time() - t0) * 1000), "ok": True})
                    if modelo != self.modelo:
                        self.avisar(f"🔁 Groq: usando {modelo}")
                        self.modelo = modelo
                    return resp
                except Exception as e:
                    ultimo = str(e)
                    self.registrar({"provedor": "groq", "modelo": modelo, "ms": int((time.time() - t0) * 1000),
                                    "ok": False, "erro": ultimo[:120]})
                    if any(c in ultimo for c in ("401", "403", "invalid_api_key")):
                        raise ProvedorIndisponivel(f"chave do Groq inválida: {ultimo[:120]}")
                    if any(c in ultimo for c in ("404", "model_not_found", "decommissioned", "tool_use_failed")):
                        self.avisar(f"⏭️ {modelo}: {ultimo[:60]}")
                        break
                    self.avisar(f"⏳ {modelo} indisponível ({ultimo[:60]}...)")
                    time.sleep(3 * (tentativa + 1))
        raise ProvedorIndisponivel(ultimo[:200])

    def rodar(self, sistema, conversa, mensagem, chamar, avisar):
        messages = [{"role": "system", "content": sistema}]
        messages += [{"role": "user" if r == "user" else "assistant", "content": x} for r, x in conversa]
        messages.append({"role": "user", "content": mensagem})
        for passo in range(1, MAX_PASSOS + 1):
            avisar(f"🧠 passo {passo}: pensando ({self.modelo})...")
            msg = self._gerar(messages).choices[0].message
            if not msg.tool_calls:
                return msg.content or ""
            messages.append({"role": "assistant", "content": msg.content or "",
                             "tool_calls": [{"id": tc.id, "type": "function",
                                             "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                                            for tc in msg.tool_calls]})
            for tc in msg.tool_calls:
                try:
                    args = json.loads(tc.function.arguments or "{}")
                except json.JSONDecodeError:
                    resultado = {"erro": "argumentos em JSON inválido; tente de novo"}
                else:
                    resultado = chamar(tc.function.name, args, passo)
                messages.append({"role": "tool", "tool_call_id": tc.id,
                                 "content": json.dumps(resultado, ensure_ascii=False, default=str, separators=(",", ":"))})
        return None


# ----------------------------------------------------------------------- agente
class AgenteCicloZero:
    def __init__(self, api_key: str | None = None, groq_key: str | None = None):
        criar_tabelas()
        self.ao_passo = None  # callback opcional para mostrar o progresso (terminal/Streamlit)
        self.sessao = uuid.uuid4().hex[:8]
        self.conversa: list[tuple[str, str]] = []  # turnos já concluídos (texto), comum a todos os provedores
        chaves = {"gemini": api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"),
                  "groq": groq_key or os.getenv("GROQ_API_KEY")}
        classes = {"gemini": _Gemini, "groq": _Groq}
        self.provedores = []
        for nome in PROVEDORES:
            if chaves.get(nome) and nome in classes:
                try:
                    self.provedores.append(classes[nome](chaves[nome], self._avisar))
                except ImportError as e:
                    print(f"[aviso] provedor {nome} sem biblioteca instalada ({e}); rode pip install -r requirements.txt")
        for prov in self.provedores:
            prov.registrar = lambda d: _log(self.sessao, 0, "llm", d)
        if not self.provedores:
            raise RuntimeError("Nenhum provedor configurado: defina GEMINI_API_KEY e/ou GROQ_API_KEY no arquivo .env")

    @property
    def modelo(self) -> str:
        return " → ".join(f"{p.nome}:{p.modelo}" for p in self.provedores)

    def _avisar(self, texto: str) -> None:
        if self.ao_passo:
            self.ao_passo(texto)

    def _sistema(self) -> str:
        from .relogio import hoje as _hoje_loja
        hoje = _hoje_loja()
        return INSTRUCOES.format(hoje=hoje.strftime("%d/%m/%Y"), dia_semana=_DIAS[hoje.weekday()])

    def perguntar(self, mensagem: str) -> dict:
        """Processa uma mensagem e devolve {'resposta': str, 'passos': [chamadas de ferramenta]}."""
        passos: list[dict] = []
        _log(self.sessao, 0, "usuario", mensagem)
        t0 = time.time()
        modelos_ini = {p.nome: p.modelo for p in self.provedores}

        def fim(resultado: dict, prov=None, trocou_provedor=False) -> dict:
            _log(self.sessao, len(passos), "fim", {
                "segundos": round(time.time() - t0, 1), "passos": len(passos),
                "provedor": prov.nome if prov else None, "modelo": prov.modelo if prov else None,
                "usou_reserva": trocou_provedor or any(p.modelo != modelos_ini[p.nome] for p in self.provedores),
                "erro": bool(resultado.get("erro_sistema"))})
            return resultado

        escritas_recusadas: set[str] = set()

        def chamar(nome, args, passo):
            self._avisar(f"🔧 {nome}({args})")
            # guardrail: se uma alteração de estoque foi recusada, não deixa "contornar" com OUTRA alteração
            # (ex.: entrada vencida recusada -> registrar como perda tirando do estoque bom)
            outras = escritas_recusadas - {nome}
            if nome == "registrar_saida" and _mensagem_so_de_chegada(mensagem):
                resultado = {"erro": "Bloqueado: o usuário informou CHEGADA de mercadoria, não saída. Não registre "
                                     "venda/perda/doação. Se a mercadoria chegou vencida, ela não entra no estoque: "
                                     "oriente devolver ao fornecedor."}
            elif nome == "registrar_entrada" and "validade" in escritas_recusadas:
                resultado = {"erro": "Bloqueado: a validade informada foi recusada. Não invente outra data; "
                                     "pergunte ao usuário a validade correta."}
            elif nome in FERRAMENTAS_QUE_ALTERAM and outras - {"validade"}:
                resultado = {"erro": f"Bloqueado: a operação '{sorted(outras - {'validade'})[0]}' foi recusada nesta conversa. "
                                     "Não faça outra alteração no estoque para contornar; explique ao usuário e "
                                     "pergunte como ele quer seguir."}
            else:
                resultado = _datas_br(_executar(nome, args))
                if nome in FERRAMENTAS_QUE_ALTERAM and isinstance(resultado, dict) and "erro" in resultado:
                    escritas_recusadas.add(nome)
                    if nome == "registrar_entrada" and "alidade" in resultado["erro"]:
                        escritas_recusadas.add("validade")
            passos.append({"ferramenta": nome, "argumentos": args, "resultado": resultado})
            _log(self.sessao, passo, "ferramenta", {"nome": nome, "args": args, "resultado": resultado})
            return _enxuto(resultado)

        erro = ""
        for i, prov in enumerate(self.provedores):
            if i > 0:
                self._avisar(f"🔁 trocando para o provedor {prov.nome}")
            try:
                texto = prov.rodar(self._sistema(), self.conversa[-10:], mensagem, chamar, self._avisar)
            except ProvedorIndisponivel as e:
                erro = f"{prov.nome}: {e}"
                _log(self.sessao, len(passos), "erro", erro)
                if any(p["ferramenta"] in FERRAMENTAS_QUE_ALTERAM for p in passos):
                    return fim({"resposta": "⚠️ O modelo caiu no meio da tarefa, depois de já ter alterado o estoque. "
                                        "Confira a aba Estoque antes de repetir o pedido.", "passos": passos,
                            "erro_sistema": True})
                continue
            if texto is None:
                _log(self.sessao, MAX_PASSOS, "erro", "limite de passos atingido")
                return fim({"resposta": "⚠️ Atingi o limite de passos para esta pergunta. Pode reformular de forma mais específica?",
                            "passos": passos, "erro_sistema": True}, prov, i > 0)
            texto = _limpar_resposta(texto)
            _log(self.sessao, len(passos) + 1, "resposta", f"[{prov.nome}:{prov.modelo}] {texto}")
            self.conversa += [("user", mensagem), ("assistant", texto)]
            return fim({"resposta": texto, "passos": passos, "modelo": f"{prov.nome}:{prov.modelo}"}, prov, i > 0)
        return fim({"resposta": f"⚠️ Nenhum modelo de IA respondeu agora ({erro}). Tente de novo em instantes.",
                    "passos": passos, "erro_sistema": True})

    def rotina_diaria(self) -> dict:
        """Modo autônomo: o agente faz a checagem completa sem o usuário perguntar nada."""
        return self.perguntar(ROTINA_DIARIA)


if __name__ == "__main__":
    agente = AgenteCicloZero()
    agente.ao_passo = lambda t: print("   " + t, flush=True)
    print(f"Provedores: {agente.modelo}")
    print("Ciclo Zero — digite 'rotina' para a rotina diária ou 'sair'.")
    while True:
        msg = input("\nVocê: ").strip()
        if msg.lower() in ("sair", "exit"):
            break
        r = agente.rotina_diaria() if msg.lower() == "rotina" else agente.perguntar(msg)
        print("\nCiclo Zero:", r["resposta"])
