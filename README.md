# Ciclo Zero

**Agente de IA que reduz o desperdício de alimentos em pequenos comércios**, controlando o estoque e agindo antes que o produto vença ou encalhe.

Projeto do AKCIT Camp 2026 — Hackathon Regional Centro-Oeste.

## Equipe
- Matheus — agente de IA e ferramentas
- João Paulo ([@joaopaulo167](https://github.com/joaopaulo167)) — interface e dados.
- Arthur ([@arthurarroyo101-lgtm](https://github.com/arthurarroyo101-lgtm)) — negócio, pitch e validação.

## Como rodar
```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env   # e coloque sua GEMINI_API_KEY
streamlit run app.py
```
Na primeira execução o app cria um banco com dados de exemplo (padaria fictícia). Para testar só no terminal: `python -m ciclozero.agent`.
Testes: `python -m tests.eval_agente` (agente, precisa de chave) e `python -m tests.test_nota_fiscal` (nota fiscal, offline).

**Entrada por foto da nota fiscal:** aba 📷 Nota fiscal — há uma nota fictícia de exemplo em `docs/exemplos/`.

## Landing page
Página de apresentação estática em [`landing/`](landing/) (abrir `landing/index.html`; publicação na Vercel em `landing/README.md`).

## Documentação
- **[Slides do pitch (PDF)](docs/pitch.pdf)**
- Resumo para estudar, um por pessoa: [Matheus](docs/estudo/MATHEUS.md), [João Paulo](docs/estudo/JOAO.md), [Arthur](docs/estudo/ARTHUR.md)
- **[Contexto do projeto](docs/CONTEXTO.md): comece por aqui** (o problema, a ideia, as regras e quem faz o quê). Assistentes de IA: [`AGENTS.md`](AGENTS.md).
- [Diário de decisões](docs/DECISOES.md)
- [Divisão de tarefas](docs/TAREFAS.md)
- [Roteiro da demo](docs/DEMO.md)
- [Business Model Canvas](docs/BMC.md)
- [Roteiro do pitch](docs/PITCH.md)
- [Validação com comerciantes](docs/validacao.md)
- [Avaliação automática do agente](docs/AVALIACAO.md)
- [Base normativa (RAG) — leis conferidas](docs/NORMAS.md)
- [Fluxo do agente (inputs, lógica, outputs)](docs/FLUXO_AGENTE.md)

## Licença
MIT
