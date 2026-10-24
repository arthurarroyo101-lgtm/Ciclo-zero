# Landing page do Ciclo Zero

Página estática (um arquivo, sem build). Segue `docs/DESIGN.md`.

## Publicar na Vercel (grátis, ~3 min)
1. vercel.com → **Add New → Project** → importar o repositório `Ciclo-zero`.
2. Em **Root Directory**, escolher `landing`. Framework: **Other**. Sem comando de build.
3. **Deploy.** A Vercel gera um link `*.vercel.app`.

Para ver localmente: abrir `landing/index.html` no navegador.

> O app (Streamlit) não roda na Vercel: ele precisa de um servidor Python sempre ligado, banco em arquivo e a simulação ao vivo. Para link público do app: Streamlit Community Cloud.
