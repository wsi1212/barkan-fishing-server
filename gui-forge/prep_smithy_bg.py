#!/usr/bin/env python3
"""대장간 4장 납품본 반입 — ~/Downloads/smithy-all → src/<이름>/bg_source.png.

허브 타일에는 **글자를 굽지 말라고 발주했다**(그림만). 아이콘은 왔지만 이름이 없으면
무슨 작업대인지 모르므로 여기서 글자만 얹는다 — 발주 왕복 없이 문구를 고칠 수 있다.

사용: python3 prep_smithy_bg.py
"""
import os

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
DL = os.path.expanduser("~/Downloads/smithy-all")
RP = os.path.expanduser("~/development/barkan-resourcepack")
FONT_TTF = os.path.join(RP, "assets/barkan/font/aggro_bold.ttf")

S, GX, GY, C = 4, 7, 17, 18
W, H = 704, 888
FILES = {"smithy": "smithy-hub-with-icons.png", "crafting": "crafting.png",
         "disassemble": "disassemble.png", "forge": "forge.png"}
# 허브 타일 (라벨, 시작열, 시작행, 열수, 행수) — make_page_layouts.TILES 와 같은 값
TILES = [("조합대", 1, 1, 3, 2), ("낚싯대 강화", 5, 1, 3, 2),
         ("부품 분해", 1, 4, 3, 2), ("재료 제작소", 5, 4, 3, 2)]
LABEL_SIZE, LABEL_UP = 30, 38          # 타일 아래쪽에서 LABEL_UP 만큼 띄운다
GOLD, INK = (255, 226, 150, 255), (18, 12, 8, 255)


def font(px):
    try:
        return ImageFont.truetype(FONT_TTF, px)
    except Exception:
        return ImageFont.load_default()


def label_tiles(im):
    d = ImageDraw.Draw(im, "RGBA")
    f = font(LABEL_SIZE)
    for text, col, row, wc, hr in TILES:
        x0 = (GX + C * col) * S
        x1 = x0 + C * wc * S
        y1 = (GY + C * (row + hr)) * S
        bb = d.textbbox((0, 0), text, font=f)
        d.text(((x0 + x1 - (bb[2] - bb[0])) / 2, y1 - LABEL_UP - (bb[3] - bb[1]) / 2),
               text, font=f, fill=GOLD, stroke_width=3, stroke_fill=INK)


def main():
    for name, f in FILES.items():
        src = os.path.join(DL, f)
        if not os.path.exists(src):
            print(f"  ! {f} 없음 — 건너뜀")
            continue
        im = Image.open(src).convert("RGBA")
        assert im.size == (W, H), f"{name} 크기 {im.size} != {(W, H)}"
        if name == "smithy":
            label_tiles(im)
        im.putalpha(255)
        out = os.path.join(HERE, "src", name, "bg_source.png")
        os.makedirs(os.path.dirname(out), exist_ok=True)
        im.save(out)
        print(f"  {name:12} → {out}" + ("  (타일 글자 4개 얹음)" if name == "smithy" else ""))


if __name__ == "__main__":
    main()
