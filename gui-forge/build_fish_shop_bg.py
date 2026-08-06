#!/usr/bin/env python3
"""물고기 판매창 배경 조립 — 좌판 칸 구분선 + 인벤 격자를 좌표 계산으로 얹는다.

낚시 성공 창과 달리 소켓·광휘·등급 티어가 없다. 여긴 유저가 물고기를 올려놓는
**좌판**이라 칸이 따로 도드라질 필요가 없고, 배경 한 벌이면 된다.
그림에는 칸 구분선을 그리지 않는다 — 18px 격자에 픽셀 단위로 맞아야 해서
그림 작업이 감당할 정밀도가 아니다(낚시창에서 4장 연속 실패한 그 문제).

입력:  src/fish_shop/bg_source.png   704x744 불투명 (프레임·헤더·좌판·구분선)
산출:  <RP>/assets/barkan/textures/gui/shop_bg_r{0..2}c{0..2}.png (9타일)
       gui.json provider 병합(멱등) + src/.../_glyph.txt, _preview_full.png
"""
import json
import os

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "src", "fish_shop")
RP = os.path.expanduser("~/development/barkan-resourcepack")
OUTDIR = os.path.join(RP, "assets/barkan/textures/gui")
FONT_JSON = os.path.join(RP, "assets/barkan/font/gui.json")

SCALE = 4
GW, ROWS = 176, 4
GH = 114 + ROWS * 18                   # 186
W, H = GW * SCALE, GH * SCALE          # 704 x 744

GRID_X, GRID_Y, CELL, COLS = 7, 17, 18, 9
INV_Y0 = 31 + ROWS * CELL              # 103
INV_ROWS_Y = [INV_Y0, INV_Y0 + CELL, INV_Y0 + 2 * CELL]
HOTBAR_Y = INV_Y0 + 58                 # 161

COL_GUI = [59, 59, 58]                 # 합 176
ROW_GUI = [62, 62, 62]                 # 합 186 (타일 248px ≤ 아틀라스 256)
CODE0 = 0xE650                         # E620~E643 은 낚시 성공 창이 사용 중
TILE_PREFIX = "shop_bg_"
CELL_IN, CELL_GRID = (10, 16, 20, 255), (26, 36, 42, 255)

# 물고기 투입칸 = 가운데 두 행의 1~7열. 자바 SellGuiListener.INPUT_SLOTS 와 일치해야 한다.
INPUT_SLOTS = list(range(10, 17)) + list(range(19, 26))
# ★홈 진하기 — 90 으로는 좌판 나뭇결이 촘촘해지자 완전히 묻혔다(2026-08-07 2차 납품).
#   칸 경계가 안 보이면 어디에 올려야 하는지 알 수 없으니 대비를 올린다.
GROOVE = (0, 0, 0, 150)                # 좌판 칸 구분 홈 — 나뭇결이 비치게 반투명
GROOVE_HI = (255, 255, 255, 40)        # 홈 아래쪽 하이라이트(파인 느낌)

# 버튼 자리(전부판매·닫기) — 2차 납품에서 명판이 빠져 버튼이 허공에 뜬다. 우리가 홈을 판다.
BTN_SLOTS = [31, 35]
BTN_FILL = (0, 0, 0, 110)
BTN_EDGE = (0, 0, 0, 180)
BTN_HI = (255, 255, 255, 34)


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


def draw_tray_grooves(im):
    """좌판 안쪽 칸 경계에만 홈을 새긴다 — 바깥 테두리는 이미 그림에 있다.

    ★칸마다 사각형을 그리면 인접 칸 경계가 두 번 그려져 두꺼워진다. 경계 좌표당
      한 번씩만 긋는다(스킬트리 인벤 격자에서 겪은 문제와 같다).
    """
    d = Image.new("RGBA", im.size, (0, 0, 0, 0))
    px = d.load()
    cols = sorted({s % COLS for s in INPUT_SLOTS})
    rows = sorted({s // COLS for s in INPUT_SLOTS})
    x0 = (GRID_X + CELL * cols[0]) * SCALE
    x1 = (GRID_X + CELL * (cols[-1] + 1)) * SCALE - 1
    y0 = (GRID_Y + CELL * rows[0]) * SCALE
    y1 = (GRID_Y + CELL * (rows[-1] + 1)) * SCALE - 1
    t = SCALE // 2
    for c in cols[1:]:                                   # 세로 홈(내부 경계만)
        gx = (GRID_X + CELL * c) * SCALE
        for k in range(t):
            for y in range(y0, y1 + 1):
                px[gx - t // 2 + k, y] = GROOVE
        for y in range(y0, y1 + 1):
            px[gx - t // 2 + t, y] = GROOVE_HI
    for r in rows[1:]:                                   # 가로 홈
        gy = (GRID_Y + CELL * r) * SCALE
        for k in range(t):
            for x in range(x0, x1 + 1):
                px[x, gy - t // 2 + k] = GROOVE
        for x in range(x0, x1 + 1):
            px[x, gy - t // 2 + t] = GROOVE_HI
    im.alpha_composite(d)
    return im


def draw_button_recess(im):
    """버튼이 박힐 홈 — 슬롯 한 칸 크기로 살짝 파낸다. 위/왼쪽 어둡게, 아래/오른쪽 밝게."""
    d = Image.new("RGBA", im.size, (0, 0, 0, 0))
    px = d.load()
    n = CELL * SCALE
    for s in BTN_SLOTS:
        c, r = s % COLS, s // COLS
        x0, y0 = (GRID_X + CELL * c) * SCALE, (GRID_Y + CELL * r) * SCALE
        for y in range(y0, y0 + n):
            for x in range(x0, x0 + n):
                px[x, y] = BTN_FILL
        for k in range(SCALE // 2):
            for x in range(x0, x0 + n):
                px[x, y0 + k] = BTN_EDGE
                px[x, y0 + n - 1 - k] = BTN_HI
            for y in range(y0, y0 + n):
                px[x0 + k, y] = BTN_EDGE
                px[x0 + n - 1 - k, y] = BTN_HI
    im.alpha_composite(d)
    return im


def draw_inventory(im):
    px = im.load()
    n = CELL * SCALE
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
    draw_tray_grooves(im)
    draw_button_recess(im)
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
    print(f"  gui.json: 기존 {kept}개 보존 + {len(provs)}개 등록 (U+{CODE0:04X}~U+{CODE0+8:04X})")
    print(f"  글리프 → {os.path.join(SRC, '_glyph.txt')}")


if __name__ == "__main__":
    main()
