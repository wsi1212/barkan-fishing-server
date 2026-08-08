#!/usr/bin/env python3
"""강화 배경 손질 — 납품본(bg_source_rebuild.png) → bg_source.png.

납품본을 그대로 못 쓰는 이유 두 가지:

1. **▼ 화살표가 34번(강화 후)에 그려져 왔다.** 34는 강화 결과 아이템이 올라가는
   칸이라 화살표가 그 밑에 깔린다. 25번(중간)으로 옮긴다 — 두 칸이 같은 소켓이라
   차분으로 화살표만 떼어낼 수 있다. 흐름은 16(강화 전) → 25(▼) → 34(강화 후).

2. **입력칸이 비어 있으면 뭘 넣는 자리인지 안 보인다.** 회색 실루엣을 깔아 둔다.
   낚싯대는 카탈로그 아이콘(초보 낚싯대)을 쓰고, 주문서는 **리소스팩에 아이콘이
   없어서**(캐시샵이 바닐라 종이를 그대로 쓴다) 두루마리 모양을 그려 넣는다.
   → 주문서 전용 아이콘이 생기면 SCROLL_ICON 에 경로만 넣으면 된다.
"""
import hashlib
import os

from PIL import Image, ImageChops, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "src", "enhance")
RP_ICONS = os.path.expanduser("~/development/barkan-resourcepack/assets/minecraft/textures/item/barkan_icon")

S, GX, GY, C = 4, 7, 17, 18
SLOT_ROD, SLOT_ARROW_FROM, SLOT_ARROW_TO = 19, 34, 25
SCROLL_SLOTS = (21, 22, 23)
GHOST_ALPHA = 84          # 0~255. 넣을 자리는 알려주되 진짜 아이템과 헷갈리면 안 된다
GHOST_SIZE = 46           # 72px 칸 안에서 차지할 크기
SCROLL_ICON = None        # 주문서 전용 아이콘이 생기면 여기에 파일명


def cell(slot):
    r, c = divmod(slot, 9)
    x0, y0 = (GX + C * c) * S, (GY + C * r) * S
    return (x0, y0, x0 + C * S, y0 + C * S)


def sha10(*parts):
    return hashlib.sha1("\0".join(parts).encode("utf-8")).hexdigest()[:10]


def to_ghost(im):
    """회색 실루엣으로 — 색을 빼고 어둡게 눌러 '비어 있는 자리'로 읽히게."""
    g = im.convert("LA").convert("RGBA")
    px = g.load()
    for y in range(g.height):
        for x in range(g.width):
            r, _, _, a = px[x, y]
            v = int(r * 0.55 + 40)
            px[x, y] = (v, v, v, min(a, GHOST_ALPHA) if a else 0)
    return g


def scroll_glyph(size):
    """두루마리 실루엣 — 리소스팩에 주문서 아이콘이 없어서 직접 그린다.
    ★세로로 길게. 가로로 퍼지면 두루마리가 아니라 리본/현수막으로 보인다.
    ★흰색으로 그리면 낚싯대 실루엣보다 훨씬 밝아 혼자 튄다 — 중간 회색으로 그린다."""
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    body, roll = int(size * 0.52), max(3, size // 12)
    x0, x1 = (size - body) // 2, (size + body) // 2
    ink = (170, 170, 170, 255)
    d.rectangle([x0, roll, x1, size - roll], fill=ink)
    for cy in (roll, size - roll):
        d.rounded_rectangle([x0 - roll, cy - roll, x1 + roll, cy + roll], radius=roll, fill=ink)
    for i in range(3):
        y = roll * 2 + int((size - roll * 4) * (i + 1) / 4)
        d.line([x0 + roll, y, x1 - roll, y], fill=(40, 40, 40, 170), width=max(1, size // 26))
    return to_ghost(im)


def main():
    im = Image.open(os.path.join(SRC, "bg_source_rebuild.png")).convert("RGBA")

    b_from, b_to = cell(SLOT_ARROW_FROM), cell(SLOT_ARROW_TO)
    c_from, c_to = im.crop(b_from), im.crop(b_to)
    diff = ImageChops.difference(c_to.convert("RGB"), c_from.convert("RGB")).convert("L")
    mask = diff.point(lambda v: 0 if v < 18 else min(255, (v - 18) * 5))
    mask = mask.filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.GaussianBlur(0.7))
    arrow = c_from.copy(); arrow.putalpha(mask)
    im.paste(c_to, (b_from[0], b_from[1]))          # 34는 깨끗한 소켓으로
    im.alpha_composite(arrow, (b_to[0], b_to[1]))   # 25에 화살표만

    rod_file = os.path.join(RP_ICONS, f"catalog_rod_{sha10('낚싯대', '초보 낚싯대')}.png")
    rod = to_ghost(Image.open(rod_file).convert("RGBA")) if os.path.exists(rod_file) else None
    if rod is None:
        print("  ! 낚싯대 아이콘을 못 찾음 — 실루엣 생략")
    scroll = (to_ghost(Image.open(os.path.join(RP_ICONS, SCROLL_ICON)).convert("RGBA"))
              if SCROLL_ICON else scroll_glyph(GHOST_SIZE * 2))

    for slot, art in [(SLOT_ROD, rod)] + [(s, scroll) for s in SCROLL_SLOTS]:
        if art is None:
            continue
        x0, y0, x1, y1 = cell(slot)
        k = GHOST_SIZE / max(art.size)
        w, h = max(1, round(art.width * k)), max(1, round(art.height * k))
        im.alpha_composite(art.resize((w, h), Image.Resampling.LANCZOS),
                           (x0 + (x1 - x0 - w) // 2, y0 + (y1 - y0 - h) // 2))

    im.putalpha(255)
    out = os.path.join(SRC, "bg_source.png")
    im.save(out)
    print(f"  ▼ {SLOT_ARROW_FROM}→{SLOT_ARROW_TO} · 실루엣 {SLOT_ROD}(낚싯대)"
          f" {list(SCROLL_SLOTS)}(주문서) → {out}")


if __name__ == "__main__":
    main()
