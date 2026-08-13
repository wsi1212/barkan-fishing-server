#!/usr/bin/env python3
"""뼈대판(_template.png) 생성 — 발주 시트의 왼쪽에 깔리는, 덧칠할 판.

`_guide.png` 는 슬롯 번호와 역할이 잔뜩 적힌 **우리가 보는 도면**이고, 이건 그 위에
그림을 그릴 사람이 받는 **깨끗한 판**이다. 칸 자리만 얕게 파여 있고 글씨가 없다.

## 왜 스크립트로 남기나
처음엔 화면마다 즉석에서 만들었는데, 새 화면을 발주할 때마다 같은 걸 다시 짜게 됐다
(2026-08-09 도감 발주에서 4장이 한꺼번에 필요해지며 정리). PAGES 에 항목만 추가하면
뼈대판이 나온다.

사용: python3 make_templates.py [이름 ...]     (기본: PAGES 전체)
산출: src/<이름>/_template.png
"""
import os
import sys

from PIL import Image, ImageDraw

import make_page_layouts as L

HERE = os.path.dirname(os.path.abspath(__file__))

S, GX, GY, CELL, COLS = L.SCALE, L.GRID_X, L.GRID_Y, L.CELL, L.COLS
BG = (38, 40, 46, 255)
FRAME = (150, 152, 162, 255)
SOCKET = (74, 78, 87, 255)
SOCKET_EDGE = (176, 178, 188, 255)
# 역할별 홈 색 — 발주 시트의 범례와 같은 언어를 쓴다(회색=홈 / 파랑=목록 / 초록=넣는 칸).
ROLE_FILL = {"목록": (62, 74, 92, 255), "입력": (58, 84, 66, 255)}
ROLE_EDGE = {"목록": (150, 178, 214, 255), "입력": (150, 210, 164, 255)}
REGION = (210, 212, 222, 255)


def socket(d, slot, role="홈"):
    r, c = divmod(slot, COLS)
    x0, y0 = (GX + CELL * c) * S, (GY + CELL * r) * S
    d.rounded_rectangle([x0, y0, x0 + CELL * S - 1, y0 + CELL * S - 1], radius=10,
                        fill=ROLE_FILL.get(role, SOCKET),
                        outline=ROLE_EDGE.get(role, SOCKET_EDGE), width=3)


def build(name):
    rows, roles, default = L.PAGES[name]
    gh = 114 + rows * CELL
    W, H = 176 * S, gh * S
    im = Image.new("RGBA", (W, H), BG)
    d = ImageDraw.Draw(im, "RGBA")

    d.rectangle([6, 6, W - 7, H - 7], outline=FRAME, width=4)

    # 제목 띠 — 글자는 코드가 찍는다. 판만 그리라고 자리만 표시.
    d.rounded_rectangle([GX * S, L.TITLE_Y0, (GX + CELL * COLS) * S - 1, L.TITLE_Y1],
                        radius=8, outline=REGION, width=3)

    for slot, (role, _) in roles.items():
        if role != "장식":
            socket(d, slot, role)
    if default != "장식":
        for s in range(rows * COLS):
            if s not in roles:
                socket(d, s, default)

    # 타일(큰 버튼)은 한 덩어리로
    for _, col, row, wc, hr in L.TILES.get(name, []):
        x0, y0 = (GX + CELL * col) * S, (GY + CELL * row) * S
        d.rounded_rectangle([x0, y0, x0 + CELL * wc * S - 1, y0 + CELL * hr * S - 1],
                            radius=12, fill=SOCKET, outline=SOCKET_EDGE, width=4)

    # ★30 이다(31 아님) — 바닐라의 139/197 은 아이템이 그려지는 y 이고 셀 좌상단은 그보다
    #   1 GUI px 위다. build_plate 는 30 을 쓰는데 여기만 31 이면 발주 시 그려 준 '건드리지
    #   말 자리'가 실제 인벤 격자와 4px 어긋난다.
    inv_y = (30 + rows * CELL) * S
    d.rectangle([GX * S, inv_y, (GX + CELL * COLS) * S - 1, inv_y + 76 * S],
                outline=REGION, width=3)

    out = os.path.join(HERE, "src", name)
    os.makedirs(out, exist_ok=True)
    im.save(os.path.join(out, "_template.png"))
    print(f"  {name:11} {W}x{H} · {rows}행 · 홈 {sum(1 for r, _ in roles.values() if r != '장식')}개")


if __name__ == "__main__":
    for n in (sys.argv[1:] or L.PAGES):
        build(n)
