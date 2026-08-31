#!/usr/bin/env python3
"""Fit and align the ImageGen backpack-shop art to the 27-slot GUI plate.

BackpackGui.openShop uses the bottom top-inventory row (slots 18..26) for the
nine upgrade tiers.  The lower player inventory grid is intentionally left to
build_plate.py so it cannot drift from every other 3-row screen.
"""
from pathlib import Path

from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
RAW = HERE / "src" / "backpack_shop_bg_imagegen.png"
OUT = HERE / "src" / "backpack_shop" / "bg_source.png"
W, H = 704, 672
SLOT = 72
X0 = 28


def socket(draw: ImageDraw.ImageDraw, x: int, y: int) -> None:
    box = (x + 4, y + 4, x + SLOT - 5, y + SLOT - 5)
    draw.rounded_rectangle(box, radius=9, fill=(28, 18, 13, 255), outline=(115, 69, 27, 255), width=4)
    draw.rounded_rectangle(
        (box[0] + 4, box[1] + 4, box[2] - 4, box[3] - 4),
        radius=6,
        outline=(174, 111, 39, 255),
        width=2,
    )


def main() -> None:
    if not RAW.exists():
        raise SystemExit(f"원화가 없습니다: {RAW}")
    raw = Image.open(RAW).convert("RGBA")
    # The generated image is almost the same aspect ratio as the 704x672
    # plate, so preserve its full composition with a small deterministic fit.
    im = raw.resize((W, H), Image.Resampling.LANCZOS)

    draw = ImageDraw.Draw(im)
    # Remove the generator's approximate bottom sockets and the lower grid;
    # build_plate.py owns the player inventory grid and the code owns sockets.
    draw.rectangle((24, 198, 680, 286), fill=(53, 31, 19, 255))
    draw.line((28, 202, 676, 202), fill=(184, 117, 43, 255), width=3)
    draw.line((28, 284, 676, 284), fill=(23, 14, 10, 255), width=4)
    for col in range(9):
        socket(draw, X0 + SLOT * col, 212)
    draw.rectangle((24, 332, 680, 671), fill=(22, 17, 14, 255))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    im.convert("RGB").save(OUT)
    print(f"배낭 상점 전용 판 → {OUT} (원화 {raw.size} → {W}x{H})")


if __name__ == "__main__":
    main()
