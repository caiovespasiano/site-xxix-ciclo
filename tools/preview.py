"""Auditoria automatizada + capturas de tela da landing page.

Sobe um http.server local, abre a pagina no Chromium via Playwright e:
  1. reporta erros de console e requisicoes 404;
  2. mede overflow horizontal em varios breakpoints;
  3. confere a hierarquia de headings e atributos de acessibilidade;
  4. captura telas desktop, tablet e mobile em `preview/`.

Uso:
    python tools/preview.py
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
PORT = 4322
URL = f"http://127.0.0.1:{PORT}/index.html"

VIEWPORTS = [
    ("desktop", 1440, 900),
    ("laptop", 1180, 800),
    ("tablet", 820, 1180),
    ("mobile", 390, 844),
    ("mobile-small", 320, 640),
]


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):  # noqa: D102
        pass


@contextlib.contextmanager
def serve():
    handler = functools.partial(QuietHandler, directory=str(ROOT))
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("127.0.0.1", PORT), handler) as httpd:
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        try:
            yield
        finally:
            httpd.shutdown()


def audit(page, label: str) -> None:
    result = page.evaluate(
        """() => {
        const docW = document.documentElement.clientWidth;
        const wide = [];
        for (const el of document.querySelectorAll('body *')) {
          const r = el.getBoundingClientRect();
          if (r.width === 0) continue;
          if (r.right > docW + 1 || r.left < -1) {
            wide.push(`${el.tagName.toLowerCase()}.${el.className || '-'}` +
                      ` [${Math.round(r.left)}..${Math.round(r.right)}]`);
          }
        }
        const headings = [...document.querySelectorAll('h1,h2,h3,h4,h5,h6')]
          .map(h => `${h.tagName} ${h.textContent.trim().slice(0, 42)}`);
        const imgNoAlt = [...document.querySelectorAll('img')]
          .filter(i => !i.hasAttribute('alt')).map(i => i.src.split('/').pop());
        const imgsNoDims = [...document.querySelectorAll('img')]
          .filter(i => !i.hasAttribute('width') || !i.hasAttribute('height'))
          .map(i => i.src.split('/').pop());
        const linksNoRel = [...document.querySelectorAll('a[target=_blank]')]
          .filter(a => !(a.rel || '').includes('noopener')).length;
        const noAccessibleName = [...document.querySelectorAll('a,button')]
          .filter(el => {
            const t = (el.textContent || '').trim();
            return !t && !el.getAttribute('aria-label') && !el.getAttribute('title');
          }).length;
        const hidden = [...document.querySelectorAll('[data-reveal]')]
          .filter(el => getComputedStyle(el).opacity === '0').length;
        return {
          docW,
          scrollW: document.documentElement.scrollWidth,
          wide: wide.slice(0, 8),
          headings,
          imgNoAlt,
          imgsNoDims,
          linksNoRel,
          noAccessibleName,
          hiddenReveals: hidden,
          totalReveals: document.querySelectorAll('[data-reveal]').length,
        };
        }"""
    )

    overflow = result["scrollW"] - result["docW"]
    status = "OK " if overflow <= 1 else "OVERFLOW"
    print(f"\n=== {label} ({result['docW']}px) — {status} ===")
    print(f"  scrollWidth: {result['scrollW']} (overflow {overflow}px)")
    if result["wide"]:
        print("  elementos fora da viewport:")
        for w in result["wide"]:
            print(f"    - {w}")
    print(f"  imagens sem alt: {len(result['imgNoAlt'])} {result['imgNoAlt']}")
    print(f"  imagens sem width/height: {len(result['imgsNoDims'])} {result['imgsNoDims']}")
    print(f"  target=_blank sem rel=noopener: {result['linksNoRel']}")
    print(f"  links/botões sem nome acessível: {result['noAccessibleName']}")
    print(f"  [data-reveal] ainda invisíveis: {result['hiddenReveals']}/{result['totalReveals']}")
    if label == "desktop":
        print("  hierarquia de headings:")
        for h in result["headings"]:
            print(f"    {h}")


def launch_browser(pw):
    """Usa o Edge já instalado no sistema, evitando baixar outro Chromium."""
    try:
        return pw.chromium.launch(channel="msedge")
    except Exception:
        return pw.chromium.launch()


def main() -> None:
    OUT.mkdir(exist_ok=True)

    with serve(), sync_playwright() as pw:
        browser = launch_browser(pw)
        console_errors: list[str] = []
        failed: list[str] = []

        for name, width, height in VIEWPORTS:
            page = browser.new_page(viewport={"width": width, "height": height})
            page.on(
                "console",
                lambda m: console_errors.append(f"[{m.type}] {m.text}")
                if m.type in ("error", "warning")
                else None,
            )
            page.on("requestfailed", lambda r: failed.append(f"{r.url} — {r.failure}"))
            page.on(
                "response",
                lambda r: failed.append(f"{r.status} {r.url}") if r.status >= 400 else None,
            )

            page.goto(URL, wait_until="networkidle")
            page.wait_for_timeout(1200)

            audit(page, name)

            page.screenshot(path=str(OUT / f"{name}-topo.png"))

            # Desliga a rolagem suave: com ela ligada, os scrollTo em sequência
            # são interrompidos e a página nunca chega a rolar de fato.
            page.add_style_tag(content="html { scroll-behavior: auto !important; }")

            # Rola a página inteira para disparar as revelações antes da captura.
            page.evaluate(
                """async () => {
                  const step = window.innerHeight * 0.6;
                  for (let y = 0; y < document.body.scrollHeight; y += step) {
                    window.scrollTo(0, y);
                    await new Promise(r => setTimeout(r, 120));
                  }
                  await new Promise(r => setTimeout(r, 300));
                }"""
            )
            page.wait_for_timeout(700)

            # Confere que o fundo fixo continua visível no meio da página.
            page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2)")
            page.wait_for_timeout(500)
            page.screenshot(path=str(OUT / f"{name}-meio.png"))

            page.evaluate("window.scrollTo(0, 0)")
            page.wait_for_timeout(500)

            page.screenshot(path=str(OUT / f"{name}-completo.png"), full_page=True)
            page.close()

        browser.close()

    print("\n=== rede ===")
    print("  requicoes com falha / 404:", failed or "nenhuma")

    print("\n=== console ===")
    noise = [e for e in console_errors if "favicon" not in e]
    for e in noise[:20]:
        print(f"  {e}")
    if not noise:
        print("  nenhum erro ou aviso")

    print(f"\nCapturas em: {OUT}")


if __name__ == "__main__":
    main()