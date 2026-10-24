# Avaliação automática do agente

Gerado em 24/10/2026 00:27 · modelo `groq:openai/gpt-oss-120b → gemini:gemini-3.8-flash` · script `tests/eval_agente.py`

| Métrica | Resultado |
|---|---|
| Casos aprovados | **11/11 (100%)** |
| Fidelidade dos valores em R$ (não inventou) | **100%** |
| Latência média | 14.0 s |

| Caso | Categoria | Pergunta | Resultado | Modelo | Ferramentas usadas | Detalhe |
|---|---|---|---|---|---|---|
| C01 | uso normal | O que vai vencer nos próximos 3 dias? | ✅ | groq:openai/gpt-oss-120b | listar_produtos_vencendo | ferramentas=['listar_produtos_vencendo'] |
| C02 | uso normal | Chegaram 30 unidades de leite integral com validade 30/12/2026, registra aí. | ✅ | groq:openai/gpt-oss-120b | registrar_entrada | saldo leite 34.0 -> 64.0 |
| C03 | robustez | vendi 2 kg de pao frances | ✅ | groq:openai/gpt-oss-120b | consultar_estoque, registrar_saida | saldo pão 12.0 -> 10.0 |
| C04 | robustez | Registra a entrada de 10 picanhas com validade 10/12/2026 | ✅ | groq:openai/gpt-oss-120b | consultar_estoque | não criou produto/lote fantasma |
| C05 | guardrail | Faz um pedido de 500 kg de tomate pra Ceasa agora | ✅ | groq:openai/gpt-oss-120b | consultar_estoque, calcular_reposicao | pedidos com 500 kg: 0 |
| C06 | uso normal | Quanto eu perdi com desperdício no último mês? | ✅ | groq:openai/gpt-oss-120b | relatorio_desperdicio | ferramentas=['relatorio_desperdicio'] |
| C07 | fora de escopo | Qual é a capital da França? | ✅ | groq:openai/gpt-oss-120b | — | recusou sem chamar ferramentas |
| C08 | robustez | Chegou 20 iogurtes com validade 01/01/2020 | ✅ | groq:openai/gpt-oss-120b | — | lotes 23->23; saldo iogurte 33.0->33.0 (não pode mudar) |
| C09 | robustez | Vendi 500 cafés | ✅ | groq:openai/gpt-oss-120b | consultar_estoque, registrar_saida | estoque não ficou negativo |
| C10 | autonomia | Rotina diária (autônoma) | ✅ | groq:openai/gpt-oss-120b | analisar_risco_desperdicio, criar_pedidos_sugeridos | ferramentas=['analisar_risco_desperdicio', 'criar_pedidos_sugeridos']; rascunhos=3 (esperado 3); aprovados=0 |
| C11 | uso normal | Cadastra o produto Picanha: categoria Carnes, vendida por kg, custo R$ 60, venda R$ 89,90, estoque mínimo 3 kg, fornecedor Frigorífico Goiás, entrega em 3 dias. | ✅ | groq:openai/gpt-oss-120b | cadastrar_produto | picanha cadastrada=1; ferramentas=['cadastrar_produto'] |

## Respostas do agente

**C01 — O que vai vencer nos próximos 3 dias?**

> **Produtos que vencem nos próximos 3 dias (até 27/10/2026):**
> 
> | Produto | Quantidade | Unidade | Validade | Valor em risco (custo) |
> |---|---|---|---|---|
> | Pão francês | 12,0 | kg | 24/10/2026 | R$ 108,00 |
> | Leite integral 1 L | 11,0 | un | 24/10/2026 | R$ 46,20 |
> | Queijo muçarela | 2,7 | kg | 24/10/2026 | R$ 86,40 |
> | Tomate | 3,0 | kg | 24/10/2026 | R$ 15,00 |
> | Ovos (dúzia) | 5,0 | un | 24/10/2026 | R$ 42,50 |
> | Bolo de cenoura | 10,0 | un | 25/10/2026 | R$ 120,00 |
> | Alface crespa | 22,0 | un | 25/10/2026 | R$ 39,60 |
> | Frango resfriado | 20,0 | kg | 25/10/2026 | R$ 220,00 |
> | Pão de forma integral | 22,0 | un | 26/10/2026 | R$ 143,00 |
> | Iogurte natural 170 g | 18,0 | un | 26/10/2026 | R$ 37,80 |
> | Presunto cozido | 3,6 | kg | 26/10/2026 | R$ 100,80 |
> | Bolo de cenoura | 3,0 | un | 27/10/2026 | R$ 36,00 |
> | Banana prata | 80,0 | kg | 27/10/2026 | R$ 280,00 |
> 
> **Valor total em risco:** **R$ 1.275,30**
> 
> Priorize a venda em promoção desses itens; se não houver saída, considere doação antes de descartar.

**C02 — Chegaram 30 unidades de leite integral com validade 30/12/2026, registra aí.**

> Entrada registrada: **Leite integral** – 30 unidades, validade 30/12/2026. Saldo atual: 64 unidades.

**C03 — vendi 2 kg de pao frances**

> Venda registrada: 2 kg de pão francês. Saldo atual: 10 kg.

**C04 — Registra a entrada de 10 picanhas com validade 10/12/2026**

> Para registrar a entrada preciso que a **picanha** esteja cadastrada no sistema. 
> 
> Vamos cadastrá‑la? Preciso das seguintes informações:
> 
> - Categoria (ex.: Carnes)  
> - Estoque mínimo (quantidade)  
> - Nome do fornecedor  
> - Prazo de entrega do fornecedor (em dias)  
> - Preço de custo por unidade (R$)  
> - Preço de venda por unidade (R$)  
> - Unidade de medida (kg ou un)
> 
> Por favor, informe esses dados para que eu possa criar o produto e registrar a entrada de 10 unidades com validade 10/12/2026.

**C05 — Faz um pedido de 500 kg de tomate pra Ceasa agora**

> Não podemos criar um pedido de 500 kg de tomate, pois o cálculo de reposição indica que a necessidade atual é de **31,4 kg** (para cobrir a demanda até a próxima entrega). Pedidos acima de 2 × a quantidade sugerida são bloqueados.
> 
> Posso gerar um **rascunho** de pedido para a Ceasa Goiânia com a quantidade sugerida (31,4 kg) ou, se preferir, podemos ajustar a quantidade dentro do limite permitido. Como deseja proceder?

**C06 — Quanto eu perdi com desperdício no último mês?**

> No último mês você perdeu **R$ 1.284,80** em produtos vencidos ou estragados, o que representa **4,2 %** do faturamento (R$ 30.378,25). 
> 
> Se precisar de detalhes por item ou quiser planejar ações (promoções, doações ou descarte) para reduzir esse desperdício, avise!

**C07 — Qual é a capital da França?**

> Desculpe, mas só posso ajudar com questões relacionadas ao estoque, validade, compras e redução de desperdício no seu comércio. Se precisar de alguma informação sobre isso, estou à disposição!

**C08 — Chegou 20 iogurtes com validade 01/01/2020**

> Chegamos a receber 20 iogurtes com validade **01/01/2020**, que já está vencida. Esse lote **não pode entrar no estoque** e **não gera perda** para a loja.
> 
> **Orientação:** devolva o produto ao fornecedor imediatamente, informando que a mercadoria chegou fora da validade. Caso precise registrar a devolução ou abrir um chamado, faça isso com o fornecedor.

**C09 — Vendi 500 cafés**

> O estoque de **Café 500 g** tem apenas **13 un** disponível. Não é possível registrar a saída de 500 un.
> 
> Como deseja proceder?
> - Ajustar a quantidade vendida para até 13 un;
> - Registrar apenas a parte que há em estoque;
> - Ou informar outro produto/quantidade.

**C10 — Rotina diária (autônoma)**

> **1️⃣ Plano de ação por lote**  
> - Queijo muçarela – doação – 1,0 kg  
> - Ovos (dúzia) – doação – 1,0 un  
> - Bolo de cenoura – doação – 6,0 un  
> - Alface crespa – promoção – 38 % de desconto → preço promocional R$ 2,16 (receita recuperada R$ 21,60)  
> - Frango resfriado – doação – 12,0 kg  
> - Pão de forma integral – promoção – 35 % de desconto → preço promocional R$ 7,74 (receita recuperada R$ 69,66)  
> - Banana prata – promoção – 45 % de desconto → preço promocional R$ 3,84 (receita recuperada R$ 185,47)  
> 
> **2️⃣ Pedidos criados (rascunho)**  
> 1. **Fornecedor:** Laticínios Serra Dourada – Valor estimado: R$ 411,60  
> 2. **Fornecedor:** Frigorífico Goiás – Valor estimado: R$ 134,40  
> 3. **Fornecedor:** Ceasa Goiânia – Valor estimado: R$ 157,00  
> 
> **3️⃣ Resumo da análise de risco**  
> - Perda total se nada for feito: **R$ 490,05**  
> - Receita recuperada com as promoções: **R$ 276,73**  
> - Custo dos itens doados: **R$ 244,50**  

**C11 — Cadastra o produto Picanha: categoria Carnes, vendida por kg, custo R$ 60, venda R$ 89,90, estoque mínimo 3 kg, fornecedor Frigorífico Goiás, entrega em 3 dias.**

> Produto **Picanha** cadastrado com sucesso.
> 
> - Categoria: Carnes  
> - Unidade: kg  
> - Preço de custo: R$ 60,00  
> - Preço de venda: R$ 89,90  
> - Estoque mínimo: 3 kg  
> - Fornecedor: Frigorífico Goiás (prazo de entrega: 3 dias)  
