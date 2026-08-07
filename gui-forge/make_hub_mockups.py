#!/usr/bin/env python3
"""메뉴 타일을 눌렀을 때 열리는 **상세 화면 목업** — 발주/합의용.

상세 화면은 메뉴와 달리 **전용 그림을 굽지 않는다.** 공용 6행 판(common6) 위에
아이템 버튼만 올린다 — 44개 화면이 같은 판을 쓰는 구조를 깨지 않기 위해서다.
그래서 여기 목업은 "이 판 위에 이런 버튼이 이 자리에 놓인다"를 보여주는 용도다.

새로 만들어야 하는 건 두 개:
  · 내 정보 허브 — 프로필 · 스탯 · 칭호 · 도전과제 · 랭킹
  · 상점 허브   — 캐시(+추천 코인탭) · 잠수 · 스크롤
나머지 타일(레벨·특성/장비/퀘스트/내 섬/길드)은 이미 있는 화면으로 바로 간다.

산출: src/menu/_hub_<이름>.png
"""
import os

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "src", "menu")
COMMON = os.path.join(HERE, "src", "common6", "bg_source.png")
RP = os.path.expanduser("~/development/barkan-resourcepack")
FONT_TTF = os.path.join(RP, "assets/barkan/font/aggro_bold.ttf")

SCALE = 4
W, H = 704, 888
GRID_X, GRID_Y, CELL, COLS = 7, 17, 18, 9

HUBS = {
    "myinfo": ("내 정보",
               [("프로필", 11), ("스탯", 12), ("칭호", 13), ("도전과제", 14), ("랭킹", 15)]),
    "shop":   ("상점",
               [("캐시 상점", 12), ("잠수 상점", 13), ("스크롤 상점", 14)]),
}
SLOT_BACK, SLOT_CLOSE = 45, 53


def font(px):
    try:
        return ImageFont.truetype(FONT_TTF, px)
    except Exception:
        return ImageFont.load_default()


def slot_box(s):
    c, r = s % COLS, s // COLS
    x0 = (GRID_X + CELL * c) * SCALE
    y0 = (GRID_Y + CELL * r) * SCALE
    return x0, y0, x0 + CELL * SCALE - 1, y0 + CELL * SCALE - 1


def build(title, buttons):
    im = Image.open(COMMON).convert("RGBA").resize((W, H), Image.LANCZOS)
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov, "RGBA")
    ft, fb = font(30), font(17)

    # 제목(실제로는 금박 아트 글리프로 얹는다)
    bb = d.textbbox((0, 0), title, font=ft)
    d.text((W / 2 - (bb[2] - bb[0]) / 2, 34), title, font=ft,
           fill=(255, 226, 150, 255), stroke_width=3, stroke_fill=(18, 12, 8, 255))

    for label, s in buttons + [("← 뒤로", SLOT_BACK), ("닫기", SLOT_CLOSE)]:
        x0, y0, x1, y1 = slot_box(s)
        d.rounded_rectangle([x0 + 3, y0 + 3, x1 - 3, y1 - 3], radius=8,
                            fill=(14, 20, 26, 160), outline=(198, 150, 78, 235), width=3)
        lb = d.textbbox((0, 0), label, font=fb)
        d.text(((x0 + x1) / 2 - (lb[2] - lb[0]) / 2, y1 + 4), label, font=fb,
               fill=(235, 220, 190, 255), stroke_width=2, stroke_fill=(12, 10, 8, 255))
    im.alpha_composite(ov)
    return im


def main():
    os.makedirs(OUT, exist_ok=True)
    for key, (title, buttons) in HUBS.items():
        p = os.path.join(OUT, f"_hub_{key}.png")
        build(title, buttons).save(p)
        print(f"  {title:8} 버튼 {[s for _, s in buttons]}  → {os.path.basename(p)}")
    print("  (뒤로 45 · 닫기 53 — 상세 화면 공통)")


if __name__ == "__main__":
    main()
