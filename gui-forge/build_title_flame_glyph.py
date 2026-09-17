#!/usr/bin/env python3
"""Build the animated premium-fire title glyph for the default Minecraft font.

The glyph is intentionally registered in ``minecraft:default``: TextDisplay title
components use that font, while barkan:gui is only used by inventory menus.
"""
from __future__ import annotations

import json
from pathlib import Path

from PIL import Image

GLYPH = "\ue3f0"
PROVIDER_FILE = "barkan:font/title_flame.png"
PROVIDER = {
    "type": "bitmap",
    "file": PROVIDER_FILE,
    "ascent": 8,
    "height": 10,
    "chars": [GLYPH],
}
PACKS = (
    Path("/Users/user/development/barkan-resourcepack"),
    Path("/Users/user/Downloads/barkan-resourcepack"),
)

# Top-left light: cream core → gold → orange → ember-red silhouette.
PIXELS = {
    "D": (78, 12, 8, 255), "R": (164, 31, 12, 255),
    "O": (234, 76, 15, 255), "G": (255, 151, 24, 255),
    "Y": (255, 207, 72, 255), "L": (255, 244, 181, 255),
}
ROWS = (
    "..........",
    "....D.....",
    "...DRO....",
    "...ROO....",
    "..ROGO....",
    "..ROYYO...",
    ".ROOYYO...",
    ".ROYYOO...",
    ".ROYYOOD..",
    "..OYYOOD..",
    "..OOOOO...",
    "...OOO....",
)


def flame() -> Image.Image:
    image = Image.new("RGBA", (10, 12), (0, 0, 0, 0))
    for y, row in enumerate(ROWS):
        for x, token in enumerate(row):
            if token != ".":
                image.putpixel((x, y), PIXELS[token])
    return image


def install(pack: Path, image: Image.Image) -> None:
    font = pack / "assets/minecraft/font/default.json"
    texture = pack / "assets/barkan/textures/font/title_flame.png"
    if not font.is_file():
        raise SystemExit(f"기본 폰트가 없습니다: {font}")
    texture.parent.mkdir(parents=True, exist_ok=True)
    image.save(texture)

    data = json.loads(font.read_text(encoding="utf-8"))
    providers = data.get("providers", [])
    providers = [p for p in providers if p.get("file") != PROVIDER_FILE]
    # A bitmap provider must precede the bundled TTF/reference providers so the
    # private-use character cannot fall through to a missing-glyph placeholder.
    data["providers"] = [PROVIDER, *providers]
    font.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    image = flame()
    preview = Path(__file__).with_name("out") / "title_flame_glyph_preview.png"
    preview.parent.mkdir(exist_ok=True)
    image.resize((200, 240), Image.Resampling.NEAREST).save(preview)
    for pack in PACKS:
        install(pack, image)
        print(f"installed U+E3F0 → {pack}")
    print(f"preview → {preview}")


if __name__ == "__main__":
    main()
