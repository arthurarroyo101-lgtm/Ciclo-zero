# Divisão de tarefas — Ciclo Zero

> Regra de ouro: **cada pessoa mexe só nos seus arquivos.** Assim ninguém sobrescreve o trabalho do outro e o git não dá conflito.

## Quem é dono de quê
| Pessoa | Arquivos (só ela edita) | Missão |
|---|---|---|
| **Matheus** | `ciclozero/*.py` (agent, tools, db, seed), `tests/` | Cérebro do agente: ferramentas, guardrails, avaliação de qualidade |
| **João Paulo** | `app.py`, `ciclozero/graficos.py` (criar), `.streamlit/` | Tela e dashboards: gráficos, visual, gravação da demo |
| **Arthur** | `docs/BMC.md`, `docs/PITCH.md`, `docs/validacao.md`, `docs/FLUXO_AGENTE.md` | Negócio: validação com comerciante, BMC, roteiro do pitch |

`README.md` e `docs/DECISOES.md`: qualquer um pode editar, mas **puxe antes** (Sync) e faça mudanças pequenas.

Se precisar de algo no arquivo de outra pessoa (ex.: João precisa de um dado novo do banco), **peça no grupo** — o dono faz.

## Fluxo no git (todo mundo na branch `main`)
1. **Antes de começar** e **antes de enviar**: Source Control → **Sync Changes** (puxa o dos outros + envia o seu).
2. Commits pequenos e frequentes, com mensagem clara: `feat: gráfico de perdas por categoria`.
3. Nunca commitar o `.env` (já está no `.gitignore`).
4. Deu conflito? Pare e chame o Matheus antes de apertar qualquer botão.

## Tarefas — HOJE à noite (até ~00h30)

### Matheus
- [x] Datas e valores no padrão brasileiro (DD/MM/AAAA, R$ 1.234,56)
- [ ] Validar o agente com o Gemini de verdade (rotina diária + perguntas soltas)
- [ ] `tests/eval_agente.py`: bateria de perguntas com resposta esperada → nota de qualidade do agente (conta para os 30% de "Solução e Uso de IA")
- [ ] Ajustar instruções/ferramentas conforme os testes

### João Paulo
- [ ] Rodar o projeto no próprio computador (ver README)
- [ ] Criar `ciclozero/graficos.py` e uma aba **📊 Dashboard** no `app.py` com:
  - perdas em R$ por categoria (barras)
  - vendas × perdas por dia nos últimos 30 dias (linhas)
  - lotes por dias até vencer, coloridos pela ação recomendada (promoção/doação/descarte)
  - top 5 produtos que mais geram desperdício
- [ ] Dados prontos para os gráficos: `tools.historico_diario(30)`, `tools.analisar_risco_desperdicio()`, `tools.relatorio_desperdicio(30)`, `tools.consultar_estoque()`
- [ ] Use `st.bar_chart`/`st.line_chart` ou Plotly (`pip install plotly`, adicionar ao `requirements.txt`)

### Arthur
- [ ] **Entrevista hoje** (WhatsApp ou ligação, 10 min) com o comerciante conhecido → `docs/validacao.md`. Perguntas:
  1. Que tipo de comércio é e quantos funcionários?
  2. Como controla o estoque hoje (caderno, planilha, sistema)?
  3. Quanto joga fora por semana/mês (estimativa em R$ ou %)? Quais produtos mais?
  4. Já perdeu venda por falta de produto?
  5. Quanto tempo gasta por semana com estoque e pedidos?
  6. Pagaria por uma ferramenta que avisa o que vai vencer e monta o pedido? Quanto por mês?
  7. Usaria pelo WhatsApp/celular ou computador?
- [ ] Buscar 2–3 dados oficiais de desperdício de alimentos no Brasil (FAO, Embrapa, ABRAS) com fonte → `docs/validacao.md`
- [ ] `docs/BMC.md` — Business Model Canvas (rascunho)

## Tarefas — SÁBADO (no hackathon)
| Hora | Matheus | João Paulo | Arthur |
|---|---|---|---|
| 09h–10h | Ajustes do agente pós-teste | Polir dashboard | Fechar BMC |
| 10h | **Mentoria (15 min)** — levar dúvidas do pitch e da demo | | |
| 10h–12h30 | Avaliação + robustez | Visual final | Roteiro do pitch (`docs/PITCH.md`) |
| 13h30–15h | Congelar código, rodar teste final | **Gravar vídeo da demo (backup)** | Ensaiar pitch 3 min (cronometrado) |
| **15h00** | **Congelamento interno**: tudo no GitHub, revisão final | | |
| 15h30 | Congelamento oficial | | |

## Checkpoints
- **23h30 (hoje):** cada um faz Sync e manda print no grupo do que está funcionando.
- **09h00 (sábado):** todos fazem Sync antes de começar.
