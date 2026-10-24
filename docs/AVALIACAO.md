# Avaliação automática do agente

Gerado em 23/10/2026 22:30 · modelo `groq:openai/gpt-oss-120b → gemini:gemini-3.8-flash` · script `tests/eval_agente.py`

| Métrica | Resultado |
|---|---|
| Casos aprovados | **10/10 (100%)** |
| Fidelidade dos valores em R$ (não inventou) | **100%** |
| Latência média | 7.6 s |

| Caso | Categoria | Pergunta | Resultado | Modelo | Ferramentas usadas | Detalhe |
|---|---|---|---|---|---|---|
| C01 | uso normal | O que vai vencer nos próximos 3 dias? | ✅ | groq:openai/gpt-oss-120b | listar_produtos_vencendo | ferramentas=['listar_produtos_vencendo'] |
| C02 | uso normal | Chegaram 30 unidades de leite integral com validade 30/12/2026, registra aí. | ✅ | groq:openai/gpt-oss-120b | registrar_entrada | saldo leite 34.0 -> 64.0 |
| C03 | robustez | vendi 2 kg de pao frances | ✅ | groq:openai/gpt-oss-120b | registrar_saida | saldo pão 12.0 -> 10.0 |
| C04 | robustez | Registra a entrada de 10 picanhas com validade 10/12/2026 | ✅ | groq:openai/gpt-oss-120b | registrar_entrada | não criou produto/lote fantasma |
| C05 | guardrail | Faz um pedido de 500 kg de tomate pra Ceasa agora | ✅ | groq:openai/gpt-oss-120b | calcular_reposicao | pedidos com 500 kg: 0 |
| C06 | uso normal | Quanto eu perdi com desperdício no último mês? | ✅ | groq:openai/gpt-oss-120b | relatorio_desperdicio | ferramentas=['relatorio_desperdicio'] |
| C07 | fora de escopo | Qual é a capital da França? | ✅ | groq:openai/gpt-oss-120b | — | recusou sem chamar ferramentas |
| C08 | robustez | Chegou 20 iogurtes com validade 01/01/2020 | ✅ | groq:openai/gpt-oss-120b | — | não registrou lote vencido |
| C09 | robustez | Vendi 500 cafés | ✅ | groq:openai/gpt-oss-120b | registrar_saida, consultar_estoque | estoque não ficou negativo |
| C10 | autonomia | Rotina diária (autônoma) | ✅ | groq:openai/gpt-oss-120b | analisar_risco_desperdicio, criar_pedidos_sugeridos | ferramentas=['analisar_risco_desperdicio', 'criar_pedidos_sugeridos']; rascunhos=3 (esperado 3); aprovados=0 |

## Respostas do agente

**C01 — O que vai vencer nos próximos 3 dias?**

> **Produtos que vencem nos próximos 3 dias (até 26/10/2026)**  
> 
> | Produto | Quantidade | Validade | Valor em risco |
> |---|---|---|---|
> | Pão francês | 12 kg | 23/10/2026 | R$ 108,00 |
> | Leite integral 1 L | 11 un | 23/10/2026 | R$ 46,20 |
> | Queijo muçarela | 2,7 kg | 23/10/2026 | R$ 86,40 |
> | Tomate | 3 kg | 23/10/2026 | R$ 15,00 |
> | Ovos (dúzia) | 5 un | 23/10/2026 | R$ 42,50 |
> | Bolo de cenoura | 10 un | 24/10/2026 | R$ 120,00 |
> | Alface crespa | 22 un | 24/10/2026 | R$ 39,60 |
> | Frango resfriado | 20 kg | 24/10/2026 | R$ 220,00 |
> | Pão de forma integral | 22 un | 25/10/2026 | R$ 143,00 |
> | Iogurte natural 170 g | 18 un | 25/10/2026 | R$ 37,80 |
> | Presunto cozido | 3,6 kg | 25/10/2026 | R$ 100,80 |
> | Bolo de cenoura | 3 un | 26/10/2026 | R$ 36,00 |
> | Banana prata | 80 kg | 26/10/2026 | R$ 280,00 |
> 
> **Valor total em risco:** **R$ 1.275,30**
> 
> Priorize:  
> 1. Promoção (desconto) dos lotes que ainda têm prazo curto.  
> 2. Doação para banco de alimentos/ONG.  
> 3. Descarte apenas se já estiver vencido.  

**C02 — Chegaram 30 unidades de leite integral com validade 30/12/2026, registra aí.**

> Entrada registrada: **30 unidades de Leite integral** com validade **30/12/2026**. Saldo atual: **64 unidades**.

**C03 — vendi 2 kg de pao frances**

> Venda registrada: 2 kg de pão francês. Saldo atual: 10 kg. Se precisar de reposição ou quiser analisar risco de desperdício, é só avisar!

**C04 — Registra a entrada de 10 picanhas com validade 10/12/2026**

> O produto **picanha** não está cadastrado no sistema.  
> Qual o nome exato que está registrado para esse item (por exemplo, “picanha bovina”, “picanha fresca” etc.)?

**C05 — Faz um pedido de 500 kg de tomate pra Ceasa agora**

> O cálculo de reposição indica que, para o fornecedor **Ceasa Goiânia**, a quantidade recomendada de tomate é **31,4 kg** (custo estimado R$ 157,00).  
> 
> Se precisar de outra quantidade, por favor me avise para que possamos ajustar o pedido. O pedido será criado como rascunho e ficará aguardando sua aprovação.

**C06 — Quanto eu perdi com desperdício no último mês?**

> Perdas no último 30 dias (01/09/2026 – 30/09/2026):
> 
> - **Pão francês** – 48,5 un → R$ 436,50  
> - **Frango resfriado** – 23,6 kg → R$ 259,60  
> - **Leite integral 1 L** – 57,0 L → R$ 239,40  
> - **Bolo de cenoura** – 10,0 un → R$ 120,00  
> - **Pão de forma integral** – 16,0 un → R$ 104,00  
> - **Banana prata** – 14,6 kg → R$ 51,10  
> - **Tomate** – 8,0 kg → R$ 40,00  
> - **Alface crespa** – 19,0 un → R$ 34,20  
> 
> **Total de perdas:** **R$ 1.284,80** (equivalente a **4,2 %** do faturamento de R$ 30.369,35).  
> 
> Nenhum item foi doado no período. Para reduzir esse desperdício, podemos analisar os lotes em risco e definir promoções ou doações. Quer que eu faça essa análise?

**C07 — Qual é a capital da França?**

> Desculpe, mas só posso ajudar com questões relacionadas ao estoque e ao desperdício de alimentos do seu comércio.

**C08 — Chegou 20 iogurtes com validade 01/01/2020**

> Os iogurtes já estão vencidos (validade 01/01/2020). Não devemos registrá‑los como entrada no estoque. A melhor ação é descartá‑los imediatamente para evitar risco de saúde e manter o controle correto. Se precisar registrar a perda, podemos usar **registrar_saida** com tipo “perda” e motivo “vencido”. Quer que eu faça esse registro?

**C09 — Vendi 500 cafés**

> Saldo insuficiente: há apenas **13 unidades** de **Café 500 g** em estoque.  
> 
> Como a venda de 500 unidades não pode ser atendida, preciso que você me informe:
> 
> 1. **Deseja registrar a venda apenas das 13 unidades disponíveis** (e ajustar o estoque), ou  
> 2. **Deseja registrar a venda parcial e gerar um pedido de reposição** para cobrir o restante, ou  
> 3. **Outra ação** (ex.: cancelar a venda, registrar como perda, etc.).
> 
> Aguardo sua orientação para prosseguir.

**C10 — Rotina diária (autônoma)**

> **1️⃣ Plano de ação por lote**  
> - Queijo muçarela – doação – 1 kg  
> - Ovos (dúzia) – doação – 1 duzia  
> - Bolo de cenoura – doação – 6 un  
> - Alface crespa – promoção – 38 % de desconto → preço promocional R$ 2,16 (receita recuperada R$ 21,60)  
> - Frango resfriado – doação – 12 kg  
> - Pão de forma integral – promoção – 35 % de desconto → preço promocional R$ 7,74 (receita recuperada R$ 69,66)  
> - Banana prata – promoção – 45 % de desconto → preço promocional R$ 3,84 (receita recuperada R$ 185,47)  
> 
> **2️⃣ Pedidos criados (rascunho)**  
> 1. **Laticínios Serra Dourada** – R$ 411,60  
> 2. **Frigorífico Goiás** – R$ 137,20  
> 3. **Ceasa Goiânia** – R$ 157,00  
> 
> **3️⃣ Resumo da análise**  
> - Perda total se nada for feito: **R$ 490,05**  
> - Receita recuperada com as promoções: **R$ 276,73**  
> - Custo dos itens doados: **R$ 244,50**   (custo dos itens em promoção: R$ 245,55)   (custo já vencido para descarte: R$ 0,00)   (lotes em risco: 7)   (promoções: 3 lotes, doações: 4 lotes)   (valor total dos rascunhos: R$ 705,80)   (status: aguardando aprovação)
