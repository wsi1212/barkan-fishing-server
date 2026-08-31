#!/usr/bin/env python3
"""Fit and align the ImageGen recipe confirmation workstation."""
from pathlib import Path

from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
RAW = HERE / "src" / "cooking_confirm_bg_imagegen.png"
OUT = HERE / "src" / "cooking_confirm" / "bg_source.png"
W, H = 704, 672
SLOT = 72


def socket(draw: ImageDraw.ImageDraw, x: int, y: int, accent) -> None:
    box = (x + 4, y + 4, x + SLOT - 5, y + SLOT - 5)
    draw.rounded_rectangle(box, radius=9, fill=(35, 22, 16, 255), outline=(*accent, 255), width=4)
    draw.rounded_rectangle((box[0] + 4, box[1] + 4, box[2] - 4, box[3] - 4),
                           radius=6, outline=(153, 96, 48, 255), width=2)


def main() -> None:
    if not RAW.exists():
        raise SystemExit(f"원화가 없습니다: {RAW}")
    raw = Image.open(RAW).convert("RGBA")
    im = raw.resize((W, 470), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (W, H), (31, 20, 13, 255))
    canvas.paste(im, (0, 0))
    draw = ImageDraw.Draw(canvas)

    # Replace approximate generated recesses with exact slots 11/13/15.
    draw.rectangle((132, 124, 572, 220), fill=(68, 41, 25, 255), outline=(120, 73, 36, 255), width=3)
    socket(draw, 172, 140, (49, 137, 124))
    socket(draw, 316, 140, (210, 148, 55))
    socket(draw, 460, 140, (172, 72, 56))

    # Shared player inventory grid is deterministic in build_plate.py.
    draw.rectangle((24, 332, 680, 671), fill=(22, 16, 12, 255))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    canvas.convert("RGB").save(OUT)
    print(f"요리 확인 전용 판 → {OUT} (원화 {raw.size} → {W}x{H})")


if __name__ == "__main__":
    main()
