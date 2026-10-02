"""Valida o index.html no validador oficial do W3C (Nu).

    python tools/validate.py
"""

from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENDPOINT = "https://validator.w3.org/nu/?out=json"


def main() -> int:
    html = (ROOT / "index.html").read_bytes()

    request = urllib.request.Request(
        ENDPOINT,
        data=html,
        headers={"Content-Type": "text/html; charset=utf-8", "User-Agent": "Mozilla/5.0"},
    )

    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            messages = json.load(response)["messages"]
    except Exception as exc:  # noqa: BLE001
        print(f"Falha ao chamar o validador: {exc}")
        return 2

    errors = [m for m in messages if m["type"] == "error"]
    others = [m for m in messages if m["type"] != "error"]

    print(f"ERROS: {len(errors)}   AVISOS: {len(others)}\n")

    for kind, group in (("ERRO ", errors), ("AVISO", others)):
        for msg in group[:30]:
            line = msg.get("lastLine", "?")
            print(f" {kind} linha {line} - {msg['message'][:160]}")

    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())