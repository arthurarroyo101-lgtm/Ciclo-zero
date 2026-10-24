# Fluxo do agente Ciclo Zero

> Entregável obrigatório do edital: inputs, lógica e outputs do agente. (Arthur: revisar a linguagem para o pitch.)

## Visão geral

```
 ENTRADAS                     AGENTE (Gemini + function calling)                SAÍDAS
 ─────────                    ─────────────────────────────────                 ──────
 • Dono/funcionário fala      1. Entende o pedido                               • Resposta em linguagem natural
   em linguagem natural       2. Decide quais ferramentas chamar ──► SQLite     • Plano de ação por lote
   ("chegou 30L de leite")    3. Lê o resultado (dados reais)                     (promoção c/ preço, doação, descarte)
 • Rotina diária automática   4. Se der erro, corrige ou pergunta               • Rascunho de pedido de compra
   (botão / agendamento)      5. Encadeia mais ferramentas se precisar            (aguarda aprovação humana)
 • Estoque, lotes e           6. Responde só com números das ferramentas        • Relatório de desperdício em R$
   histórico de vendas                                                          • Log de cada passo (rastreio)
```

## Entradas
| Entrada | Exemplo |
|---|---|
| Mensagem do usuário | "Vendi 5 kg de pão", "o que vai vencer essa semana?", "faz o pedido da Ceasa" |
| Rotina diária (modo autônomo) | Botão "Rodar rotina diária" — o agente checa tudo sozinho, sem pergunta |
| Base de dados | Produtos, lotes com validade, 30 dias de vendas e perdas, fornecedores e prazos de entrega |

## Ferramentas (o que o agente sabe fazer)
| Ferramenta | O que faz |
|---|---|
| `consultar_estoque` | Saldo, validade mais próxima, média de vendas/dia, abaixo do mínimo |
| `registrar_entrada` | Novo lote com validade (valida data e quantidade) |
| `registrar_saida` | Venda, perda ou doação, baixando primeiro o que vence antes (FEFO) |
| `listar_produtos_vencendo` | Lotes que vencem em N dias e o R$ em risco |
| `analisar_risco_desperdicio` | Projeta quanto de cada lote **não** será vendido até vencer e recomenda promoção (com desconto e preço), doação ou descarte |
| `calcular_reposicao` | Quanto comprar por fornecedor = vendas/dia × (prazo de entrega + 5 dias) − saldo; não compra o que vai sobrar |
| `criar_pedidos_sugeridos` | Gera, numa chamada só, um **rascunho** de pedido por fornecedor com as quantidades calculadas (nunca esquece fornecedor, não duplica pedido em aberto) |
| `criar_pedido_compra` | Pedido específico que o usuário pedir; também só **rascunho** — o dono aprova na tela |
| `relatorio_desperdicio` | Perdas e doações do período em R$ e % do faturamento |

## Lógica
1. O modelo (Gemini) recebe instruções fixas: missão, regras e a data de hoje.
2. A cada passo, ele escolhe chamar uma ou mais ferramentas, ou responder.
3. Cada chamada é validada e executada em Python; o resultado volta ao modelo como dado.
4. O ciclo repete até a resposta final (máximo de 8 passos).

**Exemplo — rotina diária (2 passos, ~25 s):** `analisar_risco_desperdicio` + `criar_pedidos_sugeridos` (em paralelo) → resposta com plano por lote, pedidos criados e resumo (perda sem ação, receita recuperada com promoções, valor doado).

## Guardrails e confiabilidade
| Risco | Como tratamos |
|---|---|
| Modelo inventar números | Regra: todo número vem de ferramenta. Cálculos são feitos em Python, não pelo LLM. Medido: **fidelidade 100%** na avaliação automática |
| Provedor de IA fora do ar | Troca automática de modelo e de provedor (Groq → Gemini) |
| Nome de produto errado ("pao frances") | Busca tolerante a acento/erro; se ambíguo, devolve sugestões e o agente pergunta |
| Entrada inválida (quantidade negativa, data no passado, saldo insuficiente) | Ferramenta recusa com mensagem clara; o agente explica ao usuário |
| Comprar demais (gera desperdício) | Pedido acima de 2× o sugerido é bloqueado; o cálculo desconta o que já foi pedido (sem pedido duplicado) |
| Ação cara sem supervisão | Pedido de compra é só rascunho; aprovação é humana |
| Desconto exagerado | Limite de 50%; o agente sinaliza quando o preço promocional fica abaixo do custo |
| Loop infinito / gasto de cota | Máximo de 8 passos por pergunta + novas tentativas automáticas se a API falhar |
| Pergunta fora do escopo | O agente recusa educadamente e volta ao tema estoque/desperdício |

## Observabilidade
Toda interação é gravada na tabela `log_agente` (sessão, passo, ferramenta, argumentos, resultado, resposta) e aparece na aba **Rastreio**. Assim conseguimos investigar uma resposta ruim: ver exatamente quais dados o agente recebeu e o que decidiu.

## Memória e dados (LGPD)
- O agente lembra a conversa só durante a sessão; o que persiste é o estoque e o log operacional.
- Não coletamos dados pessoais de clientes; os dados são do estoque do comércio e ficam no próprio computador (SQLite).
