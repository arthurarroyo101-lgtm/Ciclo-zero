# Roteiro da apresentação (palco)

> **O que aparece na tela:** os **slides** (`docs/pitch.pdf`) são o fio condutor. No slide 5, a tela troca para a **demo**, que é o app Streamlit rodando ao vivo. Depois volta aos slides até o fim.
> **Landing page:** não entra no tempo do pitch. Fica aberta numa aba para a hora das perguntas (ex.: "como o cliente conheceria o produto?") e o link vai no README.
> Fala detalhada de cada slide: `docs/estudo/JOAO.md`. Cliques da demo: `docs/DEMO.md`.

## Quem faz o quê
| Pessoa | No palco |
|---|---|
| **João Paulo** | Fala o pitch inteiro, do slide 1 ao 10. Passa os slides (passador ou setas). |
| **Matheus** | No computador: opera a demo no slide 5. Responde às perguntas técnicas. |
| **Arthur** | Cronometra, mostra o sinal de "1 minuto" e responde às perguntas de negócio. |

## Montagem do computador (10 min antes)
1. **Janela 1, os slides:** `docs/pitch.pdf` em tela cheia (ou o deck do Claude em modo Apresentar).
2. **Janela 2, o app:** `streamlit run app.py` no navegador em tela cheia, zoom 125%.
   - Clicar em **Recriar dados de exemplo**.
   - Preencher o nome da loja: "Padaria Canto Caseiro".
   - Deixar a aba **Dashboard** aberta, com Loja ao vivo e Modo técnico **desligados**.
3. **Janela 3, reserva:** o vídeo da demo pronto para dar play. Numa aba extra, a landing page.
4. Trocar de janela: **⌘+Tab** (Mac) ou **Alt+Tab** (Windows). Teste a troca uma vez antes de subir.
5. Mac em **Não perturbe**, carregador na tomada e internet testada (com o roteador do celular como reserva).

## Linha do tempo (versão de 5 min)
| Tempo | Tela | Quem | O que acontece |
|---|---|---|---|
| 0:00 | Slide 1 (capa) | João | Gancho: "E se parte do lucro da sua loja estivesse vencendo na prateleira?" |
| 0:30 | Slide 2 (problema) | João | Decidir todo dia sem informação; o relato do Canto Caseiro. |
| 1:10 | Slide 3 (sem e com) | João | O dia do comerciante, antes e depois. |
| 1:55 | Slide 4 (como funciona) | João | Registrar, acompanhar, agir e aprovar. |
| 2:30 | Slide 5 (demo) | João | "Os dados são fictícios; as vendas são simuladas. **Matheus, mostra pra gente.**" |
| 2:35 | **App (⌘+Tab)** | Matheus opera, João narra | Loja ao vivo → nota fiscal → rotina diária → aprovar pedido e mensagem ao fornecedor (cerca de 85 s, `DEMO.md`). |
| 4:00 | **Slides (⌘+Tab)**, slide 6 | João | "Feito para não inventar nada": 100%, 3 leis, 16 testes. |
| 4:15 | Slides 7 e 8 | João | Validação (uma frase cada entrevista) e modelo de negócio (R$ 49 é hipótese). |
| 4:40 | Slide 9 | João | Próximo passo: piloto de 30 dias; quem é a equipe. |
| 4:55 | Slide 10 | João | "Não dá para recuperar o que já venceu. Mas dá para decidir melhor antes. Obrigado." |

> Com a demo no meio, 5 minutos fica justo. Nos slides 6 a 9, fale **uma frase por slide**. Se o Arthur mostrar "1 minuto" antes do slide 7, pule direto para o 9.

## Se o pitch tiver só 3 minutos
Slides 1 → 2 → 4 → 5 (demo **curta**, cerca de 60 s: Loja ao vivo + nota fiscal + rotina) → 6 → 9 → 10. Pule os slides 3, 7 e 8. A validação vira uma frase no slide 2 e o modelo de negócio vira uma frase no slide 9.

## Se algo der errado
| Problema | O que fazer |
|---|---|
| App travou ou deu erro na tela | Matheus: ⌘+Tab para o **vídeo** e dar play. João continua narrando. |
| A IA demora mais de 40 s | João continua explicando o fluxo; se passar de 60 s, ir para o vídeo. |
| Sem internet | Vídeo direto. |
| A notificação amarela não apareceu | Seguir o roteiro e, na volta, mostrar a aba **Alertas**. |
| Estourou o tempo | Ir direto para o slide 10 e fechar com a frase final. |

## Perguntas da banca
- **Técnicas** (IA, dados, testes, leis) → Matheus (`docs/estudo/MATHEUS.md`).
- **Tela e uso** → João (`docs/estudo/JOAO.md`).
- **Negócio, preço, mercado, validação** → Arthur (`docs/estudo/ARTHUR.md`).
- Regra: responder curto, sem prometer o que não foi medido. "Isso o piloto vai medir" é uma boa resposta.
