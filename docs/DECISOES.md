# Diário de decisões — Ciclo Zero

> Registro vivo de tudo que a equipe decide. Cada nova decisão entra no **Log** (mais recente em cima) e, se mudar algo estrutural, atualiza as seções acima dele.

## Equipe
| Pessoa | GitHub | Responsabilidade |
|---|---|---|
| Matheus | matheussari | Agente de IA e ferramentas (núcleo da solução) |
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
- **LLM principal:** Groq `openai/gpt-oss-120b` (gratuito, rápido, 10/10 na avaliação)
- **LLM reserva:** Gemini — troca automática se o Groq cair
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
- [x] Matheus com acesso de push ao repositório
- [ ] João Paulo aceitar convite de colaborador (se ainda não aceitou)
- [ ] Cada um criar sua chave do **Groq** (https://console.groq.com/keys) e do Gemini (https://aistudio.google.com/apikey) e rodar `pip install -r requirements.txt` de novo
- [ ] Entrevista rápida com comerciante conhecido (Arthur) — registrar respostas em `docs/validacao.md`

## Arquitetura (v0.1)
```
app.py                  → interface Streamlit (João Paulo evolui)
ciclozero/db.py         → SQLite: produtos, lotes (validade), movimentações, pedidos, log_agente
ciclozero/tools.py      → 8 ferramentas do agente (os números saem daqui, nunca do LLM)
ciclozero/agent.py      → loop Gemini + function calling, guardrails, rastreio
ciclozero/seed.py       → padaria/mercadinho fictício com 30 dias de histórico
docs/FLUXO_AGENTE.md    → entregável: inputs, lógica, outputs (Arthur revisa)
```
Decisões de projeto: cálculos em Python (não no LLM) para evitar número inventado; FEFO na baixa de estoque; pedido de compra sempre como rascunho com aprovação humana; pedido > 2× o sugerido é bloqueado; desconto máximo 50%; máximo 8 passos por pergunta; modelo configurável por `GEMINI_MODEL` (padrão `gemini-3.8-flash`).

## Log
- **2026-10-23 23:00** — Observabilidade: cada chamada ao LLM registrada (provedor, modelo, ms, erro) e cada pergunta com tempo total; painel "Saúde do agente" na aba Rastreio (tempo médio, p95, taxa de erro, uso de reserva, erros de ferramenta) — `ciclozero/metricas.py`. Nova ferramenta `cadastrar_produto` (só com dados do usuário; bloqueia duplicado/nome parecido). Novo caso de teste C11 (cadastro). Justificativa de agente único documentada em `FLUXO_AGENTE.md`.
- **2026-10-23 22:47** — João subiu a aba 📊 Dashboard (4 gráficos em Altair, `ciclozero/graficos.py`); integrada sem conflito com o agente. Matheus testou dashboard + agente (Groq) pela interface: aprovados pela equipe.
- **2026-10-23 22:39** — ✅ **Avaliação v2: 10/10, fidelidade 100%, latência média 7,6 s** (era 11,9 s); rotina completa em 28 s com os 3 pedidos corretos. Parte do agente pronta para a demo.
- **2026-10-23 22:35** — Rotina caiu para 27 s, mas com raciocínio baixo o modelo esqueceu 1 de 3 fornecedores. Solução: nova ferramenta `criar_pedidos_sugeridos` (um rascunho por fornecedor numa chamada, determinístico). `calcular_reposicao` agora desconta pedidos em aberto → rodar a rotina 2× não duplica pedidos. Teste C10 agora exige 1 rascunho por fornecedor que precisa de reposição. Rotina em 2 passos.
- **2026-10-23 22:28** — Otimização de velocidade da rotina: `reasoning_effort=low` no gpt-oss (Groq, configurável por `GROQ_REASONING`), resultados enxutos para o modelo (~20% menos tokens; a interface continua vendo tudo) e rotina em 3 passos (ferramentas chamadas em paralelo). Meta: rotina < 30 s.
- **2026-10-23 22:18** — ✅ **Avaliação final: 10/10 casos, fidelidade 100% (nenhum R$ inventado), latência média 11,9 s** (perguntas simples ~2 s; rotina completa 43–91 s, afetada pelo limite por minuto do Groq gratuito). Resultado em `docs/AVALIACAO.md` — evidência para o critério Solução e Uso de IA (30%).
- **2026-10-23 22:15** — C08 e C10 passando (rotina com Groq agora cria 3 rascunhos de pedido). **Decisão: Groq como provedor principal, Gemini como reserva** (`PROVEDORES=groq,gemini`) — Groq mais rápido e sem estourar cota; Gemini estourou a cota gratuita em poucas rodadas.
- **2026-10-23 22:12** — 1ª avaliação automática (Groq `gpt-oss-120b`): **9/10, fidelidade 100%, 15,3 s/resposta**. C08 falhou por bug do teste (agente recusou corretamente o lote vencido). C10 passou mas o Groq não criou pedidos na rotina → instrução da rotina reescrita em passos explícitos e teste endurecido (exige rascunhos). Teste agora aceita `EVAL_CASOS=C08,C10` para rodar só alguns casos e registra o modelo usado em cada caso.
- **2026-10-23 22:05** — ✅ Primeira rotina diária completa com IA real (analisou risco → reposição → 3 pedidos rascunho → plano por lote → resumo); o fallback de modelo funcionou ao vivo (3.8-flash com cota estourada → flash-lite). Corrigido: resumo mostrava 'em risco' = 'evitado' (mesmo número); agora a análise devolve campos separados (perda sem ação, receita recuperada com promoções, custo doado, descarte). Sobra de produto vendido por unidade arredondada para cima.
- **2026-10-23 22:00** — Gemini instável à noite (429 cota, 503 sobrecarga, 504 timeout em todos os modelos). Decidido adicionar **Groq como provedor reserva automático** (ordem em `PROVEDORES`). O agente agora mantém a conversa em texto comum aos provedores; se um cair depois de já ter alterado o estoque, não repete a operação no outro (evita lançamento duplicado). Interface mostra os passos do agente ao vivo (`st.status`).
- **2026-10-23 21:52** — Gemini com 503 (sobrecarga do Google). Criado fallback automático de modelos (`GEMINI_MODELOS_RESERVA`): se o principal cair, o agente troca sozinho — protege a demo ao vivo.
- **2026-10-23 21:48** — `gemini-3.8-flash` deu 504 (tempo esgotado) por raciocinar demais com 8 ferramentas. Raciocínio limitado a `low` (configurável por `GEMINI_THINKING`). Agente agora mostra o progresso de cada passo e tem timeout de 60 s por chamada.
- **2026-10-23 21:45** — Criada a avaliação automática `tests/eval_agente.py`: 10 casos (uso normal, robustez, guardrails, fora de escopo, rotina autônoma), mede acerto, fidelidade dos R$ citados e latência; gera `docs/AVALIACAO.md` como evidência para a banca. Obs.: a API do Gemini só é acessível do computador de cada um.
- **2026-10-23 21:30** — Datas e valores em padrão brasileiro (DD/MM/AAAA; R$ 1.234,56) na interface e nas respostas do agente; o agente aceita validade em DD/MM/AAAA. Decidido incluir **dashboards com gráficos** (João Paulo). Divisão de tarefas por dono de arquivo, todos na `main` com Sync antes/depois → ver `docs/TAREFAS.md`. Criado `tools.historico_diario()` como base dos gráficos.
- **2026-10-23 21:22** — Primeiro teste real: interface ok; Gemini respondeu 404 porque `gemini-2.5-flash` não está mais disponível para contas novas. Modelo padrão trocado para `gemini-3.8-flash` (configurável via `GEMINI_MODEL` no `.env`).
- **2026-10-23 21:15** — Base do agente criada (v0.1): banco, 8 ferramentas, loop do agente com Gemini, modo autônomo "rotina diária", interface Streamlit com abas Agente/Estoque/Pedidos/Rastreio, dados de exemplo e documentação do fluxo. Ferramentas testadas localmente; falta testar com chave real do Gemini.
- **2026-10-23 21:10** — Primeiro push feito. Commits usam o e-mail noreply do GitHub (o GitHub bloqueia push que expõe e-mail privado).
- **2026-10-23 21:00** — Confirmado: hackathon presencial Centro-Oeste (24/10). Tema da inscrição: Ciclo Zero (desperdício de alimentos em pequenos comércios). Repositório criado pelo Arthur (`arthurarroyo101-lgtm/Ciclo-zero`). Sem créditos AWS → Gemini gratuito. Divisão de tarefas aceita. A equipe conhece comerciantes para validação.
- **2026-10-23 20:50** — Análise do edital feita; definidos critérios, entregáveis e stack sugerida (Python + Streamlit + SQLite + LLM com function calling).
