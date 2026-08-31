#!/usr/bin/env python3
"""Fit and align the ImageGen two-player trade board to a 45-slot GUI."""
from pathlib import Path

from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
RAW = HERE / "src" / "trade_bg_imagegen.png"
OUT = HERE / "src" / "trade" / "bg_source.png"
W, H = 704, 816
SLOT = 72


def socket(draw: ImageDraw.ImageDraw, x: int, y: int, color=(128, 91, 40)) -> None:
    box = (x + 4, y + 4, x + SLOT - 5, y + SLOT - 5)
    draw.rounded_rectangle(box, radius=8, fill=(18, 16, 14, 255), outline=(*color, 255), width=4)
    draw.rounded_rectangle(
        (box[0] + 4, box[1] + 4, box[2] - 4, box[3] - 4),
        radius=5,
        outline=(88, 124, 116, 255),
        width=2,
    )


def button(draw: ImageDraw.ImageDraw, x: int, y: int, accent) -> None:
    box = (x + 5, y + 7, x + SLOT - 6, y + 65)
    draw.rounded_rectangle(box, radius=8, fill=(21, 19, 16, 255), outline=(*accent, 255), width=3)


def main() -> None:
    if not RAW.exists():
        raise SystemExit(f"원화가 없습니다: {RAW}")
    raw = Image.open(RAW).convert("RGBA")
    # The source is a wide working-board illustration.  Fit its full width into
    # the five-row upper GUI; the lower player inventory is rebuilt by the plate
    # builder so it remains identical to every other 5-row screen.
    fitted = raw.resize((W, round(raw.height * W / raw.width)), Image.Resampling.LANCZOS)
    im = Image.new("RGBA", (W, H), (22, 17, 12, 255))
    im.paste(fitted, (0, 0))
    draw = ImageDraw.Draw(im)

    # Hide approximate generated bays and install exact 3x3 MY/OTHER sockets.
    draw.rectangle((88, 128, 316, 356), fill=(25, 20, 15, 255), outline=(93, 69, 35, 255), width=3)
    draw.rectangle((380, 128, 608, 356), fill=(25, 20, 15, 255), outline=(93, 69, 35, 255), width=3)
    for y in (140, 212, 284):
        for x in (100, 172, 244):
            socket(draw, x, y, (64, 137, 118))
        for x in (388, 460, 532):
            socket(draw, x, y, (164, 106, 38))

    # Exact control row: 37/39 for me, 41/43 for the other player.
    for x, accent in ((100, (64, 137, 118)), (244, (64, 137, 118)),
                      (388, (164, 106, 38)), (532, (164, 106, 38))):
        button(draw, x, 356, accent)
    # Cancel slot 31 sits in the middle of the third working row.
    socket(draw, 316, 284, (150, 74, 54))

    # Player inventory starts at GUI y=120 (art y=480) for a 5-row top GUI.
    draw.rectangle((24, 476, 680, 815), fill=(14, 15, 14, 255))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    im.convert("RGB").save(OUT)
    print(f"거래 전용 판 → {OUT} (원화 {raw.size} → {W}x{H})")


if __name__ == "__main__":
    main()
