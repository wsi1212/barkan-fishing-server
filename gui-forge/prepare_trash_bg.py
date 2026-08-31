#!/usr/bin/env python3
"""Fit the ImageGen refuse/recycling station to the trash-bin GUI."""
from pathlib import Path

from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
RAW = HERE / "src" / "trash_bg_imagegen.png"
OUT = HERE / "src" / "trash" / "bg_source.png"
W, H = 704, 888
SLOT = 72


def cell(draw: ImageDraw.ImageDraw, x: int, y: int) -> None:
    box = (x + 3, y + 3, x + SLOT - 4, y + SLOT - 4)
    draw.rounded_rectangle(box, radius=7, fill=(17, 18, 18, 255), outline=(91, 92, 88, 255), width=3)
    draw.rounded_rectangle((box[0] + 4, box[1] + 4, box[2] - 4, box[3] - 4),
                           radius=4, outline=(49, 50, 48, 255), width=2)


def button(draw: ImageDraw.ImageDraw, x: int, y: int, accent) -> None:
    draw.rounded_rectangle((x + 4, y + 6, x + SLOT - 5, y + SLOT - 6),
                           radius=9, fill=(37, 29, 22, 255), outline=(*accent, 255), width=3)


def main() -> None:
    if not RAW.exists():
        raise SystemExit(f"원화가 없습니다: {RAW}")
    raw = Image.open(RAW).convert("RGBA")
    out = Image.new("RGBA", (W, H), (18, 17, 16, 255))
    bands = [
        ((0, 150), (0, 68)),
        ((150, 800), (68, 428)),
        ((800, 1110), (428, 552)),
    ]
    for (y0, y1), (t0, t1) in bands:
        crop = raw.crop((0, y0, raw.width, y1))
        out.paste(crop.resize((W, t1 - t0), Image.Resampling.LANCZOS), (0, t0))
    draw = ImageDraw.Draw(out)

    # The top 45 slots are real drop-in slots, so the art only provides their
    # visual cells; Java leaves the actual inventory slots empty.
    for row in range(5):
        for col in range(9):
            cell(draw, 28 + SLOT * col, 68 + SLOT * row)
    button(draw, 244, 428, (184, 137, 46))  # info 48
    button(draw, 316, 428, (216, 93, 39))   # clear 49
    button(draw, 388, 428, (125, 125, 119)) # close 50

    draw.rectangle((24, 548, 680, 887), fill=(14, 15, 15, 255))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    out.convert("RGB").save(OUT)
    print(f"쓰레기통 전용 판 → {OUT} (원화 {raw.size} → {W}x{H})")


if __name__ == "__main__":
    main()
