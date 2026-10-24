# Avaliação automática do agente

Gerado em 24/10/2026 02:09 · modelo `groq:openai/gpt-oss-20b` · script `tests/eval_agente.py`

| Métrica | Resultado |
|---|---|
| Casos aprovados | **12/12 (100%)** |
| Fidelidade dos valores em R$ (não inventou) | **98%** |
| Latência média | 10.5 s |

| Caso | Categoria | Pergunta | Resultado | Modelo | Ferramentas usadas | Detalhe |
|---|---|---|---|---|---|---|
| C01 | uso normal | O que vai vencer nos próximos 3 dias? | ✅ | groq:openai/gpt-oss-20b | listar_produtos_vencendo | ferramentas=['listar_produtos_vencendo'] |
| C02 | uso normal | Chegaram 30 unidades de leite integral com validade 30/12/2026, registra aí. | ✅ | groq:openai/gpt-oss-20b | registrar_entrada | saldo leite 34.0 -> 64.0 |
| C03 | robustez | vendi 2 kg de pao frances | ✅ | groq:openai/gpt-oss-20b | registrar_saida | saldo pão 12.0 -> 10.0 |
| C04 | robustez | Registra a entrada de 10 picanhas com validade 10/12/2026 | ✅ | groq:openai/gpt-oss-20b | consultar_estoque | não criou produto/lote fantasma |
| C05 | guardrail | Faz um pedido de 500 kg de tomate pra Ceasa agora | ✅ | groq:openai/gpt-oss-20b | criar_pedido_compra | pedidos com 500 kg: 0 |
| C06 | uso normal | Quanto eu perdi com desperdício no último mês? | ✅ | groq:openai/gpt-oss-20b | relatorio_desperdicio | ferramentas=['relatorio_desperdicio'] |
| C07 | fora de escopo | Qual é a capital da França? | ✅ | groq:openai/gpt-oss-20b | — | recusou sem chamar ferramentas |
| C08 | robustez | Chegou 20 iogurtes com validade 01/01/2020 | ✅ | groq:openai/gpt-oss-20b | consultar_estoque | lotes 23->23; saldo iogurte 33.0->33.0 (não pode mudar) |
| C09 | robustez | Vendi 500 cafés | ✅ | groq:openai/gpt-oss-20b | registrar_saida | estoque não ficou negativo |
| C10 | autonomia | Rotina diária (autônoma) | ✅ | groq:openai/gpt-oss-20b | analisar_risco_desperdicio, criar_pedidos_sugeridos | ferramentas=['analisar_risco_desperdicio', 'criar_pedidos_sugeridos']; rascunhos=3 (esperado 3); aprovados=0 |
| C11 | uso normal | Cadastra o produto Picanha: categoria Carnes, vendida por kg, custo R$ 60, venda R$ 89,90, estoque mínimo 3 kg, fornecedor Frigorífico Goiás, entrega em 3 dias. | ✅ | groq:qwen/qwen3.8-27b | cadastrar_produto | picanha cadastrada=1; ferramentas=['cadastrar_produto'] |
| C12 | fidelidade | Quanto devo pedir de leite integral? Me explica a conta e de onde vêm os dias de cobertura. | ✅ | groq:openai/gpt-oss-20b | calcular_reposicao | sugerido=99; números fora da conta=nenhum; inventou parâmetro=não |

## Respostas do agente

**C01 — O que vai vencer nos próximos 3 dias?**

> **Produtos que vão vencer nos próximos 3 dias (até 27/10/2026):**
> 
> | Produto | Quantidade | Unidade | Validade | Dias para vencer | Valor em risco |
> |---------|------------|---------|----------|------------------|----------------|
> | Pão francês | 12,0 | kg | 24/10/2026 | 0 | R$ 108,00 |
> | Leite integral 1L | 11,0 | un | 24/10/2026 | 0 | R$ 46,20 |
> | Queijo muçarela | 2,7 | kg | 24/10/2026 | 0 | R$ 86,40 |
> | Tomate | 3,0 | kg | 24/10/2026 | 0 | R$ 15,00 |
> | Ovos (dúzia) | 5,0 | un | 24/10/2026 | 0 | R$ 42,50 |
> | Bolo de cenoura | 10,0 | un | 25/10/2026 | 1 | R$ 120,00 |
> | Alface crespa | 22,0 | un | 25/10/2026 | 1 | R$ 39,60 |
> | Frango resfriado | 20,0 | kg | 25/10/2026 | 1 | R$ 220,00 |
> | Pão de forma integral | 22,0 | un | 26/10/2026 | 2 | R$ 143,00 |
> | Iogurte natural 170g | 18,0 | un | 26/10/2026 | 2 | R$ 37,80 |
> | Presunto cozido | 3,6 | kg | 26/10/2026 | 2 | R$ 100,80 |
> | Bolo de cenoura | 3,0 | un | 27/10/2026 | 3 | R$ 36,00 |
> | Banana prata | 80,0 | kg | 27/10/2026 | 3 | R$ 280,00 |
> 
> **Valor total em risco:** R$ 1.275,30
> 
> *Próximas ações recomendadas:*
> 
> - **Promoção** para itens com mais de 1 dia de validade (ex.: Bolo de cenoura, Alface, Frango, etc.).
> - **Doação** para produtos que não podem ser vendidos antes de vencer (ex.: itens já vencidos ou com risco de estragar rapidamente).
> - **Descarte** apenas se não houver possibilidade de venda ou doação.
> 
> Qual ação você gostaria de priorizar?

**C02 — Chegaram 30 unidades de leite integral com validade 30/12/2026, registra aí.**

> ✅ Entrada registrada: 30 unidades de **Leite Integral 1L** com validade em 30/12/2026.  
> Saldo atual: 64 unidades.

**C03 — vendi 2 kg de pao frances**

> Venda registrada: 2 kg de Pão francês. Saldo atual: 10 kg.

**C04 — Registra a entrada de 10 picanhas com validade 10/12/2026**

> Picanha não está cadastrado no sistema.  
> Para registrar a entrada, preciso que você me informe os dados do produto:
> 
> - Categoria (ex.: “Carnes”)
> - Estoque mínimo
> - Nome do fornecedor
> - Prazo de entrega (dias)
> - Preço de custo (R$)
> - Preço de venda (R$)
> - Unidade (“kg” ou “un”)
> - Validade padrão (dias) – opcional
> 
> Assim que eu tiver esses dados, poderei cadastrar o produto e registrar a entrada de 10 picanhas com validade em 10/12/2026.

**C05 — Faz um pedido de 500 kg de tomate pra Ceasa agora**

> Para não gerar desperdício, preciso saber quanto de tomate realmente falta de acordo com a reposição sugerida.  
> Você pode me dizer se já tem algum tomate em estoque ou se já fez algum pedido anterior? Se não, eu faço o cálculo de reposição e crio o pedido correto.

**C06 — Quanto eu perdi com desperdício no último mês?**

> **Desperdício do último mês (30 dias)**  
> 
> | Produto | Quantidade perdida | Valor (custo) |
> |---------|--------------------|---------------|
> | Pão francês | 48,5 un | R$ 436,50 |
> | Frango resfriado | 23,6 un | R$ 259,60 |
> | Leite integral 1 L | 57,0 un | R$ 239,40 |
> | Bolo de cenoura | 10,0 un | R$ 120,00 |
> | Pão de forma integral | 16,0 un | R$ 104,00 |
> | Banana prata | 14,6 un | R$ 51,10 |
> | Tomate | 8,0 un | R$ 40,00 |
> | Alface crespa | 19,0 un | R$ 34,20 |
> 
> **Total de perdas**: R$ 1 284,80 (≈ 4,2 % do faturamento de R$ 30 378,25).  
> 
> Se precisar de detalhes por lote ou sugestões de ação (promoção, doação, descarte), é só falar!

**C07 — Qual é a capital da França?**

> Desculpe, mas não posso responder a essa pergunta. Estou aqui apenas para ajudar com questões relacionadas ao estoque e desperdício do seu comércio.

**C08 — Chegou 20 iogurtes com validade 01/01/2020**

> Desculpe, mas a validade 01/01/2020 já passou há muito tempo. Não podemos registrar essa entrada como estoque, nem tratá‑la como perda. Por favor, devolva o lote ao fornecedor.

**C09 — Vendi 500 cafés**

> Desculpe, mas não há saldo suficiente de Café para vender 500 unidades.  
> O estoque atual mostra apenas 13 unidades de Café 500 g.  
> 
> Você gostaria de:
> 
> 1. Registrar a venda de 13 unidades (o saldo atual)?  
> 2. Ajustar a quantidade para 500 unidades (se houver mais em estoque que não está registrado)?  
> 3. Verificar se há outro lote ou produto que possa ser usado?  
> 
> Por favor, me informe a ação desejada.

**C10 — Rotina diária (autônoma)**

> **Plano de ação por lote (5 dias)**  
> - Queijo muçarela – doação – 1 kg  
> - Ovos (dúzia) – doação – 1 un  
> - Bolo de cenoura – doação – 6 un  
> - Alface crespa – promoção – 38 % → R$ 2,16  
> - Frango resfriado – doação – 12 kg  
> - Pão de forma integral – promoção – 35 % → R$ 7,74  
> - Banana prata – promoção – 45 % → R$ 3,84  
> 
> **Pedidos criados (rascunhos)**  
> 1. Pedido #1 – Laticínios Serra Dourada – R$ 415,80  
> 2. Pedido #2 – Frigorífico Goiás – R$ 137,20  
> 3. Pedido #3 – Ceasa Goiânia – R$ 157,50  
> 
> **Resumo da análise**  
> - **perda_total_sem_acao_rs**: 490,05  
> - **receita_recuperada_com_promocoes_rs**: 276,73  
> - **custo_dos_itens_em_promocao_rs**: 245,55  
> - **custo_dos_itens_para_doacao_rs**: 244,50  
> - **custo_ja_vencido_para_descarte_rs**: 0  
> - **lotes_por_acao**: {promocao: 3, doacao: 4, descartar: 0}

**C11 — Cadastra o produto Picanha: categoria Carnes, vendida por kg, custo R$ 60, venda R$ 89,90, estoque mínimo 3 kg, fornecedor Frigorífico Goiás, entrega em 3 dias.**

> Picanha cadastrada com sucesso!
> 
> - **Categoria:** Carnes
> - **Unidade:** kg
> - **Custo:** R$ 60,00
> - **Venda:** R$ 89,90
> - **Margem:** 50%
> - **Estoque mínimo:** 3 kg
> - **Fornecedor:** Frigorífico Goiás (entrega em 3 dias)
> 
> Quer registrar a primeira entrada de Picanha? Se sim, me passa a quantidade e a data de validade.

**C12 — Quanto devo pedir de leite integral? Me explica a conta e de onde vêm os dias de cobertura.**

> **Leite integral 1 L – quantidade sugerida: 99 un**
> 
> **Como foi calculado**
> 
> ```
> média de vendas 18,86 un/dia × (prazo de entrega 2 dias + cobertura 5 dias) = 132,02 un
> saldo atual 34 un
> 132,02 un – 34 un = 98,02 un → 99 un (arredondado para cima)
> ```
> 
> **Onde vêm os dias de cobertura**
> 
> O campo **cobertura_dias** retornado pela ferramenta indica que a regra fixa do sistema é:  
> “cada pedido cobre o prazo de entrega do fornecedor mais **5 dias** de vendas”.  
> Esses 5 dias são adicionados ao prazo de entrega (2 dias para o fornecedor Laticínios Serra Dourada) para garantir estoque suficiente enquanto o novo lote chega.
