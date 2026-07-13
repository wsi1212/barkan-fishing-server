#!/usr/bin/env python3
"""슬롯 배당표 벽 그림 (페인팅 시스템 — worldmap과 동일 방식).

⚠️ 2026-07-13 폐기: 현재 prod/dev는 ChatGPT 아르데코 아트(수동, 1024×1536)를
   slot_paytable.png에 직접 넣어 쓴다. 이 생성기를 실행하면 그 아트를 덮어쓰니 실행 금지.
   (배당값 참고용으로만 남김 — SlotRules와 동기화 확인 시.)


- RP 텍스처: assets/barkan/textures/painting/slot_paytable.png (고해상, painting 아틀라스)
- 데이터팩: barkanmap/data/barkan/painting_variant/slot_paytable.json (asset_id + width/height)
2블록 폭 × 3블록 높이 세로 패널. 심볼 아이콘 + 배수(트리플/페어), SlotRules 실제 값.
카지노 레퍼런스풍(짙은 펠트 + 금테 + 섹션).
"""

import math
import os
from PIL import Image, ImageDraw, ImageFont

RP = os.path.expanduser("~/development/barkan-resourcepack")
STAGING = os.environ.get("PT_STAGING", os.path.expanduser("~/Desktop/casino-cards-preview"))

# 2×3 블록 → 세로 패널. 텍스처 512×768(블록당 256px).
W, H = 512, 768
FONT_BOLD = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
HANGUL = "/System/Library/Fonts/AppleSDGothicNeo.ttc"

FELT = (24, 58, 38)          # 짙은 초록 펠트
FELT_HI = (32, 74, 48)
GOLD = (226, 178, 60)
GOLD_DK = (150, 112, 28)
CREAM = (244, 238, 214)
DIM = (176, 186, 170)
RED = (214, 64, 58)


def font(size, hangul=False):
    try:
        return ImageFont.truetype(HANGUL if hangul else FONT_BOLD, size)
    except OSError:
        return ImageFont.truetype(FONT_BOLD, size)


# ===== 심볼 아이콘 (슬롯 심볼, s = 반크기 픽셀) =====

def sym_cherry(d, cx, cy, s):
    r = s * 0.42
    for dx in (-r * 0.95, r * 0.95):
        d.ellipse([cx + dx - r, cy + s * 0.1 - r, cx + dx + r, cy + s * 0.1 + r],
                  fill=(210, 40, 44), outline=(150, 20, 24), width=max(1, s // 14))
        d.ellipse([cx + dx - r * 0.35, cy + s * 0.1 - r * 0.5, cx + dx - r * 0.35 + r * 0.4,
                   cy + s * 0.1 - r * 0.5 + r * 0.4], fill=(255, 180, 180))
    d.line([(cx - r * 0.95, cy + s * 0.1 - r), (cx, cy - s * 0.6)], fill=(70, 130, 50), width=max(2, s // 8))
    d.line([(cx + r * 0.95, cy + s * 0.1 - r), (cx, cy - s * 0.6)], fill=(70, 130, 50), width=max(2, s // 8))


def sym_lemon(d, cx, cy, s):
    d.ellipse([cx - s * 0.6, cy - s * 0.42, cx + s * 0.6, cy + s * 0.42],
              fill=(240, 210, 60), outline=(190, 150, 30), width=max(1, s // 12))
    d.ellipse([cx - s * 0.3, cy - s * 0.28, cx + s * 0.05, cy - s * 0.02], fill=(252, 240, 160))


def sym_bell(d, cx, cy, s):
    d.pieslice([cx - s * 0.55, cy - s * 0.6, cx + s * 0.55, cy + s * 0.4], 180, 360, fill=GOLD, outline=GOLD_DK, width=max(1, s // 14))
    d.rectangle([cx - s * 0.55, cy + s * 0.05, cx + s * 0.55, cy + s * 0.28], fill=GOLD, outline=GOLD_DK, width=max(1, s // 16))
    d.ellipse([cx - s * 0.13, cy + s * 0.28, cx + s * 0.13, cy + s * 0.54], fill=GOLD_DK)


def sym_bar(d, cx, cy, s):
    d.rounded_rectangle([cx - s * 0.72, cy - s * 0.34, cx + s * 0.72, cy + s * 0.34], s * 0.12,
                        fill=(28, 30, 40), outline=GOLD, width=max(2, s // 10))
    f = font(int(s * 0.62))
    d.text((cx, cy), "BAR", font=f, fill=GOLD, anchor="mm")


def sym_diamond(d, cx, cy, s):
    pts = [(cx, cy - s * 0.62), (cx + s * 0.5, cy), (cx, cy + s * 0.62), (cx - s * 0.5, cy)]
    d.polygon(pts, fill=(90, 210, 230), outline=(40, 150, 180), width=max(1, s // 12))
    d.polygon([(cx, cy - s * 0.62), (cx + s * 0.22, cy - s * 0.18), (cx - s * 0.22, cy - s * 0.18)],
              fill=(200, 245, 250))


def sym_seven(d, cx, cy, s):
    f = font(int(s * 1.5))
    d.text((cx, cy), "7", font=f, fill=RED, anchor="mm", stroke_width=max(1, s // 12), stroke_fill=(150, 20, 24))


SYMS = {"cherry": sym_cherry, "lemon": sym_lemon, "bell": sym_bell,
        "bar": sym_bar, "diamond": sym_diamond, "seven": sym_seven}


def build():
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # 패널 + 금테
    d.rounded_rectangle([6, 6, W - 6, H - 6], 18, fill=FELT, outline=GOLD, width=8)
    d.rounded_rectangle([16, 16, W - 16, H - 16], 12, outline=GOLD_DK, width=2)

    # 헤더
    d.rectangle([28, 26, W - 28, 82], fill=(18, 44, 30))
    d.text((W // 2, 54), "슬롯 배당표", font=font(36, hangul=True), fill=GOLD, anchor="mm")

    def section(y0, title):
        d.text((40, y0), title, font=font(22, hangul=True), fill=CREAM, anchor="lm")
        d.line([(40, y0 + 16), (W - 40, y0 + 16)], fill=GOLD_DK, width=2)

    def row(y, syms, mult, count):
        s = 21
        x = 54
        for i in range(count):
            SYMS[syms](d, x, y, s)
            x += 52
        d.text((W - 44, y), mult, font=font(30), fill=GOLD, anchor="rm")

    # 트리플 섹션 (3개) — 6줄, step 46
    section(104, "★ 같은 그림 3개")
    triples = [("cherry", "×3"), ("lemon", "×5"), ("bell", "×8"),
               ("bar", "×15"), ("diamond", "×50"), ("seven", "×100")]
    ty = 134
    for sym, mult in triples:
        row(ty, sym, mult, 3)
        ty += 46

    # 페어 섹션 (2개) — 심볼별 차등, 6줄
    section(ty + 4, "◆ 같은 그림 2개 (심볼별)")
    ty += 34
    pairs = [("cherry", "×1.0"), ("lemon", "×1.0"), ("bell", "×1.2"),
             ("bar", "×1.4"), ("diamond", "×2.0"), ("seven", "×6.0")]
    for sym, mult in pairs:
        row(ty, sym, mult, 2)
        ty += 46

    # 푸터
    d.text((W // 2, H - 34), "모든 배수 원금 포함",
           font=font(18, hangul=True), fill=DIM, anchor="mm")

    tex = os.path.join(RP, "assets/barkan/textures/painting/slot_paytable.png")
    os.makedirs(os.path.dirname(tex), exist_ok=True)
    img.save(tex)
    os.makedirs(STAGING, exist_ok=True)
    img.save(os.path.join(STAGING, "slot_paytable.png"))
    print("배당표 텍스처:", tex)


if __name__ == "__main__":
    build()
