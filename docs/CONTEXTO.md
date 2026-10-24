# Contexto do projeto: Ciclo Zero

> Ponto de partida para qualquer pessoa ou IA que for trabalhar no projeto. Explica **o que é, por que existe, o que já foi decidido e o que não pode mudar**.
> O histórico detalhado está em [`DECISOES.md`](DECISOES.md). Atualize este arquivo quando uma decisão de produto mudar, não a cada commit.

Última revisão: 24/10/2026, dia do hackathon.

## 1. O evento
- **AKCIT Camp 2026**, Hackathon Regional **Centro-Oeste**, presencial em Goiânia, 24/10/2026. Tema geral: **Agentes de IA**.
- Tema da equipe: **"Ciclo Zero: Inteligência Artificial aplicada à redução do desperdício de alimentos em pequenos comércios"**.
- **Entregas:** protótipo funcional (demo ao vivo ou gravada), Business Model Canvas, pitch e documentação do fluxo do agente (entradas, lógica, saídas).
- **Horários do dia:** mentoria às 10h, interface congelada às **13h**, tudo no GitHub até **15h30** e pitches às 16h.
- **Critérios:** a solução e o uso de IA pesam 30%. Também contam a viabilidade do negócio, a validação com o público e a qualidade da apresentação.

## 2. O problema
- Pequenos comércios de alimentos, como padarias, mercadinhos, hortifrútis e lanchonetes, controlam o estoque **no olhômetro**, em caderno ou de cabeça.
- Sem medição, o produto vence na prateleira, a compra sai maior que a venda e o prejuízo fica invisível.
- **Validação** (ver [`validacao.md`](validacao.md)): foram feitas 2 entrevistas em Goiânia.
  - No **Canto Caseiro**, a dor é o controle manual do estoque, que consome horas do dia em anotações e planejamento de compras.
  - No **Subway**, não há dor, porque o sistema da franquia já resolve. Isso define quem **não** é o nosso cliente.
- **Dados do setor:** segundo a ABRAS (2020), as perdas são de 5,25% do faturamento em hortifrúti, 2,74% em padaria e 1,79% no total dos supermercados.

## 3. A solução
O Ciclo Zero é um **agente de IA que controla o estoque sozinho** e age antes de o produto virar lixo:
1. **Entrada:** foto da nota do fornecedor. A IA lê os itens, confere a soma e associa cada item ao cadastro. Nada entra no estoque sem a confirmação do dono.
2. **Acompanhamento:** cada lote tem a sua validade, e as vendas chegam do caixa (na demo, um simulador "Loja ao vivo").
3. **Rotina diária autônoma:** o agente prevê o que vai sobrar em cada lote, sugere promoção com preço, doação ou descarte, e monta os pedidos de compra sem excesso.
4. **Aprovação humana:** pedidos são só rascunho até o dono aprovar.
5. **Chat em português:** responde perguntas como "o que vence essa semana?" ou "posso doar esse pão?", com a lei citada.
- Compra acima do que a loja vende gera um **alerta na hora**, que é o problema acontecendo na frente da banca.

## 4. Regras que não podem ser quebradas
- **O agente não inventa dados.** Todo número em R$ é calculado em código, a partir do banco de dados. O modelo só escolhe ferramentas e explica o resultado.
- **Lei só da base conferida** (`ciclozero/normas.py`, [`NORMAS.md`](NORMAS.md)):
  - Lei 15.224/2025, que é a lei vigente de doação; a Lei 14.016/2020 foi **revogada** por ela;
  - CDC, art. 18, §6º;
  - Lei 8.137/1990, art. 7º, IX.
  - Fora da base, o agente diz que não sabe.
- **Produto vencido** nunca vai para promoção nem para doação.
- **Pedido de compra:** é sempre rascunho. Pedido acima de 2× a sugestão é bloqueado, e o desconto máximo é de 50%.
- **Dados de demonstração** são sempre fictícios e identificados como tal.
- **Chaves de API** ficam só no `.env`, que nunca vai para o git. Nunca colar chave no terminal, no chat ou no código.

## 5. Como é feito
| Parte | Onde | Observação |
|---|---|---|
| Interface | `app.py` (Streamlit), `ciclozero/ui_agente.py`, `ui_nota.py`, `ao_vivo.py`, `graficos.py` | Modo técnico desligado = visão limpa do comerciante |
| Agente | `ciclozero/agent.py` | Groq `gpt-oss-120b` como principal e Gemini de reserva; no máximo 8 passos; guardrails no código |
| Ferramentas | `ciclozero/tools.py` | Estoque, risco por lote, reposição, pedidos, financeiro |
| Nota fiscal | `ciclozero/nota_fiscal.py` | Visão do Gemini → OCR (Tesseract) + IA de texto → visão do Groq; aprende os apelidos de cada loja |
| Banco | SQLite (`ciclozero/db.py`, `seed.py`) | Padaria fictícia com 14 produtos |
| Qualidade | `tests/eval_agente.py` (16 casos), `tests/test_nota_fiscal.py` | Ver [`AVALIACAO.md`](AVALIACAO.md) |
| Visual | [`DESIGN.md`](DESIGN.md) | Etiqueta de gôndola, paleta do balcão, ícones Material (sem emoji em botões) |
| Landing page | `landing/index.html` | Estática, publicada pela Vercel (Root Directory `landing`) |

## 6. Equipe e posse dos arquivos
| Pessoa | Papel | Mexe em |
|---|---|---|
| Matheus | Agente de IA, ferramentas, nota fiscal, testes, coordenação | `ciclozero/*` (exceto `graficos.py` e `ui_agente.py`), `tests/`, `landing/` |
| João Paulo | Interface e dados | `app.py`, `ciclozero/ui_agente.py`, `ciclozero/graficos.py`, `.streamlit/` |
| Arthur | Negócio, validação, pitch e slides | `docs/BMC.md`, `docs/PITCH.md`, `docs/validacao.md` |

**Git:** todos trabalham na `main`.
- Dê **Sync** antes de começar e antes de enviar.
- Faça commits pequenos.
- Se der conflito, chame o Matheus.

## 7. Decisões de produto (resumo)
- **Streamlit no app; Vercel só para a landing.** Migrar para React/Next com API em Python fica para depois do hackathon.
- **O Ciclo Zero lê nota fiscal, não emite.** Emitir NF-e exige certificado digital e integração com a SEFAZ, e está fora do escopo.
- **Previsão de vendas** usa só dias fechados, porque o dia em andamento distorce a média.
- **Modelo de negócio** (ver [`BMC.md`](BMC.md)):
  - assinatura mensal de baixo custo por loja, com teste grátis que mostra a economia em R$;
  - canais: venda no bairro e parcerias com o Sebrae;
  - o dicionário de notas e o histórico de cada loja são um ativo que melhora com o uso.

## 8. Próximos passos (depois do hackathon)
- Piloto de 30 dias no Canto Caseiro.
- Integração com o PDV/caixa real, no lugar do simulador.
- Login por loja.
- App em React/Next com API em Python.
- Rotacionar as chaves de API usadas no evento.

## Mapa dos documentos
[DECISOES](DECISOES.md) (diário) · [TAREFAS](TAREFAS.md) · [FLUXO_AGENTE](FLUXO_AGENTE.md) · [DEMO](DEMO.md) · [PITCH](PITCH.md) · [BMC](BMC.md) · [validacao](validacao.md) · [AVALIACAO](AVALIACAO.md) · [NORMAS](NORMAS.md) · [DESIGN](DESIGN.md)
