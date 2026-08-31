#!/usr/bin/env python3
"""Fit and align the ImageGen enchanting workstation plate."""
from pathlib import Path

from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
RAW = HERE / "src" / "enchant_bg_imagegen.png"
OUT = HERE / "src" / "enchant" / "bg_source.png"
W, H = 704, 672
SLOT = 72


def socket(draw: ImageDraw.ImageDraw, x: int, y: int, result: bool = False) -> None:
    box = (x + 4, y + 4, x + SLOT - 5, y + SLOT - 5)
    draw.rounded_rectangle(box, radius=10, fill=(10, 8, 18, 255), outline=(91, 76, 106, 255), width=4)
    draw.rounded_rectangle(
        (box[0] + 4, box[1] + 4, box[2] - 4, box[3] - 4),
        radius=7,
        outline=(166, 91, 211, 255) if result else (110, 94, 130, 255),
        width=2,
    )


def main() -> None:
    if not RAW.exists():
        raise SystemExit(f"원화가 없습니다: {RAW}")
    raw = Image.open(RAW).convert("RGBA")
    im = raw.resize((W, H), Image.Resampling.LANCZOS)
    draw = ImageDraw.Draw(im)

    # The generated sockets are close but not on Minecraft's 11/13/15 slots.
    # Replace that center strip with exact, evenly aligned recesses.
    draw.rectangle((128, 128, 576, 336), fill=(20, 13, 29, 255), outline=(75, 57, 92, 255), width=3)
    draw.line((148, 206, 556, 206), fill=(75, 44, 105, 255), width=2)
    socket(draw, 172, 140)
    socket(draw, 316, 140, result=True)
    socket(draw, 460, 140)

    # Player inventory grid is shared and deterministic in build_plate.py.
    draw.rectangle((24, 332, 680, 671), fill=(12, 12, 18, 255))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    im.convert("RGB").save(OUT)
    print(f"인첸트 전용 판 → {OUT} (원화 {raw.size} → {W}x{H})")


if __name__ == "__main__":
    main()
