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
- Emoji em todo título: só nas abas (servem de navegação) e nos alertas.
- Palavras em CAIXA ALTA como rótulo; seta "→" em botão; texto de enfeite.
- Animação em tudo: a única animação é a contagem dos números do topo.

## Textos
- Falar como o dono fala: "Vai para o lixo", "A pagar", "Comprado a mais". Não "excedente", não "KPI".
- Botão diz exatamente o que acontece: "Aprovar pedido", "Lançar no estoque".
- Erro diz o que houve e como resolver, sem pedir desculpas.

## Quem mexe em quê
| Pessoa | Arquivos |
|---|---|
| Matheus | `docs/DESIGN.md`, etiquetas do topo (`ciclozero/ao_vivo.py`), aba Nota fiscal (`ciclozero/ui_nota.py`) |
| João | tema e fontes (`.streamlit/config.toml`, CSS em `ciclozero/ui_agente.py`), Dashboard, chat, Pedidos, rótulos no `app.py` |
