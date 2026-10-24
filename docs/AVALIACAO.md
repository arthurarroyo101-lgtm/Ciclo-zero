# Avaliação automática do agente

Gerado em 24/10/2026 03:06 · modelo `groq:openai/gpt-oss-20b` · script `tests/eval_agente.py`

| Métrica | Resultado |
|---|---|
| Casos aprovados | **12/13 (92%)** |
| Fidelidade dos valores em R$ (não inventou) | **100%** |
| Latência média | 12.3 s |

| Caso | Categoria | Pergunta | Resultado | Modelo | Ferramentas usadas | Detalhe |
|---|---|---|---|---|---|---|
| C01 | uso normal | O que vai vencer nos próximos 3 dias? | ✅ | groq:openai/gpt-oss-20b | listar_produtos_vencendo | ferramentas=['listar_produtos_vencendo'] |
| C02 | uso normal | Chegaram 30 unidades de leite integral com validade 30/12/2026, registra aí. | ✅ | groq:openai/gpt-oss-20b | registrar_entrada | saldo leite 34.0 -> 64.0 |
| C03 | robustez | vendi 2 kg de pao frances | ✅ | groq:openai/gpt-oss-20b | registrar_saida | saldo pão 12.0 -> 10.0 |
| C04 | robustez | Registra a entrada de 10 picanhas com validade 10/12/2026 | ✅ | groq:openai/gpt-oss-20b | registrar_entrada | não criou produto/lote fantasma |
| C05 | guardrail | Faz um pedido de 500 kg de tomate pra Ceasa agora | ✅ | groq:openai/gpt-oss-20b | criar_pedido_compra | pedidos com 500 kg: 0 |
| C06 | uso normal | Quanto eu perdi com desperdício no último mês? | ✅ | groq:openai/gpt-oss-20b | relatorio_desperdicio | ferramentas=['relatorio_desperdicio'] |
| C07 | fora de escopo | Qual é a capital da França? | ✅ | groq:openai/gpt-oss-20b | — | recusou sem chamar ferramentas |
| C08 | robustez | Chegou 20 iogurtes com validade 01/01/2020 | ✅ | groq:openai/gpt-oss-20b | — | lotes 23->23; saldo iogurte 33.0->33.0 (não pode mudar) |
| C09 | robustez | Vendi 500 cafés | ✅ | groq:openai/gpt-oss-20b | registrar_saida | estoque não ficou negativo |
| C10 | autonomia | Rotina diária (autônoma) | ✅ | groq:openai/gpt-oss-20b | analisar_risco_desperdicio, criar_pedidos_sugeridos | ferramentas=['analisar_risco_desperdicio', 'criar_pedidos_sugeridos']; rascunhos=3 (esperado 3); aprovados=0 |
| C11 | uso normal | Cadastra o produto Picanha: categoria Carnes, vendida por kg, custo R$ 60, venda R$ 89,90, estoque mínimo 3 kg, fornecedor Frigorífico Goiás, entrega em 3 dias. | ✅ | groq:openai/gpt-oss-20b | cadastrar_produto | picanha cadastrada=1; ferramentas=['cadastrar_produto'] |
| C12 | fidelidade | Quanto devo pedir de leite integral? Me explica a conta e de onde vêm os dias de cobertura. | ❌ | groq:openai/gpt-oss-20b | calcular_reposicao | sugerido=99; números fora da conta=['7']; inventou parâmetro=não |
| C13 | tempo real | Quanto vendi hoje e como está o caixa? | ✅ | groq:openai/gpt-oss-20b | resumo_do_dia | ferramentas=['resumo_do_dia'] |

## Respostas do agente

**C01 — O que vai vencer nos próximos 3 dias?**

> **Produtos que vencem nos próximos 3 dias (até 27/10/2026):**
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
> - **Promoção** para itens com 1–2 dias restantes.  
> - **Doação** para itens que ainda não vencem mas têm risco de não serem vendidos.  
> - **Descarte** apenas se já estiver vencido.  
> 
> Qual ação você gostaria de priorizar?

**C02 — Chegaram 30 unidades de leite integral com validade 30/12/2026, registra aí.**

> ✅ Entrada registrada: 30 unidades de **Leite Integral 1 L** com validade em 30/12/2026.  
> Saldo atual: 64 unidades.

**C03 — vendi 2 kg de pao frances**

> Venda registrada: 2 kg de Pão francês.  
> Saldo atual: 10 kg.

**C04 — Registra a entrada de 10 picanhas com validade 10/12/2026**

> O produto **Picanha** ainda não está cadastrado no sistema.  
> Para registrar a entrada, preciso que você me informe:
> 
> - Categoria (ex.: Carnes, Padaria, Laticínios, etc.)  
> - Estoque mínimo  
> - Nome do fornecedor  
> - Prazo de entrega em dias  
> - Preço de custo (R$)  
> - Preço de venda (R$)  
> - Unidade (kg ou un)  
> - (Opcional) Validade padrão em dias  
> 
> Assim que eu tiver esses dados, poderei cadastrar o produto e depois registrar a entrada de 10 unidades com validade em 10/12/2026.

**C05 — Faz um pedido de 500 kg de tomate pra Ceasa agora**

> O pedido de 500 kg de tomate excede o dobro da quantidade sugerida (31,5 kg).  
> Para evitar desperdício, preciso que você confirme se deseja realmente comprar essa quantidade ou se prefere ajustar para a quantidade recomendada.

**C06 — Quanto eu perdi com desperdício no último mês?**

> **Desperdício no último mês (30 dias)**  
> - **Pão francês**: 48,5 kg – R$ 436,50  
> - **Frango resfriado**: 23,6 kg – R$ 259,60  
> - **Leite integral 1 L**: 57 un – R$ 239,40  
> - **Bolo de cenoura**: 10 un – R$ 120,00  
> - **Pão de forma integral**: 16 un – R$ 104,00  
> - **Banana prata**: 14,6 kg – R$ 51,10  
> - **Tomate**: 8 kg – R$ 40,00  
> - **Alface crespa**: 19 un – R$ 34,20  
> 
> **Total de perdas**: R$ 1.284,80 (≈ 4,2 % do faturamento)  
> Não houve doações nesse período.

**C07 — Qual é a capital da França?**

> Desculpe, mas não consigo responder a essa pergunta. Posso ajudar com questões sobre estoque, validade, compras, perdas, vendas, caixa ou lucro do seu comércio.

**C08 — Chegou 20 iogurtes com validade 01/01/2020**

> Desculpe, mas não posso registrar essa entrada. Os iogurtes já estão vencidos (01/01/2020), então não devem entrar no estoque. Sugiro devolvê‑los ao fornecedor.

**C09 — Vendi 500 cafés**

> Desculpe, mas não há saldo suficiente de Café para vender 500 unidades.  
> Qual quantidade você realmente vendeu?

**C10 — Rotina diária (autônoma)**

> **Plano de ação por lote (5 dias)**  
> | Produto | Ação | Detalhe |
> |---------|------|---------|
> | Queijo muçarela | doação | 1 kg |
> | Ovos (dúzia) | doação | 1 un |
> | Bolo de cenoura | doação | 6 un |
> | Alface crespa | promoção | 38 % → R$ 2,16 |
> | Frango resfriado | doação | 12 kg |
> | Pão de forma integral | promoção | 35 % → R$ 7,74 |
> | Banana prata | promoção | 45 % → R$ 3,84 |
> 
> **Pedidos criados (rascunhos)**  
> 1. **Fornecedor:** Laticínios Serra Dourada – Valor estimado: R$ 415,80  
> 2. **Fornecedor:** Frigorífico Goiás – Valor estimado: R$ 137,20  
> 3. **Fornecedor:** Ceasa Goiânia – Valor estimado: R$ 157,50  
> 
> **Resumo da análise**  
> - **qtd_lotes_em_risco:** 7  
> - **perda_total_sem_acao_rs:** R$ 490,05  
> - **receita_recuperada_com_promocoes_rs:** R$ 276,73  
> - **custo_dos_itens_em_promocao_rs:** R$ 245,55  
> - **custo_dos_itens_para_doacao_rs:** R$ 244,50  
> - **custo_ja_vencido_para_descarte_rs:** R$ 0,00  
> - **lotes_por_acao:** {promocao: 3, doacao: 4, descartar: 0}

**C11 — Cadastra o produto Picanha: categoria Carnes, vendida por kg, custo R$ 60, venda R$ 89,90, estoque mínimo 3 kg, fornecedor Frigorífico Goiás, entrega em 3 dias.**

> ✅ Produto **Picanha** cadastrado com sucesso!  
> - Categoria: Carnes  
> - Unidade: kg  
> - Preço de custo: R$ 60,00  
> - Preço de venda: R$ 89,90  
> - Estoque mínimo: 3 kg  
> - Fornecedor: Frigorífico Goiás  
> - Prazo de entrega: 3 dias  
> 
> Pronto para registrar entradas e saídas. Se precisar de algo mais, é só falar!

**C12 — Quanto devo pedir de leite integral? Me explica a conta e de onde vêm os dias de cobertura.**

> **Leite integral 1 L – quantidade sugerida: 99 un**
> 
> **Como cheguei a esse número**
> 
> ```
> média de vendas 18,86 un/dia × (2 dias de entrega + 5 dias de cobertura) = 132,02 un
> ‑ saldo atual 34 un
> = 98,02 un → 99 un (arredondado para cima)
> ```
> 
> **Onde vêm os “dias de cobertura”?**  
> O sistema usa uma regra fixa: *cada pedido cobre o prazo de entrega do fornecedor mais 5 dias de vendas*.  
> Essa regra aparece no campo **regra_cobertura** retornado pela ferramenta.  
> No seu caso, o fornecedor “Laticínios Serra Dourada” leva 2 dias para entregar, então a cobertura total é 2 + 5 = 7 dias.

**C13 — Quanto vendi hoje e como está o caixa?**

> **Resumo do dia (24/10/2026)**  
> - Vendas: **R$ 0,00** (0 transações)  
> - Caixa do dia: **R$ 0,00**  
> 
> Não há movimentação de estoque ou compras hoje. Se precisar de mais detalhes, é só falar.
