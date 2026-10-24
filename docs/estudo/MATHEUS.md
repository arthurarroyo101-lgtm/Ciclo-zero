# Estudo: Matheus (agente de IA, operação da demo)

> Leia só este arquivo. Ele resume o que **você** precisa saber para apresentar e responder à banca.
> Pitch às 16h. Tudo no GitHub até 15h30. Slides: `docs/pitch.pdf`.

## 1. O projeto em 30 segundos
- **Problema:** pequenos comércios de alimentos (padaria, mercadinho, hortifrúti) controlam estoque "no olhômetro". Compram ou produzem a mais, o produto vence e vira perda sem ninguém perceber.
- **Solução:** Ciclo Zero, um **agente de IA** que lê a nota do fornecedor, acompanha cada lote e sua validade, avisa quando entra mercadoria demais e monta um plano por lote (promoção com preço, doação ou descarte) e os pedidos de compra. **O dono aprova tudo.**
- **Validação:** Canto Caseiro (dor real: controle manual) e Subway (sem dor: a franquia já tem sistema). Nosso cliente é quem ainda controla o estoque na mão.

## 2. Seu papel no dia
- **Operar o computador na demo** (cerca de 85 s, slide 5). Roteiro em `docs/DEMO.md`.
- Responder às **perguntas técnicas** da banca.
- Antes de subir: rodar o `streamlit run app.py`, **Recriar dados de exemplo**, nome da loja "Padaria Canto Caseiro", Modo técnico desligado, Loja ao vivo desligada, vídeo de reserva aberto.

## 3. A demo, passo a passo
1. **Dashboard** → ligar **Loja ao vivo**. Mostrar a faixa verde com o relógio. Quando aparecer a **notificação amarela** (compra a mais), dizer que fica guardada na aba **Alertas**.
2. **Nota fiscal** → "Exemplo: Ceasa" → **Ler nota** → **Lançar no estoque**. A IA confere a soma e associa os itens. O agente avisa a banana que vai sobrar.
3. **Agente** → **Rodar rotina diária**. Enquanto roda, explicar: *entrada* (estoque, validades, 30 dias de vendas), *lógica* (projeção lote a lote feita em código), *saída* (plano e pedidos).
4. **Pedidos** → **Aprovar pedido** → abrir **Mensagem para o fornecedor**.
5. Ligar **Modo técnico** → **Rastreio**: cada passo do agente é auditável.
- **Plano B:** a nota falhou → digitar no chat "Chegaram 30 unidades de leite integral com validade 30/12/2026". Sem internet → vídeo. O Groq caiu → o agente troca sozinho para o Gemini.

## 4. Como o agente funciona (para explicar)
- **Modelo:** Groq `gpt-oss-120b` (principal). Reservas automáticas: outros modelos do Groq e o Gemini. Se um provedor cai, troca sozinho.
- **Function calling:** o modelo **não calcula nada**. Ele escolhe **ferramentas** em Python (`ciclozero/tools.py`) que leem o banco SQLite e fazem as contas. São 12 ferramentas, por exemplo:
  - `resumo_do_dia`
  - `analisar_risco_desperdicio`
  - `calcular_reposicao`
  - `criar_pedidos_sugeridos`
  - `consultar_normas`
- **Travas de segurança no código (guardrails):**
  - no máximo 8 passos por pergunta;
  - pedido é sempre rascunho;
  - pedido acima de 2× a sugestão é bloqueado;
  - desconto de no máximo 50%;
  - produto vencido nunca vai para promoção nem para doação;
  - quando o usuário diz que mercadoria "chegou", o agente não pode registrar saída.
- **RAG de normas** (`ciclozero/normas.py`): base pequena com textos **conferidos** no site do Planalto:
  - Lei 15.224/2025, a lei vigente de doação, que revogou a 14.016/2020;
  - CDC, art. 18, §6º (vencido é impróprio para consumo);
  - Lei 8.137/1990, art. 7º, IX (vender impróprio é crime).
  - A busca é por palavras-chave. Fora da base, o agente diz que não sabe.
- **Previsão:** média de vendas dos últimos 14 dias **fechados** (o dia de hoje fica de fora, porque ainda está pela metade). Sobra projetada = estoque do lote − (média × dias até vencer).
- **Nota fiscal:** a visão do Gemini lê a foto. As reservas são OCR local (Tesseract) com IA de texto e a visão do Groq. Depois o sistema confere a soma dos itens com o total, associa cada item ao cadastro (e aprende os apelidos de cada loja) e só lança no estoque com a confirmação do dono.
- **Avaliação:** `tests/eval_agente.py`, com 16 casos (nome errado, nota vencida, compra exagerada, pergunta fora do assunto, perguntas de lei). Mede se cada R$ da resposta existe nos dados (fidelidade 100%). O teste revelou dois comportamentos perigosos, que viraram travas.
- **Observabilidade:** a tabela `log_agente` registra cada passo. A aba Rastreio mostra latência, erros e uso do modelo reserva.
- **Loja ao vivo:** é um simulador. O dia vai das 7h às 20h e dura cerca de 6 minutos de verdade. Ao fechar, os contadores zeram e os vencidos viram perda. As vendas usam a mesma ferramenta do agente.

## 5. Perguntas prováveis (respostas curtas)
| Pergunta | Resposta |
|---|---|
| E se a IA inventar números? | Ela não calcula: os números vêm das ferramentas e do banco. Medimos fidelidade de 100% em 16 casos. |
| De onde vêm as regras legais? | De uma base conferida no site oficial, citada com artigo e link. Fora dela, o agente diz que não sabe. |
| Por que um agente e não só um sistema? | Ele decide quais ferramentas usar para cada pergunta em português, encadeia passos e explica o resultado. A rotina diária roda sozinha. |
| E se a internet ou o modelo cair? | Ele troca de provedor sozinho. Os dados ficam no banco local. |
| Os dados são reais? | Não: padaria fictícia, vendas simuladas. Numa loja real, as vendas viriam do caixa (PDV). |
| Quanto custa rodar a IA? | Usamos provedores com camada gratuita no protótipo. O custo real por loja será medido no piloto. |
| Emite nota fiscal? | Não. Lê a nota do fornecedor. Emitir exige certificado digital e integração com a SEFAZ. |
| Por que Streamlit? | Para prototipar rápido em Python. A migração para React/Next com API em Python fica para depois. |

## 6. Não esqueça
- Dizer que os dados são **fictícios**.
- Não prometer economia: "o piloto vai medir".
- Às 15h20: Sync final e conferir no site do GitHub.
- Depois do evento: **trocar as chaves de API** que foram usadas.
