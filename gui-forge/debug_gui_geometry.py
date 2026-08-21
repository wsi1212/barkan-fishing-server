#!/usr/bin/env python3
"""배경판 위에 실제 슬롯 좌표를 그린 검증용 렌더를 만든다.

빨강 = 상단 컨테이너 슬롯, 청록 = 플레이어 인벤토리·핫바,
노랑 = 플레이어 인벤토리 시작선. 이 파일은 납품 타일에 포함되지 않는다.
"""

import os

from PIL import Image, ImageDraw


HERE = os.path.dirname(os.path.abspath(__file__))
SCALE = 4
GRID_X, GRID_Y, CELL = 7, 17, 18
SCREENS = {
    "questnpc": (2, 30 + 2 * 18),
    "questlist": (3, 30 + 3 * 18),
    "questjournal": (4, 30 + 4 * 18),
    "questpage": (6, 30 + 6 * 18),
}


def rect(draw, x, y, w, h, color, width=2):
    draw.rectangle((x * SCALE, y * SCALE,
                    (x + w) * SCALE - 1, (y + h) * SCALE - 1),
                   outline=color, width=width)


for name, (rows, inv_y) in SCREENS.items():
    path = os.path.join(HERE, "src", name, "_preview_full.png")
    im = Image.open(path).convert("RGBA")
    overlay = Image.new("RGBA", im.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    # 컨테이너 슬롯 0~8, 9~17, ... — 아이템이 실제로 놓이는 9xrows 셀.
    for row in range(rows):
        for col in range(9):
            rect(draw, GRID_X + CELL * col, GRID_Y + CELL * row,
                 CELL, CELL, (255, 65, 65, 220), 2)

    # 플레이어 인벤토리 3줄 + 핫바. 공용 빌더와 같은 좌표를 다시 그린다.
    inv_rows = [inv_y, inv_y + CELL, inv_y + 2 * CELL]
    hotbar = inv_y + 58
    for row in inv_rows + [hotbar]:
        for col in range(9):
            rect(draw, GRID_X + CELL * col, row,
                 CELL, CELL, (45, 230, 235, 235), 2)

    # 실제 플레이어 인벤토리 시작선과 구간 외곽선.
    draw.line((0, inv_y * SCALE, im.width - 1, inv_y * SCALE),
              fill=(255, 220, 40, 255), width=3)
    rect(draw, GRID_X, inv_y, CELL * 9, CELL * 3,
         (80, 255, 255, 255), 3)
    rect(draw, GRID_X, hotbar, CELL * 9, CELL,
         (80, 255, 255, 255), 3)

    # ImageGen 원화의 제목 명판 기준선 — 글리프 제목과 원화 그림자가 같은
    # 명판 안에 들어가는지 확인한다. 여기에 별도 암부를 그리지 않는다.
    rect(draw, 41, 7, 94, 30, (255, 80, 235, 230), 3)
    draw.line((88 * SCALE, 0, 88 * SCALE, im.height - 1),
              fill=(255, 235, 55, 170), width=2)

    # 셀 중심점 — 슬롯 아이템 앵커가 실제로 어느 줄에 놓이는지 확인용.
    for row in inv_rows + [hotbar]:
        for col in range(9):
            cx = (GRID_X + CELL * col + CELL // 2) * SCALE
            cy = (row + CELL // 2) * SCALE
            draw.ellipse((cx - 3, cy - 3, cx + 3, cy + 3), fill=(255, 255, 255, 230))

    Image.alpha_composite(im, overlay).save(
        os.path.join(HERE, "src", name, "_debug_geometry.png"))
    print(name, im.size, "inv-start GUI y=", inv_y,
          "hotbar GUI y=", hotbar)
