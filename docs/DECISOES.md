# Diário de decisões — Ciclo Zero

> Registro vivo de tudo que a equipe decide. Cada nova decisão entra no **Log** (mais recente em cima) e, se mudar algo estrutural, atualiza as seções acima dele.

## Equipe
| Pessoa | GitHub | Responsabilidade |
|---|---|---|
| Matheus | — | Agente de IA e ferramentas (núcleo da solução) |
| João Paulo | joaopaulo167 | Interface (Streamlit) e dados de exemplo |
| Arthur | arthurarroyo101-lgtm | BMC, pitch, documentação do fluxo e validação com comerciante real · dono do repositório |

## Contexto
- **Evento:** AKCIT Camp — Hackathon Regional **Centro-Oeste, presencial, Goiânia, sábado 24/10/2026**.
- **Tema do edital:** Soluções usando Agentes de IA (livre).
- **Nosso tema (registrado na inscrição):** *Ciclo Zero — Inteligência Artificial aplicada à redução do desperdício de alimentos em pequenos comércios.*
- **Solução:** agente de IA que controla o estoque de pequenas e médias empresas do ramo alimentício e age para reduzir desperdício (validade, estoque parado, compras erradas).

## Stack (decidida)
- **Linguagem:** Python
- **Interface:** Streamlit
- **Banco:** SQLite (arquivo local, zero custo)
- **LLM:** Google Gemini (plano gratuito) com function calling — a equipe não tem créditos AWS
- **Repositório:** público, licença MIT (o edital valoriza código aberto)

## Prazos do dia (24/10)
| Hora | O quê |
|---|---|
| 08h00 | Credenciamento |
| 09h00 | Início do desenvolvimento |
| 10h00 | Check-in de mentores (15 min/equipe) |
| **15h30** | **Congelamento — tudo no GitHub** |
| 16h00 | Pitches (3–5 min + 3 min Q&A) |
| 18h30 | Resultado |

Mínimo de 2 integrantes presentes.

## Entregáveis obrigatórios (no GitHub até 15h30)
- [ ] Protótipo funcional do agente (demo ao vivo **ou gravada** — gravar backup!)
- [ ] BMC (Business Model Canvas)
- [ ] Pitch de 3 minutos
- [ ] Documentação do fluxo do agente (inputs, lógica, outputs)

## Como seremos avaliados (regional)
| Critério | Peso | O que precisamos mostrar |
|---|---|---|
| Solução e Uso de IA | **30%** | IA é o núcleo (sem o agente, não há valor); tratamento de erros, guardrails, avaliação da saída |
| Problema e Validação | 20% | Persona clara + evidência real (entrevista com comerciante, dados de desperdício) |
| Diferencial e Viabilidade | 20% | Vantagem sobre planilha/ERP, modelo de negócio, escala |
| Equipe | 15% | Complementaridade, evolução na jornada |
| Pitch | 15% | Clareza em 3 min, explicar o fluxo do agente na demo |

Nota 1 a 5 por critério; item não abordado = 1. Desempate: maior nota em Solução e Uso de IA.

Perguntas que a banca tende a fazer (seção 10 do edital): de onde vêm os fatos do agente e como evita inventar; como decide chamar uma ferramenta e o que faz quando nenhuma serve; o que acontece com entrada inesperada; o que lembra entre sessões e LGPD; como investigaríamos uma resposta ruim.

## Pendências
- [ ] Matheus ter acesso de push ao repositório (Arthur adiciona como colaborador)
- [ ] Cada um criar sua chave do Gemini em https://aistudio.google.com/apikey
- [ ] Entrevista rápida com comerciante conhecido (Arthur) — registrar respostas em `docs/validacao.md`

## Log
- **2026-10-23 21:00** — Confirmado: hackathon presencial Centro-Oeste (24/10). Tema da inscrição: Ciclo Zero (desperdício de alimentos em pequenos comércios). Repositório criado pelo Arthur (`arthurarroyo101-lgtm/Ciclo-zero`). Sem créditos AWS → Gemini gratuito. Divisão de tarefas aceita. A equipe conhece comerciantes para validação.
- **2026-10-23 20:50** — Análise do edital feita; definidos critérios, entregáveis e stack sugerida (Python + Streamlit + SQLite + LLM com function calling).
