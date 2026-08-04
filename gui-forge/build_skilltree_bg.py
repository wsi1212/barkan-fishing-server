#!/usr/bin/env python3
"""특성 트리 **공용** 배경 조립 — 벽면 타일 + 9슬라이스 프레임 + 인벤 칸 → 4타일 글리프.

★핵심: 노드 소켓·연결선은 배경에 굽지 않는다. 전부 **아이템 아이콘**으로 올린다.
  그래서 3계열/4계열/2페이지 구분이 사라지고 **배경 1장이 모든 트리를 커버**한다.
  (기존: 레이아웃별 3장 × 4타일 = 글리프 12개 → 이제 4개)
  레이아웃 변경·새 숙련 추가에 아트 작업이 0이 된다.

좌표는 전부 2배(캔버스 352x408 = GUI 176x204). GUI 기하 그대로 유도한 값:
  · 좌우 프레임 x0~13 / x338~351      (GUI 7px)
  · 상단 프레임 y0~13                  (GUI 상단 여유는 17px이나 밴드는 7px만)
  · 트리 패널(9x5 슬롯) y34~213        (= 5행 x 36)
  · 구분 밴드 y214~241                 (GUI 107~120)
  · 인벤 3행 y242~349 / 여백 y350~357 / 핫바 y358~393
  · 하단 프레임 y394~407

프레임 배율은 하나로 통일한다(s = 14 / frame_left 폭) — 조각마다 다른 배율을 쓰면
모서리와 변의 두께가 어긋나 이음선이 보인다.
하단 모서리만 **아래 14px로 잘라 쓴다**: 원래 크기(28px)로 놓으면 핫바 첫 칸을 덮는다.
"""
import os

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "src", "skilltree")
OUTDIR = os.path.expanduser("~/development/barkan-resourcepack/assets/barkan/textures/gui")

W, H = 352, 408
SIDE = 14                          # 좌우/상하 프레임 두께 (2배)
PANEL = (14, 34, 338, 214)         # 트리 패널 (x0,y0,x1,y1)
DIVIDER = (214, 242)               # 구분 밴드 y구간
INV_CELL_Y = [242, 278, 314]       # 인벤 3행 칸 top — 36px 간격
HOTBAR_Y = 358
CELL_X0, CELL_W, CELL_N = 14, 36, 9
# 청록 하이라이트는 격자 와이어처럼 보였다 → 바닐라처럼 무채색 베벨로
CELL_IN, CELL_SH, CELL_HL = (10, 16, 20, 255), (4, 7, 9, 255), (44, 54, 60, 255)
WALL_TILE = 400                    # 벽면 텍스처를 이 크기로 줄여 타일링 (격자 눈이 커지지 않게)

TILES = [("tl", (0, 0, 194, 214)), ("tr", (194, 0, 352, 214)),
         ("bl", (0, 214, 194, 408)), ("br", (194, 214, 352, 408))]


def load(name):
    return Image.open(os.path.join(SRC, name + ".png")).convert("RGBA")


def fit_h(im, h):
    return im.resize((max(1, round(im.width * h / im.height)), h), Image.LANCZOS)


def fit_w(im, w):
    return im.resize((w, max(1, round(im.height * w / im.width))), Image.LANCZOS)


def tile_into(dst, tex, box):
    """box 영역을 tex로 타일링 (seamless 텍스처 전제)."""
    x0, y0, x1, y1 = box
    for y in range(y0, y1, tex.height):
        for x in range(x0, x1, tex.width):
            part = tex.crop((0, 0, min(tex.width, x1 - x), min(tex.height, y1 - y)))
            dst.paste(part, (x, y))


def tile_strip_h(dst, tex, x0, x1, y, cap=0.22):
    """가로 변 조각을 3슬라이스로 깐다 — 양끝 캡 + 가운데만 반복.

    ★조각을 통째로 반복하면 조각 양끝의 볼트/마감이 같이 반복돼 "여러 판을 이어붙인"
      티가 난다(1차 렌더에서 구분 밴드가 4토막으로 보였다). 가운데 띠만 반복한다.
    """
    cw = max(1, int(tex.width * cap))
    lcap, mid, rcap = tex.crop((0, 0, cw, tex.height)), \
        tex.crop((cw, 0, tex.width - cw, tex.height)), \
        tex.crop((tex.width - cw, 0, tex.width, tex.height))
    span = x1 - x0
    if span <= 2 * cw:
        dst.alpha_composite(tex.crop((0, 0, span, tex.height)), (x0, y)); return
    dst.alpha_composite(lcap, (x0, y))
    x = x0 + cw
    end = x1 - cw
    while x < end:
        dst.alpha_composite(mid.crop((0, 0, min(mid.width, end - x), mid.height)), (x, y))
        x += mid.width
    dst.alpha_composite(rcap, (end, y))


def tile_strip_v(dst, tex, y0, y1, x, cap=0.22):
    """세로 변 — 가로와 같은 3슬라이스."""
    ch = max(1, int(tex.height * cap))
    tcap, mid, bcap = tex.crop((0, 0, tex.width, ch)), \
        tex.crop((0, ch, tex.width, tex.height - ch)), \
        tex.crop((0, tex.height - ch, tex.width, tex.height))
    span = y1 - y0
    if span <= 2 * ch:
        dst.alpha_composite(tex.crop((0, 0, tex.width, span)), (x, y0)); return
    dst.alpha_composite(tcap, (x, y0))
    y = y0 + ch
    end = y1 - ch
    while y < end:
        dst.alpha_composite(mid.crop((0, 0, mid.width, min(mid.height, end - y))), (x, y))
        y += mid.height
    dst.alpha_composite(bcap, (x, end))


def slot_cell(px, x0, y0):
    """플레이어 인벤 칸 음각 — 2배라 테두리 2px = GUI 1px."""
    for y in range(y0, y0 + CELL_W):
        for x in range(x0, x0 + CELL_W):
            px[x, y] = CELL_IN
    for k in range(2):
        for x in range(x0, x0 + CELL_W):
            px[x, y0 + k] = CELL_SH
            px[x, y0 + CELL_W - 1 - k] = CELL_HL
        for y in range(y0, y0 + CELL_W):
            px[x0 + k, y] = CELL_SH
            px[x0 + CELL_W - 1 - k, y] = CELL_HL


def main():
    im = Image.new("RGBA", (W, H), (0, 0, 0, 255))

    # ① 벽면: 프레임 안쪽 전체를 타일링
    wall = Image.open(os.path.join(SRC, "wall_plate.png")).convert("RGBA")
    wall = wall.resize((WALL_TILE, WALL_TILE), Image.LANCZOS)
    tile_into(im, wall, (SIDE, SIDE, W - SIDE, H - SIDE))

    # ② 프레임 9슬라이스 — 배율 하나로 통일
    left, right = load("frame_left"), load("frame_right")
    s = SIDE / left.width
    left, right = fit_w(left, SIDE), fit_w(right, SIDE)
    top, bottom = fit_h(load("frame_top"), SIDE), fit_h(load("frame_bottom"), SIDE)

    tile_strip_v(im, left, 0, H, 0)
    tile_strip_v(im, right, 0, H, W - SIDE)
    tile_strip_h(im, top, SIDE, W - SIDE, 0)
    tile_strip_h(im, bottom, SIDE, W - SIDE, H - SIDE)

    # 모서리는 변 위에 덮어 이음선을 가린다
    for name, pos, crop_bottom in (("frame_tl", "tl", False), ("frame_tr", "tr", False),
                                   ("frame_bl", "bl", True), ("frame_br", "br", True)):
        c = load(name)
        c = c.resize((max(1, round(c.width * s)), max(1, round(c.height * s))), Image.LANCZOS)
        if crop_bottom:
            # 원래 높이(28px)로 놓으면 핫바 첫 칸을 덮는다 → 아래 14px만 쓴다
            c = c.crop((0, c.height - SIDE, c.width, c.height))
        x = 0 if pos in ("tl", "bl") else W - c.width
        y = 0 if pos in ("tl", "tr") else H - c.height
        im.alpha_composite(c, (x, y))

    # ③ 구분 밴드 — 상단 변 조각을 재사용(볼트·글로우선 그대로)
    band = fit_h(load("frame_top"), DIVIDER[1] - DIVIDER[0])
    tile_strip_h(im, band, SIDE, W - SIDE, DIVIDER[0])

    # ④ 플레이어 인벤 36칸 음각
    px = im.load()
    for cy in INV_CELL_Y + [HOTBAR_Y]:
        for c in range(CELL_N):
            slot_cell(px, CELL_X0 + CELL_W * c, cy)

    # ⑤ 4타일 분할 (폰트 아틀라스 256px 제한)
    os.makedirs(OUTDIR, exist_ok=True)
    for suf, box in TILES:
        im.crop(box).save(os.path.join(OUTDIR, f"tree_bg_{suf}.png"))
    print(f"tree_bg_* 4타일 저장 (프레임 배율 {s:.4f})")
    im.save(os.path.join(HERE, "src", "skilltree", "_preview_full.png"))
    return im


if __name__ == "__main__":
    main()
