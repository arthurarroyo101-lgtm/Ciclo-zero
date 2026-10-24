# Ciclo Zero

**Agente de IA que reduz o desperdício de alimentos em pequenos comércios**, controlando o estoque e agindo antes que o produto vença ou encalhe.

Projeto do AKCIT Camp 2026 — Hackathon Regional Centro-Oeste.

## Equipe
- Matheus — agente de IA e ferramentas
- João Paulo ([@joaopaulo167](https://github.com/joaopaulo167)) — interface e dados
- Arthur ([@arthurarroyo101-lgtm](https://github.com/arthurarroyo101-lgtm)) — negócio, pitch e validação

## Como rodar
```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env   # e coloque sua GEMINI_API_KEY
streamlit run app.py
```

## Documentação
- [Diário de decisões](docs/DECISOES.md)

## Licença
MIT
