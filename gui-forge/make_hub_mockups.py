#!/usr/bin/env python3
"""상세 화면(내 정보 / 상점) — 타일형 가이드 + 목업.

메뉴와 마찬가지로 **버튼 그림과 글자를 배경에 굽는다.** 전용 그림을 굽는 화면은
메뉴 · 내 정보 · 상점 **딱 셋뿐**이고, 나머지 목록형 화면은 공용 6행 판 + 아이템 아이콘이다.

## 타일 폭은 9열을 정확히 나눠야 한다
빈칸이 생기면 가운데에 골이 보인다(2026-08-07 확인). 9열을 나누는 조합만 쓴다:
  3+3+3 (3개)  ·  9 (1개)  ·  4+5 같은 비대칭은 쓰지 않는다.

  내 정보 : 3열x2행 타일 6개 (1~4행)  — 프로필·스탯·칭호·도전과제·랭킹·도감
  상점    : 3열x4행 타일 3개 (1~4행)  — 캐시(+추천 코인탭)·잠수·스크롤
           항목이 3개뿐이라 세로로 꽉 채워 큰 판 3장으로 만든다.

산출: src/<이름>/_guide.png · src/<이름>/_mockup.png
"""
import os

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
COMMON = os.path.join(HERE, "src", "common6", "bg_source.png")
RP = os.path.expanduser("~/development/barkan-resourcepack")
FONT_TTF = os.path.join(RP, "assets/barkan/font/aggro_bold.ttf")

SCALE = 4
W, H = 704, 888
GRID_X, GRID_Y, CELL, COLS = 7, 17, 18, 9

# 이름: (제목, [ (라벨, 시작열, 시작행, 열수, 행수) ], [하단 아이콘 슬롯])
HUBS = {
    "myinfo": ("내 정보", [
        ("프로필", 0, 1, 3, 2), ("스탯", 3, 1, 3, 2), ("칭호", 6, 1, 3, 2),
        ("도전과제", 0, 3, 3, 2), ("랭킹", 3, 3, 3, 2), ("도감", 6, 3, 3, 2),
    ]),
    "shop": ("상점", [
        ("캐시 상점", 0, 1, 3, 4), ("잠수 상점", 3, 1, 3, 4), ("스크롤 상점", 6, 1, 3, 4),
    ]),
}
SLOT_BACK, SLOT_CLOSE = 45, 53


def font(px):
    try:
        return ImageFont.truetype(FONT_TTF, px)
    except Exception:
        return ImageFont.load_default()


def rect(col, row, wcol, hrow):
    x0 = (GRID_X + CELL * col) * SCALE
    y0 = (GRID_Y + CELL * row) * SCALE
    return [x0, y0, x0 + CELL * wcol * SCALE - 1, y0 + CELL * hrow * SCALE - 1]


def guide(title, tiles):
    im = Image.new("RGBA", (W, H), (44, 44, 52, 255))
    d = ImageDraw.Draw(im, "RGBA")
    f, fs = font(26), font(17)
    for r in range(6):
        for c in range(COLS):
            x0 = (GRID_X + CELL * c) * SCALE
            y0 = (GRID_Y + CELL * r) * SCALE
            d.rectangle([x0, y0, x0 + CELL * SCALE - 1, y0 + CELL * SCALE - 1],
                        fill=(0, 190, 190, 55), outline=(0, 255, 255, 200), width=2)
            d.text((x0 + 5, y0 + 5), str(r * COLS + c), font=fs, fill=(255, 255, 255, 210))
    for label, col, row, wc, hr in tiles:
        box = rect(col, row, wc, hr)
        d.rectangle(box, outline=(255, 200, 0, 255), width=6)
        d.text((box[0] + 10, box[1] + 8), label, font=f, fill=(255, 220, 60, 255))
    for lbl, s in (("뒤로", SLOT_BACK), ("닫기", SLOT_CLOSE)):
        c, r = s % COLS, s // COLS
        box = rect(c, r, 1, 1)
        d.rectangle(box, outline=(255, 140, 0, 255), width=5)
        d.text((box[0] + 4, box[1] + 22), lbl, font=fs, fill=(255, 170, 60, 255))
    d.rectangle(rect(0, 0, 9, 1), outline=(150, 150, 255, 255), width=5)
    d.text((rect(0, 0, 9, 1)[0] + 10, rect(0, 0, 9, 1)[1] + 20),
           f'TITLE "{title}" — 그림에 직접', font=fs, fill=(190, 190, 255, 255))
    iy = 31 + 6 * CELL
    d.rectangle([GRID_X * SCALE, iy * SCALE, (GRID_X + CELL * COLS) * SCALE - 1, (iy + 76) * SCALE],
                outline=(255, 90, 90, 220), width=5)
    d.text((GRID_X * SCALE + 8, (iy - 13) * SCALE), "PLAYER INVENTORY - 격자 그리지 말 것",
           font=fs, fill=(255, 120, 120, 255))
    d.text((12, H - 34), f"CANVAS {W} x {H}", font=f, fill=(255, 255, 0, 255))
    return im


def mockup(title, tiles):
    im = Image.open(COMMON).convert("RGBA").resize((W, H), Image.LANCZOS)
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov, "RGBA")
    ft, f = font(30), font(24)
    bb = d.textbbox((0, 0), title, font=ft)
    d.text((W / 2 - (bb[2] - bb[0]) / 2, 88), title, font=ft,
           fill=(255, 226, 150, 255), stroke_width=3, stroke_fill=(18, 12, 8, 255))
    for label, col, row, wc, hr in tiles:
        x0, y0, x1, y1 = rect(col, row, wc, hr)
        d.rounded_rectangle([x0 + 4, y0 + 4, x1 - 4, y1 - 4], radius=10,
                            fill=(14, 20, 26, 150), outline=(198, 150, 78, 235), width=4)
        lb = d.textbbox((0, 0), label, font=f)
        d.text(((x0 + x1) / 2 - (lb[2] - lb[0]) / 2, y1 - 48), label, font=f,
               fill=(255, 226, 150, 255), stroke_width=3, stroke_fill=(18, 12, 8, 255))
    for s in (SLOT_BACK, SLOT_CLOSE):
        c, r = s % COLS, s // COLS
        x0, y0, x1, y1 = rect(c, r, 1, 1)
        d.rounded_rectangle([x0 + 3, y0 + 3, x1 - 3, y1 - 3], radius=8,
                            fill=(14, 20, 26, 150), outline=(198, 150, 78, 220), width=3)
    im.alpha_composite(ov)
    return im


def main():
    for key, (title, tiles) in HUBS.items():
        out = os.path.join(HERE, "src", key)
        os.makedirs(out, exist_ok=True)
        guide(title, tiles).save(os.path.join(out, "_guide.png"))
        mockup(title, tiles).save(os.path.join(out, "_mockup.png"))
        print(f"  {title:8} 타일 {len(tiles)}개 → src/{key}/")
        for label, col, row, wc, hr in tiles:
            slots = sorted((row + dr) * COLS + (col + dc) for dr in range(hr) for dc in range(wc))
            print(f"     {label:10} {wc}열x{hr}행  슬롯 {slots}")
    print(f"  (뒤로 {SLOT_BACK} · 닫기 {SLOT_CLOSE} — 상세 화면 공통)")


if __name__ == "__main__":
    main()
