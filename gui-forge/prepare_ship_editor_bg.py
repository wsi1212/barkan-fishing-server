#!/usr/bin/env python3
"""Fit the ImageGen shipwright blueprint to the 3-row ship block editor."""
from pathlib import Path

from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
RAW = HERE / "src" / "ship_editor_bg_imagegen.png"
OUT = HERE / "src" / "ship_editor" / "bg_source.png"
W, H = 704, 672
SLOT = 72


def socket(draw: ImageDraw.ImageDraw, x: int, y: int, accent) -> None:
    box = (x + 4, y + 4, x + SLOT - 5, y + SLOT - 5)
    draw.rounded_rectangle(box, radius=8, fill=(29, 35, 37, 255), outline=(*accent, 255), width=3)
    draw.rounded_rectangle((box[0] + 4, box[1] + 4, box[2] - 4, box[3] - 4),
                           radius=5, outline=(105, 120, 117, 255), width=2)


def main() -> None:
    if not RAW.exists():
        raise SystemExit(f"원화가 없습니다: {RAW}")
    raw = Image.open(RAW).convert("RGBA")

    # Keep the blueprint board visible only in the top GUI area. The lower half
    # is the player's inventory and is drawn by build_plate.py.
    top = raw.resize((W, 336), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (W, H), (17, 23, 24, 255))
    canvas.paste(top, (0, 0))
    draw = ImageDraw.Draw(canvas)

    # Exact sockets from ShipEditor.java: info 4, collision 9, animation 11-14,
    # and scale presets 18-21.
    socket(draw, 28 + SLOT * 4, 68, (202, 163, 72))
    socket(draw, 28 + SLOT * 0, 140, (185, 74, 67))
    for col, accent in enumerate(((184, 199, 207), (194, 199, 205), (177, 143, 76), (186, 79, 69)), start=1):
        socket(draw, 28 + SLOT * col, 140, accent)
    for col in range(4):
        socket(draw, 28 + SLOT * col, 212, (86, 151, 160))

    # Make the boundary to the shared player inventory explicit. The common
    # builder then adds the exact vanilla inventory grid on this surface.
    draw.rectangle((24, 332, 680, 671), fill=(15, 21, 22, 255))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    canvas.convert("RGB").save(OUT)
    print(f"배 블록 편집기 전용 판 → {OUT} (원화 {raw.size} → {W}x{H})")


if __name__ == "__main__":
    main()
