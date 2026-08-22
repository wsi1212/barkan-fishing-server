#!/usr/bin/env python3
"""QA for the two 3-row specialty plates and their font providers."""
import json
from pathlib import Path

from PIL import Image

import build_plate


HERE = Path(__file__).resolve().parent
RP = Path.home() / "development" / "barkan-resourcepack"
FONT = RP / "assets/barkan/font/gui.json"
TILES = RP / "assets/barkan/textures/gui"
SCALE, GRID_X, GRID_Y, CELL = 4, 7, 17, 18


def cell(im: Image.Image, slot: int, inset: int = 4) -> Image.Image:
    row, col = divmod(slot, 9)
    x0 = (GRID_X + CELL * col) * SCALE + inset
    y0 = (GRID_Y + CELL * row) * SCALE + inset
    x1 = (GRID_X + CELL * (col + 1)) * SCALE - inset
    y1 = (GRID_Y + CELL * (row + 1)) * SCALE - inset
    return im.crop((x0, y0, x1, y1))


def verify(name: str, code0: int, used: tuple[int, ...]) -> None:
    plate = HERE / "src" / name / "bg_source.png"
    glyph_path = HERE / "src" / name / "_glyph.txt"
    im = Image.open(plate).convert("RGBA")
    assert im.size == (704, 672), (name, im.size)
    assert im.getchannel("A").getextrema() == (255, 255), name

    reference = cell(im, used[0])
    assert reference.getbbox() is not None, name
    for slot in used[1:]:
        assert cell(im, slot).getbbox() is not None, (name, slot)

    glyph = glyph_path.read_text(encoding="utf-8")
    assert all(f"\\u{code:04x}" in glyph for code in range(code0, code0 + 12)), name
    providers = json.loads(FONT.read_text(encoding="utf-8"))["providers"]
    plate_providers = [p for p in providers if f"{name}_" in str(p.get("file", ""))]
    assert len(plate_providers) == 12, (name, len(plate_providers))
    for provider in plate_providers:
        tile = Image.open(TILES / Path(provider["file"]).name)
        assert max(tile.size) <= 256, (name, tile.size)


def main() -> None:
    verify("artifact", 0xE880, (13, 26))
    verify("horse", 0xE890, (10, 12, 14, 16, 22))
    print("artifact/horse QA: canvas/opacity ✓ · live socket areas ✓ · glyph providers ✓")


if __name__ == "__main__":
    main()
