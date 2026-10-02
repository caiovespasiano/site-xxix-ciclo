"""Redimensiona e recomprime os assets do site.

O repositório guardava os PNGs originais (cerca de 12 MB) em resolução bem
acima do que o site exibe, e as fotos de retrato vinham com uma margem
branca uniforme em volta. Este script corta essa margem, redimensiona para o
tamanho real de exibição e grava WebP.

Uso:
    python tools/optimize-images.py [--src PASTA] [--dst PASTA]

O default (--src e --dst = source/img) assume que os PNGs originais ainda
estejam na pasta. Para regerar os WebP a partir dos arquivos que estão no
histórico do git:

    git archive <commit> source/img | tar -x -C $env:TEMP/orig
    python tools/optimize-images.py --src "$env:TEMP/orig/source/img"
"""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DIR = ROOT / "source" / "img"

PEOPLE = {
    "Moderador1.png": 400,
    "Moderador2.png": 400,
    "Moderador3.png": 400,
    **{f"Palestrante{i}.png": 400 for i in range(1, 11)},
}

# insignia "ciclo" e a marca do IMM: dimensões enormes, exibidas pequenas
WIDE_LOGOS = {
    "logociclo.png": 760,
    "logoimm.png": 640,
}

# O background original é um retrato (1600x1923) em que o mapa ocupa apenas a
# faixa central. Com `background-size: cover` em telas largas ele era ampliado
# várias vezes e só a parte lisa do topo aparecia. O recorte 16:9 abaixo serve
# tanto para desktop quanto para celular, sem ampliar demais.
BACKGROUND_CROP = (0, 600, 1600, 1500)
BACKGROUND_QUALITY = 80

# Abaixo deste valor de cinza o pixel é considerado foto; acima, margem.
BORDER_THRESHOLD = 242

# Arquivos que não são usados pelo site e não valem manter no repositório.
JUNK = ["d", "logociclo2.png"]


def human(size: int) -> str:
    return f"{size / 1024:8.1f} KB"


def trim_border(image: Image.Image, threshold: int = BORDER_THRESHOLD) -> tuple[Image.Image, bool]:
    """Remove a margem clara uniforme em volta da foto.

    Sem isso, as fotos apareciam com uma borda branca e, ao aplicar
    `border-radius: 50%`, sobrava um pedaço dessa borda dentro do círculo.
    """
    # 255 onde há foto (escuro), 0 na margem (claro)
    mask = image.convert("L").point(lambda p: 255 if p < threshold else 0)
    box = mask.getbbox()

    if not box:
        return image, False

    # margem já é desprezível
    if box == (0, 0, image.width, image.height):
        return image, False

    return image.crop(box), True


def square(image: Image.Image) -> Image.Image:
    """Recorte centralizado para um quadrado exato.

    Depois de tirar a margem as fotos ficam entre 0.99 e 1.03 de proporção.
    Deixar como está faria `object-fit: cover` cortar um pedaço da foto de
    forma diferente em cada retrato. Centralizar uniformiza.
    """
    side = min(image.width, image.height)
    left = (image.width - side) // 2
    top = (image.height - side) // 2
    if (left, top, left + side, top + side) == (0, 0, image.width, image.height):
        return image
    return image.crop((left, top, left + side, top + side))


def save_square_webp(image: Image.Image, target: Path, size: int, quality: int) -> None:
    """Redimensiona para `size` x `size`, preservando o enquadramento."""
    image = square(image).resize((size, size), Image.LANCZOS)
    image.save(target, "WEBP", quality=quality, method=6)
    print(f"  {target.name:<24} -> webp {image.width}x{image.height} {human(target.stat().st_size)}")


def save_webp(image: Image.Image, target: Path, width: int, quality: int) -> None:
    if image.width > width:
        height = round(image.height * width / image.width)
        image = image.resize((width, height), Image.LANCZOS)

    image.save(target, "WEBP", quality=quality, method=6)
    print(f"  {target.name:<24} -> webp {image.width}x{image.height} {human(target.stat().st_size)}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--src", type=Path, default=DEFAULT_DIR)
    parser.add_argument("--dst", type=Path, default=DEFAULT_DIR)
    args = parser.parse_args()

    src_dir, dst_dir = args.src, args.dst
    dst_dir.mkdir(parents=True, exist_ok=True)

    before = sum(p.stat().st_size for p in src_dir.iterdir() if p.is_file())
    print(f"Antes: {human(before)}\n")

    print("Retratos (recorta margem branca + redimensiona)")
    for name, width in PEOPLE.items():
        src = src_dir / name
        if not src.exists():
            print(f"  [ignorado] {name} não existe em {src_dir}")
            continue

        with Image.open(src) as img:
            photo, trimmed = trim_border(img.convert("RGB"))
            note = "margem recortada" if trimmed else "sem margem"
            target = dst_dir / name.replace(".png", ".webp")
            before_size = target.stat().st_size if target.exists() else 0
            save_square_webp(photo, target, width, 82)
            gain = f"  (-{before_size / 1024:.0f} KB)" if before_size else ""
            print(f"  {'':<24}    {note}{gain}")
            if src_dir == dst_dir:
                src.unlink()

    print("\nMarcas grandes")
    for name, width in WIDE_LOGOS.items():
        src = src_dir / name
        if not src.exists():
            print(f"  [ignorado] {name} não existe em {src_dir}")
            continue

        with Image.open(src) as img:
            mode = "RGBA" if img.mode in ("RGBA", "LA", "P") else "RGB"
            save_webp(img.convert(mode), dst_dir / name.replace(".png", ".webp"), width, 88)
            if src_dir == dst_dir:
                src.unlink()

    print("\nBackground -> panorama 16:9")
    src = src_dir / "background.webp"
    if not src.exists():
        src = src_dir / "background.png"
    if not src.exists():
        print("  [ignorado] background não encontrado")
    else:
        with Image.open(src) as img:
            img = img.convert("RGB")
            if img.size != (BACKGROUND_CROP[2], BACKGROUND_CROP[3] - BACKGROUND_CROP[1]):
                img = img.crop(BACKGROUND_CROP)
            target = dst_dir / "background.webp"
            img.save(target, "WEBP", quality=BACKGROUND_QUALITY, method=6)
            print(f"  background.webp         -> {img.width}x{img.height} {human(target.stat().st_size)}")
            if src_dir == dst_dir and src != target:
                src.unlink()

    print("\nRemovendo arquivos não utilizados")
    for name in JUNK:
        junk = src_dir / name
        if junk.exists():
            junk.unlink()
            print(f"  {name}")

    total = sum(p.stat().st_size for p in dst_dir.iterdir() if p.is_file())
    print(f"\nDepois: {human(total)}  ({before / total:.1f}x menor)")


if __name__ == "__main__":
    main()
