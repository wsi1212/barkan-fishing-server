#!/usr/bin/env python3
"""공용 6행 배경 조립 — 54칸 GUI 44개가 공유하는 한 벌.

## 공유판이라 넣지 않는 것
버튼 홈·칸 구분선은 **화면마다 위치가 달라** 여기 굽지 않는다. 구우면 다른 화면에서
엉뚱한 자리에 홈이 남는다. 버튼은 아이템으로 올라가므로 홈이 없어도 동작에 지장 없다.
(판매창처럼 화면 전용 배경이면 그쪽 빌더에서 draw_button_recess 로 파낸다.)

## 넣는 것
플레이어 인벤 격자 — 이건 **모든 54칸 GUI가 동일**하므로 공유판에 구워도 안전하다.

입력:  src/common6/bg_source.png   704x888 불투명 (fit_plate.py 산출)
산출:  <RP>/assets/barkan/textures/gui/common6_r{0..3}c{0..2}.png (12타일)
       gui.json provider 병합(멱등) + src/.../_glyph.txt, _preview_full.png
"""
import json
import os

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "src", "common6")
RP = os.path.expanduser("~/development/barkan-resourcepack")
OUTDIR = os.path.join(RP, "assets/barkan/textures/gui")
FONT_JSON = os.path.join(RP, "assets/barkan/font/gui.json")

SCALE = 4
GW, ROWS = 176, 6
GH = 114 + ROWS * 18                   # 222
W, H = GW * SCALE, GH * SCALE          # 704 x 888

GRID_X, GRID_Y, CELL, COLS = 7, 17, 18, 9
# ★30 이다 — 139/197 은 아이템 좌표이고 셀 좌상단은 그보다 1 GUI px 위다(진열칸이
#   GRID_Y=17, 아이템 18 인 것과 같은 관계). 31 로 두면 인벤 격자가 4px 밀린다.
INV_Y0 = 30 + ROWS * CELL              # 138
INV_ROWS_Y = [INV_Y0, INV_Y0 + CELL, INV_Y0 + 2 * CELL]
HOTBAR_Y = INV_Y0 + 58                 # 197

COL_GUI = [59, 59, 58]                 # 합 176
ROW_GUI = [56, 56, 55, 55]             # 합 222 (타일 224/224/220/220px ≤ 256)
CODE0 = 0xE660                         # E620~E643 낚시창, E650~E658 판매창이 사용 중
TILE_PREFIX = "common6_"
CELL_IN, CELL_GRID = (10, 16, 20, 255), (26, 36, 42, 255)


def tiles():
    out, gy = [], 0
    for r, gh in enumerate(ROW_GUI):
        gx = 0
        for c, gw in enumerate(COL_GUI):
            out.append((f"r{r}c{c}", (gx * SCALE, gy * SCALE, (gx + gw) * SCALE, (gy + gh) * SCALE),
                        gw, gh, gx, gy))
            gx += gw
        gy += gh
    return out


def draw_inventory(im, slot_path=None):
    """플레이어 인벤토리 3줄+핫바를 실제 18 GUI px 슬롯으로 합성한다.

    ``slot_path``가 있으면 ImageGen으로 받은 단일 72x72 art px 슬롯을 반복하고,
    없으면 기존 공용판의 단순 격자를 유지한다.
    """
    px = im.load()
    n = CELL * SCALE
    if slot_path:
        slot = Image.open(slot_path).convert("RGBA")
        assert slot.size == (n, n), f"슬롯 텍스처 {slot.size} != {(n, n)}"
        for gy in INV_ROWS_Y + [HOTBAR_Y]:
            for c in range(COLS):
                im.alpha_composite(slot, ((GRID_X + CELL * c) * SCALE, gy * SCALE))
        return

    # ★경계선은 좌표당 한 번만 — 칸마다 사각형을 그리면 내부선이 두 배로 두꺼워진다.
    for gy in INV_ROWS_Y + [HOTBAR_Y]:
        for c in range(COLS):
            bx, by = (GRID_X + CELL * c) * SCALE, gy * SCALE
            for y in range(by, by + n):
                for x in range(bx, bx + n):
                    px[x, y] = CELL_IN
    cols_x = [(GRID_X + CELL * c) * SCALE for c in range(COLS)]
    for block in (INV_ROWS_Y, [HOTBAR_Y]):
        rows_y = [y * SCALE for y in block]
        t = max(1, SCALE // 2)
        for lx in cols_x + [cols_x[-1] + n]:
            for k in range(t):
                x = lx - t // 2 + k
                for y in range(rows_y[0], rows_y[-1] + n):
                    px[x, y] = CELL_GRID
        for ly in rows_y + [rows_y[-1] + n]:
            for k in range(t):
                y = ly - t // 2 + k
                for x in range(cols_x[0], cols_x[-1] + n):
                    px[x, y] = CELL_GRID


def merge_providers(new):
    d = json.load(open(FONT_JSON, encoding="utf-8"))
    kept = [p for p in d["providers"] if TILE_PREFIX not in str(p.get("file", ""))]
    d["providers"] = kept + new
    json.dump(d, open(FONT_JSON, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    return len(kept)


def main():
    im = Image.open(os.path.join(SRC, "bg_source.png")).convert("RGBA")
    assert im.size == (W, H), f"배경판 크기 {im.size} != {(W, H)}"
    draw_inventory(im)

    os.makedirs(OUTDIR, exist_ok=True)
    for f in os.listdir(OUTDIR):
        if f.startswith(TILE_PREFIX):
            os.remove(os.path.join(OUTDIR, f))
    provs, glyph = [], []
    for i, (name, box, gw, gh, gx, gy) in enumerate(tiles()):
        crop = im.crop(box)
        assert max(crop.size) <= 256, f"{name} {crop.size} — 아틀라스 256px 초과"
        crop.save(os.path.join(OUTDIR, f"{TILE_PREFIX}{name}.png"))
        ch = chr(CODE0 + i)
        provs.append({"type": "bitmap", "file": f"barkan:gui/{TILE_PREFIX}{name}.png",
                      "ascent": 13 - gy, "height": gh, "chars": [ch]})
        glyph.append("\\uf801" if i == 0 else ("\\uf803" if gx == 0 else "\\uf802"))
        glyph.append(f"\\u{ord(ch):04x}")
    kept = merge_providers(provs)
    open(os.path.join(SRC, "_glyph.txt"), "w", encoding="utf-8").write("".join(glyph))
    im.save(os.path.join(SRC, "_preview_full.png"))
    print(f"  타일 {len(provs)}개 → {OUTDIR}")
    print(f"  gui.json: 기존 {kept}개 보존 + {len(provs)}개 등록 "
          f"(U+{CODE0:04X}~U+{CODE0 + len(provs) - 1:04X})")
    print(f"  글리프 → {os.path.join(SRC, '_glyph.txt')}")


if __name__ == "__main__":
    main()
