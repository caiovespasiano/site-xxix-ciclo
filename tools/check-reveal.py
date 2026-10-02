"""Confere a direcao da animacao de reveal.

Rola a pagina, dispara a revelacao de um bloco e mede a posicao do elemento
durante a transicao. Se desce, a coordenada `top` aumenta ao longo do tempo.

    python tools/check-reveal.py
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
PORT = 4361


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
            yield f"http://127.0.0.1:{PORT}/index.html"
        finally:
            httpd.shutdown()


SAMPLE = """async (sel) => {
  const el = document.querySelector(sel);
  const samples = [];
  // rola ate o elemento e dispara a revelacao manualmente
  el.scrollIntoView({ block: 'center', behavior: 'instant' });
  await new Promise(r => setTimeout(r, 300));
  const rest = el.getBoundingClientRect().top;
  el.classList.remove('is-visible');
  await new Promise(r => setTimeout(r, 300));
  const start = el.getBoundingClientRect().top;
  el.classList.add('is-visible');
  for (let i = 0; i < 10; i++) {
    samples.push(Math.round(el.getBoundingClientRect().top * 10) / 10);
    await new Promise(r => setTimeout(r, 70));
  }
  return { start, rest, samples };
}"""


def main() -> None:
    with serve(), sync_playwright() as pw:
        browser = pw.chromium.launch(channel="msedge")
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto(
            f"http://127.0.0.1:{PORT}/index.html", wait_until="domcontentloaded"
        )
        page.add_style_tag(content="html{scroll-behavior:auto !important}")
        page.wait_for_timeout(800)

        failures = 0
        for selector in (".distintivostopo", ".ciclotitulo1a", "#moderadores-titulo"):
            data = page.evaluate(SAMPLE, selector)
            start, rest, samples = data["start"], data["rest"], data["samples"]

            print(f"\n{selector}")
            print(f"  inicio  top={start}  (repouso top={rest})")
            print(f"  amostras: {' -> '.join(str(s) for s in samples)}")

            delta = samples[-1] - samples[0]
            descending = delta > 0
            print(f"  deslocamento total: {delta:+.1f}px")

            if not descending:
                print("  FALHA: o elemento esta subindo")
                failures += 1
            elif abs(rest - samples[0]) < 4:
                print("  FALHA: comecou ja no lugar, sem deslocamento")
                failures += 1
            else:
                print("  OK: desce de cima para o lugar")

        browser.close()

    print("\n" + ("todos os blocos descem" if not failures else f"{failures} falha(s)"))
    raise SystemExit(1 if failures else 0)


if __name__ == "__main__":
    main()
