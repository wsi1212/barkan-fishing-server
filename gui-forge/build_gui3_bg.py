#!/usr/bin/env python3
"""Build the three fixed tile GUI backgrounds from the common6 plate.

The layout is intentionally procedural: the brief fixes every art-pixel boundary,
so using generated full-canvas art here would make the slot hitboxes drift.
"""
from __future__ import annotations

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
SRC = HERE / "src"
COMMON = SRC / "common6" / "bg_source.png"
OUT = SRC
FONT = Path.home() / "development" / "barkan-resourcepack" / "assets" / "barkan" / "font" / "aggro_bold.ttf"

W, H = 704, 888
X0, X1 = 28, 675
COLS = [(28, 243), (244, 459), (460, 675)]
TOP_Y, MID_Y, TILE_BOTTOM = 140, 284, 427
HOME_Y0, HOME_Y1 = 428, 499
# 제목 명판은 슬롯 0행(art y 68~139)이 아니라 그 위, 공용판이 그려 둔 움푹 팬 띠다.
TITLE_Y0, TITLE_Y1 = 36, 100
TITLES = {"menu": "메뉴", "myinfo": "내 정보", "shop": "상점"}

# 생성 그림을 얹는 경로(compose_gui3_imagegen)에서는 절차 아이콘을 끈다 —
# 켜두면 뽑아낸 아이콘의 투명한 틈으로 밑그림이 비쳐 잡동사니가 보인다.
DRAW_ICONS = True

INK = (18, 13, 10, 255)
PLATE = (31, 30, 29, 255)
PLATE_HI = (57, 48, 39, 255)
GOLD = (197, 153, 79, 255)
GOLD_HI = (237, 199, 120, 255)
CYAN = (70, 181, 185, 255)
CYAN_HI = (155, 228, 220, 255)
RED = (173, 77, 55, 255)


def fnt(size: int):
    return ImageFont.truetype(str(FONT), size) if FONT.exists() else ImageFont.load_default()


def center_text(d: ImageDraw.ImageDraw, box, text: str, size=28, y=None):
    x0, y0, x1, y1 = box
    font = fnt(size)
    bb = d.multiline_textbbox((0, 0), text, font=font, spacing=1, stroke_width=0)
    tw, th = bb[2] - bb[0], bb[3] - bb[1]
    xx = (x0 + x1 - tw) // 2
    yy = (y if y is not None else (y0 + y1 - th) // 2)
    d.multiline_text((xx, yy), text, font=font, fill=GOLD_HI, spacing=1,
                     stroke_width=3, stroke_fill=INK)


def tile_box(col: int, y0: int, y1: int):
    x0, x1 = COLS[col]
    return (x0 + 4, y0 + 4, x1 - 4, y1 - 4)


def plate(d, box, radius=11):
    x0, y0, x1, y1 = box
    # A flat, quiet tile: only a thin molding and a dark plate. No wood texture or FX.
    d.rounded_rectangle(box, radius=radius, fill=PLATE, outline=INK, width=5)
    d.rounded_rectangle((x0 + 2, y0 + 2, x1 - 2, y1 - 2), radius=max(2, radius - 2),
                        outline=GOLD, width=3)
    d.line((x0 + 10, y0 + 7, x1 - 10, y0 + 7), fill=PLATE_HI, width=2)


def line(d, points, fill=GOLD_HI, width=5):
    d.line(points, fill=fill, width=width, joint="curve")


def icon_base(d, cx, cy):
    # A small grounding shadow keeps the two-tone glyph readable on the dark plate.
    d.ellipse((cx - 38, cy + 28, cx + 38, cy + 38), fill=(10, 9, 8, 190))


def icon_profile(d, cx, cy):
    icon_base(d, cx, cy)
    d.rounded_rectangle((cx - 30, cy - 34, cx + 30, cy + 31), 6, outline=GOLD_HI, width=6, fill=INK)
    d.ellipse((cx - 13, cy - 23, cx + 13, cy + 3), fill=CYAN_HI, outline=GOLD, width=4)
    d.arc((cx - 24, cy - 4, cx + 24, cy + 28), 190, 350, fill=CYAN, width=8)


def icon_star_tree(d, cx, cy):
    icon_base(d, cx, cy)
    line(d, [(cx, cy + 30), (cx, cy - 8)], GOLD_HI, 7)
    d.polygon([(cx, cy - 39), (cx + 9, cy - 17), (cx + 32, cy - 15),
               (cx + 14, cy - 2), (cx + 20, cy + 21), (cx, cy + 8),
               (cx - 20, cy + 21), (cx - 14, cy - 2), (cx - 32, cy - 15),
               (cx - 9, cy - 17)], fill=CYAN_HI, outline=GOLD_HI)
    d.ellipse((cx - 7, cy - 7, cx + 7, cy + 7), fill=GOLD_HI)


def icon_equipment(d, cx, cy):
    icon_base(d, cx, cy)
    d.rectangle((cx - 31, cy + 6, cx + 27, cy + 23), fill=GOLD_HI, outline=INK, width=5)
    d.rectangle((cx - 17, cy - 13, cx + 15, cy + 8), fill=CYAN, outline=INK, width=5)
    line(d, [(cx - 26, cy - 29), (cx + 29, cy - 2)], GOLD_HI, 7)
    d.ellipse((cx + 21, cy - 9, cx + 34, cy + 4), fill=CYAN_HI, outline=INK, width=4)


def icon_scroll(d, cx, cy):
    icon_base(d, cx, cy)
    d.rectangle((cx - 26, cy - 29, cx + 26, cy + 29), fill=(118, 84, 46, 255), outline=INK, width=5)
    d.ellipse((cx - 34, cy - 34, cx - 18, cy + 34), fill=GOLD_HI, outline=INK, width=4)
    d.ellipse((cx + 18, cy - 34, cx + 34, cy + 34), fill=GOLD, outline=INK, width=4)
    line(d, [(cx - 10, cy - 6), (cx + 10, cy - 6), (cx + 10, cy - 20),
             (cx + 25, cy), (cx + 10, cy + 20), (cx + 10, cy + 6), (cx - 10, cy + 6)], CYAN_HI, 5)


def icon_island(d, cx, cy):
    icon_base(d, cx, cy)
    d.polygon([(cx - 38, cy + 19), (cx - 26, cy + 2), (cx + 26, cy + 2),
               (cx + 40, cy + 19), (cx + 27, cy + 29), (cx - 27, cy + 29)], fill=GOLD_HI, outline=INK)
    line(d, [(cx, cy + 4), (cx - 4, cy - 28)], CYAN, 6)
    d.polygon([(cx - 4, cy - 26), (cx - 25, cy - 17), (cx - 9, cy - 13)], fill=CYAN_HI, outline=INK)
    d.polygon([(cx - 4, cy - 27), (cx + 18, cy - 21), (cx + 4, cy - 13)], fill=CYAN, outline=INK)


def icon_guild(d, cx, cy):
    icon_base(d, cx, cy)
    line(d, [(cx - 25, cy - 33), (cx - 25, cy + 30)], GOLD_HI, 7)
    d.polygon([(cx - 20, cy - 29), (cx + 31, cy - 20), (cx + 12, cy - 3), (cx - 20, cy - 9)], fill=CYAN_HI, outline=INK)
    d.polygon([(cx - 1, cy + 16), (cx + 24, cy + 16), (cx + 13, cy + 29), (cx - 13, cy + 29)], fill=GOLD, outline=INK)


def icon_stats(d, cx, cy):
    icon_base(d, cx, cy)
    for i, h in enumerate((20, 33, 46)):
        x = cx - 30 + i * 25
        d.rectangle((x, cy + 25 - h, x + 14, cy + 25), fill=(CYAN_HI if i == 2 else GOLD_HI), outline=INK, width=4)
    line(d, [(cx - 37, cy + 28), (cx + 38, cy + 28)], GOLD, 5)


def icon_title(d, cx, cy):
    icon_base(d, cx, cy)
    d.polygon([(cx - 31, cy - 22), (cx + 31, cy - 22), (cx + 21, cy + 8),
               (cx, cy + 28), (cx - 21, cy + 8)], fill=GOLD_HI, outline=INK)
    line(d, [(cx - 20, cy - 4), (cx + 20, cy - 4)], CYAN, 5)
    d.polygon([(cx - 32, cy - 25), (cx - 20, cy - 13), (cx - 15, cy - 34)], fill=CYAN_HI, outline=INK)
    d.polygon([(cx + 32, cy - 25), (cx + 20, cy - 13), (cx + 15, cy - 34)], fill=CYAN_HI, outline=INK)


def icon_trophy(d, cx, cy):
    icon_base(d, cx, cy)
    d.rectangle((cx - 19, cy - 30, cx + 19, cy + 9), fill=GOLD_HI, outline=INK, width=5)
    d.arc((cx - 37, cy - 23, cx - 7, cy + 10), 270, 90, fill=CYAN_HI, width=6)
    d.arc((cx + 7, cy - 23, cx + 37, cy + 10), 90, 270, fill=CYAN_HI, width=6)
    line(d, [(cx, cy + 9), (cx, cy + 27)], GOLD_HI, 6)
    d.rectangle((cx - 27, cy + 25, cx + 27, cy + 33), fill=CYAN, outline=INK, width=4)


def icon_podium(d, cx, cy):
    icon_base(d, cx, cy)
    d.rectangle((cx - 33, cy + 2, cx - 11, cy + 29), fill=GOLD, outline=INK, width=4)
    d.rectangle((cx - 11, cy - 15, cx + 11, cy + 29), fill=GOLD_HI, outline=INK, width=4)
    d.rectangle((cx + 11, cy + 10, cx + 33, cy + 29), fill=CYAN, outline=INK, width=4)
    for x, y, n in ((cx, cy - 30, GOLD_HI), (cx - 22, cy - 15, CYAN_HI), (cx + 22, cy - 8, CYAN_HI)):
        d.ellipse((x - 7, y - 7, x + 7, y + 7), fill=n, outline=INK, width=3)


def icon_book_fish(d, cx, cy):
    icon_base(d, cx, cy)
    d.polygon([(cx, cy - 26), (cx - 37, cy - 34), (cx - 37, cy + 25), (cx, cy + 33)], fill=GOLD_HI, outline=INK)
    d.polygon([(cx, cy - 26), (cx + 37, cy - 34), (cx + 37, cy + 25), (cx, cy + 33)], fill=(150, 112, 63, 255), outline=INK)
    d.ellipse((cx - 15, cy - 4, cx + 18, cy + 12), fill=CYAN_HI, outline=INK, width=4)
    d.polygon([(cx + 17, cy + 4), (cx + 31, cy - 7), (cx + 31, cy + 15)], fill=CYAN, outline=INK)


def icon_gems(d, cx, cy):
    icon_base(d, cx, cy)
    d.polygon([(cx - 8, cy - 37), (cx + 20, cy - 19), (cx + 10, cy + 16), (cx - 20, cy + 4)], fill=CYAN_HI, outline=INK)
    d.polygon([(cx - 8, cy - 37), (cx - 28, cy - 12), (cx - 20, cy + 4), (cx + 10, cy + 16)], fill=GOLD_HI, outline=INK)
    for x, y in ((cx - 31, cy + 13), (cx - 11, cy + 26), (cx + 25, cy + 22)):
        d.ellipse((x - 10, y - 7, x + 10, y + 7), fill=GOLD_HI, outline=INK, width=4)


def icon_hourglass(d, cx, cy):
    icon_base(d, cx, cy)
    d.polygon([(cx - 27, cy - 32), (cx + 27, cy - 32), (cx + 10, cy - 2), (cx + 27, cy + 30), (cx - 27, cy + 30), (cx - 10, cy - 2)], fill=GOLD_HI, outline=INK)
    d.polygon([(cx - 12, cy - 19), (cx + 12, cy - 19), (cx + 2, cy - 4), (cx - 2, cy - 4)], fill=CYAN_HI)
    d.polygon([(cx - 2, cy + 4), (cx + 2, cy + 4), (cx + 15, cy + 20), (cx - 15, cy + 20)], fill=CYAN)
    line(d, [(cx - 32, cy - 35), (cx + 32, cy - 35)], GOLD, 5)
    line(d, [(cx - 32, cy + 34), (cx + 32, cy + 34)], GOLD, 5)


def icon_scroll_shop(d, cx, cy):
    icon_scroll(d, cx, cy)
    d.ellipse((cx + 8, cy - 8, cx + 22, cy + 6), fill=CYAN_HI, outline=INK, width=3)


ICONS = {
    "profile": icon_profile, "level": icon_star_tree, "equipment": icon_equipment,
    "quest": icon_scroll, "island": icon_island, "guild": icon_guild,
    "stats": icon_stats, "title": icon_title, "trophy": icon_trophy,
    "ranking": icon_podium, "codex": icon_book_fish, "gems": icon_gems,
    "hourglass": icon_hourglass, "shop_scroll": icon_scroll_shop,
}


def draw_home_slots(d):
    # The brief explicitly requires all nine grooves; the item icons are supplied in-game.
    for x0, x1 in zip((28, 100, 172, 244, 316, 388, 460, 532, 604),
                      (99, 171, 243, 315, 387, 459, 531, 603, 675)):
        plate(d, (x0 + 3, HOME_Y0 + 4, x1 - 3, HOME_Y1 - 4), radius=9)


def draw_title(d, name):
    text = TITLES.get(name)
    if not text:
        return
    center_text(d, (X0, TITLE_Y0, X1, TITLE_Y1), text, size=44,
                y=TITLE_Y0 + (TITLE_Y1 - TITLE_Y0 - 44) // 2)


def draw_tiles(im, specs, tall=False):
    d = ImageDraw.Draw(im, "RGBA")
    for col, y0, y1, label, icon_name in specs:
        box = tile_box(col, y0, y1)
        plate(d, box, radius=12)
        if not DRAW_ICONS:
            continue
        x0, _, x1, _ = box
        cx = (x0 + x1) // 2
        if tall:
            cy = 248
            ICONS[icon_name](d, cx, cy)
            center_text(d, box, label, size=30, y=378)
        else:
            cy = y0 + 51
            ICONS[icon_name](d, cx, cy)
            center_text(d, box, label, size=28, y=y1 - 47)


def build(name, specs, tall=False):
    guide = Image.open(SRC / name / "_guide.png").convert("RGBA")
    if guide.size != (W, H):
        raise ValueError(f"guide size drift: {name} {guide.size}")
    im = Image.open(COMMON).convert("RGBA")
    if im.size != (W, H):
        raise ValueError(f"common6 size drift: {im.size}")
    draw_tiles(im, specs, tall=tall)
    d = ImageDraw.Draw(im, "RGBA")
    draw_home_slots(d)
    draw_title(d, name)
    # The common plate and all additions must be fully opaque; Minecraft cannot show
    # the GUI underneath through rounded corners.
    im.putalpha(255)
    out = OUT / name / "bg_source.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    im.save(out)
    print(out)


def main():
    build("menu", [
        (0, 140, 283, "내 정보", "profile"), (1, 140, 283, "레벨·특성", "level"),
        (2, 140, 283, "장비", "equipment"), (0, 284, 427, "퀘스트", "quest"),
        (1, 284, 427, "내 섬", "island"), (2, 284, 427, "길드", "guild"),
    ])
    build("myinfo", [
        (0, 140, 283, "프로필", "profile"), (1, 140, 283, "스탯", "stats"),
        (2, 140, 283, "칭호", "title"), (0, 284, 427, "도전과제", "trophy"),
        (1, 284, 427, "랭킹", "ranking"), (2, 284, 427, "도감", "codex"),
    ])
    build("shop", [
        (0, 140, 427, "캐시 상점", "gems"), (1, 140, 427, "잠수 상점", "hourglass"),
        (2, 140, 427, "스크롤 상점", "shop_scroll"),
    ], tall=True)


if __name__ == "__main__":
    main()
