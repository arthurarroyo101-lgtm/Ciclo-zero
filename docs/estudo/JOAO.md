# Estudo: João Paulo (interface e dados)

> Leia só este arquivo. Ele resume o que **você** precisa saber para apresentar e responder à banca.
> Pitch às 16h. Tudo no GitHub até 15h30. Slides: `docs/pitch.pdf`.

## 1. O projeto em 30 segundos
- **Problema:** pequenos comércios de alimentos (padaria, mercadinho, hortifrúti) controlam estoque "no olhômetro". Compram ou produzem a mais, o produto vence e vira perda sem ninguém perceber.
- **Solução:** Ciclo Zero, um **agente de IA** que lê a nota do fornecedor, acompanha cada lote e sua validade, avisa quando entra mercadoria demais e monta um plano por lote (promoção com preço, doação ou descarte) e os pedidos de compra. **O dono aprova tudo.**
- **Validação:** Canto Caseiro (dor real: controle manual) e Subway (sem dor: a franquia já tem sistema). Nosso cliente é quem ainda controla o estoque na mão.

## 2. Seu papel no dia
- Você é quem conhece a **tela**. Se a banca perguntar sobre usabilidade, design ou "o que o dono vê", a pergunta é sua.
- **Não mexer mais no visual** (a interface congelou às 13h). Testar e avisar o Matheus se algo quebrar.
- Ajudar a gravar o vídeo de reserva e, se der tempo, publicar a landing na Vercel (Root Directory `landing`).

## 3. A tela, botão por botão
- **Faixa verde no topo:** relógio da loja (dia e hora), ponto "Ao vivo" pulsando e resumo do dia anterior.
- **Etiquetas do topo:** Vendas hoje, Caixa do dia, Lucro do dia, Lotes em risco, **Vai para o lixo** (amarela, a etiqueta de gôndola: dinheiro que ainda dá para salvar) e Jogado fora no mês.
- **Agente:** chat em português e botão **Rodar rotina diária** (plano por lote e pedidos).
- **Nota fiscal:** foto ou exemplo → Ler nota → tabela para conferir (dá para corrigir) → Lançar no estoque.
- **Dashboard:** como está o dia (vendas, caixa, lucro, comprado a mais, a pagar, pedidos para aprovar) e gráficos (lotes em risco, produtos que mais vão para o lixo, vendas × perdas em 30 dias, perdas por categoria).
- **Estoque:** **plaquinhas de oferta** prontas para imprimir, lotes perto de vencer e tudo o que tem na loja.
- **Pedidos:** rascunhos para aprovar ou recusar; aprovado vira "a pagar"; botão "Chegou: lançar no estoque"; mensagem pronta para o fornecedor (WhatsApp).
- **Alertas:** tudo o que entrou a mais hoje, agrupado por produto, para quem não viu a notificação.
- **Modo técnico** (barra lateral): mostra fórmulas, os passos do agente e a aba Rastreio. Desligado, é a visão limpa do comerciante.

## 4. Decisões de design (para explicar)
- **Para quem:** o dono de uma padaria, não um analista. Por isso a tela usa palavras dele ("Vai para o lixo", "A pagar", "Comprado a mais"), não "KPI" nem "excedente".
- **Cores com significado** (`docs/DESIGN.md`):
  - **verde** = marca e ação;
  - **amarelo** = "olhe aqui" (etiqueta, alerta, oferta);
  - **vermelho** = só prejuízo;
  - **papel** = nota e recibo.
- **Etiqueta de gôndola:** o elemento visual que todo comerciante reconhece. O amarelo é a cor da promoção, ou seja, do dinheiro que ainda dá para salvar.
- **Letras finas e legíveis:** Manrope nos textos, Archivo nos títulos e valores. O mesmo sistema visual da landing page.
- **Ícones** de traço único no lugar de emoji, e botões grandes e explícitos.
- **Notificação** que some sozinha (cerca de 12 s), mais a aba Alertas: avisa sem atrapalhar, e nada se perde.
- **Ao vivo:** a tela se atualiza a cada 3 s sem recarregar a página (fragmentos do Streamlit).

## 5. Dados (para explicar)
- Banco **SQLite** com produtos, lotes (cada lote com validade), movimentações (venda, entrada, perda, doação), pedidos, despesas e o registro do agente.
- **Dados de exemplo:** padaria fictícia com 14 produtos e 30 dias de histórico. "Recriar dados de exemplo" volta tudo ao início.
- **Caixa × lucro:**
  - **caixa** = vendas − compras − despesas (pode ficar negativo no dia em que chega mercadoria);
  - **lucro** = vendas − custo do que foi vendido − perdas − despesas.
- **Loja ao vivo:** simulador de um dia de loja (vendas, fornadas, entregas, perdas, contas). Às 20h o dia fecha e os números zeram. Numa loja real, as vendas viriam do caixa (PDV).

## 6. Perguntas prováveis (respostas curtas)
| Pergunta | Resposta |
|---|---|
| Um dono de padaria consegue usar? | A tela usa as palavras dele, botões grandes e só o essencial. O técnico fica escondido no Modo técnico. |
| Por que o amarelo no "Vai para o lixo"? | É a etiqueta de promoção: dinheiro que ainda dá para salvar. O vermelho fica só para o prejuízo que já aconteceu. |
| Os números são reais? | Não: padaria fictícia, vendas simuladas. |
| Funciona no celular? | O protótipo roda no navegador. A versão para celular é próximo passo. |
| Por que Streamlit? | Para prototipar rápido em Python. React/Next fica para depois do hackathon. |

## 7. Não esqueça
- Dar **Pull** antes de testar.
- Testar a Loja ao vivo ligada e desligada, o Modo técnico ligado e desligado, e todos os botões.
- Se algo quebrar: mandar um **print** para o Matheus, sem tentar consertar sozinho.
