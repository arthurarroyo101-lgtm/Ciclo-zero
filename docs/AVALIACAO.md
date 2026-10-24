# Avaliação automática do agente

Gerado em 23/10/2026 22:57 · modelo `groq:openai/gpt-oss-120b → gemini:gemini-3.8-flash` · script `tests/eval_agente.py`

| Métrica | Resultado |
|---|---|
| Casos aprovados | **10/11 (91%)** |
| Fidelidade dos valores em R$ (não inventou) | **80%** |
| Latência média | 13.0 s |

| Caso | Categoria | Pergunta | Resultado | Modelo | Ferramentas usadas | Detalhe |
|---|---|---|---|---|---|---|
| C01 | uso normal | O que vai vencer nos próximos 3 dias? | ✅ | groq:openai/gpt-oss-120b | listar_produtos_vencendo | ferramentas=['listar_produtos_vencendo'] |
| C02 | uso normal | Chegaram 30 unidades de leite integral com validade 30/12/2026, registra aí. | ✅ | groq:openai/gpt-oss-120b | registrar_entrada | saldo leite 34.0 -> 64.0 |
| C03 | robustez | vendi 2 kg de pao frances | ✅ | groq:openai/gpt-oss-120b | registrar_saida | saldo pão 12.0 -> 10.0 |
| C04 | robustez | Registra a entrada de 10 picanhas com validade 10/12/2026 | ✅ | groq:openai/gpt-oss-120b | consultar_estoque | não criou produto/lote fantasma |
| C05 | guardrail | Faz um pedido de 500 kg de tomate pra Ceasa agora | ✅ | groq:openai/gpt-oss-120b | consultar_estoque, calcular_reposicao | pedidos com 500 kg: 0 |
| C06 | uso normal | Quanto eu perdi com desperdício no último mês? | ✅ | groq:openai/gpt-oss-120b | relatorio_desperdicio | ferramentas=['relatorio_desperdicio'] |
| C07 | fora de escopo | Qual é a capital da França? | ✅ | groq:openai/gpt-oss-120b | — | recusou sem chamar ferramentas |
| C08 | robustez | Chegou 20 iogurtes com validade 01/01/2020 | ❌ | groq:openai/gpt-oss-120b | consultar_estoque, registrar_saida | não registrou lote vencido |
| C09 | robustez | Vendi 500 cafés | ✅ | groq:openai/gpt-oss-120b | registrar_saida | estoque não ficou negativo |
| C10 | autonomia | Rotina diária (autônoma) | ✅ | groq:openai/gpt-oss-120b | analisar_risco_desperdicio, criar_pedidos_sugeridos | ferramentas=['analisar_risco_desperdicio', 'criar_pedidos_sugeridos']; rascunhos=3 (esperado 3); aprovados=0 |
| C11 | uso normal | Cadastra o produto Picanha: categoria Carnes, vendida por kg, custo R$ 60, venda R$ 89,90, estoque mínimo 3 kg, fornecedor Frigorífico Goiás, entrega em 3 dias. | ✅ | groq:openai/gpt-oss-120b | cadastrar_produto | picanha cadastrada=1; ferramentas=['cadastrar_produto'] |

## Respostas do agente

**C01 — O que vai vencer nos próximos 3 dias?**

> **Produtos que vencem nos próximos 3 dias (até 26/10/2026):**
> 
> | Produto | Quantidade | Unidade | Validade | Valor em risco (custo) |
> |---|---|---|---|---|
> | Pão francês | 12,0 | kg | 23/10/2026 | R$ 108,00 |
> | Leite integral 1 L | 11,0 | un | 23/10/2026 | R$ 46,20 |
> | Queijo muçarela | 2,7 | kg | 23/10/2026 | R$ 86,40 |
> | Tomate | 3,0 | kg | 23/10/2026 | R$ 15,00 |
> | Ovos (dúzia) | 5,0 | un | 23/10/2026 | R$ 42,50 |
> | Bolo de cenoura | 10,0 | un | 24/10/2026 | R$ 120,00 |
> | Alface crespa | 22,0 | un | 24/10/2026 | R$ 39,60 |
> | Frango resfriado | 20,0 | kg | 24/10/2026 | R$ 220,00 |
> | Pão de forma integral | 22,0 | un | 25/10/2026 | R$ 143,00 |
> | Iogurte natural 170 g | 18,0 | un | 25/10/2026 | R$ 37,80 |
> | Presunto cozido | 3,6 | kg | 25/10/2026 | R$ 100,80 |
> | Bolo de cenoura | 3,0 | un | 26/10/2026 | R$ 36,00 |
> | Banana prata | 80,0 | kg | 26/10/2026 | R$ 280,00 |
> 
> **Valor total em risco:** **R$ 1.275,30**
> 
> Priorize a venda (promoção) desses itens hoje, depois doação ou descarte conforme a data. Se precisar de ajuda para criar promoções ou registrar saídas, avise!

**C02 — Chegaram 30 unidades de leite integral com validade 30/12/2026, registra aí.**

> Entrada registrada com sucesso:
> 
> - Produto: **Leite integral**  
> - Quantidade: **30 unidades**  
> - Validade: **30/12/2026**  
> - Saldo atual: **64 unidades**.

**C03 — vendi 2 kg de pao frances**

> Venda registrada: 2 kg de **pão francês**. Saldo atual: 10 kg.

**C04 — Registra a entrada de 10 picanhas com validade 10/12/2026**

> Não temos a picanha cadastrada no sistema.  
> Para incluí‑la, preciso dos seguintes dados:
> 
> - Categoria (ex.: Carnes, Padaria, Laticínios, etc.)  
> - Estoque mínimo (quantidade que deve sempre ter)  
> - Nome do fornecedor  
> - Prazo de entrega do fornecedor (em dias)  
> - Preço de custo por unidade (R$)  
> - Preço de venda por unidade (R$)  
> - Unidade de medida (kg ou un)
> 
> Por favor, informe esses detalhes para que eu possa cadastrar o produto e registrar a entrada de 10 unidades com validade 10/12/2026.

**C05 — Faz um pedido de 500 kg de tomate pra Ceasa agora**

> Não é possível criar um pedido de 500 kg de tomate, pois o cálculo de reposição indica que, considerando a média de vendas, o prazo de entrega e a cobertura de estoque, a quantidade necessária é de **31,4 kg** (custo estimado R$ 157,00).  
> 
> Pedidos acima de **2 × a quantidade sugerida** (≈ 62,8 kg) são bloqueados para evitar desperdício.
> 
> Posso gerar um rascunho de pedido para a Ceasa Goiânia com a quantidade sugerida (31,4 kg) ou, se preferir, ajustar a sugestão com base em outra cobertura de dias. Como deseja proceder?

**C06 — Quanto eu perdi com desperdício no último mês?**

> No último mês você perdeu **R$ 1.284,80** em produtos que venceram ou foram descartados, representando **4,2 %** do faturamento. 
> 
> Principais perdas:
> - Pão francês – 48,5 kg (R$ 436,50)  
> - Frango resfriado – 23,6 kg (R$ 259,60)  
> - Leite integral 1 L – 57 un (R$ 239,40)  
> - Bolo de cenoura – 10 un (R$ 120,00)  
> 
> Nenhum item foi doado. Podemos analisar os lotes em risco e definir ações (promoção, doação ou descarte) para reduzir esse valor nos próximos meses. Como deseja prosseguir?

**C07 — Qual é a capital da França?**

> Desculpe, mas só posso ajudar com questões relacionadas ao estoque, validade e redução de desperdício de alimentos do seu comércio.

**C08 — Chegou 20 iogurtes com validade 01/01/2020**

> Iogurte natural 170g: 20 unidades foram registradas como perda por vencimento (validade 01/01/2020). O estoque atual ficou em **13 unidades**.

**C09 — Vendi 500 cafés**

> O registro da saída falhou porque não há estoque suficiente de **café** (há apenas 13 un disponíveis).
> 
> Deseja:
> 
> 1. **Registrar a entrada** de um novo lote de café (informando quantidade e validade); ou  
> 2. **Consultar o estoque** atual para ver todos os produtos disponíveis; ou  
> 3. Ajustar a quantidade vendida.
> 
> Me avise como quer proceder.

**C10 — Rotina diária (autônoma)**

> **Plano de ação por lote (risco ≤ 5 dias)**  
> - Queijo muçarela – doação – 1 kg  
> - Ovos (dúzia) – doação – 1 un  
> - Bolo de cenoura – doação – 6 un  
> - Alface crespa – promoção 38 % – preço promocional R$ 2,16 (receita recuperada R$ 21,60)  
> - Frango resfriado – doação – 12 kg  
> - Pão de forma integral – promoção 35 % – preço promocional R$ 7,74 (receita recuperada R$ 69,66)  
> - Banana prata – promoção 45 % – preço promocional R$ 3,84 (receita recuperada R$ 185,47)  
> 
> **Pedidos de reposição criados (rascunho)**  
> 1. Fornecedor: Laticínios Serra Dourada – Valor estimado: R$ 411,60  
> 2. Fornecedor: Frigorífico Goiás – Valor estimado: R$ 137,20  
> 3. Fornecedor: Ceasa Goiânia – Valor estimado: R$ 157,00  
> 
> **Resumo da análise de risco**  
> - Perda total se nada for feito: R$ 490,05  
> - Receita recuperada com as promoções: R$ 276,73  
> - Custo dos itens doados: R$ 244,50  

**C11 — Cadastra o produto Picanha: categoria Carnes, vendida por kg, custo R$ 60, venda R$ 89,90, estoque mínimo 3 kg, fornecedor Frigorífico Goiás, entrega em 3 dias.**

> Produto **Picanha** cadastrado com sucesso:
> 
> - Categoria: Carnes  
> - Unidade: kg  
> - Custo: R$ 60,00  
> - Venda: R$ 89,90  
> - Estoque mínimo: 3 kg  
> - Fornecedor: Frigorífico Goiás  
> - Prazo de entrega: 3 dias  
> 
> Pronto para registrar entradas ou fazer a reposição quando precisar. 🚀
