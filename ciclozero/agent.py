"""Agente Ciclo Zero: loop de raciocínio + function calling com o Gemini.

Fluxo:  entrada (usuário ou rotina automática)
        -> Gemini decide quais ferramentas chamar (pode encadear várias)
        -> cada chamada é validada, executada e registrada em log_agente
        -> Gemini responde usando SOMENTE os números devolvidos pelas ferramentas.

Guardrails:
- limite de passos por pergunta (evita loop infinito e gasto de cota)
- só ferramentas da lista FERRAMENTAS podem ser executadas
- erros de ferramenta voltam ao modelo como dado, para ele se corrigir
- compras saem como rascunho; o humano aprova na interface
"""
from __future__ import annotations

import json
import os
import time
import uuid
from datetime import date

from dotenv import load_dotenv
from google import genai
from google.genai import types

from .db import conectar, criar_tabelas
import re

from .tools import FERRAMENTAS, data_br

load_dotenv()

MODELO = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
MAX_PASSOS = 8
# nível de raciocínio do modelo: "minimal", "low", "medium" ou "high" (menos = mais rápido)
NIVEL_RACIOCINIO = os.getenv("GEMINI_THINKING", "low")

INSTRUCOES = """Você é o Ciclo Zero, agente de estoque de um pequeno comércio de alimentos (padaria/mercadinho).
Missão: reduzir o desperdício de alimentos sem deixar faltar produto.

Regras:
1. Todo número que você citar (quantidade, data, R$, %) deve vir de uma ferramenta. Nunca estime nem invente.
2. Antes de responder sobre estoque, validade, compras ou perdas, chame a ferramenta adequada.
3. Se uma ferramenta devolver "erro", leia a mensagem: corrija (ex.: use o nome sugerido) ou pergunte ao usuário.
4. Pedidos de compra: chame calcular_reposicao antes de criar_pedido_compra. Pedidos ficam como rascunho até o dono aprovar; deixe isso claro.
5. Para lotes em risco, priorize: promoção (vender) > doação (banco de alimentos/ONG) > descarte.
6. Se o pedido estiver fora do seu escopo (não for sobre o estoque do comércio), diga educadamente que só ajuda com estoque e desperdício.
7. Datas: sempre escreva no formato brasileiro DD/MM/AAAA. Ao passar validade para ferramentas, use DD/MM/AAAA.
8. Valores em reais no formato R$ 1.234,56.
9. Responda em português do Brasil, curto e prático, como quem fala com o dono do comércio. Use listas quando houver vários itens.
Hoje é {hoje} ({dia_semana})."""

ROTINA_DIARIA = (
    "Execute a rotina diária de abertura da loja: (1) analise o risco de desperdício dos próximos 5 dias, "
    "(2) monte o plano de ação por lote (promoção com preço, doação ou descarte), "
    "(3) calcule a reposição e crie rascunhos de pedido por fornecedor apenas para o que for realmente necessário, "
    "(4) termine com um resumo: R$ em risco, R$ que o plano evita perder e pedidos aguardando aprovação."
)

_FERR_POR_NOME = {f.__name__: f for f in FERRAMENTAS}
_DIAS = ["segunda-feira", "terça-feira", "quarta-feira", "quinta-feira", "sexta-feira", "sábado", "domingo"]
_ISO = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _datas_br(obj):
    """Converte toda data ISO do resultado para DD/MM/AAAA antes de mostrar ao modelo."""
    if isinstance(obj, dict):
        return {k: _datas_br(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_datas_br(v) for v in obj]
    if isinstance(obj, str) and _ISO.match(obj):
        return data_br(obj)
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


class AgenteCicloZero:
    def __init__(self, api_key: str | None = None, modelo: str = MODELO):
        criar_tabelas()
        chave = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not chave:
            raise RuntimeError("Defina GEMINI_API_KEY no arquivo .env")
        self.client = genai.Client(api_key=chave, http_options=types.HttpOptions(timeout=60_000))  # 60 s por chamada
        self.modelo = modelo
        self.historico: list[types.Content] = []
        self.ao_passo = None  # callback opcional para mostrar o progresso (terminal/Streamlit)
        self.sessao = uuid.uuid4().hex[:8]
        self.config = types.GenerateContentConfig(
            system_instruction=INSTRUCOES.format(hoje=date.today().strftime("%d/%m/%Y"),
                                                  dia_semana=_DIAS[date.today().weekday()]),
            tools=FERRAMENTAS,
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
            temperature=0.2,
            thinking_config=types.ThinkingConfig(thinking_level=NIVEL_RACIOCINIO) if NIVEL_RACIOCINIO else None,
        )

    def _gerar(self, contents):
        # tenta de novo em caso de limite de cota/instabilidade do plano gratuito
        for tentativa in range(4):
            try:
                return self.client.models.generate_content(model=self.modelo, contents=contents, config=self.config)
            except Exception as e:
                msg = str(e)
                # modelo que não aceita nível de raciocínio: tira a opção e tenta de novo
                if "thinking" in msg.lower() and self.config.thinking_config is not None:
                    self.config.thinking_config = None
                    self._avisar("ℹ️ modelo não aceita nível de raciocínio; seguindo sem ele")
                    continue
                # erro de configuração (modelo inexistente, chave inválida): não adianta tentar de novo
                if tentativa == 3 or any(c in msg for c in ("404", "401", "403", "API key", "INVALID_ARGUMENT")):
                    raise
                self._avisar(f"⏳ API instável ({msg[:80]}...), tentando de novo")
                time.sleep(4 * (tentativa + 1))

    def _avisar(self, texto: str) -> None:
        if self.ao_passo:
            self.ao_passo(texto)

    def perguntar(self, mensagem: str) -> dict:
        """Processa uma mensagem e devolve {'resposta': str, 'passos': [chamadas de ferramenta]}."""
        passos: list[dict] = []
        _log(self.sessao, 0, "usuario", mensagem)
        self.historico.append(types.Content(role="user", parts=[types.Part(text=mensagem)]))
        for passo in range(1, MAX_PASSOS + 1):
            self._avisar(f"🧠 passo {passo}: pensando...")
            try:
                resp = self._gerar(self.historico)
            except Exception as e:
                _log(self.sessao, passo, "erro", str(e))
                return {"resposta": f"⚠️ Não consegui falar com o modelo agora ({e}). Tente de novo em instantes.",
                        "passos": passos}
            conteudo = resp.candidates[0].content if resp.candidates else None
            if conteudo is None:
                return {"resposta": "⚠️ O modelo não retornou resposta.", "passos": passos}
            self.historico.append(conteudo)
            chamadas = resp.function_calls or []
            if not chamadas:
                texto = resp.text or ""
                _log(self.sessao, passo, "resposta", texto)
                return {"resposta": texto, "passos": passos}
            partes = []
            for fc in chamadas:
                args = dict(fc.args or {})
                self._avisar(f"🔧 {fc.name}({args})")
                resultado = _datas_br(_executar(fc.name, args))
                passos.append({"ferramenta": fc.name, "argumentos": args, "resultado": resultado})
                _log(self.sessao, passo, "ferramenta", {"nome": fc.name, "args": args, "resultado": resultado})
                partes.append(types.Part.from_function_response(name=fc.name, response={"result": resultado}))
            self.historico.append(types.Content(role="user", parts=partes))
        _log(self.sessao, MAX_PASSOS, "erro", "limite de passos atingido")
        return {"resposta": "⚠️ Atingi o limite de passos para esta pergunta. Pode reformular de forma mais específica?",
                "passos": passos}

    def rotina_diaria(self) -> dict:
        """Modo autônomo: o agente faz a checagem completa sem o usuário perguntar nada."""
        return self.perguntar(ROTINA_DIARIA)


if __name__ == "__main__":
    agente = AgenteCicloZero()
    agente.ao_passo = lambda t: print("   " + t, flush=True)
    print(f"Modelo: {agente.modelo}")
    print("Ciclo Zero — digite 'rotina' para a rotina diária ou 'sair'.")
    while True:
        msg = input("\nVocê: ").strip()
        if msg.lower() in ("sair", "exit"):
            break
        r = agente.rotina_diaria() if msg.lower() == "rotina" else agente.perguntar(msg)
        print("\nCiclo Zero:", r["resposta"])
