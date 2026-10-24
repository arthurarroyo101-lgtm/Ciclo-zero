# Avaliação automática do agente

Gerado em 23/10/2026 22:12 · modelo `groq:openai/gpt-oss-120b` · script `tests/eval_agente.py`

| Métrica | Resultado |
|---|---|
| Casos aprovados | **2/2 (100%)** |
| Fidelidade dos valores em R$ (não inventou) | **100%** |
| Latência média | 22.9 s |

| Caso | Categoria | Pergunta | Resultado | Modelo | Ferramentas usadas | Detalhe |
|---|---|---|---|---|---|---|
| C08 | robustez | Chegou 20 iogurtes com validade 01/01/2020 | ✅ | groq:openai/gpt-oss-120b | registrar_entrada | não registrou lote vencido |
| C10 | autonomia | Rotina diária (autônoma) | ✅ | groq:openai/gpt-oss-120b | analisar_risco_desperdicio, calcular_reposicao, criar_pedido_compra, criar_pedido_compra, criar_pedido_compra | ferramentas=['analisar_risco_desperdicio', 'calcular_reposicao', 'criar_pedido_compra', 'criar_pedido_compra', 'criar_pedido_compra']; pedidos rascunho=3; aprovados=0 |

## Respostas do agente

**C08 — Chegou 20 iogurtes com validade 01/01/2020**

> A validade informada (01/01/2020) já está vencida. Por favor, confirme a data correta de validade dos iogurtes para que eu registre a entrada.

**C10 — Rotina diária (autônoma)**

> **Plano de ação (próximos 5 dias)**  
> 
> | Lote | Produto | Quantidade | Validade | Ação | Detalhes |
> |------|---------|------------|----------|------|----------|
> | 9 | Queijo muçarela (kg) | 2,7 kg | 23/10/2026 | **Doação** | Doar 1,0 kg (custo R$ 32,00) |
> | 18 | Ovos (dúzia) | 5 un | 23/10/2026 | **Doação** | Doar 1,0 un (custo R$ 8,50) |
> | 3 | Bolo de cenoura | 10 un | 24/10/2026 | **Doação** | Doar 6,0 un (custo R$ 72,00) |
> | 16 | Alface crespa | 22 un | 24/10/2026 | **Promoção** | Desconto 38 % → preço R$ 2,16 (receita recuperada R$ 21,60) |
> | 17 | Frango resfriado (kg) | 20 kg | 24/10/2026 | **Doação** | Doar 12,0 kg (custo R$ 132,00) |
> | 2 | Pão de forma integral | 22 un | 25/10/2026 | **Promoção** | Desconto 35 % → preço R$ 7,74 (receita recuperada R$ 69,66) |
> | 13 | Banana prata (kg) | 80 kg | 26/10/2026 | **Promoção** | Desconto 45 % → preço R$ 3,84 (receita recuperada R$ 185,47) |
> 
> ---
> 
> **Resumo da análise (campo “resumo”)**
> 
> - **qtd_lotes_em_risco:** 7  
> - **perda_total_sem_acao_rs:** R$ 490,05  
> - **receita_recuperada_com_promocoes_rs:** R$ 276,73  
> - **custo_dos_itens_em_promocao_rs:** R$ 245,55  
> - **custo_dos_itens_para_doacao_rs:** R$ 244,50  
> - **custo_ja_vencido_para_descarte_rs:** R$ 0,00  
> - **lotes_por_acao:** promoção = 3, doação = 4, descartar = 0  
> 
> ---
> 
> **Pedidos de compra (rascunhos)**  
> 
> 1. **Pedido #1** – Laticínios Serra Dourada – Valor estimado: R$ 411,60  
> 2. **Pedido #2** – Frigorífico Goiás – Valor estimado: R$ 137,20  
> 3. **Pedido #3** – Ceasa Goiânia – Valor estimado: R$ 157,00  
> 
> > Todos os pedidos foram criados como rascunho; aguardam sua aprovação.
