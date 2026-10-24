# Business Model Canvas — Ciclo Zero

> **RASCUNHO** preparado a partir do protótipo, da validação (`validacao.md`) e de dados públicos. **Arthur revisa e ajusta.**
> Itens marcados com 🧪 são **hipóteses ainda não validadas** — dizer isso na banca é ponto a favor, não contra.

| Bloco | Conteúdo |
|---|---|
| **1. Segmento de clientes** | Pequenos comércios de alimentos com estoque perecível e **sem sistema de estoque**: padarias, mercadinhos de bairro, hortifrútis, lanchonetes. Perfil inicial: dono/gerente que controla "no olhômetro" ou em caderno (persona validada: Canto Caseiro). **Não-alvo:** redes e franquias com processo já estruturado (ex.: Subway na validação). |
| **2. Proposta de valor** | **"Seu estoque se controla sozinho — e você para de jogar dinheiro fora."** Fotografa a nota e o estoque está lançado (fim do caderno); toda manhã o agente diz o que vai vencer, sugere promoção com preço ou doação, e monta o pedido de compra sem excesso. Números em R$, não em planilha. |
| **3. Canais** | Venda direta porta a porta no bairro (prova de valor com os dados da própria loja); parceria com **Sebrae** e associações de panificação/supermercados; contadores e distribuidores que já atendem esses comércios; boca a boca entre comerciantes. 🧪 |
| **4. Relacionamento** | Self-service com onboarding assistido (cadastro dos produtos na 1ª semana); o agente "conversa" todo dia (rotina da manhã); relatório mensal de quanto a loja economizou. |
| **5. Fontes de receita** | 🧪 Assinatura mensal por loja, faixa a validar (ex.: R$ 49–99/mês), com teste grátis de 30 dias provando a economia em R$ antes de cobrar. Futuro: plano com integração a PDV/ERP e módulo de doação com recibo para ONGs. |
| **6. Recursos-chave** | O agente (ferramentas determinísticas + LLM), a avaliação automática de qualidade, e o **dado de cada loja**: histórico de vendas/perdas e o dicionário de notas que ela ensina ao sistema (melhora com o uso). |
| **7. Atividades-chave** | Evoluir o agente e as ferramentas; onboarding de lojas; monitorar qualidade (fidelidade, erros, latência — já instrumentado); validar preço e canais. |
| **8. Parcerias-chave** | Provedores de IA (Groq, Google Gemini; AWS via AKCIT); Sebrae/associações do varejo alimentar; **bancos de alimentos e ONGs** (destino da doação); fornecedores (pedido automático). |
| **9. Estrutura de custos** | IA por uso (uma rotina diária = ~2 chamadas ao modelo; leitura de nota = 1 chamada) — 🧪 estimativa de poucos reais por loja/mês em escala; hospedagem; aquisição de clientes (visita/parcerias); suporte. |

## Por que agora / por que nós
- Perdas no varejo alimentar são reais e medidas: supermercados perdem **1,79% do faturamento**, chegando a **5,25% em FLV** e **2,74% em padaria** (ABRAS, 2020). Pequenos comércios, sem sistema, tendem a não medir — e por isso não percebem.
- Agentes de IA com visão e ferramentas tornaram viável um "funcionário de estoque" barato para quem nunca teria um ERP.

## Diferencial frente às alternativas
| Alternativa | Limitação | Ciclo Zero |
|---|---|---|
| Caderno / "olhômetro" | Horas por dia anotando; não avisa nada | Foto da nota lança tudo; avisa antes de vencer |
| Planilha (ex.: modelo do Sebrae) | Manual, sem previsão, sem ação | Calcula sobra por lote e age (promoção, doação, pedido) |
| ERP de supermercado | Caro, complexo, feito para redes | Assinatura de baixo custo, conversa em português, sem treinamento |

## Fontes
- ABRAS — 21ª Avaliação de Perdas no Varejo Brasileiro de Supermercados (2020), via Super Rádio Tupi (16/04/2021): https://www.tupi.fm/?p=515195
- PNUMA — Índice de Desperdício de Alimentos 2021 (17% dos alimentos disponíveis ao consumidor desperdiçados, dado global): https://www.unep.org/pt-br/noticias-e-reportagens/comunicado-de-imprensa/pnuma-e-fao-convocam-movimento-no-brasil-para-reduzir
- Validação própria: `docs/validacao.md` (2 entrevistas, 23/10/2026)
