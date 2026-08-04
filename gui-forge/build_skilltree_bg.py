#!/usr/bin/env python3
"""특성 트리 **공용** 배경 조립 — 원본 아트에서 프레임·벽면을 떠와 노드/선만 지운다.

★핵심: 노드 소켓·연결선은 배경에 굽지 않는다. 전부 **아이템 아이콘**으로 올린다.
  그래서 3계열/4계열/2페이지 구분이 사라지고 **배경 1장이 모든 트리를 커버**한다.

★2026-08-04 방향 전환: Codex 프레임 조각(9슬라이스)으로 조립했더니 **나무 색이 원본과
  천지차이**였다. 원본 `barkan_skilltree_gui_A_detailrestored5.png` 는 이미 승인된 그림이니
  거기서 프레임·구분밴드·벽면을 그대로 쓰고, 트리 패널의 노드·선만 깨끗한 벽면으로 덮는다.
  (레일을 같은 아트에서 칸 단위로 떠온 것과 같은 원리 — 있는 걸 재료로 쓴다)
  깨끗한 벽면 출처: row0(첫 슬롯 행 위 여백)은 노드·선이 없다 — 측정으로 확인.

## 해상도 = GUI x SCALE (4배 = 704x816)
원본이 2배라 4배는 정수배(2x) 확대다. MC가 GUI 스케일 3에서 1.5배로 늘리는 대신 미리
정수배로 올려두는 것이라 화질 손실이 없다.
★폰트 아틀라스 256px 제한 → 3열 x 4행 = 12타일.
좌표는 GUI 기하에서 SCALE 배로 유도한다(하드코딩 금지).
"""
import json
import os

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "src", "skilltree")
OUTDIR = os.path.expanduser("~/development/barkan-resourcepack/assets/barkan/textures/gui")
SRC_ART = os.path.expanduser("~/Downloads/barkan_skilltree_gui_A_detailrestored5.png")

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
    art = Image.open(SRC_ART).convert("RGBA")
    if art.size != (GW * 2, GH * 2):
        raise SystemExit(f"원본 아트가 2배(352x408)가 아님: {art.size}")

    # ① 트리 패널의 노드·선을 깨끗한 벽면으로 덮는다 (2배 좌표)
    #   ★가로로 타일링하면 벽면의 좌우 명암 기울기가 되풀이돼 세로 이음선이 보인다(1차 시도).
    #     **같은 x에서 세로로만** 복사하면 가로 방향 정보가 원본 그대로라 이음선이 안 생긴다.
    #     원본은 row0(첫 계열 행 위 여백)만 노드·선이 없다 — 측정 확인.
    #     좌우 테두리 발광(x14~19 / x333~337)도 세로로 이어지는 것이라 같이 복사돼야 맞다.
    px0, py0 = 7 * 2, 17 * 2                       # 슬롯 격자 원점
    band = art.crop((px0, py0, px0 + 18 * 2 * 9, py0 + 18 * 2))
    for r in range(1, 5):
        art.paste(band, (px0, py0 + 18 * 2 * r))

    # ② 정수배 확대 (원본 2배 → SCALE배)
    im = art.resize((W, H), Image.NEAREST) if SCALE != 2 else art

    # ③ 플레이어 인벤 36칸 음각
    px = im.load()
    for cy in INV_CELL_Y + [HOTBAR_Y]:
        for c in range(CELL_N):
            slot_cell(px, CELL_X0 + CELL_W * c, cy)

    # ④ 타일 분할 + 폰트 프로바이더·글리프 문자열 산출
    os.makedirs(OUTDIR, exist_ok=True)
    for f in os.listdir(OUTDIR):
        if f.startswith("tree_bg_"):
            os.remove(os.path.join(OUTDIR, f))
    tiles = tile_boxes()
    providers, glyph, code = [], [], 0xE606
    for i, (name, box, gw, gh, (gx, gy)) in enumerate(tiles):
        crop = im.crop(box)
        assert max(crop.size) <= 256, f"{name} {crop.size} — 폰트 아틀라스 256px 초과"
        crop.save(os.path.join(OUTDIR, f"tree_bg_{name}.png"))
        ch = chr(code + i)
        providers.append({"type": "bitmap", "file": f"barkan:gui/tree_bg_{name}.png",
                          "ascent": 13 - gy, "height": gh, "chars": [ch]})
        glyph.append("\\uf801" if i == 0 else ("\\uf803" if gx == 0 else "\\uf802"))
        glyph.append(f"\\u{ord(ch):04x}")
    with open(os.path.join(HERE, "src", "skilltree", "_providers.json"), "w", encoding="utf-8") as f:
        json.dump(providers, f, ensure_ascii=False, indent=2)
    with open(os.path.join(HERE, "src", "skilltree", "_glyph.txt"), "w", encoding="utf-8") as f:
        f.write("".join(glyph))
    im.save(os.path.join(HERE, "src", "skilltree", "_preview_full.png"))
    print(f"tree_bg_* {len(tiles)}타일 저장 ({SCALE}배, 원본 아트 기반)")
    print(f"  타일 {set(t[1][2]-t[1][0] for t in tiles)} x {set(t[1][3]-t[1][1] for t in tiles)}")
    return im


if __name__ == "__main__":
    main()
