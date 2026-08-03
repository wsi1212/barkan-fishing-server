#!/usr/bin/env python3
"""특성 트리 GUI 배경 — 원본 아트의 각 요소를 뜯어 45칸 창(176x204)으로 재조립 (2배).

소스: gui-forge/src/skilltree_fan.png (근원+계열) / skilltree_col.png (2페이지, 좌측 진입)
산출: assets/barkan/textures/gui/tree_{4br,3br,p2}_{tl,tr,bl,br}.png

── 재조립 원칙 ──────────────────────────────────────────────────────
확산 모델은 픽셀 격자를 못 맞춘다(실측 노드 간격 가로 28·세로 25px, 필요값 36·18px).
그래서 "다시 그리기"가 아니라 "뜯어 붙이기":
  ① 창 프레임(나무+모서리 철제) = 9-slice, 모서리는 통째 축소(전단 방지)
  ② 패널 = 9-slice. 모서리 블록에 청록 보더와 코너 필리그리가 같이 들어있어 통째로 옮겨진다.
     가운데는 원본의 **노드 없는 벽 조각을 미러 타일링** → 벽 노이즈 보존
     (평면 단색 채움은 질감이 통째로 날아간다 — 앞선 시안들의 실패 원인)
  ③ 구분바 = 가로만 늘리고 좌우 끝 조각 유지
  ④ 노드·근원 = 스프라이트로 뽑아 **칸 중심 기준** 배치. 18px 칸에 억지로 넣지 않는다
     (넣으면 근원 뿔이 잘린다) → 24~28px, 이웃 칸은 화살표 자리라 넘쳐도 무해
  ⑤ 연결선 = 원본 선 조각을 **노드 사이 빈 구간만** 채운다(노드를 관통하지 않게)

── 창 규격 (45칸 = 176x204) ────────────────────────────────────────
칸 = (7+18*col, 17+18*row) 18x18 / 칸 중심 = (16+18*col, 26+18*row)
  UI 행 y17~34(슬롯 0·1·4·7·8) · 계열 행 35~52 / 53~70 / 71~88 / 89~106
  근원 = 슬롯 18(col0,row2) · 구분 107~119 · 인벤 120~173 · 핫바 178~195 · 하단 196~203
  2페이지 = 계열 잭팟(슬롯 11·20·29·38 = col2) — 근원 없이 **왼쪽에서 선이 들어온다**
  (1페이지에서 이어지는 느낌. 화살표 아이템도 슬롯 10/19/28/37에 렌더된다)

── 타일 (256 아틀라스 회피) ────────────────────────────────────────
2배 352x408, 이음선 x=97 / y=107 → 194x214 / 158x214 / 194x194 / 158x194
  advance = round(폭 x height/높이) + 1 = 98 / 80 · ascent 13(위) / -94(아래)
"""
import os

from PIL import Image, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
OUTDIR = os.path.expanduser("~/development/barkan-resourcepack/assets/barkan/textures/gui")
SCALE = 2
GW, GH = 176, 204
TW, TH = GW * SCALE, GH * SCALE

T_FRAME_TOP, T_FRAME = 17, 7
T_PANEL_UP = (7, 15, 169, 107)
T_DIVIDER = (7, 107, 169, 120)
T_PANEL_LO = (7, 120, 169, 197)

S_FRAME_CORNER, S_FRAME_TOP = 330, 175
S_PANEL_UP = (78, 150, 1086, 812)
S_DIVIDER = (78, 815, 1086, 911)
S_PANEL_LO = (78, 914, 1086, 1300)
S_PANEL_CORNER = 150   # ★버스선 꺾임(x250) 앞까지만 — 넘기면 반전된 갈고리 잔상이 우측에 붙는다
S_WALL_UP = (400, 306, 1000, 360)
S_WALL_LO = (300, 1000, 1000, 1120)

GEO = {"fan": {"cols": [397, 589, 774, 966], "rows": [252, 417, 583, 735], "r": 53,
               "root": (152, 417), "line_y": 417, "line_x": (460, 526)},
       "col": {"cols": [350], "rows": [295, 437, 583, 722], "r": 53,
               "root": None, "line_y": 295, "line_x": (150, 260)}}
NODE_COLS = [2, 4, 6, 8]
ROOT_ROW = 2
INV_Y = [121, 139, 157]
HOTBAR_Y = 179
NODE_G, ROOT_G = 20, 28   # 행 간격이 18px이라 노드는 20px까지 (근원은 위아래가 비어 28px 가능)
CELL_IN, CELL_SH, CELL_HL = (10, 20, 26, 255), (4, 10, 13, 255), (24, 60, 66, 255)
KEY_LUM = 22
TILES = [("tl", (0, 0), (97, 107)), ("tr", (97, 0), (79, 107)),
         ("bl", (0, 107), (97, 97)), ("br", (97, 107), (79, 97))]


def wall_plate(src, box, w, h):
    """벽 조각을 미러 타일링 — 노이즈 질감 보존 + 이음선 안 보이게."""
    tile = src.crop(box)
    tw, th = tile.size
    fl = {(0, 0): tile, (1, 0): tile.transpose(Image.FLIP_LEFT_RIGHT),
          (0, 1): tile.transpose(Image.FLIP_TOP_BOTTOM),
          (1, 1): tile.transpose(Image.FLIP_LEFT_RIGHT).transpose(Image.FLIP_TOP_BOTTOM)}
    out = Image.new("RGBA", (w, h))
    for j, y in enumerate(range(0, h, th)):
        for i, x in enumerate(range(0, w, tw)):
            out.paste(fl[(i % 2, j % 2)], (x, y))
    return out


def nine_slice(src, sbox, tbox, corner, edge, wall=None):
    sx0, sy0, sx1, sy1 = sbox
    tx0, ty0, tx1, ty1 = [v * SCALE for v in tbox]
    tw, th = tx1 - tx0, ty1 - ty0
    # 소스 모서리는 밴드 크기의 절반을 넘을 수 없다(구분바는 높이 96px뿐)
    c = min(corner, (sx1 - sx0) // 2 - 1, (sy1 - sy0) // 2 - 1)
    ct = max(2, round(c * tw / (sx1 - sx0)))
    # ★변 스트립 깊이는 모서리와 따로 잡는다. 모서리만큼(210px) 깊게 잡으면 원본 1행 노드가
    #   스트립에 딸려와 늘어나면서 유령 노드가 생긴다(v6 실패). 보더 두께만 얕게 뜬다.
    e = min(edge, c)
    et = max(2, round(e * tw / (sx1 - sx0)))
    ct = min(ct, tw // 2 - 1, th // 2 - 1)
    layer = Image.new("RGBA", (tw, th))
    if wall is not None:
        layer.paste(wall_plate(src, wall, tw, th), (0, 0))
    else:
        layer.paste(src.crop((sx0 + c, sy0, sx1 - c, sy1)).resize((tw, th), Image.LANCZOS), (0, 0))
    # ★오른쪽 모서리는 왼쪽 블록을 좌우 반전해서 쓴다. 원본 오른쪽 모서리에는 4열 노드(x966)가
    #   걸려 있어 그대로 뜨면 유령 노드가 생긴다(v7 실패). 필리그리는 좌우 대칭이라 반전이 자연스럽다.
    for sb, tb, flip in [((sx0, sy0, sx0 + c, sy0 + c), (0, 0, ct, ct), 0),
                         ((sx0, sy0, sx0 + c, sy0 + c), (tw - ct, 0, tw, ct), 1),
                         ((sx0, sy1 - c, sx0 + c, sy1), (0, th - ct, ct, th), 0),
                         ((sx0, sy1 - c, sx0 + c, sy1), (tw - ct, th - ct, tw, th), 1),
                         ((sx0 + c, sy0, sx1 - c, sy0 + e), (ct, 0, tw - ct, et), 0),
                         ((sx0 + c, sy1 - e, sx1 - c, sy1), (ct, th - et, tw - ct, th), 0),
                         ((sx0, sy0 + c, sx0 + e, sy1 - c), (0, ct, et, th - ct), 0),
                         ((sx0, sy0 + c, sx0 + e, sy1 - c), (tw - et, ct, tw, th - ct), 1)]:
        w, h = tb[2] - tb[0], tb[3] - tb[1]
        if w > 0 and h > 0:
            piece = src.crop(sb)
            if flip:
                piece = piece.transpose(Image.FLIP_LEFT_RIGHT)
            layer.alpha_composite(piece.resize((w, h), Image.LANCZOS), (tb[0], tb[1]))
    return layer, (tx0, ty0)


def build_frame(src, out):
    sw, sh = src.size
    c, t, tt, ts = S_FRAME_CORNER, T_FRAME * SCALE, T_FRAME_TOP * SCALE, S_FRAME_TOP
    for sb, tb in [((0, 0, c, ts), (0, 0, t, tt)), ((sw - c, 0, sw, ts), (TW - t, 0, TW, tt)),
                   ((0, sh - c, c, sh), (0, TH - t, t, TH)),
                   ((sw - c, sh - c, sw, sh), (TW - t, TH - t, TW, TH)),
                   ((c, 0, sw - c, ts), (t, 0, TW - t, tt)),
                   ((c, sh - c, sw - c, sh), (t, TH - t, TW - t, TH)),
                   ((0, ts, c, sh - c), (0, tt, t, TH - t)),
                   ((sw - c, ts, sw, sh - c), (TW - t, tt, TW, TH - t))]:
        out.paste(src.crop(sb).resize((tb[2] - tb[0], tb[3] - tb[1]), Image.LANCZOS), (tb[0], tb[1]))


def sprite(src, cx, cy, r, g):
    im = src.crop((cx - r, cy - r, cx + r, cy + r)).resize((g * SCALE,) * 2, Image.LANCZOS)
    im = im.filter(ImageFilter.UnsharpMask(radius=1, percent=110, threshold=1))
    px = im.load()
    for y in range(im.height):
        for x in range(im.width):
            a, b, c2, _ = px[x, y]
            lum = (a * 2 + b * 5 + c2) // 8
            px[x, y] = (a, b, c2, max(0, min(255, (lum - KEY_LUM) * 5)))
    return im


def line_sprites(src, geo):
    y, (x0, x1) = geo["line_y"], geo["line_x"]
    seg = src.crop((x0, y - 14, x1, y + 15))
    h = max(2, round(29 * SCALE * GW / 1164))
    return seg.resize((32, h), Image.LANCZOS), seg.rotate(90, expand=True).resize((h, 32), Image.LANCZOS)


def slot_cell(px, gx, gy):
    x0, y0, n = gx * SCALE, gy * SCALE, 18 * SCALE
    for y in range(y0, y0 + n):
        for x in range(x0, x0 + n):
            px[x, y] = CELL_IN
    for k in range(SCALE):
        for x in range(x0, x0 + n):
            px[x, y0 + k] = CELL_SH
            px[x, y0 + n - 1 - k] = CELL_HL
        for y in range(y0, y0 + n):
            px[x0 + k, y] = CELL_SH
            px[x0 + n - 1 - k, y] = CELL_HL


def main():
    jobs = [("4br", "skilltree_fan.png", "fan", [1, 2, 3, 4], NODE_COLS, True),
            ("3br", "skilltree_fan.png", "fan", [1, 2, 3], NODE_COLS, True),
            ("p2", "skilltree_col.png", "col", [1, 2, 3, 4], [2], False)]
    for key, fname, gk, rows, cols, has_root in jobs:
        src = Image.open(os.path.join(HERE, "src", fname)).convert("RGBA")
        geo = GEO[gk]
        base = Image.new("RGBA", (TW, TH), (0, 0, 0, 255))
        build_frame(src, base)
        for sbox, tbox, wall in ((S_PANEL_UP, T_PANEL_UP, S_WALL_UP),
                                 (S_DIVIDER, T_DIVIDER, None),
                                 (S_PANEL_LO, T_PANEL_LO, S_WALL_LO)):
            layer, pos = nine_slice(src, sbox, tbox,
                                    S_PANEL_CORNER if wall else 120, 44, wall)
            base.alpha_composite(layer, pos)
        base = base.filter(ImageFilter.UnsharpMask(radius=1.1, percent=75, threshold=2))

        hseg, vseg = line_sprites(src, geo)
        ccx = lambda col: 16 + 18 * col
        ccy = lambda row: 26 + 18 * row
        half = NODE_G // 2

        def hline(xa, xb, gy):
            if xb - xa >= 2:
                base.alpha_composite(hseg.resize(((xb - xa) * SCALE, hseg.height), Image.LANCZOS),
                                     (xa * SCALE, gy * SCALE - hseg.height // 2))

        def vline(ya, yb, gx):
            if yb - ya >= 2:
                base.alpha_composite(vseg.resize((vseg.width, (yb - ya) * SCALE), Image.LANCZOS),
                                     (gx * SCALE - vseg.width // 2, ya * SCALE))

        if has_root:
            bus = ccx(1)
            vline(ccy(rows[0]), ccy(rows[-1]), bus)
            hline(ccx(0) + half, bus, ccy(ROOT_ROW))
            for r in rows:
                hline(bus, ccx(cols[0]) - half, ccy(r))
        else:
            for r in rows:
                hline(T_PANEL_UP[0] + 2, ccx(cols[0]) - half, ccy(r))
        for r in rows:
            for i in range(len(cols) - 1):
                hline(ccx(cols[i]) + half, ccx(cols[i + 1]) - half, ccy(r))

        px = base.load()
        for gy in INV_Y + [HOTBAR_Y]:
            for c in range(9):
                slot_cell(px, 7 + 18 * c, gy - 1)

        node = sprite(src, geo["cols"][0], geo["rows"][1], geo["r"], NODE_G)
        for r in rows:
            for c in cols:
                base.alpha_composite(node, (ccx(c) * SCALE - node.width // 2,
                                            ccy(r) * SCALE - node.height // 2))
        if has_root and geo["root"]:
            rt = sprite(src, geo["root"][0], geo["root"][1], geo["r"], ROOT_G)
            base.alpha_composite(rt, (ccx(0) * SCALE - rt.width // 2,
                                      ccy(ROOT_ROW) * SCALE - rt.height // 2))

        for suf, (tx, ty), (tw, th) in TILES:
            base.crop((tx * SCALE, ty * SCALE, (tx + tw) * SCALE, (ty + th) * SCALE)) \
                .save(os.path.join(OUTDIR, f"tree_{key}_{suf}.png"))
        print(f"  tree_{key}_* 4타일 저장")


if __name__ == "__main__":
    main()
