# Instruções para assistentes de IA (Claude, Copilot, Cursor, Gemini...)

Antes de qualquer mudança, leia [`docs/CONTEXTO.md`](docs/CONTEXTO.md): o que é o projeto, as regras que não podem ser quebradas e quem é dono de cada arquivo.

Resumo do que vale sempre:
- **Idioma:** português do Brasil, em textos e mensagens de commit. Datas no formato DD/MM/AAAA e valores como R$ 1.234,56.
- **O agente não inventa dados.** Nenhum número em R$ vem do modelo: vem de `ciclozero/tools.py` ou do banco. Lei, só da base `ciclozero/normas.py`.
- **Interface:** siga [`docs/DESIGN.md`](docs/DESIGN.md).
  - Use ícones Material (`:material/nome:`) e nunca emoji em botões.
  - O amarelo fica só para "olhe aqui" e o vermelho só para prejuízo.
  - Escreva como o dono da loja fala, sem jargão técnico. O que é técnico fica atrás do "Modo técnico".
- **Compatibilidade:** Python 3.10. Não atualize o Streamlit no dia da demo.
- **Segurança:** nunca leia, imprima ou commite o `.env` nem chaves de API.
- **Arquivos de outra pessoa:** mexa só nos arquivos do seu dono (tabela em `docs/CONTEXTO.md`). Se precisar mudar o de outra pessoa, avise no grupo.
- **Depois de mudar:**
  - rode `python -m py_compile app.py ciclozero/*.py`;
  - abra o app com `streamlit run app.py`;
  - registre decisões relevantes em `docs/DECISOES.md`.
