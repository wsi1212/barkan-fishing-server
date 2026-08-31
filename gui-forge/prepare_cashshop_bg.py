#!/usr/bin/env python3
"""Prepare the dedicated 54-slot storefront plate.

The generated source supplies the frame, leather panels, teal inlay and brass
ornament.  Slot recesses are redrawn here from the real Bukkit slot geometry;
the generator's approximate repeated buttons must not be used as hitbox art.
The 54-slot plate is shared by cash/recommend/scroll and the other read-only
shop pages, so only the common product and header sockets are baked in.
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
SRC = HERE / "src" / "cashshop"
RAW = SRC / "bg_raw.png"
OUT = SRC / "bg_source.png"

W, H = 704, 888
SLOT = 72  # 18 GUI px × 4 art scale
X0 = 28    # (GUI slot x=7) × 4
TOP_Y = 68  # (GUI slot y=17) × 4
PRODUCT_Y = 140  # row 1: (GUI y=35) × 4


def remap_vertical(raw: Image.Image) -> Image.Image:
    """Compress the generated header and product panel into the 54-slot plate."""
    raw = raw.convert("RGBA").resize((W, raw.height), Image.Resampling.LANCZOS)
    # The source was generated at 1122×1402.  Keep the visual bands intact while
    # putting the product panel and player inventory at the exact GUI y ranges.
    bands = [
        ((0, 280), (0, 112)),       # title/header
        ((280, 330), (112, 140)),   # header divider / tab rail
        ((330, 1030), (140, 500)),  # four rows of shop products
        ((1030, 1100), (500, 552)), # separator above player inventory
        ((1100, 1402), (552, 888)), # player inventory panel
    ]
    out = Image.new("RGBA", (W, H), (22, 27, 30, 255))
    for (y0, y1), (t0, t1) in bands:
        crop = raw.crop((0, y0, W, y1))
        out.paste(crop.resize((W, t1 - t0), Image.Resampling.LANCZOS), (0, t0))
    return out


def slot(draw: ImageDraw.ImageDraw, x: int, y: int, product: bool = False) -> None:
    """Draw one exact 72×72 art-pixel socket."""
    inset = 4
    box = (x + inset, y + inset, x + SLOT - inset - 1, y + SLOT - inset - 1)
    fill = (13, 18, 21, 235) if product else (11, 28, 34, 245)
    draw.rounded_rectangle(box, radius=11, fill=fill, outline=(119, 84, 39, 255), width=4)
    draw.rounded_rectangle(
        (box[0] + 3, box[1] + 3, box[2] - 3, box[3] - 3),
        radius=8,
        outline=(211, 158, 67, 255),
        width=2,
    )


def redraw_sockets(im: Image.Image) -> None:
    draw = ImageDraw.Draw(im)

    # Hide the generator's approximate seven-tab row before placing the exact
    # nine Minecraft slots (balance + seven tabs + the reserved blank slot).
    draw.rectangle((24, 58, 680, 144), fill=(47, 38, 29, 255))
    draw.line((28, 62, 676, 62), fill=(104, 76, 39, 255), width=3)
    draw.line((28, 143, 676, 143), fill=(20, 24, 26, 255), width=3)
    for col in range(9):
        slot(draw, X0 + SLOT * col, TOP_Y, product=False)

    # CashShopGui, ScrollShopGui and the other 54-slot shop pages use rows 1–4
    # for products.  Their item icons sit inside these exact recesses.
    for row in range(4):
        for col in range(9):
            slot(draw, X0 + SLOT * col, PRODUCT_Y + SLOT * row, product=True)


def main() -> None:
    if not RAW.exists():
        raise SystemExit(f"원화가 없습니다: {RAW}")
    im = remap_vertical(Image.open(RAW))
    redraw_sockets(im)
    im.convert("RGB").save(OUT)
    print(f"상점 전용 판 → {OUT} (원화 {Image.open(RAW).size} → {W}x{H})")


if __name__ == "__main__":
    main()
