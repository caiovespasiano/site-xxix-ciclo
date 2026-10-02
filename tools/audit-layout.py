"""Diagnostico visual: close (2x) em cada bloco + auditoria de alinhamento.

    python tools/inspect.py
"""

from __future__ import annotations

import contextlib
import functools
import http.server
import socketserver
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "preview"
PORT = 4341

BLOCKS = {
    "icones-palestrantes": ".menu3",
    "card-moderador": ".moderadores",
    "linha-realizacao": "#realizacao-titulo",
    "logos-realizacao": "#realizacao-titulo ~ ul.sobre-logos-apoio, #realizacao-titulo ~ div > ul.sobre-logos-apoio",
    "logos-apoio": "#apoio-titulo ~ ul.sobre-logos-apoio",
    "sobre": ".sobre",
    "organizadores": 'section[aria-labelledby="organizadores-titulo"] .sobre-inline',
    "footer": ".footer",
}

# Detecta desalinhamentos reais.
ALIGN_JS = """() => {
  const report = [];
  const px = n => Math.round(n * 10) / 10;

  // 1. colunas de grid: segmentos iguais e item centrado na sua coluna
  for (const g of document.querySelectorAll('[class*="-colunas"]')) {
    const cs = getComputedStyle(g);
    const parts = cs.gridTemplateColumns.split(' ').map(parseFloat).filter(n => !isNaN(n));
    if (parts.length > 1) {
      const min = Math.min(...parts), max = Math.max(...parts);
      if (max - min > 0.6) {
        report.push(`colunas com larguras diferentes em ${g.className}: ${parts.map(px).join(', ')}`);
      }
    }
    // o passo entre centros inclui o gap, que nao aparece em gridTemplateColumns
    const gap = parseFloat(cs.columnGap) || 0;
    const colW = parts[0] || 0;
    const gr = g.getBoundingClientRect();
    [...g.children].forEach((k, i) => {
      const kr = k.getBoundingClientRect();
      if (kr.width === 0) return;
      const expected = gr.left + i * (colW + gap) + colW / 2;
      const actual = kr.left + kr.width / 2;
      if (Math.abs(expected - actual) > 1.5) {
        report.push(`item ${i} fora do centro da coluna em ${g.className}: desvio ${px(Math.abs(expected - actual))}px`);
      }
    });
  }

  // 2. itens de flex com espacamento central desigual
  for (const f of document.querySelectorAll('.sobre-logos-apoio')) {
    const kids = [...f.children].filter(k => k.getBoundingClientRect().width > 0);
    if (kids.length < 2) continue;
    const gaps = [];
    for (let i = 1; i < kids.length; i++) {
      const a = kids[i - 1].getBoundingClientRect();
      const b = kids[i].getBoundingClientRect();
      gaps.push(px(b.left - a.right));
    }
    if (Math.max(...gaps) - Math.min(...gaps) > 1.5) {
      report.push(`espacamento irregular em .sobre-logos-apoio: ${gaps.join(', ')}`);
    }
    // bloco como todo deve estar centralizado
    const fr = f.getBoundingClientRect();
    const first = kids[0].getBoundingClientRect();
    const last = kids[kids.length - 1].getBoundingClientRect();
    const leftGap = first.left - fr.left;
    const rightGap = fr.right - last.right;
    if (Math.abs(leftGap - rightGap) > 2) {
      report.push(`.sobre-logos-apoio nao centralizado: esquerda ${px(leftGap)}px, direita ${px(rightGap)}px`);
    }
  }

  // 3. linha de base: nomes/divisorias/icones devem alinhar ENTRE os itens
  //    de uma mesma linha. O par (container, seletor-do-item) importa: um
  //    seletor de item solto faria a comparação dentro de um unico cartao.
  const linhas = [
    ['.sobre-logos-apoio-pessoas-3-colunas', '> li'],
    ['.sobre-logos-apoio-pessoas-4-colunas', '> li'],
    ['.sobre-logos-apoio', '> li'],
  ];

  for (const [seletor, sufixo] of linhas) {
    for (const lista of document.querySelectorAll(seletor)) {
      const items = [...lista.querySelectorAll(':scope' + sufixo)]
        .filter(k => k.getBoundingClientRect().height > 0);
      if (items.length < 2) continue;

      // agrupa por fileira: so compara itens que estao na mesma linha visual
      const porFileira = new Map();
      for (const it of items) {
        const t = Math.round(it.getBoundingClientRect().top);
        const chave = [...porFileira.keys()].find(k => Math.abs(k - t) < 4) ?? t;
        (porFileira.get(chave) ?? porFileira.set(chave, []).get(chave)).push(it);
      }

      for (const [top, grupo] of porFileira) {
        if (grupo.length < 2) continue;

        const rows = {};
        for (const it of grupo) {
          const pares = [
            ['nome', it.querySelector('p, h3, h4')],
            ['divisoria', it.querySelector('.linhadivisoriasociais')],
            ['icones', it.querySelector('.menu3')],
          ];
          for (const [chave, el] of pares) {
            if (!el) continue;
            const r = el.getBoundingClientRect();
            if (r.height === 0) continue;
            (rows[chave] ||= []).push(Math.round(r.top));
          }
        }

        for (const [chave, tops] of Object.entries(rows)) {
          if (tops.length < 2) continue;
          const spread = Math.max(...tops) - Math.min(...tops);
          if (spread > 2) {
            report.push(`"${chave}" desalinhado em ${seletor}: tops ${tops.join(', ')} (${spread}px)`);
          }
        }

        const bases = grupo.map(it => Math.round(it.getBoundingClientRect().bottom));
        const spread = Math.max(...bases) - Math.min(...bases);
        if (spread > 2) {
          report.push(`altura dos itens irregular em ${seletor}: ${bases.join(', ')} (${spread}px)`);
        }
      }
    }
  }

  // 4. elemento mais largo que o pai (transbordando)
  for (const el of document.querySelectorAll('.container *')) {
    if (el.matches('i, svg, use, path, g, br')) continue;
    const r = el.getBoundingClientRect();
    const p = el.parentElement.getBoundingClientRect();
    if (r.width > 0 && r.width > p.width + 1.5) {
      report.push(`transborda: ${el.tagName.toLowerCase()}.${el.className} ${px(r.width)}px > pai ${px(p.width)}px`);
    }
  }

  // 4. texto com text-align:center que nao esta de fato centralizado
  for (const el of document.querySelectorAll('p, h1, h2, h3, h4')) {
    if (getComputedStyle(el).textAlign !== 'center') continue;
    const r = el.getBoundingClientRect();
    if (r.width < 10) continue;
    const range = document.createRange();
    range.selectNodeContents(el);
    const rects = [...range.getClientRects()];
    if (!rects.length) continue;
    const left = Math.min(...rects.map(x => x.left));
    const right = Math.max(...rects.map(x => x.right));
    const off = Math.abs((r.left + r.width / 2) - (left + right) / 2);
    // elementos com padding lateral assimétrico deslocam o texto de proposito
    const cs = getComputedStyle(el);
    const skew = Math.abs(parseFloat(cs.paddingLeft) - parseFloat(cs.paddingRight));
    if (off > 3 && skew < 1) {
      report.push(`texto desalinhado ${px(off)}px: <${el.tagName.toLowerCase()} class="${el.className}">`);
    }
  }

  // 5. icones: glifo presente, com area e com a fonte da lib aplicada.
  //    O Bootstrap Icons define font-family no ::before, nao no <i>.
  for (const ic of document.querySelectorAll('i.bi')) {
    const r = ic.getBoundingClientRect();
    if (r.width < 6 || r.height < 6) {
      report.push(`icone sem area: .${ic.className} ${px(r.width)}x${px(r.height)}`);
      continue;
    }
    const cls = [...ic.classList].find(c => c.startsWith('bi-') && c !== 'bi');
    if (!cls) { report.push(`classe do Bootstrap Icons ausente: "${ic.className}"`); continue; }

    const before = getComputedStyle(ic, '::before');
    const fam = (before.fontFamily || '').toLowerCase();
    if (!fam.includes('bootstrap-icons')) {
      report.push(`fonte do icone nao aplicada: .${cls} -> ${before.fontFamily || '(vazio)'}`);
    }
    if (before.content === 'none' || before.content === 'normal') {
      report.push(`glifo vazio: .${cls} (content=${before.content})`);
    }
  }

  // 6. a fonte de icones realmente baixou
  const faces = [...document.fonts].filter(f => /bootstrap-icons/i.test(f.family));
  if (!faces.length) {
    report.push('Bootstrap Icons: nenhuma @font-face registrada');
  } else if (!faces.some(f => f.status === 'loaded')) {
    report.push(`Bootstrap Icons: fonte registrada mas nao carregada (${faces.map(f => f.status).join(', ')})`);
  }

  return [...new Set(report)];
}"""


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):  # noqa: D102
        pass


@contextlib.contextmanager
def serve():
    handler = functools.partial(Quiet, directory=str(ROOT))
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("127.0.0.1", PORT), handler) as httpd:
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        try:
            yield
        finally:
            httpd.shutdown()


def main() -> None:
    OUT.mkdir(exist_ok=True)

    with serve(), sync_playwright() as pw:
        browser = pw.chromium.launch(channel="msedge")
        page = browser.new_page(
            viewport={"width": 1440, "height": 900}, device_scale_factor=2
        )
        page.goto(f"http://127.0.0.1:{PORT}/index.html", wait_until="networkidle")
        page.add_style_tag(content="html{scroll-behavior:auto !important}")
        page.wait_for_timeout(700)
        page.evaluate(
            """async () => { const s = innerHeight*0.6;
              for (let y=0; y<document.body.scrollHeight; y+=s) {
                scrollTo(0,y); await new Promise(r=>setTimeout(r,110)); } }"""
        )
        page.wait_for_timeout(900)

        for name, sel in BLOCKS.items():
            loc = page.locator(sel).first
            if loc.count() == 0:
                print(f"  [pulado] {name}: seletor '{sel}' nao encontrado")
                continue
            try:
                loc.scroll_into_view_if_needed()
                page.wait_for_timeout(250)
                loc.screenshot(path=str(OUT / f"insp-{name}.png"))
            except Exception as exc:  # noqa: BLE001
                print(f"  [erro] {name}: {exc}")

        print("\n=== auditoria de alinhamento ===")
        issues = page.evaluate(ALIGN_JS)
        for issue in issues:
            print("  -", issue)
        if not issues:
            print("  nada encontrado")

        # O skip-link precisa estar escondido e aparecer no primeiro Tab.
        skip = page.evaluate(
            """() => { const a = document.querySelector('.skip-link').getBoundingClientRect();
                       return { visivel: a.bottom > 0 }; }"""
        )
        page.keyboard.press("Tab")
        page.wait_for_timeout(500)
        skip_focus = page.evaluate(
            """() => { const e = document.querySelector('.skip-link');
                       const a = e.getBoundingClientRect();
                       return { visivel: a.bottom > 0,
                                focado: document.activeElement === e }; }"""
        )

        print("\n=== skip-link ===")
        if skip["visivel"]:
            print("  - PROBLEMA: visível sem estar focado")
        elif not skip_focus["visivel"] or not skip_focus["focado"]:
            print("  - PROBLEMA: não aparece no primeiro Tab")
        else:
            print("  OK: escondido por padrão e aparece no primeiro Tab")

        browser.close()

    print(f"\nCapturas em: {OUT}")


if __name__ == "__main__":
    main()