#!/usr/bin/env python3
"""타일형 전용 배경 3장을 리소스팩 글리프로 굽는다 — 메뉴 · 내 정보 · 상점.

공용 6행 판(build_common6_bg)과 조립 방식은 같다. 다른 건 화면마다 **전용 그림**을
쓴다는 것뿐이라, 타일 분할·인벤 격자·provider 병합은 그쪽 함수를 그대로 빌려 쓴다.
(격자를 여기서 다시 구현하면 좌표가 갈라져 두 판이 미묘하게 어긋난다.)

입력:  src/<이름>/bg_source.png  704x888 불투명 (compose_gui3_imagegen.py 산출)
산출:  <RP>/assets/barkan/textures/gui/<이름>3_r{0..3}c{0..2}.png (각 12타일)
       gui.json provider 병합(멱등) + src/<이름>/_glyph.txt, _preview_full.png
"""
import json
import os

from PIL import Image

import build_common6_bg as c6

HERE = os.path.dirname(os.path.abspath(__file__))

# E620~E643 낚시창 · E650~E658 판매창 · E660~E66B 공용판 · E700~ 제목 글리프
SCREENS = {
    "menu": ("menu3_", 0xE670),
    "myinfo": ("myinfo3_", 0xE680),
    "shop": ("shop3_", 0xE690),
}


def merge_providers(prefix, new):
    d = json.load(open(c6.FONT_JSON, encoding="utf-8"))
    kept = [p for p in d["providers"] if prefix not in str(p.get("file", ""))]
    d["providers"] = kept + new
    json.dump(d, open(c6.FONT_JSON, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    return len(kept)


def build(name, prefix, code0):
    src = os.path.join(HERE, "src", name)
    im = Image.open(os.path.join(src, "bg_source.png")).convert("RGBA")
    assert im.size == (c6.W, c6.H), f"{name} 배경판 크기 {im.size} != {(c6.W, c6.H)}"
    c6.draw_inventory(im)

    os.makedirs(c6.OUTDIR, exist_ok=True)
    for f in os.listdir(c6.OUTDIR):
        if f.startswith(prefix):
            os.remove(os.path.join(c6.OUTDIR, f))
    provs, glyph = [], []
    for i, (tile, box, gw, gh, gx, gy) in enumerate(c6.tiles()):
        crop = im.crop(box)
        assert max(crop.size) <= 256, f"{name} {tile} {crop.size} — 아틀라스 256px 초과"
        crop.save(os.path.join(c6.OUTDIR, f"{prefix}{tile}.png"))
        ch = chr(code0 + i)
        provs.append({"type": "bitmap", "file": f"barkan:gui/{prefix}{tile}.png",
                      "ascent": 13 - gy, "height": gh, "chars": [ch]})
        glyph.append("\\uf801" if i == 0 else ("\\uf803" if gx == 0 else "\\uf802"))
        glyph.append(f"\\u{ord(ch):04x}")
    kept = merge_providers(prefix, provs)
    open(os.path.join(src, "_glyph.txt"), "w", encoding="utf-8").write("".join(glyph))
    im.save(os.path.join(src, "_preview_full.png"))
    print(f"  {name:7} 타일 {len(provs)}개 (U+{code0:04X}~U+{code0 + len(provs) - 1:04X}) "
          f"· gui.json 기존 {kept}개 보존")


def main():
    for name, (prefix, code0) in SCREENS.items():
        build(name, prefix, code0)
    print(f"  → {c6.OUTDIR}")


if __name__ == "__main__":
    main()
