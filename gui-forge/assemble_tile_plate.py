#!/usr/bin/env python3
"""타일형 허브 조립 — 배경 + 타일 액자 + 아이콘 + 라벨을 코드가 앉힌다.

assemble_plate 의 타일판이다. 다른 점은 셋뿐이다.
  · 액자가 두 종류다 — 큰 타일(3열x2행)과 작은 칸(1칸).
  · 타일 안에 **아이콘과 글자**가 들어간다. 아이콘은 따로 받고, 글자는 여기서 굽는다
    (발주 글자는 폰트·자간이 매번 달라 판마다 따로 논다).
  · 아이콘 자리는 액자 구멍에서 아래 라벨 띠를 뺀 만큼이다.

사용: python3 assemble_tile_plate.py <허브이름>
산출: src/<이름>/bg_source.png (+ .assembled 마커)
"""
import os
import sys

from PIL import Image, ImageDraw, ImageFont

import assemble_plate as A
import build_plate
import make_page_layouts as L
import make_tile_order as T

HERE = os.path.dirname(os.path.abspath(__file__))
GEN = A.GEN
S, GX, GY, CELL, COLS = L.SCALE, L.GRID_X, L.GRID_Y, L.CELL, L.COLS
FONT_TTF = os.path.expanduser("~/development/barkan-resourcepack/assets/barkan/font/aggro_bold.ttf")
GOLD_HI, INK = (247, 214, 138), (26, 20, 14)

# 허브: 배경 · 큰 타일 액자 · 작은 칸 액자 · {타일 라벨: 아이콘}
PARTS = {
    "guild": {
        "bg": "exec-57c21d2c-03ff-4a64-9235-dafa476562d9.png",     # ★타일 없는 쪽(발주대로)
        "tile": "exec-3d35f90c-1704-427e-8c5c-daca75272d16.png",
        "cell": "exec-6309bb29-dd27-4a14-8776-e710aef25438.png",
        "icons": {
            "길드 섬": "exec-8f6959ac-66be-4aa1-a11d-7911215704b4.png",   # 2026-08-14 교체(전: 79508801 깃발형)
            "업그레이드": "exec-df73fe9a-5ed7-4224-b0b5-ebdb71be8947.png",
            "기부": "exec-1b0b0157-778a-4a03-8564-e8200f088b79.png",
            "길드원": "exec-9966343f-774d-4e3d-90a8-832cbce3edb2.png",
            "랭킹": "exec-635348e0-08fb-4272-8f9c-ada9f036029a.png",
            "엠블럼": "exec-b4679f69-89b3-40f9-83c5-6423a4b2972d.png",
        },
    },
}

# 아이콘은 **타일을 꽉 채우고 글자가 그 위에 얹힌다**. 글자 자리를 따로 비워 두면
# (발주서의 40px 띠) 구멍이 169x96 뿐인 이 액자에서는 아이콘이 36px 짜리 점이 된다.
# 그래서 띠를 없애고 구멍 + 베벨까지 아이콘에 내준 다음, 라벨을 아래쪽에 겹쳐 굽는다.
# 겹쳐도 읽히게 테두리(stroke)를 두껍게 준다 — 그림 위 글자는 stroke 가 전부다.
ICON_PAD = 2
ICON_BLEED = 11                # 구멍 밖(액자 안쪽 베벨)으로 아이콘이 번져도 되는 폭
LABEL_DROP = 2                 # 라벨 밑단을 구멍 아래에서 띄우는 여유
ICON_RISE = 4                  # 아이콘을 살짝 올린다 — 라벨이 주제(아래쪽)를 덜 가리게
SCRIM_H = 42                   # 라벨 뒤에 까는 어둠의 높이
SCRIM_A = 165                  # 그 어둠의 최대 불투명도


def font(px):
    try:
        return ImageFont.truetype(FONT_TTF, px)
    except Exception:
        return ImageFont.load_default()


EDGE_TRIM = 3        # 생성물 가장자리의 비네팅 링
KEY_TOL = 110        # 어두워진 마젠타까지 잡는다
SOLID = 96           # 상자를 잡을 때 '확실히 그림'으로 칠 알파


def sprite(path):
    """마젠타를 지우고 그림만 남긴 RGBA.

    ★상자는 **확실히 불투명한 픽셀**로만 잡는다. 키에서 살아남은 반투명 얼룩까지 세면
      상자가 그쪽으로 늘어나고, 가운데 정렬이 그만큼 밀린다 — 길드 섬 아이콘이 오른쪽으로
      밀려 있던 이유다(알파 무게중심 622 vs 상자중심 442, 2026-08-14 실측).
    """
    raw = Image.open(os.path.join(GEN, path))
    keyed = raw.mode == "RGBA" and raw.getchannel("A").getextrema()[0] < 250
    if keyed:
        im = raw.convert("RGBA")
    else:
        w, h = raw.size
        im = A.dekey(raw.crop((EDGE_TRIM, EDGE_TRIM, w - EDGE_TRIM, h - EDGE_TRIM)), tol=KEY_TOL)
    box = im.getchannel("A").point(lambda v: 255 if v > SOLID else 0).getbbox()
    return im.crop(box) if box else im


def hole_of(im):
    """액자 안쪽 빈 곳(알파 0)의 상자. 아이콘·글자가 들어갈 자리다."""
    a = im.getchannel("A").load()
    w, h = im.size
    cx, cy = w // 2, h // 2
    def go(dx, dy):
        k = 0
        while 0 <= cx + dx * (k + 1) < w and 0 <= cy + dy * (k + 1) < h \
                and a[cx + dx * (k + 1), cy + dy * (k + 1)] < 32:
            k += 1
        return k
    return cx - go(-1, 0), cy - go(0, -1), cx + go(1, 0), cy + go(0, 1)


def fit(im, box_w, box_h):
    """비율 유지로 상자 안에 넣는다."""
    k = min(box_w / im.width, box_h / im.height)
    return im.resize((max(1, round(im.width * k)), max(1, round(im.height * k))), Image.LANCZOS)


def cell_frame(path):
    """작은 칸 액자 — assemble_plate.make_frame 과 같은 계산을, 청소된 스프라이트로."""
    sp = sprite(path)
    hx0, hy0, hx1, hy1 = A.hole_box(sp)
    tw = round(A.PAD_OUT * (hx1 - hx0) / A.ICON)
    th = round(A.PAD_OUT * (hy1 - hy0) / A.ICON)
    cut = sp.crop((max(0, hx0 - tw), max(0, hy0 - th),
                   min(sp.width, hx1 + tw), min(sp.height, hy1 + th)))
    size = A.ICON + 2 * A.PAD_OUT
    print(f"  작은 칸 액자 {sp.size} · 구멍 {hx1-hx0}x{hy1-hy0} → {size}x{size}")
    return cut.resize((size, size), Image.LANCZOS)


def build(name):
    spec = PARTS[name]
    rows = build_plate.PLATES[name][0] if name in build_plate.PLATES else 6
    W, H = 176 * S, (114 + rows * CELL) * S

    bg = Image.open(os.path.join(GEN, spec["bg"])).convert("RGBA")
    if bg.size != (W, H):
        print(f"  배경 {bg.size} → {W}x{H}")
        bg = bg.resize((W, H), Image.LANCZOS)

    # ── 큰 타일 ─────────────────────────────────────────────
    tw, th = CELL * 3 * S, CELL * 2 * S
    tile = sprite(spec["tile"]).resize((tw, th), Image.LANCZOS)
    hx0, hy0, hx1, hy1 = hole_of(tile)
    print(f"  타일 액자 {tw}x{th} · 구멍 ({hx0},{hy0})~({hx1},{hy1})")
    d = ImageDraw.Draw(bg)
    for label, box in T.tile_boxes(name):
        x0, y0 = box[0], box[1]
        bg.alpha_composite(tile, (x0, y0))
        icon = sprite(spec["icons"][label])
        area_w = hx1 - hx0 + 2 * (ICON_BLEED - ICON_PAD)
        area_h = hy1 - hy0 + 2 * (ICON_BLEED - ICON_PAD)
        icon = fit(icon, area_w, area_h)
        cx = x0 + (hx0 + hx1) // 2
        cy = y0 + (hy0 + hy1) // 2
        bg.alpha_composite(icon, (cx - icon.width // 2, cy - icon.height // 2 - ICON_RISE))
        # ★금색 글자가 금색 아이콘 위에 겹치면 게임 크기에서 뭉갠다(실측 — 랭킹 메달·기부
        #   금화가 그랬다). 아이콘은 그대로 두고 글자 아래에만 어둠을 깔아 대비를 만든다.
        #   아래로 갈수록 짙어지는 그라데이션이라 띠처럼 보이지 않는다.
        scrim = Image.new("RGBA", (hx1 - hx0, SCRIM_H), (0, 0, 0, 0))
        sp = scrim.load()
        for yy in range(SCRIM_H):
            a = int(SCRIM_A * (yy / (SCRIM_H - 1)) ** 1.6)
            for xx in range(scrim.width):
                sp[xx, yy] = (12, 9, 7, a)
        bg.alpha_composite(scrim, (x0 + hx0, y0 + hy1 - SCRIM_H))
        # 라벨은 아이콘 **위에** 얹는다. 그림 위 글자라 stroke 가 두꺼워야 읽힌다.
        f = font(26)
        bb = d.textbbox((0, 0), label, font=f, stroke_width=4)
        # ★textbbox 는 (0,0) 기준 상자다 — 높이만 빼면 bb[1] 만큼 위로 뜬다. 밑단을 맞추려면
        #   bb[3] 을 빼야 한다. 그렇게 안 해서 글자가 아이콘 한가운데 걸쳤다(실측).
        d.text((cx - (bb[0] + bb[2]) // 2, y0 + hy1 - LABEL_DROP - bb[3]),
               label, font=f, fill=GOLD_HI, stroke_width=4, stroke_fill=INK)

    # ── 작은 칸(정보칸 · 아래 버튼 줄 · 플레이어 인벤) ────────
    cell = cell_frame(spec["cell"])            # 구멍이 정확히 64px 인 72x72
    def put(gx, gy):
        bg.alpha_composite(cell, (gx * S + A.PAD - A.PAD_OUT, gy * S + A.PAD - A.PAD_OUT))
    _, roles, _ = L.PAGES[name]
    small = sorted(s for s, (r, _) in roles.items() if r != "장식")
    for slot in small:
        r, c = divmod(slot, COLS)
        put(GX + CELL * c, GY + CELL * r)
    inv_y0 = 30 + rows * CELL
    inv_rows = [inv_y0, inv_y0 + CELL, inv_y0 + 2 * CELL, inv_y0 + 58]
    for gy in inv_rows:
        for c in range(COLS):
            put(GX + CELL * c, gy)

    out_dir = os.path.join(HERE, "src", name)
    os.makedirs(out_dir, exist_ok=True)
    bg.convert("RGB").save(os.path.join(out_dir, "bg_source.png"))
    open(os.path.join(out_dir, ".assembled"), "w").write("assemble_tile_plate.py\n")
    print(f"  {name} 타일 {len(L.TILES[name])} + 작은칸 {len(small)} + 인벤 {len(inv_rows) * COLS}"
          f" → {out_dir}/bg_source.png")


if __name__ == "__main__":
    for n in sys.argv[1:] or PARTS:
        build(n)
