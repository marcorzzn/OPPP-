"""Genera le icone PWA di OverPowerPoint (da rilanciare solo se cambiano i colori brand).

Uso:  python tests/_generate_icons.py
Richiede Pillow (incluso nell'ambiente Python fornito con DSH; non è una dipendenza dell'app).
"""
from __future__ import annotations

import pathlib

from PIL import Image, ImageDraw, ImageFont

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "icons"
OUT.mkdir(exist_ok=True)

TOP = (255, 154, 46)
BOTTOM = (201, 111, 16)
WHITE = (255, 255, 255)


def gradient(size: int) -> Image.Image:
    img = Image.new("RGB", (size, size))
    px = img.load()
    for y in range(size):
        for x in range(size):
            t = (x + y) / (2 * (size - 1))
            px[x, y] = tuple(round(TOP[i] + (BOTTOM[i] - TOP[i]) * t) for i in range(3))
    return img


def font_for(size: int) -> ImageFont.FreeTypeFont:
    for name in ("segoeuib.ttf", "arialbd.ttf", "DejaVuSans-Bold.ttf"):
        path = pathlib.Path("C:/Windows/Fonts") / name
        if path.exists():
            return ImageFont.truetype(str(path), size)
    return ImageFont.load_default()


def icon(size: int, text_ratio: float, path: pathlib.Path) -> None:
    img = gradient(size).convert("RGBA")
    draw = ImageDraw.Draw(img)
    target = int(size * text_ratio)
    font = font_for(target)
    box = draw.textbbox((0, 0), "OPP", font=font)
    w, h = box[2] - box[0], box[3] - box[1]
    draw.text(
        ((size - w) / 2 - box[0], (size - h) / 2 - box[1]),
        "OPP",
        font=font,
        fill=WHITE + (255,),
    )
    img.save(path, "PNG")
    print("scritto", path.relative_to(ROOT), f"{size}x{size}")


icon(192, 0.44, OUT / "icon-192.png")
icon(512, 0.44, OUT / "icon-512.png")
icon(512, 0.30, OUT / "icon-maskable.png")   # 20% di padding di sicurezza
icon(180, 0.44, OUT / "apple-touch-icon.png")
