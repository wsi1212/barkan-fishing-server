#!/usr/bin/env python3
"""Fit the generated harbor art to the 27-slot boat-rental plate.

BoatRentalGui uses four tier slots (10, 12, 14, 16) and a centered summon
slot (22).  The generator's approximate sockets are hidden and redrawn at
those exact Minecraft coordinates.  The lower player-inventory grid is left
to build_plate.py, which is the single authority for that shared geometry.
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
SRC = HERE / "src" / "boat"
RAW = SRC / "bg_imagegen.png"
OUT = SRC / "bg_source.png"
W, H = 704, 672
SLOT = 72
X0 = 28


def fit(raw: Image.Image) -> Image.Image:
    raw = raw.convert("RGBA").resize((W, raw.height), Image.Resampling.LANCZOS)
    # Keep the generated harbor/header composition above the player inventory
    # and preserve the lower frame separately.  The lower generated slots are
    # covered before build_plate.py adds the deterministic inventory grid.
    bands = [
        ((0, 180), (0, 68)),
        ((180, 850), (68, 336)),
        ((850, 1226), (336, 672)),
    ]
    out = Image.new("RGBA", (W, H), (12, 17, 21, 255))
    for (y0, y1), (t0, t1) in bands:
        crop = raw.crop((0, y0, W, y1))
        out.paste(crop.resize((W, t1 - t0), Image.Resampling.LANCZOS), (0, t0))
    return out


def socket(draw: ImageDraw.ImageDraw, x: int, y: int, center: bool = False) -> None:
    box = (x + 4, y + 4, x + SLOT - 5, y + SLOT - 5)
    draw.rounded_rectangle(box, radius=10, fill=(14, 20, 24, 255), outline=(93, 67, 37, 255), width=4)
    draw.rounded_rectangle(
        (box[0] + 4, box[1] + 4, box[2] - 4, box[3] - 4),
        radius=7,
        outline=(179, 126, 51, 255) if center else (116, 91, 53, 255),
        width=2,
    )


def redraw(im: Image.Image) -> None:
    draw = ImageDraw.Draw(im)

    # Remove the generated lower inventory sockets from the fitted art.  The
    # exact shared player inventory is drawn later by build_plate.py.
    draw.rectangle((24, 332, 680, 671), fill=(14, 20, 24, 255))

    # Hide approximate generated display sockets, then install exact slots:
    # raw 10/12/14/16 => row 1 (y=140), raw 22 => row 2 (y=212).
    # A deliberate dark display rack hides the generator's approximate boxes
    # without leaving a flat gray strip across the harbor scene.
    panel = (88, 132, 616, 284)
    draw.rectangle(panel, fill=(27, 22, 18, 255), outline=(105, 72, 34, 255), width=4)
    draw.line((92, 136, 612, 136), fill=(175, 119, 48, 255), width=2)
    draw.line((92, 280, 612, 280), fill=(12, 15, 18, 255), width=3)
    draw.line((92, 208, 612, 208), fill=(56, 39, 25, 255), width=2)
    for col in (1, 3, 5, 7):
        socket(draw, X0 + SLOT * col, 140)
    socket(draw, X0 + SLOT * 4, 212, center=True)


def main() -> None:
    if not RAW.exists():
        raise SystemExit(f"원화가 없습니다: {RAW}")
    raw = Image.open(RAW)
    if raw.size != (1283, 1226):
        raise SystemExit(f"배 대여 원화 크기 {raw.size} != (1283, 1226)")
    im = fit(raw)
    redraw(im)
    im.convert("RGB").save(OUT)
    print(f"배 대여 전용 판 → {OUT} (원화 {raw.size} → {W}x{H})")


if __name__ == "__main__":
    main()
