#!/usr/bin/env python3
"""Deterministic QA for the /수리 plate and its generated font tiles."""
import json
from pathlib import Path

from PIL import Image

import build_plate


HERE = Path(__file__).resolve().parent
PLATE = HERE / "src" / "repair" / "bg_source.png"
BASE = HERE / "src" / "workbench" / "bg_source.png"
GLYPH = HERE / "src" / "repair" / "_glyph.txt"
RP = Path.home() / "development" / "barkan-resourcepack"
FONT = RP / "assets" / "barkan" / "font" / "gui.json"
TILES = RP / "assets" / "barkan" / "textures" / "gui"

SCALE, GRID_X, GRID_Y, CELL = 4, 7, 17, 18
USED = (11, 12, 13, 14, 15, 22)


def cell(im: Image.Image, slot: int, inset: int = 0) -> Image.Image:
    row, col = divmod(slot, 9)
    x0 = (GRID_X + CELL * col) * SCALE + inset
    y0 = (GRID_Y + CELL * row) * SCALE + inset
    x1 = (GRID_X + CELL * (col + 1)) * SCALE - inset
    y1 = (GRID_Y + CELL * (row + 1)) * SCALE - inset
    return im.crop((x0, y0, x1, y1))


def main() -> None:
    im = Image.open(PLATE).convert("RGBA")
    base = Image.open(BASE).convert("RGBA")
    assert im.size == (704, 672), im.size
    assert im.getchannel("A").getextrema() == (255, 255)

    # The centered five-slot trap band must retain identical 64px live interiors.
    # This avoids trusting a textured-edge detector; the build script stamps one
    # tested socket cell into all five positions before applying the shared pass.
    reference = cell(im, 13, 4)
    for slot in (11, 12, 14, 15):
        assert cell(im, slot, 4).tobytes() == reference.tobytes(), slot

    glyph = GLYPH.read_text(encoding="utf-8")
    # Keep the assertion readable while still requiring all 12 tile codepoints.
    assert glyph.count("\\ue8") == 12
    assert all(f"\\u{code:04x}" in glyph for code in range(0xE870, 0xE87C))

    providers = json.loads(FONT.read_text(encoding="utf-8"))["providers"]
    repair = [p for p in providers if "repair_" in str(p.get("file", ""))]
    assert len(repair) == 12, len(repair)
    for p in repair:
        path = TILES / Path(p["file"]).name
        tile = Image.open(path)
        assert max(tile.size) <= 256, (path, tile.size)

    print("repair QA: canvas/opacity ✓ · stamped socket interiors ✓ · glyph providers ✓")


if __name__ == "__main__":
    main()
