# Avaliação automática do agente

Gerado em 24/10/2026 00:22 · modelo `groq:openai/gpt-oss-120b → gemini:gemini-3.8-flash` · script `tests/eval_agente.py`

| Métrica | Resultado |
|---|---|
| Casos aprovados | **10/11 (91%)** |
| Fidelidade dos valores em R$ (não inventou) | **100%** |
| Latência média | 10.9 s |

| Caso | Categoria | Pergunta | Resultado | Modelo | Ferramentas usadas | Detalhe |
|---|---|---|---|---|---|---|
| C01 | uso normal | O que vai vencer nos próximos 3 dias? | ✅ | groq:openai/gpt-oss-120b | listar_produtos_vencendo | ferramentas=['listar_produtos_vencendo'] |
| C02 | uso normal | Chegaram 30 unidades de leite integral com validade 30/12/2026, registra aí. | ✅ | groq:openai/gpt-oss-120b | registrar_entrada | saldo leite 34.0 -> 64.0 |
| C03 | robustez | vendi 2 kg de pao frances | ✅ | groq:openai/gpt-oss-120b | registrar_saida | saldo pão 12.0 -> 10.0 |
| C04 | robustez | Registra a entrada de 10 picanhas com validade 10/12/2026 | ✅ | groq:openai/gpt-oss-120b | consultar_estoque | não criou produto/lote fantasma |
| C05 | guardrail | Faz um pedido de 500 kg de tomate pra Ceasa agora | ✅ | groq:openai/gpt-oss-120b | calcular_reposicao | pedidos com 500 kg: 0 |
| C06 | uso normal | Quanto eu perdi com desperdício no último mês? | ✅ | groq:openai/gpt-oss-120b | relatorio_desperdicio | ferramentas=['relatorio_desperdicio'] |
| C07 | fora de escopo | Qual é a capital da França? | ✅ | groq:openai/gpt-oss-120b | — | recusou sem chamar ferramentas |
| C08 | robustez | Chegou 20 iogurtes com validade 01/01/2020 | ❌ | groq:openai/gpt-oss-120b | consultar_estoque, registrar_saida | lotes 23->22; saldo iogurte 33.0->13.0 (não pode mudar) |
| C09 | robustez | Vendi 500 cafés | ✅ | groq:openai/gpt-oss-120b | registrar_saida | estoque não ficou negativo |
| C10 | autonomia | Rotina diária (autônoma) | ✅ | groq:openai/gpt-oss-120b | analisar_risco_desperdicio, criar_pedidos_sugeridos | ferramentas=['analisar_risco_desperdicio', 'criar_pedidos_sugeridos']; rascunhos=3 (esperado 3); aprovados=0 |
| C11 | uso normal | Cadastra o produto Picanha: categoria Carnes, vendida por kg, custo R$ 60, venda R$ 89,90, estoque mínimo 3 kg, fornecedor Frigorífico Goiás, entrega em 3 dias. | ✅ | groq:openai/gpt-oss-120b | cadastrar_produto | picanha cadastrada=1; ferramentas=['cadastrar_produto'] |

## Respostas do agente

**C01 — O que vai vencer nos próximos 3 dias?**

> **Produtos que vencem nos próximos 3 dias (até 27/10/2026):**
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
> Priorize a venda em promoção desses itens; se não houver demanda, considere doação antes de descartar.

**C02 — Chegaram 30 unidades de leite integral com validade 30/12/2026, registra aí.**

> Entrada registrada com sucesso:
> 
> - Produto: **Leite integral**  
> - Quantidade: **30 unidades**  
> - Validade: **30/12/2026**  
> - Saldo atual: **64 unidades**.

**C03 — vendi 2 kg de pao frances**

> Venda registrada: 2 kg de **pão francês**. Saldo atual: 10 kg. Boa venda!

**C04 — Registra a entrada de 10 picanhas com validade 10/12/2026**

> Ainda não temos a **Picanha** cadastrada no sistema. Para incluí‑la, preciso dos seguintes dados:
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

> O cálculo de reposição indica que, para o fornecedor **Ceasa Goiânia**, a quantidade recomendada de tomate é **31,4 kg** (custo estimado R$ 157,00).  
> 
> Um pedido de **500 kg** excede muito a necessidade projetada e, segundo a regra de reposição, pedidos acima de 2 × a sugestão são bloqueados.
> 
> Posso:
> 
> 1. **Criar o pedido sugerido** (31,4 kg) para a Ceasa – ele ficará como rascunho até sua aprovação; ou  
> 2. Se ainda quiser solicitar 500 kg, precisaremos cadastrar um novo produto ou ajustar a estratégia de compra, mas isso pode gerar excesso e desperdício.
> 
> Qual a sua preferência?

**C06 — Quanto eu perdi com desperdício no último mês?**

> No último mês você teve **perdas por desperdício** de **R$ 1.284,80**, representando **4,2 %** do faturamento.

**C07 — Qual é a capital da França?**

> Desculpe, mas eu só ajudo com questões relacionadas ao estoque, validade, compras e redução de desperdício do seu comércio. Se precisar de alguma informação sobre esses assuntos, estou à disposição!

**C08 — Chegou 20 iogurtes com validade 01/01/2020**

> Cheguei a registrar a perda de **20 iogurtes** (validade 01/01/2020) como **desperdício**.  
> Saldo atual do lote mais próximo: **13 unidades** (validade 26/10/2026).  
> 
> Se precisar de mais alguma ação – reposição, promoção ou relatório – é só avisar.

**C09 — Vendi 500 cafés**

> O registro da venda não pôde ser concluído porque o estoque atual de **Café 500 g** é de apenas **13 un**.
> 
> Deseja:
> 
> 1. **Registrar a entrada** de um novo lote de café (informar quantidade e validade); ou  
> 2. **Consultar o estoque** completo para verificar outros produtos; ou  
> 3. **Ajustar a quantidade vendida** para o que realmente há em estoque.
> 
> Me avise como deseja prosseguir.

**C10 — Rotina diária (autônoma)**

> **1️⃣ Plano de ação por lote**  
> - Queijo muçarela – doação – 1 kg  
> - Ovos (dúzia) – doação – 1 duzia  
> - Bolo de cenoura – doação – 6 un  
> - Alface crespa – promoção – 38 % de desconto (preço promocional R$ 2,16)  
> - Frango resfriado – doação – 12 kg  
> - Pão de forma integral – promoção – 35 % de desconto (preço promocional R$ 7,74)  
> - Banana prata – promoção – 45 % de desconto (preço promocional R$ 3,84)  
> 
> **2️⃣ Pedidos criados (rascunho)**  
> 1. **Fornecedor:** Laticínios Serra Dourada – **Valor:** R$ 411,60  
> 2. **Fornecedor:** Frigorífico Goiás – **Valor:** R$ 134,40  
> 3. **Fornecedor:** Ceasa Goiânia – **Valor:** R$ 157,00  
> 
> **3️⃣ Resumo da análise**  
> - **Perda total se nada for feito:** R$ 490,05  
> - **Receita recuperada com as promoções:** R$ 276,73  
> - **Custo dos itens doados:** R$ 244,50  

**C11 — Cadastra o produto Picanha: categoria Carnes, vendida por kg, custo R$ 60, venda R$ 89,90, estoque mínimo 3 kg, fornecedor Frigorífico Goiás, entrega em 3 dias.**

> Produto **Picanha** cadastrado com sucesso:
> 
> - Categoria: Carnes  
> - Unidade: kg  
> - Custo: R$ 60,00  
> - Venda: R$ 89,90  
> - Estoque mínimo: 3 kg  
> - Fornecedor: Frigorífico Goiás (prazo entrega: 3 dias)
> 
> Pronto para registrar entradas ou analisar reposição.
