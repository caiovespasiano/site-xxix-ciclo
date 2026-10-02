"""Compara o site original com a versao atual, lado a lado.

Sobe os dois em servidores locais, compara altura, margem e posicao dos
blocos de titulo e salva capturas das duas paginas, para conferir se o
layout foi preservado.

    python tools/compare-original.py [--ref origin/main]

O padrao e `origin/main` (o site publicado). Nao use HEAD~1: depois do
primeiro commit ele passa a apontar para o proprio trabalho e a comparacao
fica circular, sempre "batendo".
"""

from __future__ import annotations

import argparse
import contextlib
import functools
import http.server
import socketserver
import subprocess
import threading
import tempfile
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "preview"
NEW_PORT = 4331
OLD_PORT = 4332
DEFAULT_REF = "origin/main"

# Medidas que precisam bater entre as duas versoes.
SELECTORS = [
    ".linhadivisoriatexto",
    ".linhadivisoriatexto-2",
    ".linhadivisoriabody",
    ".linhadivisoriabody-realizacao",
    ".h1-sobre",
    ".h2-sobre",
    ".h3-sobre",
    ".container-subtitulo",
    ".container-titulos",
]


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):  # noqa: D102
        pass


@contextlib.contextmanager
def serve(directory: Path, port: int):
    handler = functools.partial(Quiet, directory=str(directory))
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("127.0.0.1", port), handler) as httpd:
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        try:
            yield f"http://127.0.0.1:{port}/index.html"
        finally:
            httpd.shutdown()


def checkout_original(dest: Path, ref: str) -> None:
    """Materializa a versao de referencia num diretorio temporario."""
    archive = subprocess.run(
        ["git", "archive", ref], cwd=ROOT, capture_output=True, check=True
    ).stdout
    tar = subprocess.run(
        ["tar", "-x", "-C", str(dest)], input=archive, capture_output=True, check=True
    )
    if tar.returncode != 0:
        raise RuntimeError(tar.stderr.decode(errors="replace"))


MEASURE = """(sels) => {
  const out = [];
  for (const sel of sels) {
    const el = document.querySelector(sel);
    if (!el) { out.push({ sel, missing: true }); continue; }
    const r = el.getBoundingClientRect();
    const cs = getComputedStyle(el);
    out.push({
      sel,
      top: Math.round(r.top + window.scrollY),
      height: Math.round(r.height),
      fontSize: cs.fontSize,
      lineHeight: cs.lineHeight,
      marginTop: cs.marginTop,
      marginBottom: cs.marginBottom,
      paddingTop: cs.paddingTop,
    });
  }
  return out;
}"""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ref", default=DEFAULT_REF)
    args = parser.parse_args()

    OUT.mkdir(exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp:
        old_dir = Path(tmp)
        checkout_original(old_dir, args.ref)

        print(f"referencia: {args.ref}\n")

        with serve(ROOT, NEW_PORT), serve(old_dir, OLD_PORT), sync_playwright() as pw:
            browser = pw.chromium.launch(channel="msedge")
            results = {}

            for label, url in (("original", OLD_PORT), ("atual", NEW_PORT)):
                page = browser.new_page(viewport={"width": 1440, "height": 900})
                page.goto(f"http://127.0.0.1:{url}/index.html", wait_until="domcontentloaded")
                page.add_style_tag(content="html{scroll-behavior:auto !important}")
                # O ScrollReveal do original esconde o conteudo: revela tudo.
                page.evaluate(
                    "document.querySelectorAll('[style*=opacity]')"
                    ".forEach(e => e.style.opacity = '1')"
                )
                page.wait_for_timeout(2500)

                results[label] = page.evaluate(MEASURE, SELECTORS)

                page.screenshot(path=str(OUT / f"cmp-{label}-titulos.png"))
                page.locator(".linhadivisoriabody-realizacao").first.screenshot(
                    path=str(OUT / f"cmp-{label}-secao.png")
                )
                page.close()

            browser.close()

    print(f"{'seletor':<34}{'propriedade':<12}{args.ref.split('/')[-1]:>12}{'atual':>12}   ")
    print("-" * 72)

    diffs = 0
    for old, new in zip(results["original"], results["atual"]):
        sel = old["sel"]
        if old.get("missing") or new.get("missing"):
            print(f"{sel:<34}{'(ausente)':<12}{'-':>12}{'-':>12}")
            continue
        for prop in ("height", "fontSize", "lineHeight", "marginTop", "marginBottom", "paddingTop"):
            o, n = old[prop], new[prop]
            flag = ""
            if prop in ("height", "marginTop", "marginBottom") and o != n:
                flag = "  <-- DIFERE"
                diffs += 1
            print(f"{sel:<34}{prop:<12}{o:>12}{n:>12}{flag}")

    print(f"\n{diffs} diferença(s) de espaçamento em {len(SELECTORS)} blocos.")


if __name__ == "__main__":
    main()