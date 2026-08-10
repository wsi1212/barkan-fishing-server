#!/usr/bin/env python3
"""전용 배경판을 글리프 12타일로 굽는 공용 빌더 — 화면마다 스크립트를 복사하지 않는다.

## 타일 나누기
글리프 아틀라스가 한 타일을 256px로 제한한다. 가로는 9열(176 GUI)을 59/59/58 로,
세로는 창 높이(114 + 행수x18)를 4등분한다. 5행이면 204 → 51x4, 6행이면 222 → 56/56/55/55.

## 인벤 격자만 더한다
슬롯 소켓은 아트에 이미 그려져 있다. 여기서 더하는 건 플레이어 인벤 격자뿐이다
(모든 화면이 동일하고, 아트로 받으면 어긋난다).

사용: python3 build_plate.py <이름>
"""
import json
import os
import sys

from PIL import Image

import build_common6_bg as c6

HERE = os.path.dirname(os.path.abspath(__file__))

# 이름: (행 수, 텍스처 접두어, 시작 코드포인트[, 원본 파일명])
# E620 낚시창 · E650 판매창 · E660 공용6행 · E670 메뉴 · E680 내정보 · E690 상점 · E6A0 아이스박스
# 원본 파일명은 기본 bg_source.png. 손질 스크립트(prep_*.py)가 있는 화면은 그 산출물이
# bg_source.png 이고, 손질이 필요 없는 화면은 받은 파일을 그대로 가리킨다 — 사본을 만들지 않는다.
PLATES = {
    "enhance": (5, "enhance_", 0xE6B0),
    "mailbox": (6, "mailbox_", 0xE6C0),
    "cooking": (6, "cooking_", 0xE6D0),
    "smithy": (6, "smithy_", 0xE6E0),
    "crafting": (6, "crafting_", 0xE6F0),
    "disassemble": (6, "disasm_", 0xE710),   # E700 은 제목 글리프가 쓴다
    "forge": (6, "forge_", 0xE720),
    "iceshop": (3, "iceshop_", 0xE730),      # prep_iceshop_bg.py 가 bg_source.png 를 만든다
    # ★접두어를 skilltree_ 로 두면 기존 폴더 skilltree_parts/ 까지 지우려 든다(노드 스프라이트).
    "skilltree": (5, "sktree_", 0xE740, "bg_source_rebuild.png"),
    "skillhub": (3, "skhub_", 0xE750),
    # 도감 4종 — 슬롯 배열이 겹쳐 판 넷이 화면 여덟을 덮는다(prep_dex_bg.py 산출).
    "dexmain": (3, "dexmain_", 0xE760),
    "dextab": (6, "dextab_", 0xE770),
    "dexfish": (6, "dexfish_", 0xE780),
    "dexisland": (4, "dexisl_", 0xE790),
    "npcdialog": (4, "npcdlg_", 0xE7A0),
}


def split(total, n):
    """total 을 n 조각으로 — 앞쪽부터 1씩 더 준다(합이 정확히 맞게)."""
    base, rem = divmod(total, n)
    return [base + (1 if i < rem else 0) for i in range(n)]


def build(name):
    rows, prefix, code0, *rest = PLATES[name]
    fname = rest[0] if rest else "bg_source.png"
    gw, gh = 176, 114 + rows * c6.CELL
    W, H = gw * c6.SCALE, gh * c6.SCALE
    src = os.path.join(HERE, "src", name)
    # fit_sockets.py 산출이 있으면 그걸 쓴다 — 칸 구멍을 아이콘 상자에 맞춘 판이다.
    if os.path.exists(os.path.join(src, "bg_fitted.png")):
        fname = "bg_fitted.png"
    im = Image.open(os.path.join(src, fname)).convert("RGBA")
    assert im.size == (W, H), f"{name} 배경판 {im.size} != {(W, H)}"

    inv_y = 31 + rows * c6.CELL
    c6.INV_Y0 = inv_y
    c6.INV_ROWS_Y = [inv_y, inv_y + c6.CELL, inv_y + 2 * c6.CELL]
    c6.HOTBAR_Y = inv_y + 58
    c6.draw_inventory(im)

    col_gui = [59, 59, 58]
    row_gui = split(gh, 4)
    assert max(row_gui) * c6.SCALE <= 256, f"타일 세로 {max(row_gui) * c6.SCALE}px > 256"

    for f in os.listdir(c6.OUTDIR):
        if f.startswith(prefix):
            os.remove(os.path.join(c6.OUTDIR, f))
    provs, glyph, gy, i = [], [], 0, 0
    for r, rh in enumerate(row_gui):
        gx = 0
        for c, cw in enumerate(col_gui):
            box = (gx * c6.SCALE, gy * c6.SCALE, (gx + cw) * c6.SCALE, (gy + rh) * c6.SCALE)
            im.crop(box).save(os.path.join(c6.OUTDIR, f"{prefix}r{r}c{c}.png"))
            ch = chr(code0 + i)
            provs.append({"type": "bitmap", "file": f"barkan:gui/{prefix}r{r}c{c}.png",
                          "ascent": 13 - gy, "height": rh, "chars": [ch]})
            glyph.append("\\uf801" if i == 0 else ("\\uf803" if gx == 0 else "\\uf802"))
            glyph.append(f"\\u{ord(ch):04x}")
            gx += cw; i += 1
        gy += rh

    d = json.load(open(c6.FONT_JSON, encoding="utf-8"))
    kept = [p for p in d["providers"] if prefix not in str(p.get("file", ""))]
    d["providers"] = kept + provs
    json.dump(d, open(c6.FONT_JSON, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    open(os.path.join(src, "_glyph.txt"), "w", encoding="utf-8").write("".join(glyph))
    im.save(os.path.join(src, "_preview_full.png"))
    print(f"  {name:8} {W}x{H} · 타일 {len(provs)}개 "
          f"(U+{code0:04X}~U+{code0 + len(provs) - 1:04X}) · gui.json 기존 {len(kept)}개 보존")


if __name__ == "__main__":
    for n in (sys.argv[1:] or PLATES):
        build(n)
