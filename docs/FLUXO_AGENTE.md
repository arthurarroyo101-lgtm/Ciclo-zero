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
| **Foto da nota fiscal** (multimodal) | Foto/print da nota do fornecedor → visão computacional extrai os itens → lotes entram no estoque após conferência |
| Vendas do caixa (tempo real) | Na demo, `ciclozero/ao_vivo.py` simula o caixa: vendas proporcionais à média de cada produto, baixando do lote que vence primeiro. Numa loja real, viriam da integração com o PDV. |
| Mensagem do usuário | "Vendi 5 kg de pão", "o que vai vencer essa semana?", "faz o pedido da Ceasa" |
| Rotina diária (modo autônomo) | Botão "Rodar rotina diária" — o agente checa tudo sozinho, sem pergunta |
| Base de dados | Produtos, lotes com validade, 30 dias de vendas e perdas, fornecedores e prazos de entrega |

## Entrada multimodal: foto da nota fiscal
A dor mais citada na validação foi o **trabalho manual de anotar o que chega** ("no olhômetro", horas por dia). Por isso a entrada de mercadoria pode ser feita por **foto da nota**:

```
foto da nota ──► modelo de visão (Gemini; reserva: Groq/Llama 4) ──► JSON: fornecedor, nº, total, itens
            ──► verificação: soma dos itens = total da nota? quantidade × unitário = total do item?
            ──► conciliação: cada item ↔ produto do cadastro (+ validade padrão do produto, aviso de custo diferente)
            ──► tabela editável: o dono confere e confirma  (nada entra sem confirmação)
            ──► lotes lançados pelas MESMAS ferramentas do agente (mesmas validações)
            ──► o agente avalia na hora se a compra vai gerar sobra (ex.: 40 kg de banana para 8 kg/dia de venda)
```
- **Qualidade da leitura medida sem gabarito:** se a soma dos itens bate com o total impresso, a leitura é marcada como verificada; se não, a tela pede atenção.
- **Item desconhecido** (ex.: manteiga não cadastrada) não é lançado; o dono cadastra pelo chat.
- **Aprende com a loja (ativo próprio):** toda associação confirmada ou corrigida pelo dono ("IOG NAT DANONE 170G" → Iogurte natural 170g) é guardada na tabela `apelidos`. Na próxima nota, o item sai associado com confiança 100% e a coluna "Como associou" mostra "aprendido (Nx)". Cada loja constrói o próprio dicionário de fornecedores/produtos — dado proprietário que melhora com o uso.
- Código: `ciclozero/nota_fiscal.py` · tela: `ciclozero/ui_nota.py` · teste offline: `python -m tests.test_nota_fiscal`.

## Ferramentas (o que o agente sabe fazer)
| Ferramenta | O que faz |
|---|---|
| `consultar_estoque` | Saldo, validade mais próxima, média de vendas/dia, abaixo do mínimo |
| `cadastrar_produto` | Cadastra produto novo com os dados que o usuário informar (bloqueia duplicado e nome parecido; nunca inventa preço) |
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
| Agente "contornar" uma recusa (ex.: entrada vencida recusada → lançar como perda; inventar outra validade) | Bloqueado no código: depois de uma alteração recusada, outra alteração diferente (ou nova validade inventada) na mesma pergunta é barrada até o usuário confirmar. *Bug real encontrado pela avaliação automática e corrigido.* |
| Agente confundir chegada com saída ("chegou iogurte vencido" → lançar perda) | Regra no prompt + trava de intenção (mensagem só de chegada bloqueia registrar saída) + perda "por vencimento" só sai de lotes realmente vencidos. *Também achado pela avaliação.* |
| Ação cara sem supervisão | Pedido de compra é só rascunho; aprovação é humana |
| Desconto exagerado | Limite de 50%; o agente sinaliza quando o preço promocional fica abaixo do custo |
| Loop infinito / gasto de cota | Máximo de 8 passos por pergunta + novas tentativas automáticas se a API falhar |
| Pergunta fora do escopo | O agente recusa educadamente e volta ao tema estoque/desperdício |

## Observabilidade (LLMOps)
Tudo fica gravado na tabela `log_agente` e aparece na aba **🔍 Rastreio**:
- **cada chamada ao modelo:** provedor, modelo, tempo (ms), sucesso ou erro;
- **cada ferramenta:** argumentos e resultado completo;
- **cada pergunta:** tempo total, número de passos, se precisou de modelo reserva, se terminou com erro.

O painel "Saúde do agente" mostra tempo médio e **p95**, taxa de erro do modelo, trocas para reserva e erros de ferramenta.

**Como investigamos uma resposta ruim:** abrimos o Rastreio, achamos a sessão, vemos exatamente quais dados as ferramentas devolveram e o que o modelo respondeu. Se o número estava certo na ferramenta e errado na resposta, é problema de instrução (ajustamos o prompt e rodamos `tests/eval_agente.py`); se estava errado na ferramenta, é bug de código.

**Sinais de degradação:** p95 subindo, taxa de erro do modelo subindo, mais trocas para reserva, mais erros de ferramenta por pergunta. Antes de qualquer mudança, rodamos a avaliação automática (12 casos) para garantir que nada piorou.

## Por que um agente só (e não vários)?
O fluxo do pequeno comércio é **sequencial e de um domínio só** (estoque → risco → ação → compra). Dividir em vários agentes (ex.: "agente de validade" + "agente de compras" + "coordenador") traria:
- **mais latência e custo:** cada agente extra é mais uma ida ao modelo — a rotina hoje leva ~28 s com 2 passos;
- **mais pontos de falha** e conflito entre agentes para resolver;
- **nenhum ganho real**, porque a parte difícil (projeção de sobra, desconto, quantidade de compra) já é cálculo determinístico nas ferramentas.

A especialização está nas **ferramentas**, não em múltiplos agentes. Se o produto crescer (ex.: agente que negocia com fornecedores por WhatsApp, agente de precificação dinâmica), aí faz sentido separar, com um orquestrador consolidando.

## Memória e dados (LGPD)
- O agente lembra a conversa só durante a sessão; o que persiste é o estoque e o log operacional.
- Não coletamos dados pessoais de clientes; os dados são do estoque do comércio e ficam no próprio computador (SQLite).
