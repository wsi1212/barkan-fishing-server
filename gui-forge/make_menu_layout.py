#!/usr/bin/env python3
"""메뉴 전용 배경 발주용 — 타일 가이드 + 스타일 목업 생성.

## 배치 (54칸, 6행)
    0~1행      큰 타일 3개  (3칸 x 2칸)
    2~3행      큰 타일 3개
    4행        작은 아이콘 9개 (한 줄 꽉)
    5행        장식 푸터 (버튼 없음)

★타일은 **3열 x 2행**이다. 2열짜리를 4개 놓으면 8열이라 9열 중 한 칸이 남아
  가운데에 빈 골이 생긴다(2026-08-07 목업에서 확인). 3열 x 3개 = 정확히 9열이라
  빈칸이 없다 — 레퍼런스 서버가 깔끔했던 이유가 이것.
  제목은 슬롯 격자 위 띠(art y 0~67)에 그린다.

## 왜 타일마다 글자를 굽나
메뉴는 목적지가 고정이라 그림값을 치를 만하다. 대신 버튼 추가·개명 시 재작업이므로
**목록형 화면(도감·마켓·부품상점)에는 절대 쓰지 않는다** — 거긴 공용판 + 아이템 아이콘.

산출: src/menu/_guide.png (좌표 가이드) · src/menu/_mockup.png (스타일/배치 목업)
"""
import os

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "src", "menu")
COMMON = os.path.join(HERE, "src", "common6", "bg_source.png")
RP = os.path.expanduser("~/development/barkan-resourcepack")
FONT_TTF = os.path.join(RP, "assets/barkan/font/aggro_bold.ttf")

SCALE = 4
GW, ROWS = 176, 6
GH = 114 + ROWS * 18
W, H = GW * SCALE, GH * SCALE          # 704 x 888
GRID_X, GRID_Y, CELL, COLS = 7, 17, 18, 9

# 타일: (라벨, 시작열, 시작행). 2열x2행 고정. 가운데 열(4)은 비운다.
TILE_COLS = [0, 3, 6]
TILES = [
    ("내 정보", 0, 0), ("레벨·특성", 3, 0), ("장비", 6, 0),
    ("퀘스트", 0, 2), ("상점", 3, 2), ("내 공간", 6, 2),
]
# 4행을 9칸 꽉 채운다 — 한 칸이라도 비면 다시 골이 생긴다.
ICONS = [("도감", 36), ("아이스박스", 37), ("거점", 38), ("잠수", 39), ("이모트", 40),
         ("배경음악", 41), ("채팅", 42), ("팁", 43)]
SLOT_CLOSE = 44


def rect(col, row, wcol=3, hrow=2):
    x0 = (GRID_X + CELL * col) * SCALE
    y0 = (GRID_Y + CELL * row) * SCALE
    return [x0, y0, x0 + CELL * wcol * SCALE - 1, y0 + CELL * hrow * SCALE - 1]


def font(px):
    try:
        return ImageFont.truetype(FONT_TTF, px)
    except Exception:
        return ImageFont.load_default()


def guide():
    im = Image.new("RGBA", (W, H), (44, 44, 52, 255))
    d = ImageDraw.Draw(im, "RGBA")
    f, fs = font(26), font(17)
    # 전체 슬롯
    for r in range(ROWS):
        for c in range(COLS):
            x0 = (GRID_X + CELL * c) * SCALE
            y0 = (GRID_Y + CELL * r) * SCALE
            d.rectangle([x0, y0, x0 + CELL * SCALE - 1, y0 + CELL * SCALE - 1],
                        fill=(0, 190, 190, 55), outline=(0, 255, 255, 200), width=2)
            d.text((x0 + 5, y0 + 5), str(r * COLS + c), font=fs, fill=(255, 255, 255, 210))
    # 타일
    for label, col, row in TILES:
        box = rect(col, row)
        d.rectangle(box, outline=(255, 200, 0, 255), width=6)
        d.text((box[0] + 10, box[1] + 8), label, font=f, fill=(255, 220, 60, 255))
    # 아이콘 칸
    for label, s in ICONS + [("닫기", SLOT_CLOSE)]:
        c, r = s % COLS, s // COLS
        box = rect(c, r, 1, 1)
        d.rectangle(box, outline=(255, 140, 0, 255), width=5)
        d.text((box[0] + 4, box[1] + 22), label, font=fs, fill=(255, 170, 60, 255))
    # 제목 줄 + 인벤
    d.rectangle([0, 0, W - 1, (GRID_Y - 1) * SCALE], outline=(150, 150, 255, 255), width=4)
    d.text((12, 10), "TITLE (그림에 직접 그릴 것)", font=fs, fill=(190, 190, 255, 255))
    iy = (31 + ROWS * CELL)
    d.rectangle([GRID_X * SCALE, iy * SCALE, (GRID_X + CELL * COLS) * SCALE - 1, (iy + 76) * SCALE],
                outline=(255, 90, 90, 220), width=5)
    d.text((GRID_X * SCALE + 8, (iy - 13) * SCALE), "PLAYER INVENTORY - 민무늬, 격자 그리지 말 것",
           font=fs, fill=(255, 120, 120, 255))
    d.text((12, H - 34), f"CANVAS {W} x {H}", font=f, fill=(255, 255, 0, 255))
    return im


def mockup():
    """공용판 위에 타일/아이콘 자리를 얹은 스타일 목업 — '이런 느낌'을 보여주기 위한 것."""
    im = Image.open(COMMON).convert("RGBA").resize((W, H), Image.LANCZOS)
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov, "RGBA")
    f = font(22)
    for label, col, row in TILES:
        x0, y0, x1, y1 = rect(col, row)
        d.rounded_rectangle([x0 + 4, y0 + 4, x1 - 4, y1 - 4], radius=10,
                            fill=(14, 20, 26, 150), outline=(198, 150, 78, 235), width=4)
        bb = d.textbbox((0, 0), label, font=f)
        d.text(((x0 + x1) / 2 - (bb[2] - bb[0]) / 2, y1 - 46), label, font=f,
               fill=(255, 226, 150, 255), stroke_width=3, stroke_fill=(18, 12, 8, 255))
    for _, s in ICONS + [("", SLOT_CLOSE)]:
        c, r = s % COLS, s // COLS
        x0, y0, x1, y1 = rect(c, r, 1, 1)
        d.rounded_rectangle([x0 + 3, y0 + 3, x1 - 3, y1 - 3], radius=8,
                            fill=(14, 20, 26, 150), outline=(198, 150, 78, 220), width=3)
    im.alpha_composite(ov)
    return im


def main():
    os.makedirs(OUT, exist_ok=True)
    guide().save(os.path.join(OUT, "_guide.png"))
    mockup().save(os.path.join(OUT, "_mockup.png"))
    print(f"가이드/목업 → {OUT}  ({W}x{H})")
    print(f"  타일(3열x2행) {len(TILES)}개 — 3개x3열 = 9열 정확히, 빈칸 없음")
    for label, col, row in TILES:
        slots = [(row + dr) * COLS + (col + dc) for dr in range(2) for dc in range(3)]
        print(f"    {label:10} 슬롯 {sorted(slots)}")
    print(f"  아이콘 {[s for _, s in ICONS]}  닫기 {SLOT_CLOSE}")


if __name__ == "__main__":
    main()
