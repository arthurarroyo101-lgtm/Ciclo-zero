"""Base normativa do Ciclo Zero (RAG) — consulta a legislação sobre validade, venda e doação de alimentos.

Regra de ouro: a base só contém trechos CONFERIDOS no texto oficial (Planalto), com lei, artigo e link.
O agente responde perguntas legais SÓ com o que vem daqui; se não houver trecho relevante, diz que não sabe.
Busca por palavras-chave (determinística, sem custo, sem depender de API) — suficiente para uma base pequena.

Conferido em 24/10/2026. Não é aconselhamento jurídico.
"""
from __future__ import annotations

import re
import unicodedata

CONSULTADO_EM = "24/10/2026"
URL_15224 = "https://www.planalto.gov.br/CCIVIL_03/_Ato2023-2026/2025/Lei/L15224.htm"
URL_CDC = "https://www.planalto.gov.br/ccivil_03/leis/l8078compilado.htm"
URL_8137 = "https://www.planalto.gov.br/ccivil_03/leis/l8137.htm"
URL_14016 = "https://www.planalto.gov.br/CCIVIL_03/_Ato2019-2022/2020/Lei/L14016.htm"

# cada trecho: id, norma, dispositivo, texto (fiel ao oficial; aspas = transcrição literal), palavras-chave, fonte
TRECHOS = [
    {
        "id": "15224-ementa",
        "norma": "Lei nº 15.224, de 30 de setembro de 2025",
        "dispositivo": "arts. 1º e 2º",
        "texto": "Institui a Política Nacional de Combate à Perda e ao Desperdício de Alimentos (PNCPDA) e cria o "
                 "Selo Doador de Alimentos. É a lei federal vigente sobre doação de alimentos.",
        "chaves": "lei doacao doar desperdicio perda politica nacional selo doador vigente atual",
        "fonte": URL_15224,
    },
    {
        "id": "15224-art14",
        "norma": "Lei nº 15.224/2025",
        "dispositivo": "art. 14, caput",
        "texto": "Alimentos embalados, perecíveis ou não, podem ser doados desde que estejam \"dentro do prazo de "
                 "validade\". Alimentos in natura ou preparados podem ser doados se mantiverem as propriedades "
                 "nutricionais e a segurança para consumo humano, respeitadas as normas sanitárias. "
                 "A lei não autoriza doar alimento embalado com validade vencida.",
        "chaves": "doar doacao validade vencido vencida vence hoje prazo embalado perecivel in natura preparado "
                  "pao sobra condicao pode posso seguranca sanitaria",
        "fonte": URL_15224,
    },
    {
        "id": "15224-art14-par",
        "norma": "Lei nº 15.224/2025",
        "dispositivo": "art. 14, §§ 1º e 2º",
        "texto": "§ 1º: bancos de alimentos, instituições receptoras e doadores que entregam diretamente aos "
                 "beneficiários devem contar com profissional habilitado que ateste a qualidade nutricional e "
                 "sanitária dos alimentos, conforme regulamento. § 2º: alimentos impróprios para consumo humano "
                 "podem ser destinados a compostagem agrícola ou à produção de biomassa.",
        "chaves": "doacao direta profissional habilitado nutricionista atestar improprio compostagem biomassa "
                  "descarte destino vencido estragado lixo faco fazer jogar fora",
        "fonte": URL_15224,
    },
    {
        "id": "15224-art3",
        "norma": "Lei nº 15.224/2025",
        "dispositivo": "art. 3º, III a VII",
        "texto": "Doador: pessoa física ou jurídica, pública ou privada, que doa voluntariamente. Beneficiário: "
                 "pessoa física que consome os alimentos doados. Banco de alimentos: estrutura que capta, recebe e "
                 "distribui gratuitamente alimentos doados. Instituição receptora: pode ser pública, privada sem "
                 "fins lucrativos, organização da sociedade civil, entidade religiosa ou privada com fins lucrativos "
                 "que atue como intermediária, nos termos da lei e do regulamento.",
        "chaves": "quem pode doar doador receber beneficiario banco de alimentos ong instituicao receptora "
                  "igreja entidade religiosa intermediario para quem",
        "fonte": URL_15224,
    },
    {
        "id": "15224-art15-16",
        "norma": "Lei nº 15.224/2025",
        "dispositivo": "arts. 15 e 16",
        "texto": "A doação é exceção à responsabilidade objetiva do art. 931 do Código Civil e dos arts. 12 e 13 do "
                 "Código de Defesa do Consumidor. O doador e o intermediário só respondem civilmente por danos "
                 "causados pelos alimentos doados quando houver dolo.",
        "chaves": "responsabilidade risco processo processado culpa dolo dano intoxicacao doador responde "
                  "seguro doar problema",
        "fonte": URL_15224,
    },
    {
        "id": "15224-art17",
        "norma": "Lei nº 15.224/2025",
        "dispositivo": "art. 17",
        "texto": "A doação de alimentos não configura relação de consumo em nenhuma hipótese, mesmo quando houver "
                 "finalidade de publicidade direta ou indireta.",
        "chaves": "relacao de consumo cdc doacao publicidade marketing divulgar",
        "fonte": URL_15224,
    },
    {
        "id": "15224-incentivos",
        "norma": "Lei nº 15.224/2025",
        "dispositivo": "art. 6º, par. único; art. 7º, VI e VII e § 2º; art. 9º",
        "texto": "A lei prevê incentivos fiscais \"na forma da lei\" para doadores e instituições receptoras e "
                 "incentivos creditícios para bancos de alimentos, sujeitos à disponibilidade orçamentária; "
                 "estados e o DF podem reduzir ou isentar ICMS para estimular doações; e cria o Selo Doador de "
                 "Alimentos.",
        "chaves": "incentivo fiscal imposto icms desconto beneficio vantagem selo doador credito",
        "fonte": URL_15224,
    },
    {
        "id": "15224-revoga",
        "norma": "Lei nº 15.224/2025",
        "dispositivo": "arts. 19 e 20",
        "texto": "Revoga a Lei nº 14.016/2020 (antiga lei de doação de excedentes) e entra em vigor na data de "
                 "publicação (DOU de 1º/10/2025).",
        "chaves": "14016 14.016 antiga lei revogada vigencia vigor",
        "fonte": URL_15224,
    },
    {
        "id": "cdc-18-6",
        "norma": "Código de Defesa do Consumidor (Lei nº 8.078/1990)",
        "dispositivo": "art. 18, § 6º, I a III",
        "texto": "\"São impróprios ao uso e consumo: I - os produtos cujos prazos de validade estejam vencidos\"; "
                 "II - os deteriorados, alterados, avariados, nocivos à saúde ou em desacordo com as normas; "
                 "III - os que, por qualquer motivo, se revelem inadequados ao fim a que se destinam.",
        "chaves": "vender venda vencido vencida validade expirada desconto promocao liquidar improprio consumo "
                  "estragado deteriorado avariado cliente consumidor pode posso",
        "fonte": URL_CDC,
    },
    {
        "id": "lei8137-7-ix",
        "norma": "Lei nº 8.137/1990 (crimes contra as relações de consumo)",
        "dispositivo": "art. 7º, IX e parágrafo único",
        "texto": "É crime \"vender, ter em depósito para vender ou expor à venda ou, de qualquer forma, entregar "
                 "matéria-prima ou mercadoria, em condições impróprias ao consumo\". Pena: detenção de 2 a 5 anos, "
                 "ou multa. A modalidade culposa (sem intenção) também é punida, com pena reduzida.",
        "chaves": "crime vender vencido expor venda deposito improprio multa detencao prisao pena punicao "
                  "desconto promocao estoque vencido gondola",
        "fonte": URL_8137,
    },
]

_VAZIAS = {"de", "da", "do", "das", "dos", "a", "o", "as", "os", "e", "ou", "em", "no", "na", "um", "uma", "que",
           "para", "por", "com", "se", "eu", "meu", "minha", "isso", "esse", "essa", "como", "qual", "quais", "ao"}


def _tokens(txt: str) -> list[str]:
    txt = unicodedata.normalize("NFKD", txt or "").encode("ascii", "ignore").decode().lower()
    return [t for t in re.findall(r"[a-z0-9.]+", txt) if t not in _VAZIAS and len(t) > 1]


def _radical(t: str) -> str:
    return t[:5] if len(t) > 5 else t   # "vencido"/"vencida"/"vence" -> "venci"/"vence"... aproximação simples


def buscar(pergunta: str, k: int = 3) -> list[tuple[float, dict]]:
    q = {_radical(t) for t in _tokens(pergunta)}
    if not q:
        return []
    res = []
    for tr in TRECHOS:
        chaves = {_radical(t) for t in _tokens(tr["chaves"])}
        corpo = {_radical(t) for t in _tokens(tr["texto"] + " " + tr["dispositivo"])}
        score = 2.0 * len(q & chaves) + 0.5 * len(q & corpo)
        if score > 0:
            res.append((score, tr))
    res.sort(key=lambda x: -x[0])
    return res[:k]


RELEVANCIA_MINIMA = 3.0


def consultar(pergunta: str) -> dict:
    """Resultado no formato da ferramenta do agente."""
    achados = [(s, t) for s, t in buscar(pergunta) if s >= RELEVANCIA_MINIMA]
    if not achados:
        return {"encontrado": False,
                "mensagem": "Não há trecho sobre isso na base normativa do Ciclo Zero. Não responda com lei ou "
                            "regra de memória: diga que não sabe e sugira consultar a vigilância sanitária "
                            "do município ou um advogado.",
                "normas_disponiveis": sorted({t["norma"] for t in TRECHOS})}
    return {"encontrado": True,
            "trechos": [{"norma": t["norma"], "dispositivo": t["dispositivo"], "texto": t["texto"], "fonte": t["fonte"]}
                        for _, t in achados],
            "aviso": f"Texto conferido no site oficial em {CONSULTADO_EM}. Informação, não aconselhamento jurídico."}
