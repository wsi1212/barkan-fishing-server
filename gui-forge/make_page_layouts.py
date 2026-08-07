#!/usr/bin/env python3
"""전용 배경 3장 좌표 가이드 — 강화 · 주방 · 우편함.

세 화면 다 **0행을 슬롯이 쓴다**. 그래서 공용판(0행 = 제목 명판)을 못 쓰고,
아이스박스와 같은 구조 — 제목을 격자 **위쪽 띠**로 올린 전용 판 — 로 간다.

역할 표기
  홈   : 아이템이 올라가는 자리. 홈만 파고 아이콘은 우리가 올린다
  입력 : 플레이어가 아이템을 넣는 빈 칸. 다른 홈과 **구분되게** 그린다
  목록 : 내용물이 매번 바뀌는 칸. 안쪽은 조용하게
  장식 : 아이템 없음. 그림으로 채운다

산출: src/<이름>/_guide.png
"""
import os

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
RP = os.path.expanduser("~/development/barkan-resourcepack")
FONT_TTF = os.path.join(RP, "assets/barkan/font/aggro_bold.ttf")

SCALE, GRID_X, GRID_Y, CELL, COLS = 4, 7, 17, 18, 9
TITLE_Y0, TITLE_Y1 = 24, 64

ROLE_COLOR = {
    "홈":   ((255, 160, 0, 255), (255, 190, 90, 255)),
    "입력": ((80, 255, 140, 255), (150, 255, 190, 255)),
    "목록": ((120, 200, 255, 255), (170, 220, 255, 255)),
    "장식": ((160, 160, 160, 160), (200, 200, 200, 200)),
}

# 이름: (행 수, {슬롯: (역할, 라벨)}, 기본역할)
PAGES = {
    "enhance": (5, {
        4: ("홈", "낚싯대 정보"),
        10: ("홈", "↓라벨"), 12: ("홈", "↓라벨"), 13: ("홈", "↓라벨"), 14: ("홈", "↓라벨"),
        19: ("입력", "낚싯대"), 21: ("입력", "상승권"), 22: ("입력", "방지권"), 23: ("입력", "감소권"),
        16: ("홈", "강화 전"), 25: ("홈", "▼"), 34: ("홈", "강화 후"),
        31: ("홈", "성공률"), 40: ("홈", "강화 버튼"),
    }, "장식"),
    "cooking": (6, {
        **{s: ("홈", "탭") for s in (0, 1, 2)}, 8: ("홈", "안내"),
        **{s: ("목록", "") for s in
           list(range(10, 17)) + list(range(19, 26)) + list(range(28, 35))},
        45: ("홈", "이전"), 47: ("홈", "대기열"), 49: ("홈", "페이지"),
        50: ("홈", "다음"), 53: ("홈", "닫기"),
    }, "장식"),
    "mailbox": (6, {
        **{s: ("목록", "") for s in range(45)},
        45: ("홈", "이전"), 48: ("홈", "안내"), 49: ("홈", "모두 수령"),
        53: ("홈", "다음"),
    }, "장식"),
}


def font(px):
    try:
        return ImageFont.truetype(FONT_TTF, px)
    except Exception:
        return ImageFont.load_default()


def geom(rows):
    gh = 114 + rows * CELL
    return 176 * SCALE, gh * SCALE, 31 + rows * CELL


def guide(rows, roles, default):
    w, h, inv_y = geom(rows)
    im = Image.new("RGBA", (w, h), (34, 34, 42, 255))
    d = ImageDraw.Draw(im, "RGBA")
    fs = font(15)
    for r in range(rows):
        for c in range(COLS):
            s = r * COLS + c
            role, label = roles.get(s, (default, ""))
            outline, text = ROLE_COLOR[role]
            x0, y0 = (GRID_X + CELL * c) * SCALE, (GRID_Y + CELL * r) * SCALE
            box = [x0, y0, x0 + CELL * SCALE - 1, y0 + CELL * SCALE - 1]
            d.rectangle(box, outline=outline, width=5 if role != "장식" else 2)
            d.text((x0 + 4, y0 + 4), str(s), font=fs, fill=(255, 255, 255, 180))
            if label:
                d.text((x0 + 4, y0 + 44), label, font=fs, fill=text)
            elif role == "장식":
                d.text((x0 + 4, y0 + 44), "장식", font=fs, fill=text)

    d.rectangle([GRID_X * SCALE, TITLE_Y0, (GRID_X + CELL * COLS) * SCALE - 1, TITLE_Y1],
                outline=(150, 150, 255, 255), width=4)
    d.text((GRID_X * SCALE + 8, TITLE_Y0 + 8), "제목 띠: 글자는 코드가 찍는다. 판만 그릴 것",
           font=fs, fill=(190, 190, 255, 255))
    d.rectangle([GRID_X * SCALE, inv_y * SCALE, (GRID_X + CELL * COLS) * SCALE - 1,
                 (inv_y + 76) * SCALE], outline=(255, 90, 90, 220), width=5)
    d.text((GRID_X * SCALE + 8, (inv_y - 13) * SCALE), "PLAYER INVENTORY: 격자 그리지 말 것",
           font=fs, fill=(255, 120, 120, 255))
    d.text((12, h - 30), f"CANVAS {w} x {h}", font=font(22), fill=(255, 255, 0, 255))
    return im


def main():
    for name, (rows, roles, default) in PAGES.items():
        w, h, inv_y = geom(rows)
        out = os.path.join(HERE, "src", name)
        os.makedirs(out, exist_ok=True)
        guide(rows, roles, default).save(os.path.join(out, "_guide.png"))
        ry = [((GRID_Y + CELL * r) * SCALE, (GRID_Y + CELL * (r + 1)) * SCALE - 1) for r in range(rows)]
        print(f"  {name:8} {w}x{h} · {rows}행 · 인벤 y {inv_y * SCALE}~{(inv_y + 76) * SCALE}")
        print(f"           행 y {' · '.join(f'r{i} {a}~{b}' for i, (a, b) in enumerate(ry))}")


if __name__ == "__main__":
    main()
