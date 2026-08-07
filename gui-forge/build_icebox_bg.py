#!/usr/bin/env python3
"""아이스박스 배경 조립 — 전용 판 1장을 글리프 12타일로 굽는다.

## 0행은 그림이다
최종 아트에서 **머리줄을 없애고 5행 45칸만** 남겼다(2026-08-08 유저 확정).
그래서 0행(슬롯 0~8)에는 아이템을 올리지 않는다 — 올리면 고드름·성에 장식을 덮는다.
원래 0행에 있던 것들의 새 자리는 IceboxGui 주석 참고.

## 보관칸 소켓은 굽지 않는다
45칸 소켓은 **아트에 이미 그려져 있다**. 여기서는 플레이어 인벤 격자만 더한다.

입력:  src/icebox/bg_source.png  704x888 불투명
산출:  <RP>/assets/barkan/textures/gui/icebox_r{0..3}c{0..2}.png (12타일)
       gui.json provider 병합(멱등) + _glyph.txt, _preview_full.png
"""
import json
import os

from PIL import Image

import build_common6_bg as c6

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "src", "icebox")
PREFIX = "icebox_"
CODE0 = 0xE6A0          # E670 메뉴 · E680 내정보 · E690 상점 다음 자리


def main():
    im = Image.open(os.path.join(SRC, "bg_source.png")).convert("RGBA")
    assert im.size == (c6.W, c6.H), f"배경판 크기 {im.size} != {(c6.W, c6.H)}"
    c6.draw_inventory(im)

    os.makedirs(c6.OUTDIR, exist_ok=True)
    for f in os.listdir(c6.OUTDIR):
        if f.startswith(PREFIX):
            os.remove(os.path.join(c6.OUTDIR, f))
    provs, glyph = [], []
    for i, (tile, box, gw, gh, gx, gy) in enumerate(c6.tiles()):
        crop = im.crop(box)
        assert max(crop.size) <= 256, f"{tile} {crop.size} — 아틀라스 256px 초과"
        crop.save(os.path.join(c6.OUTDIR, f"{PREFIX}{tile}.png"))
        ch = chr(CODE0 + i)
        provs.append({"type": "bitmap", "file": f"barkan:gui/{PREFIX}{tile}.png",
                      "ascent": 13 - gy, "height": gh, "chars": [ch]})
        glyph.append("\\uf801" if i == 0 else ("\\uf803" if gx == 0 else "\\uf802"))
        glyph.append(f"\\u{ord(ch):04x}")

    d = json.load(open(c6.FONT_JSON, encoding="utf-8"))
    kept = [p for p in d["providers"] if PREFIX not in str(p.get("file", ""))]
    d["providers"] = kept + provs
    json.dump(d, open(c6.FONT_JSON, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    open(os.path.join(SRC, "_glyph.txt"), "w", encoding="utf-8").write("".join(glyph))
    im.save(os.path.join(SRC, "_preview_full.png"))
    print(f"  타일 {len(provs)}개 (U+{CODE0:04X}~U+{CODE0 + len(provs) - 1:04X}) "
          f"· gui.json 기존 {len(kept)}개 보존 → {c6.OUTDIR}")


if __name__ == "__main__":
    main()
