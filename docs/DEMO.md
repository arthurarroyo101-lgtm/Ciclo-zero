# Roteiro da demo — Ciclo Zero

> A demo ocupa ~80 s dos 3 min de pitch. Quem opera: **Matheus** (computador). Quem fala: quem estiver apresentando o pitch (ou o próprio Matheus).
> Regra: **ensaiar 3 vezes com cronômetro** antes das 15h30.

## Checklist antes de subir no palco (5 min antes)
- [ ] Notebook carregado + carregador na tomada
- [ ] Internet: Wi-Fi do evento testado **e** roteador do celular pronto
- [ ] `.env` com `GROQ_API_KEY` e `GEMINI_API_KEY` (reserva automática)
- [ ] `streamlit run app.py` rodando, navegador em tela cheia (⌃⌘F), zoom 125% (⌘+)
- [ ] Barra lateral → **🔄 Recriar dados de exemplo** (deixa os números iguais aos do roteiro e zera pedidos)
- [ ] Abrir a aba **📊 Dashboard**
- [ ] **Loja ao vivo DESLIGADA** até começar a demo (liga no primeiro passo)
- [ ] Vídeo de backup aberto em outra janela (plano B)
- [ ] Notificações do Mac desligadas (Foco → Não perturbe)

## Roteiro (≈ 80 s)

| Tempo | Tela / ação | O que falar |
|---|---|---|
| 0–12 s | **📊 Dashboard** (já aberto) → ligar **🟢 Loja ao vivo** na barra lateral | "Essa é uma padaria de bairro, aberta agora — as vendas do caixa estão chegando em tempo real *(simulação)*. Em 30 dias ela jogou fora **R$ 1.284** em comida — **4,2% do faturamento**. E repara: conforme vende, a **perda projetada vai caindo**." *(apontar os números mudando no topo)* |
| 12–35 s | Aba **📷 Nota fiscal** → "Exemplo: Ceasa" → **🔎 Ler nota com IA** → **✅ Confirmar e lançar** | "Chegou mercadoria. Em vez de anotar no caderno — que foi a maior dor que ouvimos dos comerciantes — ele tira **foto da nota**. A IA lê os itens, confere se a soma bate com o total, associa ao estoque e sugere a validade. O dono só confirma. E olha: o agente já avisa que **40 kg de banana vão sobrar** antes de vencer." |
| 35–60 s | Aba **💬 Agente** → clicar **▶️ Rodar rotina diária** | **Enquanto roda (≈25 s), explicar o fluxo:** "Toda manhã o agente faz sozinho a abertura da loja. **Entrada:** estoque, validades e 30 dias de vendas. **Lógica:** ele projeta, lote a lote, o que não vai ser vendido antes de vencer — esse cálculo é feito em código, não pelo modelo, então ele não inventa número. **Saída:** um plano de ação e os pedidos de compra." |
| 60–70 s | Resposta aparece → apontar o resumo | "Sem fazer nada, essa loja perderia **R$ 490**. Com as promoções sugeridas ela recupera **R$ 277** em vendas, e **R$ 244** viram doação em vez de lixo. E ele já montou os pedidos — sem comprar a mais." |
| 70–77 s | Aba **🧾 Pedidos** → clicar **✅ Aprovar** em um | "Compra é decisão do dono: o agente só cria rascunho, quem aprova é humano." |
| 77–80 s | Aba **🔍 Rastreio** | "E tudo é auditável: cada passo, cada número. Nosso teste automático passou em **12 de 12 casos**, com **100% de fidelidade** — zero valor inventado." |

> Com a Loja ao vivo ligada, os valores de risco **mudam a cada poucos segundos** (as vendas consomem os lotes). Os valores (R$ 1.284 / R$ 490 / R$ 277 / R$ 244) são os dos dados de exemplo **depois de "Recriar dados de exemplo" e ANTES de lançar a nota**. Depois da nota, a rotina mostra números maiores (a banana extra entra no risco) — **falar o que estiver na tela**.
> Se sobrar tempo ou na pergunta da banca: **"Exemplo: Laticinios"** mostra um item com confiança baixa ("IOG NAT DANONE") e um aviso de custo acima do cadastro; depois de confirmar, a mesma nota volta com "aprendido" — **a loja ensina o sistema**.
> Alternativa mais impactante na hora: imprimir `docs/exemplos/nota_exemplo_ceasa.png` e usar **📷 Câmera** para fotografar o papel ao vivo.

## Plano B
| Problema | O que fazer |
|---|---|
| Leitura da nota falhar ou demorar > 20 s | Pular para a aba Agente e digitar: `Chegaram 30 unidades de leite integral com validade 30/12/2026` |
| Groq fora do ar | Nada — o agente troca sozinho para o Gemini (aparece 🔁). Falar: "olha a resiliência: trocou de provedor sozinho." |
| Rotina demorando > 40 s | Continuar falando o fluxo; se passar de 60 s, ir para o vídeo |
| Sem internet / tudo falhou | **Vídeo de backup** (o edital aceita demo gravada) |
| Simulação atrapalhando (números pulando demais na hora de explicar) | Desligar o 🟢 Loja ao vivo na barra lateral; o resto continua igual |
| Erro na tela | Não tentar consertar ao vivo: vídeo |

## Gravar o vídeo de backup (hoje ou amanhã até 13h)
1. Recriar dados de exemplo, aba Dashboard.
2. **⌘⇧5** → "Gravar tela inteira" (ou janela do navegador) → Gravar.
3. Seguir o roteiro acima, **sem falar** (a fala é ao vivo).
4. Parar (ícone na barra de menus), salvar como `demo-ciclozero.mov`.
5. Subir no **YouTube como "Não listado"** ou Google Drive com link público, e colocar o link no README. *(Não subir o vídeo no GitHub: arquivo grande.)*

## Perguntas técnicas prováveis da banca (respostas curtas)
| Pergunta | Resposta |
|---|---|
| De onde vêm os números? E se o modelo inventar? | Todo número vem das ferramentas, que leem o banco; cálculo é em Python. Medimos: **fidelidade 100%** em 12 casos. |
| O que acontece com entrada errada? | Ferramenta recusa e o agente pergunta. Nossos testes cobrem nome com erro, produto inexistente, data vencida, venda maior que estoque, compra exagerada. |
| O agente pode fazer besteira sozinho? | Compra só vira rascunho; pedido > 2× o necessário é bloqueado; desconto máx. 50%. E travas que **nosso próprio teste revelou**: o agente tentava "contornar" uma recusa lançando perda — bloqueamos no código. |
| Por que um agente e não vários? | Fluxo sequencial de um domínio só; vários agentes = mais latência e custo sem ganho. A especialização está nas ferramentas. |
| O que impede um concorrente de copiar? | Cada loja acumula seu próprio dado: histórico de vendas e perdas e o **dicionário de notas que ela mesma ensinou** (cada confirmação/correção vira associação aprendida). Quanto mais usa, mais preciso e mais difícil trocar. |
| Esses números são reais? | São de uma padaria **fictícia**; a "Loja ao vivo" simula as vendas que, numa loja real, viriam do caixa/PDV. As vendas passam pela mesma ferramenta do agente. |
| A leitura da nota pode errar? | Pode — por isso a soma dos itens é conferida com o total impresso, a tabela é editável e nada entra sem confirmação. Item desconhecido não é lançado. |
| E se a API cair? | Troca automática de modelo e de provedor (Groq → Gemini). |
| Como vocês monitoram? | Aba Rastreio: tempo médio e p95, taxa de erro, uso de reserva, erros de ferramenta; log de cada passo. |
| LGPD? | Não coletamos dado pessoal de cliente; só estoque do comércio, local. Conversa não persiste entre sessões. |
| Qual LLM? Custo? | `gpt-oss-120b` (open source) via Groq, plano gratuito no protótipo; Gemini como reserva. Uma rotina diária usa 2 chamadas — custo de centavos por mês por loja em escala. |
