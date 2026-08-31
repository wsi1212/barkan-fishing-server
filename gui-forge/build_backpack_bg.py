#!/usr/bin/env python3
"""배낭 전용 GUI 배경 조립.

입력: src/backpack/bg_source.png (704x888, 불투명)
산출: ~/development/barkan-resourcepack/assets/barkan/textures/gui/backpack_r*.png
      gui.json provider 병합, src/backpack/_glyph.txt, _preview_full.png

배낭의 보관칸은 배경판에 이미 그려져 있고, 공용 6행 규칙에 따라
플레이어 인벤토리 격자만 이 단계에서 합성한다.
"""
import json
import os

from PIL import Image

import build_common6_bg as c6

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "src", "backpack")
PREFIX = "backpack_"
# E8A0~E8AB 는 상점 전용 판(cashshop)이 사용한다. 배낭은 별도 범위로 유지한다.
CODE0 = 0xE8B0


def main():
    im = Image.open(os.path.join(SRC, "bg_source.png")).convert("RGBA")
    assert im.size == (c6.W, c6.H), f"배경판 크기 {im.size} != {(c6.W, c6.H)}"
    c6.draw_inventory(im)

    os.makedirs(c6.OUTDIR, exist_ok=True)
    for filename in os.listdir(c6.OUTDIR):
        if filename.startswith(PREFIX):
            os.remove(os.path.join(c6.OUTDIR, filename))

    providers, glyph = [], []
    for i, (tile, box, gw, gh, gx, gy) in enumerate(c6.tiles()):
        crop = im.crop(box)
        assert max(crop.size) <= 256, f"{tile} {crop.size} — 아틀라스 256px 초과"
        crop.save(os.path.join(c6.OUTDIR, f"{PREFIX}{tile}.png"))
        char = chr(CODE0 + i)
        providers.append({
            "type": "bitmap",
            "file": f"barkan:gui/{PREFIX}{tile}.png",
            "ascent": 13 - gy,
            "height": gh,
            "chars": [char],
        })
        glyph.append("\\uf801" if i == 0 else ("\\uf803" if gx == 0 else "\\uf802"))
        glyph.append(f"\\u{ord(char):04x}")

    with open(c6.FONT_JSON, encoding="utf-8") as handle:
        font = json.load(handle)
    kept = [p for p in font["providers"] if PREFIX not in str(p.get("file", ""))]
    font["providers"] = kept + providers
    with open(c6.FONT_JSON, "w", encoding="utf-8") as handle:
        json.dump(font, handle, ensure_ascii=False, indent=2)

    with open(os.path.join(SRC, "_glyph.txt"), "w", encoding="utf-8") as handle:
        handle.write("".join(glyph))
    im.save(os.path.join(SRC, "_preview_full.png"))
    print(f"  타일 {len(providers)}개 (U+{CODE0:04X}~U+{CODE0 + len(providers) - 1:04X})")
    print(f"  gui.json 기존 {len(kept)}개 보존 → {c6.OUTDIR}")


if __name__ == "__main__":
    main()
