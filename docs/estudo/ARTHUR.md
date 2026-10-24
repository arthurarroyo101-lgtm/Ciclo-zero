# Estudo: Arthur (negócio, validação e pitch)

> Leia só este arquivo. Ele resume o que **você** precisa saber para apresentar e responder à banca.
> Pitch às 16h. Tudo no GitHub até 15h30. Slides: `docs/pitch.pdf` (falas nas notas de cada slide).

## 1. O projeto em 30 segundos
- **Problema:** pequenos comércios de alimentos (padaria, mercadinho, hortifrúti) controlam estoque "no olhômetro". Compram ou produzem a mais, o produto vence e vira perda sem ninguém perceber.
- **Solução:** Ciclo Zero, um **agente de IA** que lê a nota do fornecedor, acompanha cada lote e sua validade, avisa quando entra mercadoria demais e monta um plano por lote (promoção com preço, doação ou descarte) e os pedidos de compra. **O dono aprova tudo.**
- **Frase de fechamento:** "Não dá para recuperar o que já venceu. Mas dá para decidir melhor antes."

## 2. Seu papel no dia
- **Conduzir o pitch** (os slides seguem o seu `PITCH.md`). O Matheus opera a demo no slide 5.
- Responder às perguntas de **negócio, mercado e validação**.
- **Confirmar com a organização se o pitch tem 3 ou 5 minutos.** Se for 3, pular os slides 3 (Sem e com) e 7 (Validação) e falar a validação junto com o slide 2.

## 3. Os slides e o tempo (versão de 5 min)
| Slide | Tempo | Ideia |
|---|---|---|
| 1. Capa | 0:00–0:30 | "E se parte do lucro estivesse vencendo na prateleira?" |
| 2. Problema | 0:30–1:10 | Decidir todo dia com informação incompleta; relato do Canto Caseiro |
| 3. Sem e com | 1:10–1:55 | O dia do comerciante, antes e depois |
| 4. Como funciona | 1:55–2:45 | Registrar, acompanhar, agir antes da perda, aprovar |
| 5. Demo | (~85 s, Matheus) | Dizer: "os dados são fictícios; as vendas são simuladas" |
| 6. Confiança | curto | 100% dos números do estoque, 3 leis conferidas, 16 situações testadas |
| 7. Validação | 2:45–3:40 | Canto Caseiro × Subway: o cliente é quem controla na mão |
| 8. Modelo de negócio | curto | BMC em 9 blocos |
| 9. Próximo passo e equipe | 3:40–4:15 | Piloto de 30 dias medido; quem faz o quê |
| 10. Fechamento | 4:15–5:00 | Frase final e "obrigado" |

## 4. O modelo de negócio (BMC) para saber de cor
- **Clientes:** padarias, mercadinhos, hortifrútis e lanchonetes que controlam o estoque na mão.
- **Proposta de valor:** controlar o estoque, antecipar o desperdício e comprar só o necessário, num lugar só.
- **Canais:** venda direta no bairro, demonstrações, indicações e redes sociais. Associações e Sebrae ficam como possibilidades futuras.
- **Relacionamento:** uso autônomo guiado pelo agente e piloto grátis de 30 dias.
- **Receita:** assinatura de **R$ 49 por loja ao mês** depois do piloto. **É uma hipótese** a validar.
- **Recursos:** agente de IA, ferramentas de cálculo, dados de cada loja e a equipe.
- **Atividades:** evoluir o produto, testar as recomendações, acompanhar pilotos.
- **Parcerias:** provedores de IA, associações, contadores, bancos de alimentos. **Nenhuma confirmada.**
- **Custos:** uso de IA, hospedagem, desenvolvimento, aquisição de clientes e suporte.
- **Vantagem que cresce com o uso:** cada loja "ensina" o sistema (os nomes das notas e o histórico de vendas dela).

## 5. Validação (o que dá e o que não dá para dizer)
- **Canto Caseiro:** controle "no olhômetro", anotações diárias, abertura para uma solução útil e acessível.
- **Subway:** o sistema da franquia já atende, e não há interesse em pagar.
- **Pode dizer:** "ouvimos a dor em quem controla na mão; isso delimita nosso cliente".
- **Não pode dizer:** que reduzimos perdas, que temos parceiro, que o piloto está fechado ou que o R$ 49 está validado.
- **Próximo passo:** piloto de 30 dias medindo tempo de controle, utilidade dos alertas, perdas, custo por loja e disposição a pagar.

## 6. O mínimo de técnica para não travar
- O agente **não inventa números**: ele chama ferramentas em Python que leem o banco e calculam. A IA escolhe e explica.
- As regras de lei vêm de uma base conferida no site oficial, com a Lei 15.224/2025 (doação de alimentos). Fora disso, o agente diz que não sabe.
- O pedido é sempre um **rascunho**: quem aprova é o dono.
- Pergunta técnica difícil: "o Matheus explica".

## 7. Perguntas prováveis (respostas curtas)
| Pergunta | Resposta |
|---|---|
| Quem é o cliente ideal? | Pequeno comércio de alimentos que ainda controla o estoque na mão e trabalha com produto que vence em dias. |
| Já provaram que reduz desperdício? | Ainda não. Por isso o próximo passo é um piloto medido. |
| Quanto custa? | Hipótese: 30 dias grátis e depois R$ 49 por loja ao mês. Preço e custo serão validados no piloto. |
| Por que não usar uma planilha? | A planilha não avisa, não prevê sobra por lote nem prepara o pedido. A vantagem será medida no piloto. |
| Quem são os concorrentes? | Caderno, planilha e sistemas de gestão tradicionais, que são complexos e caros para o pequeno comércio. |
| Têm parceiro? | Ainda não. Uma entrevista não é parceria. |
| Por que agora? | Agentes de IA tornaram barato dar a uma loja pequena o que antes só um sistema caro fazia. |

## 8. Não esqueça
- Ensaiar com cronômetro, os três juntos, com a demo no meio.
- Combinar a frase de passagem para a demo: "Matheus, mostra pra gente."
- Ter o `BMC.md` aberto, caso a banca peça detalhes.
