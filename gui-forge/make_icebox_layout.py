#!/usr/bin/env python3
"""아이스박스 전용 배경 — 좌표 가이드 + 배치 목업.

## 공용 6행 판을 못 쓰는 이유
공용판은 **0행을 제목 명판이 먹는다**(명판 아래 레일이 0행 칸을 가로지른다).
아이스박스는 보관칸 45개(1~5행 전부) + 머리줄 버튼 4개가 있어서 0행을 비울 수가 없다.
그래서 제목을 격자 **위쪽 띠**(art y 24~64)로 올리고 0행을 머리줄로 쓰는 전용 판을 짠다.

## 슬롯 배치 (자바 IceboxGui 와 1:1, 코드 변경 없음)
  0        아이스박스 티어 명판(아이템)
  1~5      장식 — 아이템 없음. 얼음 띠로 채운다
  6        자동 수납 ON/OFF
  7        업그레이드
  8        닫기
  9~53     보관칸 45개 (잠긴 칸은 플러그인이 회색 판으로 덮는다 — 굽지 말 것)

산출: src/icebox/_guide.png · src/icebox/_mockup.png
"""
import os

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "src", "icebox")
COMMON = os.path.join(HERE, "src", "common6", "bg_source.png")
RP = os.path.expanduser("~/development/barkan-resourcepack")
FONT_TTF = os.path.join(RP, "assets/barkan/font/aggro_bold.ttf")

SCALE = 4
W, H = 704, 888
GRID_X, GRID_Y, CELL, COLS = 7, 17, 18, 9
TITLE_Y0, TITLE_Y1 = 24, 64          # 격자 위 제목 띠(art px)
INV_Y0 = 31 + 6 * CELL               # 139 GUI → art 556

HEADER = {0: "티어 명판", 6: "자동수납", 7: "업그레이드", 8: "닫기"}


def font(px):
    try:
        return ImageFont.truetype(FONT_TTF, px)
    except Exception:
        return ImageFont.load_default()


def cell(col, row, wcol=1, hrow=1):
    x0 = (GRID_X + CELL * col) * SCALE
    y0 = (GRID_Y + CELL * row) * SCALE
    return [x0, y0, x0 + CELL * wcol * SCALE - 1, y0 + CELL * hrow * SCALE - 1]


def guide():
    im = Image.new("RGBA", (W, H), (30, 40, 52, 255))
    d = ImageDraw.Draw(im, "RGBA")
    f, fs = font(24), font(16)

    # 보관칸 45개 — 물고기가 올라가는 자리
    for r in range(1, 6):
        for c in range(COLS):
            b = cell(c, r)
            d.rectangle(b, fill=(0, 170, 200, 60), outline=(120, 230, 255, 230), width=2)
    d.text((cell(0, 3)[0] + 8, cell(0, 3)[1] - 26), "보관칸 45 (1~5행) — 물고기가 올라간다",
           font=fs, fill=(150, 235, 255, 255))

    # 머리줄
    for c in range(COLS):
        b = cell(c, 0)
        label = HEADER.get(c)
        d.rectangle(b, outline=(255, 160, 0, 255) if label else (255, 255, 255, 150),
                    width=5 if label else 2)
        d.text((b[0] + 5, b[1] + 24), label or "장식", font=fs,
               fill=(255, 190, 90, 255) if label else (210, 210, 210, 200))

    d.rectangle([GRID_X * SCALE, TITLE_Y0, (GRID_X + CELL * COLS) * SCALE - 1, TITLE_Y1],
                outline=(150, 150, 255, 255), width=4)
    d.text((GRID_X * SCALE + 8, TITLE_Y0 + 8), "제목 띠 — 「아이스박스」를 여기 그린다",
           font=fs, fill=(190, 190, 255, 255))

    d.rectangle([GRID_X * SCALE, INV_Y0 * SCALE, (GRID_X + CELL * COLS) * SCALE - 1, (INV_Y0 + 76) * SCALE],
                outline=(255, 90, 90, 220), width=5)
    d.text((GRID_X * SCALE + 8, (INV_Y0 - 13) * SCALE), "PLAYER INVENTORY — 격자 그리지 말 것",
           font=fs, fill=(255, 120, 120, 255))
    d.text((12, H - 34), f"CANVAS {W} x {H}", font=f, fill=(255, 255, 0, 255))
    return im


def mockup():
    """공용판을 얼음으로 물들여 톤만 보여주는 배치용 목업(최종 아트가 아니다)."""
    im = Image.open(COMMON).convert("RGBA").resize((W, H), Image.LANCZOS)
    ice = Image.new("RGBA", (W, H), (70, 150, 200, 90))
    im.alpha_composite(ice)
    d = ImageDraw.Draw(im, "RGBA")
    for r in range(1, 6):
        for c in range(COLS):
            x0, y0, x1, y1 = cell(c, r)
            d.rounded_rectangle([x0 + 3, y0 + 3, x1 - 3, y1 - 3], radius=8,
                                fill=(12, 30, 44, 150), outline=(150, 225, 255, 210), width=3)
    for c in range(COLS):
        x0, y0, x1, y1 = cell(c, 0)
        if c in HEADER:
            d.rounded_rectangle([x0 + 3, y0 + 3, x1 - 3, y1 - 3], radius=8,
                                fill=(12, 30, 44, 150), outline=(190, 240, 255, 230), width=3)
    return im


def main():
    os.makedirs(OUT, exist_ok=True)
    guide().save(os.path.join(OUT, "_guide.png"))
    mockup().save(os.path.join(OUT, "_mockup.png"))
    print(f"  보관칸 45 · 머리줄 {sorted(HEADER)} · 제목 띠 y {TITLE_Y0}~{TITLE_Y1} → src/icebox/")


if __name__ == "__main__":
    main()
