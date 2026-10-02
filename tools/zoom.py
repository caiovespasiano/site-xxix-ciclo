"""Capturas ampliadas de trechos especificos, para inspecao visual.

    python tools/zoom.py
"""

from __future__ import annotations

import contextlib
import functools
import http.server
import socketserver
import subprocess
import tempfile
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "preview"
NEW_PORT, OLD_PORT = 4341, 4342

TARGETS = {
    "icones-realizacao": "#realizacao-titulo",
    "icones-apoio": "#apoio-titulo",
    "icones-pessoa": ".sobre-logos-apoio-pessoas-3-colunas",
    "organizadores": ".sobre-logos-apoio:has(.sobre-imm)",
}


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


def checkout_original(dest: Path) -> None:
    archive = subprocess.run(
        ["git", "archive", "HEAD~1"], cwd=ROOT, capture_output=True, check=True
    ).stdout
    subprocess.run(["tar", "-x", "-C", str(dest)], input=archive, check=True)


def main() -> None:
    OUT.mkdir(exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp, sync_playwright() as pw:
        old_dir = Path(tmp)
        checkout_original(old_dir)

        with serve(ROOT, NEW_PORT), serve(old_dir, OLD_PORT):
            browser = pw.chromium.launch(channel="msedge")

            for label, port in (("orig", OLD_PORT), ("novo", NEW_PORT)):
                page = browser.new_page(
                    viewport={"width": 1440, "height": 900}, device_scale_factor=2
                )
                page.goto(f"http://127.0.0.1:{port}/index.html", wait_until="domcontentloaded")
                page.add_style_tag(content="html{scroll-behavior:auto !important}")
                page.wait_for_timeout(2500)

                for name, selector in TARGETS.items():
                    try:
                        loc = page.locator(selector).first
                        loc.scroll_into_view_if_needed()
                        page.wait_for_timeout(300)
                        loc.screenshot(path=str(OUT / f"zoom-{name}-{label}.png"))
                    except Exception as exc:  # noqa: BLE001
                        print(f"{label}/{name}: {exc}")

                page.close()

            browser.close()

    print("capturas ampliadas em", OUT)


if __name__ == "__main__":
    main()