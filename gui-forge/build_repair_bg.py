#!/usr/bin/env python3
"""Build the /수리 3-row plate from the established workbench material language.

The source workbench plate already has the correct 704x672 canvas, title band,
blacksmith lighting, and player-inventory region. This script keeps that tested
foundation, adds one info socket in row one, a centered five-slot item band in
row two, and the centered repair button. The result is still an opaque 4x GUI
plate.
"""
from pathlib import Path

from PIL import Image


HERE = Path(__file__).resolve().parent
SRC = HERE / "src"
OUT = SRC / "repair" / "bg_source.png"
BASE = SRC / "workbench" / "bg_source.png"
ENHANCE = SRC / "enhance" / "bg_source.png"

SCALE = 4
GRID_X, GRID_Y, CELL = 7, 17, 18
PITCH = CELL * SCALE
PLATE = (704, 672)


def cell_box(slot: int) -> tuple[int, int, int, int]:
    row, col = divmod(slot, 9)
    x0 = (GRID_X + CELL * col) * SCALE
    y0 = (GRID_Y + CELL * row) * SCALE
    return x0, y0, x0 + PITCH, y0 + PITCH


def copy_cell(src: Image.Image, slot: int) -> Image.Image:
    x0, y0, x1, y1 = cell_box(slot)
    return src.crop((x0, y0, x1, y1)).copy()


def paste_cell(dst: Image.Image, src: Image.Image, slot: int) -> None:
    x0, y0, _, _ = cell_box(slot)
    dst.alpha_composite(src, (x0, y0))


def draw_batch_button(im: Image.Image, button: Image.Image) -> None:
    """Use the tested enhancement action socket at slot 22."""
    # A restrained warm button is the only high-contrast action affordance.
    paste_cell(im, button, 22)


def main() -> None:
    base = Image.open(BASE).convert("RGBA")
    if base.size != PLATE:
        raise SystemExit(f"base size {base.size} != {PLATE}")
    im = base.copy()
    im.putalpha(255)

    # Keep the original workbench art intact. The source already has the
    # centered five-slot band; re-stamp only those exact sockets.
    socket = copy_cell(base, 11)
    for slot in range(11, 16):
        paste_cell(im, socket, slot)

    # Slot 5 (raw slot 4) no longer carries an item. Replace its old empty
    # socket with a matching wall patch so the top band remains clean.
    paste_cell(im, copy_cell(base, 3), 4)

    # Slot 22 uses the existing, high-contrast action recess from the enhancement plate.
    enhance = Image.open(ENHANCE).convert("RGBA")
    action = copy_cell(enhance, 40)
    draw_batch_button(im, action)

    im.putalpha(255)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    im.save(OUT)
    print(f"repair plate -> {OUT} ({im.size[0]}x{im.size[1]}, opaque)")


if __name__ == "__main__":
    main()
