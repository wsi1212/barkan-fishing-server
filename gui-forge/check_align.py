#!/usr/bin/env python3
"""납품 그림 검수 — 아이템이 실제로 앉는 자리를 그림 위에 겹쳐 본다.

그림 생성은 72px 격자를 못 맞춘다(스킬 허브 76·80·77px, 인벤토리 70.8px). 눈으로는
멀쩡해 보여도 아이콘이 액자 밖으로 나가므로 **받자마자 이걸 돌린다.**

빨간 상자 = 아이템 아이콘(64px)이 그려지는 자리. 액자 구멍 안에 들어가면 통과.
파란 띠 = 제목 글자가 찍히는 자리. 여기에 그림이 겹치면 글자가 묻힌다.

사용: python3 check_align.py <화면이름> <납품파일>
산출: src/<화면이름>/_align_check.png
"""
import os
import sys

from PIL import Image, ImageDraw

import make_page_layouts as L

HERE = os.path.dirname(os.path.abspath(__file__))
S, GX, GY, CELL, COLS = L.SCALE, L.GRID_X, L.GRID_Y, L.CELL, L.COLS
ICON = 16 * S            # 아이템 아이콘 한 변 (16 GUI px)


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    name, src = sys.argv[1], sys.argv[2]
    rows, roles, default = L.PAGES[name]
    W, H = 176 * S, (114 + rows * CELL) * S

    im = Image.open(os.path.expanduser(src)).convert("RGBA")
    if im.size != (W, H):
        print(f"  ⚠ 캔버스 {im.size} != {(W, H)} — 맞춰서 보정해야 한다")
        im = im.resize((W, H), Image.LANCZOS)

    d = ImageDraw.Draw(im, "RGBA")
    pad = (CELL * S - ICON) // 2
    for slot, (role, _) in roles.items():
        if role == "장식":
            continue
        r, c = divmod(slot, COLS)
        x0 = (GX + CELL * c) * S + pad
        y0 = (GY + CELL * r) * S + pad
        d.rectangle([x0, y0, x0 + ICON - 1, y0 + ICON - 1], outline=(255, 60, 60, 255), width=2)
    d.rectangle([GX * S, L.TITLE_Y0, (GX + CELL * COLS) * S - 1, L.TITLE_Y1],
                outline=(110, 170, 255, 255), width=3)
    inv_y = (31 + rows * CELL) * S
    d.rectangle([GX * S, inv_y, (GX + CELL * COLS) * S - 1, inv_y + 76 * S],
                outline=(80, 230, 120, 255), width=3)

    out = os.path.join(HERE, "src", name, "_align_check.png")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    im.save(out)
    print(f"  {name:11} → {out}")


if __name__ == "__main__":
    main()
