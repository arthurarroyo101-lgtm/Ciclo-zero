# Estudo: João Paulo Pires de Mello (apresentador do pitch, interface e dados)

> Leia só este arquivo. Ele resume o que **você** precisa saber para apresentar e responder à banca.
> Pitch às 16h. Tudo no GitHub até 15h30. Slides: `docs/pitch.pdf`.

## 1. O projeto em 30 segundos
- **Problema:** pequenos comércios de alimentos (padaria, mercadinho, hortifrúti) controlam estoque "no olhômetro". Compram ou produzem a mais, o produto vence e vira perda sem ninguém perceber.
- **Solução:** Ciclo Zero, um **agente de IA** que lê a nota do fornecedor, acompanha cada lote e sua validade, avisa quando entra mercadoria demais e monta um plano por lote (promoção com preço, doação ou descarte) e os pedidos de compra. **O dono aprova tudo.**
- **Validação:** Canto Caseiro (dor real: controle manual) e Subway (sem dor: a franquia já tem sistema). Nosso cliente é quem ainda controla o estoque na mão.

## 2. Seu papel no dia
- **Você apresenta o pitch.** Os slides estão em `docs/pitch.pdf`, e a fala de cada um está na seção "O pitch, slide a slide" logo abaixo (e nas notas do apresentador do deck). O Matheus opera a demo no slide 5. O Arthur ajuda nas perguntas de negócio.
- Você também é quem conhece a **tela**. Se a banca perguntar sobre usabilidade, design ou "o que o dono vê", a pergunta é sua.
- **Não mexer mais no visual** (a interface congelou às 13h). Testar e avisar o Matheus se algo quebrar.
- Ajudar a gravar o vídeo de reserva e, se der tempo, publicar a landing na Vercel (Root Directory `landing`).

## O pitch, slide a slide (versão de 5 min)
> Se a organização confirmar **3 minutos**, pule os slides 3 e 7 e diga a validação em uma frase no slide 2.

| Slide | Tempo | O que falar (resumo) |
|---|---|---|
| 1. Capa | 0:00–0:30 | "E se parte do lucro da sua loja estivesse vencendo na prateleira? O desperdício nem sempre começa no lixo: começa numa compra sem informação ou num produto que vence antes de ser vendido. Criamos o Ciclo Zero para agir antes disso." |
| 2. Problema | 0:30–1:10 | "O dono decide todo dia o que comprar e o que vender primeiro. Entrevistamos a gerente de vendas do Canto Caseiro: ela estima as compras 'no olhômetro', repete anotações todo dia e gasta algumas horas nisso. Quer automatizar o registro e ter uma estimativa de compra, e pagaria se fosse acessível." |
| 3. Sem e com | 1:10–1:55 | "Sem apoio, ele cruza tudo sozinho. Com o Ciclo Zero, a nota prepara a entrada, cada lote é acompanhado e o agente aponta riscos e prepara pedidos. A decisão final é sempre do dono." |
| 4. Como funciona | 1:55–2:45 | "Registrar, acompanhar, agir antes da perda e aprovar. Nada entra no estoque sem confirmação; pedido é rascunho até o dono aprovar." |
| 5. Demo | ~85 s | "Os dados desta demonstração são fictícios; as vendas são simuladas. Matheus, mostra pra gente." (o Matheus opera; você pode narrar junto) |
| 6. Confiança | ~20 s | "Todo número vem do banco e é calculado em código, a IA não inventa. As regras de lei vêm de uma base conferida no site oficial. E testamos o agente em 16 situações; as falhas viraram travas." |
| 7. Validação | 2:45–3:40 | "Duas entrevistas, resultados diferentes: no Canto Caseiro a dor é real; no Subway, o sistema da franquia já atende. Nosso cliente é quem controla na mão. Ainda não provamos redução de perdas." |
| 8. Modelo de negócio | ~20 s | "Assinatura por loja: 30 dias grátis e depois R$ 49 por mês, uma hipótese que o piloto vai validar. Venda direta no bairro, demonstrações e indicações." |
| 9. Próximo passo e equipe | 3:40–4:15 | "Matheus de Melo Sari no agente e nos testes, eu, João Paulo Pires de Mello, na interface e nos dados, e Arthur Arroyo Cabral no negócio e na validação. Próximo passo: piloto de 30 dias medindo tempo, alertas, perdas, custo e se o cliente pagaria." |
| 10. Fechamento | 4:15–5:00 | "Não queremos prometer que a IA resolve tudo: queremos testar e medir. Não dá para recuperar o que já venceu. Mas dá para decidir melhor antes. Obrigado." |

**Regras de ouro ao falar:** dizer que os dados são fictícios; não prometer economia ("o piloto vai medir"); não dizer que temos parceiro; o R$ 49 é hipótese.

### O mínimo de negócio para responder
- **Cliente:** pequeno comércio de alimentos que controla o estoque na mão e trabalha com produto que vence em dias.
- **Receita:** 30 dias grátis e depois R$ 49 por loja ao mês (hipótese). **Custos:** IA, hospedagem, desenvolvimento, aquisição e suporte.
- **Concorrentes:** caderno, planilha e sistemas de gestão tradicionais, complexos e caros para o pequeno comércio.
- Pergunta técnica difícil → "o Matheus explica". Pergunta de negócio difícil → "o Arthur explica".

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
