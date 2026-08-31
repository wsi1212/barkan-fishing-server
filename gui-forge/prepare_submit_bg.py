#!/usr/bin/env python3
"""Fit the ImageGen island/guild contribution board to a 54-slot GUI."""
from pathlib import Path

from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
RAW = HERE / "src" / "submit_bg_imagegen.png"
OUT = HERE / "src" / "submit" / "bg_source.png"
W, H = 704, 888
SLOT = 72
X0 = 28


def cell(draw: ImageDraw.ImageDraw, x: int, y: int) -> None:
    box = (x + 3, y + 3, x + SLOT - 4, y + SLOT - 4)
    draw.rounded_rectangle(box, radius=7, fill=(92, 69, 38, 255), outline=(224, 176, 91, 255), width=3)
    draw.rounded_rectangle((box[0] + 4, box[1] + 4, box[2] - 4, box[3] - 4),
                           radius=4, fill=(64, 49, 32, 255), outline=(159, 116, 58, 255), width=2)


def button(draw: ImageDraw.ImageDraw, x: int, y: int, accent) -> None:
    box = (x + 4, y + 6, x + SLOT - 5, y + SLOT - 6)
    draw.rounded_rectangle(box, radius=9, fill=(55, 43, 27, 255), outline=(*accent, 255), width=3)


def main() -> None:
    if not RAW.exists():
        raise SystemExit(f"원화가 없습니다: {RAW}")
    raw = Image.open(RAW).convert("RGBA")
    out = Image.new("RGBA", (W, H), (31, 23, 14, 255))
    # Preserve the generated header, catalog, and control-strip composition,
    # but map them to the exact 6-row GUI bands.
    bands = [
        ((0, 190), (0, 68)),
        ((190, 930), (68, 428)),
        ((930, 1130), (428, 552)),
    ]
    for (y0, y1), (t0, t1) in bands:
        crop = raw.crop((0, y0, raw.width, y1))
        out.paste(crop.resize((W, t1 - t0), Image.Resampling.LANCZOS), (0, t0))
    draw = ImageDraw.Draw(out)

    # Replace the generator's near-grid with exact 9x6 item cells.
    draw.rectangle((24, 64, 680, 500), fill=(105, 78, 43, 255))
    for row in range(6):
        for col in range(9):
            cell(draw, X0 + SLOT * col, 68 + SLOT * row)

    # Submission controls: fish-all 45, ranking 48, status 49, close 53.
    button(draw, 28, 428, (48, 139, 122))
    button(draw, 244, 428, (198, 149, 56))
    button(draw, 316, 428, (66, 137, 126))
    button(draw, 604, 428, (176, 76, 63))

    # Player inventory grid begins at art y=552 for a 6-row top GUI.
    draw.rectangle((24, 548, 680, 887), fill=(28, 22, 15, 255))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    out.convert("RGB").save(OUT)
    print(f"제출소 전용 판 → {OUT} (원화 {raw.size} → {W}x{H})")


if __name__ == "__main__":
    main()
