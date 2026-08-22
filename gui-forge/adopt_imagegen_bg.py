#!/usr/bin/env python3
"""Adopt imagegen scenes without surrendering the GUI coordinate contract.

Imagegen is allowed to repaint the upper room, while the original tested
frame, sockets, title band, and player inventory remain authoritative.
"""
from pathlib import Path

from PIL import Image


HERE = Path(__file__).resolve().parent
SRC = HERE / "src"
BASE = SRC / "workbench" / "bg_source.png"
ENHANCE = SRC / "enhance" / "bg_source.png"
SIZE = (704, 672)
SCALE, GRID_X, GRID_Y, CELL = 4, 7, 17, 18
SCENE_BOX = (GRID_X * SCALE, (GRID_Y + 0 * CELL) * SCALE,
             (GRID_X + CELL * 9) * SCALE, (GRID_Y + 64) * SCALE)


def cell_box(slot: int) -> tuple[int, int, int, int]:
    row, col = divmod(slot, 9)
    x0 = (GRID_X + CELL * col) * SCALE
    y0 = (GRID_Y + CELL * row) * SCALE
    return x0, y0, x0 + CELL * SCALE, y0 + CELL * SCALE


def copy_cell(src: Image.Image, slot: int) -> Image.Image:
    return src.crop(cell_box(slot)).copy()


def paste_cell(dst: Image.Image, src: Image.Image, slot: int) -> None:
    x0, y0, _, _ = cell_box(slot)
    dst.alpha_composite(src, (x0, y0))


def adopt(name: str, live_slots: tuple[int, ...]) -> None:
    base = Image.open(BASE).convert("RGBA")
    generated_path = SRC / name / "bg_imagegen.png"
    generated = Image.open(generated_path).convert("RGBA").resize(SIZE, Image.Resampling.LANCZOS)
    out = base.copy()

    # Only the upper GUI room is imagegen-owned. The lower inventory and all
    # outer chrome stay from the tested source plate.
    x0, y0, x1, y1 = SCENE_BOX
    out.alpha_composite(generated.crop((x0, y0, x1, y1)), (x0, y0))

    socket = copy_cell(base, 11)
    if name == "artifact":
        paste_cell(out, socket, 13)
        paste_cell(out, copy_cell(Image.open(ENHANCE).convert("RGBA"), 40), 26)
    else:
        # The generated stable occasionally invents a second row of four
        # sockets. Those are not Java slots; replace only those cells with
        # neighboring generated wood panels before restoring the live sockets.
        for target, source in ((19, 20), (21, 20), (23, 24), (25, 24)):
            paste_cell(out, copy_cell(generated, source), target)
        # Clear the generator's short continuation below the optional summon
        # recess; it is scene floor, not another inventory slot.
        out.alpha_composite(generated.crop((388, 284, 460, 324)), (316, 284))
        # Raw slot 4 (screen slot 5) is intentionally empty. Replace the
        # imagegen/base socket with a neighboring stable panel so the removed
        # slot becomes continuous woodwork instead of a dead black recess.
        paste_cell(out, copy_cell(generated, 3), 4)
        for slot in live_slots:
            paste_cell(out, socket, slot)
        paste_cell(out, copy_cell(Image.open(ENHANCE).convert("RGBA"), 40), 22)

    out.putalpha(255)
    output = SRC / name / "bg_source.png"
    out.save(output)
    print(f"{name}: adopted imagegen scene → {output} ({out.size[0]}x{out.size[1]}, opaque)")


if __name__ == "__main__":
    adopt("artifact", (13, 26))
    adopt("horse", (10, 12, 14, 16))
