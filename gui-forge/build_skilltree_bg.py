#!/usr/bin/env python3
"""특성 트리 **공용** 배경 조립 — 벽면 타일 + 9슬라이스 프레임 + 인벤 칸 → 4타일 글리프.

★핵심: 노드 소켓·연결선은 배경에 굽지 않는다. 전부 **아이템 아이콘**으로 올린다.
  그래서 3계열/4계열/2페이지 구분이 사라지고 **배경 1장이 모든 트리를 커버**한다.
  (기존: 레이아웃별 3장 × 4타일 = 글리프 12개 → 이제 4개)
  레이아웃 변경·새 숙련 추가에 아트 작업이 0이 된다.

## 해상도 = GUI x SCALE (4배 = 704x816)
2배(352x408)면 GUI 스케일 3에서 1.5배 확대돼 흐렸다. 4배면 스케일 3에서 0.75배 축소,
스케일 4에서 정확히 1:1 → 손실 없음.
★폰트 아틀라스 256px 제한 때문에 4배는 4타일로 안 되고 **3열 x 4행 = 12타일**이다.
  열 GUI 59/59/58 (텍스처 236/236/232) · 행 GUI 51 x4 (텍스처 204) — 전부 256 이하.
좌표는 GUI 기하에서 SCALE 배로 유도한다(하드코딩 금지 — 배율 바꿀 때 어긋난다).

프레임 배율은 하나로 통일한다(s = 14 / frame_left 폭) — 조각마다 다른 배율을 쓰면
모서리와 변의 두께가 어긋나 이음선이 보인다.
하단 모서리만 **아래 14px로 잘라 쓴다**: 원래 크기(28px)로 놓으면 핫바 첫 칸을 덮는다.
"""
import json
import os

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "src", "skilltree")
OUTDIR = os.path.expanduser("~/development/barkan-resourcepack/assets/barkan/textures/gui")

SCALE = 4                          # GUI 배율
GW, GH = 176, 204                  # GUI 창 크기
W, H = GW * SCALE, GH * SCALE
SIDE = 7 * SCALE                   # 프레임 두께 (GUI 7px — 슬롯 격자가 x7부터라 고정값)
DIVIDER = (107 * SCALE, 121 * SCALE)          # 구분 밴드 (GUI 107~120)
INV_CELL_Y = [121 * SCALE, 139 * SCALE, 157 * SCALE]
HOTBAR_Y = 179 * SCALE
CELL_X0, CELL_W, CELL_N = 7 * SCALE, 18 * SCALE, 9
# 청록 하이라이트는 격자 와이어처럼 보였다 → 바닐라처럼 무채색 베벨로
CELL_IN, CELL_SH, CELL_HL = (10, 16, 20, 255), (4, 7, 9, 255), (44, 54, 60, 255)
WALL_TILE = 100 * SCALE            # 벽면 텍스처 타일 크기 (배율에 비례 — 격자 눈 크기 유지)

# 타일 격자 — GUI 좌표 경계(합이 정확히 176 / 204 여야 한다)
COL_GUI = [59, 59, 58]
ROW_GUI = [51, 51, 51, 51]


def tile_boxes():
    """(이름, 텍스처box, GUI폭, GUI높이, GUI좌상단) 목록."""
    out, gy = [], 0
    for r, gh in enumerate(ROW_GUI):
        gx = 0
        for c, gw in enumerate(COL_GUI):
            out.append((f"r{r}c{c}",
                        (gx * SCALE, gy * SCALE, (gx + gw) * SCALE, (gy + gh) * SCALE),
                        gw, gh, (gx, gy)))
            gx += gw
        gy += gh
    return out


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

    # ⑤ 타일 분할 + 폰트 프로바이더·글리프 문자열 산출
    os.makedirs(OUTDIR, exist_ok=True)
    tiles = tile_boxes()
    providers, glyph, code = [], [], 0xE606
    for i, (name, box, gw, gh, (gx, gy)) in enumerate(tiles):
        crop = im.crop(box)
        assert max(crop.size) <= 256, f"{name} {crop.size} — 폰트 아틀라스 256px 초과"
        crop.save(os.path.join(OUTDIR, f"tree_bg_{name}.png"))
        ch = chr(code + i)
        providers.append({"type": "bitmap", "file": f"barkan:gui/tree_bg_{name}.png",
                          "ascent": 13 - gy, "height": gh, "chars": [ch]})
        # 행 시작이면 복귀 오프셋, 그 외엔 -1 (advance = round(폭)+1 이라 1px 겹침 보정)
        glyph.append("\\uf801" if i == 0 else ("\\uf803" if gx == 0 else "\\uf802"))
        glyph.append(f"\\u{ord(ch):04x}")
    with open(os.path.join(HERE, "src", "skilltree", "_providers.json"), "w", encoding="utf-8") as f:
        json.dump(providers, f, ensure_ascii=False, indent=2)
    with open(os.path.join(HERE, "src", "skilltree", "_glyph.txt"), "w", encoding="utf-8") as f:
        f.write("".join(glyph))
    print(f"tree_bg_* {len(tiles)}타일 저장 ({SCALE}배, 프레임 배율 {s:.4f})")
    print(f"  타일 크기: {set(t[1][2]-t[1][0] for t in tiles)} x {set(t[1][3]-t[1][1] for t in tiles)}")
    print(f"  프로바이더/글리프 → src/skilltree/_providers.json, _glyph.txt")
    im.save(os.path.join(HERE, "src", "skilltree", "_preview_full.png"))
    return im


if __name__ == "__main__":
    main()
