# Design do Ciclo Zero

> Referência única da interface (Matheus + João). Feito com a skill `frontend-design` (anthropics/skills) após a mentoria de 24/10.
> Congelamento da interface: **13h**.

## Brief
- **Assunto:** estoque de padaria e mercadinho de bairro, com dinheiro indo para o lixo.
- **Quem usa:** o dono do comércio, não técnico, no balcão ou no celular. Na demo, a banca num projetor.
- **Função principal da tela:** mostrar quanto dinheiro está em risco e o que fazer agora.

## A ideia (onde gastar a ousadia)
**Os números importantes são etiquetas de gôndola**: a plaquinha de preço de supermercado, valor grande e escuro, "R$" pequeno.
Só os cartões do topo e o alerta de compra em excesso usam isso. **Todo o resto é quieto**: sem sombra, sem cartão decorativo, sem enfeite.

## Cores
| Token | Hex | Uso (e só isso) |
|---|---|---|
| `--tinta` | `#1D2B22` | texto principal |
| `--tinta-2` | `#4F5E54` | texto secundário, legendas |
| `--folha` | `#2F6B3B` | marca, botões primários, links, foco |
| `--etiqueta` | `#F6D23C` | a etiqueta em destaque (perda / compra em excesso) |
| `--tomate` | `#C8402B` | risco, valor negativo, erro |
| `--papel` | `#EFE6D6` | fundo de nota fiscal e recibos |
| `--linha` | `#D9DED6` | bordas finas |
| `--branco` | `#FFFFFF` | fundo geral |

Verde não é decoração: é marca e ação. Vermelho só significa problema. Amarelo só significa "olhe aqui".

## Tipografia
- **Texto:** Atkinson Hyperlegible (Google Fonts), 400 e 700. Feita para máxima legibilidade (celular, projetor, quem tem baixa visão).
- **Valores em R$ e números grandes:** Archivo, 800, levemente condensada (`font-stretch: 85%`), algarismos tabulares (`font-variant-numeric: tabular-nums`).
- Escala: 14 / 16 (corpo) / 20 / 26 / 36. Linhas com até ~75 caracteres.

```css
@import url('https://fonts.googleapis.com/css2?family=Archivo:wdth,wght@62..125,700..900&family=Atkinson+Hyperlegible:wght@400;700&display=swap');
```

## Layout
- Tudo alinhado à esquerda, como lista de conferência.
- Topo: as etiquetas do dia. Abaixo: só o que pede ação.
- Cantos: etiqueta 6px; botões 8px; nada de cantos iguais em tudo.

## O que NÃO fazer (vícios de interface gerada que já tínhamos)
- Rótulos com ponto no meio ("Lotes em risco · 5 dias", "Hoje · ao vivo"): escrever normal, "Lotes em risco (5 dias)".
- Todos os blocos como cartões iguais com a mesma sombra.
- Emoji em botão, aba ou título: usar ícones Material (`:material/nome:`), monocromáticos e do mesmo traço.
- Palavras em CAIXA ALTA como rótulo; seta "→" em botão; texto de enfeite.
- Animação em tudo: só a contagem dos números do topo, o ponto "Ao vivo" pulsando e o retorno de clique (botão afunda 1 px). Respeitar "reduzir movimento".

## Textos
- Falar como o dono fala: "Vai para o lixo", "A pagar", "Comprado a mais". Não "excedente", não "KPI".
- Botão diz exatamente o que acontece: "Aprovar pedido", "Lançar no estoque".
- Erro diz o que houve e como resolver, sem pedir desculpas.

## Quem mexe em quê
| Pessoa | Arquivos |
|---|---|
| Matheus | `docs/DESIGN.md`, etiquetas do topo (`ciclozero/ao_vivo.py`), aba Nota fiscal (`ciclozero/ui_nota.py`) |
| João | tema e fontes (`.streamlit/config.toml`, CSS em `ciclozero/ui_agente.py`), Dashboard, chat, Pedidos, rótulos no `app.py` |

## Sistema visual da landing page (referência para levar ao painel)
Fonte da verdade: `landing/index.html` (bloco `:root` e comentários no CSS).

**Paleta** (a mesma do app; os tons claros/escuros abaixo são derivados dela)
| Token | Hex | Uso |
|---|---|---|
| tinta | `#1D2B22` | texto; fundo do bloco de confiança |
| tinta-2 | `#4F5E54` | texto secundário |
| folha | `#2F6B3B` | marca e ação (botão principal, item ativo) |
| folha-escura | `#24552E` | hover de botão verde |
| folha-clara | `#DCEADF` | fundo de "feito para", subtítulo sobre verde |
| etiqueta | `#F6D23C` | olhe aqui: etiqueta, oferta, fechamento |
| tomate | `#C8402B` | prejuízo e preço de oferta |
| tomate-claro | `#F6DDD8` | fundo dos números de perda |
| papel | `#EFE6D6` | nota, recibo, "como funciona" |
| linha | `#D9DED6` | bordas |

**Degradês** (só da paleta, nunca arco-íris)
- Hero, só nela: verde escuro → claro na diagonal: `linear-gradient(115deg, #0F2E17 0%, #1A4424 22%, #2F6B3B 52%, #4C8E58 78%, #79B583 100%)`. Texto branco fica no lado escuro.
- Papel: `linear-gradient(180deg, #EFE6D6, #F6F0E4)`.
- Confiança: tinta `#1D2B22 → #18241C` com brilho verde no canto.
- Fechamento: amarelo `#F6D23C → #FFE27A → #F6D23C`.
- Etiqueta e botão amarelo: `#FFE066 → #F6D23C` (de cima para baixo) e sombra suave.

**Tipografia leve**
- Títulos: **Archivo** fino (h1 250, h2 300, h3 500), sem condensar, `letter-spacing` levemente negativo.
- Texto: **Manrope** 300 (negrito = 600).
- Números de destaque: Archivo 300–400; só o preço da etiqueta fica em 700, porque é a etiqueta.
- No painel (Streamlit), a mesma troca vale para títulos e textos; os valores dos cartões podem ir para Archivo 600.

**Detalhes disfarçados**
- Desenhos de mercearia em traço fino (baguete, banana, leite, ovo, maçã, nota fiscal, cenoura, pão de forma) como padrão SVG, com 5% a 10% de opacidade e máscara que some para o lado do texto. Ficam no fundo de áreas grandes (hero, blocos de cor), nunca atrás de tabela ou número.
- Sombras só em quem "flutua": etiqueta, botão principal e cartões de passo.

**Plaquinha de oferta** (`ciclozero/mensagens.py`)
- Fundo etiqueta, faixa superior tinta (o trilho da gôndola), selo "Oferta" em tomate, preço riscado em tinta-2 e preço novo grande em tomate.
