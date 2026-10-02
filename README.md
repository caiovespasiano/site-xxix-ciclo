# XXIX Ciclo de Estudos Estratégicos

Landing page do **XXIX Ciclo de Estudos Estratégicos** (XXIX CEE) da Escola de
Comando e Estado-Maior do Exército (ECEME) — *Os Desafios do Sistema
Internacional Contemporâneo para a Defesa*, realizado em 28 e 29 de maio de
2024, na Urca, Rio de Janeiro.

Site estático: HTML, CSS e JavaScript sem build, sem framework e sem
dependência de runtime.

---

## O que mudou nesta modernização

O escopo foi **corrigir a implementação sem mexer no layout**. A estrutura de
seções, a ordem, os títulos centralizados em caixa alta com as linhas
divisórias, o título do hero em três linhas e as contagens de colunas (3 / 4 /
3+3 / 4 / 2) foram preservados.

### Bugs corrigidos

| Problema | Causa | Correção |
| --- | --- | --- |
| Fundo da página não aparecia | O CSS apontava para uma URL assinada do **Discord que expirou**; o `background.png` estava no repositório sem nunca ser usado | Imagem local em duas camadas fixas (`body::before` com gradiente + `body::after` com o mapa) |
| Fundo sumia ao rolar | `background` no `<body>` com `no-repeat` e sem `background-attachment` | Camada `position: fixed`, que acompanha a viewport |
| Mapa não aparecia no desktop | A imagem é um retrato (1600×1923); com `cover` em tela larga era ampliado muitas vezes e só a faixa lisa do topo aparecia | Recorte 16:9 da região do mapa (`tools/optimize-images.py`) |
| Linhas divisórias grossas e opacas | `opacity: 20%` é **inválido**; o navegador descartava a regra e a linha ficava 100% opaca | `opacity: 0.25` e espessura de 2px |
| Logotipo CEEEx virava um traço de 1px no celular | `.logo-ceeex img { height: 1px }` dentro de media query | Tamanho responsivo normal |
| Ícones deformados | `font: 2px` no celular e `font-size` aplicado a SVG (que não funciona) | Bootstrap Icons, que é fonte: o `font-size` volta a valer |
| Espelhamento esquisito da página | `html { display: flex; align-items: center }` | Removido |
| Rolagem suave e barra de rolagem em *todo* elemento | `* { scroll-behavior }` e `*::-webkit-scrollbar` | Aplicados no `html` |
| Site "piscava" e reanimava a cada rolagem | ScrollReveal com `reset: true` e delays de até 2050ms | `IntersectionObserver`, dispara uma única vez |
| Revelação subindo em vez de descer | `transform: translateY(16px)` posicionava o elemento abaixo do lugar | `translateY(-16px)`: parte de cima e desce |
| Título do hero não se movia | `.ciclotitulo1a` era `inline`, e `transform` não se aplica a inline | `display: inline-block` |
| Colunas 3 e 4 eram idênticas | As duas classes tinham exatamente a mesma regra `flex: 0 1 calc(20% - 10px)` | `grid` com 3 e 4 colunas de verdade |
| Texto minúsculo no celular | Tamanhos em `vw` sem piso | `clamp()` com mínimo legível |
| Retratos dentro do círculo com borda branca | As fotos tinham ~24px de margem branca embutida, cortada pelo `border-radius` | Margem cortada na geração do WebP |
| Favicon 404 em subpasta | Caminho absoluto `/source/img/favicon.ico` | Caminho relativo |

### HTML e acessibilidade

- `<header>` estava **fora do `<body>`** e vazio — removido.
- `<div>` dentro de `<h1>` — substituído por `<span>` **mantendo os nomes de
  classe** (`container-titulos2`, `container-titulos3`).
- `<a>` direto dentro de `<ul>`, sem `<li>` — corrigido.
- `id` duplicado (`voltarParaCima` no container **e** no link) — corrigido.
- `&nbsp;×11` no lugar de recuo de parágrafo — removido (o texto agora é
  justificado e centralizado como no original).
- Hierarquia de headings real: um `<h1>` e `<h2>`/`<h3>` por seção, com
  `<section aria-labelledby>`.
- Os 13 `alt="Moderador 1"` repetidos foram corrigidos para descrever a pessoa.
- `target="_blank"` sem `rel="noopener noreferrer"` — corrigido.
- Ícones pelo **Bootstrap Icons** (fonte, não precisa de JavaScript): sai o kit
  do Font Awesome, que era script de terceiros render-blocking.
- `skip-link`, `:focus-visible` visível, `prefers-reduced-motion` respeitado.
- Validador oficial do W3C: **0 erros e 0 avisos**.

### Alinhamento

Nas listas de realização e apoio os distintivos têm proporções muito diferentes
(escudos verticais de 150×208 e o IMM horizontal de 324×209). Cada um ocupava
uma altura diferente, então nome, linha divisória e ícones saíam de linha —
o IMM ficava mais alto e com a divisória maior.

Agora cada distintivo ocupa uma **caixa de altura fixa com
`object-fit: contain`**, que preserva a proporção de cada imagem dentro de um
mesmo espaço, e os itens da linha têm **largura igual**. Resultado: nomes,
divisórias e ícones alinhados.

`tools/audit-layout.py` confere isso automaticamente: largura dos segmentos do
grid, centro de cada item na sua coluna, espaçamento regular entre itens de
flex, alinhamento de base entre itens de uma linha, transbordo de caixa,
centralização real do texto e integridade dos ícones (área, classe e fonte
carregada).

### Imagens

As imagens foram redimensionadas para o tamanho real de exibição e
recomprimidas em WebP, com `width`/`height`, `loading="lazy"` e
`decoding="async"`.

**12,2 MB → 545 KB (22× menor)**. Um PNG de 5.000×4.276 px usado a 389 px de
largura virou 68 KB.

As 13 fotos de retrato vieram com uma **margem branca uniforme de ~24 px** nos
quatro lados. Como o site as exibe em círculo (`border-radius: 50%`), o
recorte circularoia essa margem e sobrava um pedaço branco dentro do círculo.
`tools/optimize-images.py` agora detecta e corta essa margem, e centraliza o
resultado num quadrado exato de 400×400 — assim `object-fit: cover` não corta
nada e os 13 retratos ficam idênticos em proporção.

---

## Estrutura

```
.
├── index.html
├── style.css              # folha única, organizada por seções comentadas
├── js/
│   └── main.js            # revelação por rolagem + botão voltar ao topo
├── source/img/            # assets em WebP
└── tools/
    ├── optimize-images.py   # corta margens, redimensiona e recomprime
    ├── compare-original.py  # confere o layout contra origin/main
    ├── audit-layout.py      # audita alinhamento, ícones e skip-link
    ├── check-reveal.py      # mede a direção da animação de reveal
    ├── preview.py           # auditoria automatizada + capturas de tela
    └── validate.py          # valida o HTML no validador do W3C
```

## Rodando localmente

Não há build. Sirva a pasta com qualquer servidor estático:

```bash
python -m http.server 8000
```

E abra `http://localhost:8000`.

> Abrir o `index.html` direto pelo sistema de arquivos também funciona, mas
> um servidor evita restrições de CORS em navegadores antigas.

## Ferramentas

Recriam os assets e conferem o resultado. Requerem `pillow` e `playwright`.

```bash
pip install pillow playwright
playwright install chromium      # ou use o Edge já instalado

python tools/optimize-images.py  # regerar os WebP
python tools/preview.py          # auditoria + capturas em preview/
python tools/validate.py         # validação W3C
python tools/audit-layout.py     # alinhamento, ícones e skip-link
python tools/check-reveal.py     # direção da animação de reveal
python tools/compare-original.py # mede o layout contra origin/main
```

`tools/preview.py` verifica overflow horizontal em 5 breakpoints, imagens sem
`alt` ou sem dimensões, links externos sem `rel`, links sem nome acessível e
erros de console/rede — e salva as capturas em `preview/`.

`tools/compare-original.py` sobe `origin/main` ao lado da versão atual e
compara altura, margens e padding dos blocos de título. É o que garante que o
layout não foi desfeito: na única diferença restante está a espessura das
linhas divisórias, que foi corrigida de propósito.

`tools/check-reveal.py` amostra a posição dos elementos durante a transição e
falha se algum não descer. Foi ele que pegou o título do hero parado, porque
`transform` não se aplica a elemento `inline`.

`tools/audit-layout.py` audita alinhamento, integridade dos ícones e o
comportamento do skip-link no teclado.

Para regerar os WebP a partir dos PNGs originais (que não estão mais na
pasta), extraia-os do histórico do git:

```bash
git archive origin/main source/img | tar -x -C "$env:TEMP/orig"
python tools/optimize-images.py --src "$env:TEMP/orig/source/img"
```

## Acessibilidade e performance

- Contraste e foco visível para navegação por teclado.
- Funciona sem JavaScript: as animações ficam sob `.js`, então nada some.
- `prefers-reduced-motion: reduce` desliga as transições.
- Zero requisições de terceiros de JavaScript: as duas dependências externas
  são folhas de estilo (Google Fonts e Bootstrap Icons).

## Licença

[CC0-1.0](LICENSE) — conteúdo institucional da ECEME; o código foi
desenvolvido pela Seção de Comunicação Social da ECEME.