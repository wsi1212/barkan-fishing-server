#!/usr/bin/env python3
"""낚시 성공 창 배경 조립 — 배경판 + 소켓 + 제단을 **좌표 계산으로** 합성한다.

왜 합성인가 (2026-08-06):
  소켓 27개를 그림에 직접 그려 달라고 했더니 4장 전부 슬롯 격자를 벗어났다.
  18px 피치·원점(7,17)에 픽셀 단위로 맞추는 건 그림 작업이 감당할 정밀도가 아니다.
  → 부품(소켓 1장·제단 1장)만 받고 정렬은 이 스크립트가 보장한다.
     소켓을 고치고 싶으면 96px 한 장만 다시 받으면 27개가 전부 고쳐진다.

입력:  src/fishing_success/bg_source.png   704x672, 불투명, 소켓·제단 없음
       src/fishing_success/socket.png      96x96, 투명 (전 슬롯에 복제)
       src/fishing_success/altar[_<등급>].png  투명, #FF00FF 1px 마커로 정렬점 지정

산출:  <RP>/assets/barkan/textures/gui/fish_bg_r{0..2}c{0..2}.png  (9타일)
       gui.json 의 provider 병합(멱등)  +  src/.../_glyph.txt, _preview_full.png

사용: python3 build_fishing_success_bg.py [--grade S]
"""
import argparse
import json
import os

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "src", "fishing_success")
RP = os.path.expanduser("~/development/barkan-resourcepack")
OUTDIR = os.path.join(RP, "assets/barkan/textures/gui")
FONT_JSON = os.path.join(RP, "assets/barkan/font/gui.json")

SCALE = 4
GW = 176
ROWS = 3                          # 컨테이너 행 수
GH = 114 + ROWS * 18
W, H = GW * SCALE, GH * SCALE     # 704 x 672

GRID_X, GRID_Y = 7, 17
CELL = 18
COLS = 9
INV_Y0 = 31 + ROWS * CELL         # 85
INV_ROWS_Y = [INV_Y0, INV_Y0 + CELL, INV_Y0 + 2 * CELL]
HOTBAR_Y = INV_Y0 + 58

# 타일 분할 — 폰트 아틀라스 1장당 256px 제한. 3열 x 3행.
COL_GUI = [59, 59, 58]            # 합 176
ROW_GUI = [56, 56, 56]            # 합 168
CODE0 = 0xE620                    # ★e600~e611 은 프로필/레벨허브/스킬트리가 이미 사용 중
TILE_PREFIX = "fish_bg_"

# 인벤 칸 색 — 스킬트리와 동일하게 맞춰 GUI 간 인벤 영역 룩을 통일한다.
CELL_IN, CELL_GRID = (10, 16, 20, 255), (26, 36, 42, 255)

MARKER = (255, 0, 255)            # 제단 정렬 마커

# ★소켓을 27칸 전부에 깔면 안 된다(2026-08-06 실측). 소켓 96px 이 칸 피치 72px 보다
#   커서 링이 24px씩 겹쳐 벌집 격자처럼 뭉갠다. 그렇다고 소켓을 줄이면 안쪽 구멍도
#   같이 줄어 아이템(64px)이 링을 덮는다 — 크기가 아니라 **배치**로 풀어야 한다.
#   아이템이 실제로 들어가는 칸에만 깐다: 윗행 중앙 5칸(부가 어획) + 제단 5칸(주요 어획).
#   나머지는 민무늬 패널로 두고, 아랫행은 정보 명판이라 소켓이 필요 없다.
SOCKET_SLOTS = list(range(2, 7)) + list(range(11, 16))
ALTAR_CENTER_SLOT = 13


def slot_center(idx):
    """슬롯 인덱스 → 칸 중심 (아트 px)."""
    c, r = idx % COLS, idx // COLS
    return ((GRID_X + CELL * c + CELL // 2) * SCALE,
            (GRID_Y + CELL * r + CELL // 2) * SCALE)


def find_marker(im):
    """#FF00FF 마커 픽셀들의 중심을 찾고, 그 픽셀을 투명하게 지운다."""
    px = im.load()
    pts = []
    for y in range(im.height):
        for x in range(im.width):
            r, g, b, a = px[x, y]
            if a > 0 and r > 240 and g < 30 and b > 240:
                pts.append((x, y))
    if not pts:
        return None
    for x, y in pts:
        px[x, y] = (0, 0, 0, 0)
    return (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts))


def paste_centered(base, sprite, cx, cy):
    base.alpha_composite(sprite, (int(round(cx - sprite.width / 2)),
                                  int(round(cy - sprite.height / 2))))


def draw_inventory(im):
    """플레이어 인벤 칸 — 아트가 아니라 여기서 그린다(경계선은 좌표당 한 번만)."""
    px = im.load()
    n = CELL * SCALE
    for gy in INV_ROWS_Y + [HOTBAR_Y]:
        for c in range(COLS):
            x0, y0 = (GRID_X + CELL * c) * SCALE, gy * SCALE
            for y in range(y0, y0 + n):
                for x in range(x0, x0 + n):
                    px[x, y] = CELL_IN
    cols_x = [(GRID_X + CELL * c) * SCALE for c in range(COLS)]
    for block in (INV_ROWS_Y, [HOTBAR_Y]):
        _grid_lines(px, cols_x, [y * SCALE for y in block], n)


def _grid_lines(px, cols_x, rows_y, cell_px):
    t = max(1, SCALE // 2)
    x_lines = cols_x + [cols_x[-1] + cell_px]
    y_lines = rows_y + [rows_y[-1] + cell_px]
    x0, x1 = cols_x[0], cols_x[-1] + cell_px
    y0, y1 = rows_y[0], rows_y[-1] + cell_px
    for lx in x_lines:
        for k in range(t):
            x = lx - t // 2 + k
            for y in range(y0, y1):
                px[x, y] = CELL_GRID
    for ly in y_lines:
        for k in range(t):
            y = ly - t // 2 + k
            for x in range(x0, x1):
                px[x, y] = CELL_GRID


def tiles():
    out, gy = [], 0
    for r, gh in enumerate(ROW_GUI):
        gx = 0
        for c, gw in enumerate(COL_GUI):
            out.append((f"r{r}c{c}", (gx * SCALE, gy * SCALE,
                                      (gx + gw) * SCALE, (gy + gh) * SCALE),
                        gw, gh, gx, gy))
            gx += gw
        gy += gh
    return out


def merge_providers(new):
    """gui.json 에 provider 병합 — 이 GUI 것만 갈아끼운다(멱등). 다른 GUI 건 보존."""
    d = json.load(open(FONT_JSON, encoding="utf-8"))
    kept = [p for p in d["providers"]
            if TILE_PREFIX not in str(p.get("file", ""))]
    d["providers"] = kept + new
    json.dump(d, open(FONT_JSON, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    return len(kept), len(new)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--grade", default=None, help="등급별 제단 (altar_<등급>.png)")
    a = ap.parse_args()

    bg = Image.open(os.path.join(SRC, "bg_source.png")).convert("RGBA")
    assert bg.size == (W, H), f"배경판 크기 {bg.size} != {(W, H)}"

    # ① 제단 — 마커를 가운데 칸(슬롯 13) 중심에 맞춘다. 소켓보다 아래 레이어.
    altar_name = f"altar_{a.grade}.png" if a.grade else "altar.png"
    ap_path = os.path.join(SRC, altar_name)
    if os.path.exists(ap_path):
        altar = Image.open(ap_path).convert("RGBA")
        m = find_marker(altar)
        cx, cy = slot_center(ALTAR_CENTER_SLOT)
        if m:
            bg.alpha_composite(altar, (int(round(cx - m[0])), int(round(cy - m[1]))))
            print(f"  제단 {altar_name} — 마커 {m} → 슬롯13 중심 {(cx, cy)}")
        else:
            paste_centered(bg, altar, cx, cy)
            print(f"  제단 {altar_name} — ★마커 없음, 눈대중 중앙 정렬")
    else:
        print(f"  제단 없음({altar_name}) — 건너뜀")

    # ② 소켓 — 아이템이 들어가는 칸에만. 정렬은 여기서 보장된다.
    sock = Image.open(os.path.join(SRC, "socket.png")).convert("RGBA")
    for i in SOCKET_SLOTS:
        paste_centered(bg, sock, *slot_center(i))
    print(f"  소켓 {len(SOCKET_SLOTS)}칸 합성 ({sock.width}x{sock.height}) — 슬롯 {SOCKET_SLOTS}")

    # ③ 플레이어 인벤 칸
    draw_inventory(bg)

    # ④ 타일 분할 + provider
    os.makedirs(OUTDIR, exist_ok=True)
    for f in os.listdir(OUTDIR):
        if f.startswith(TILE_PREFIX):
            os.remove(os.path.join(OUTDIR, f))
    provs, glyph = [], []
    for i, (name, box, gw, gh, gx, gy) in enumerate(tiles()):
        crop = bg.crop(box)
        assert max(crop.size) <= 256, f"{name} {crop.size} — 아틀라스 256px 초과"
        crop.save(os.path.join(OUTDIR, f"{TILE_PREFIX}{name}.png"))
        ch = chr(CODE0 + i)
        provs.append({"type": "bitmap", "file": f"barkan:gui/{TILE_PREFIX}{name}.png",
                      "ascent": 13 - gy, "height": gh, "chars": [ch]})
        glyph.append("\\uf801" if i == 0 else ("\\uf803" if gx == 0 else "\\uf802"))
        glyph.append(f"\\u{ord(ch):04x}")

    kept, added = merge_providers(provs)
    open(os.path.join(SRC, "_glyph.txt"), "w", encoding="utf-8").write("".join(glyph))
    bg.save(os.path.join(SRC, "_preview_full.png"))
    print(f"  타일 {len(provs)}개 → {OUTDIR}")
    print(f"  gui.json provider: 기존 {kept}개 보존 + {added}개 등록 (U+{CODE0:04X}~)")
    print(f"  글리프 문자열 → {os.path.join(SRC, '_glyph.txt')}")


if __name__ == "__main__":
    main()
