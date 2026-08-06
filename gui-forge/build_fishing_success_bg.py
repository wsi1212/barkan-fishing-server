#!/usr/bin/env python3
"""낚시 성공 창 배경 조립 — 등급 티어별 배경 4벌을 **전부 코드로** 합성한다.

## 왜 합성인가 (2026-08-06)
소켓 27개를 그림에 직접 그려 달라고 했더니 4장 전부 슬롯 격자를 벗어났다.
18px 피치·원점(7,17)에 픽셀 단위로 맞추는 건 그림 작업이 감당할 정밀도가 아니다.
→ 부품(배경판·소켓) 한 벌만 받고 정렬·색·발광은 이 스크립트가 만든다.

## 등급 → 티어 (배경을 등급 9벌이 아니라 티어 4벌만 굽는다)
    E D C B  → basic  기본
    A S      → weak   약한 광휘 + 보라 소켓
    M L      → mid    중간 광휘 + 주황 소켓
    G        → max    최대 광휘 + 금색 소켓 + **금테두리**
등급마다 배경을 따로 구우면 9벌 x 9타일 = 81장이 된다. 눈에 보이는 차이는
티어 단위라 4벌이면 충분하고, 나중에 배경을 고쳐도 재생성 한 번이면 전부 반영된다.

## 제단은 폐기(2026-08-06)
가운데 제단을 세웠더니 아래 정보행과 나무 구분띠를 덮고 빛기둥이 제목을 뚫었다.
슬롯 기하 밖으로 나가는 큰 장식은 무엇을 그리든 결국 뭔가를 가린다.
등급 연출은 **슬롯 기하 안에 갇힌 소켓 + 그 뒤 광휘**로 낸다 — 가릴 수가 없다.

입력:  src/fishing_success/bg_source.png   704x672 불투명 (프레임·패널·제목만)
       src/fishing_success/socket.png      96x96 투명 (안쪽 64px 비어 있음)
산출:  <RP>/assets/barkan/textures/gui/fish_bg_<tier>_r{0..2}c{0..2}.png (4벌 x 9타일)
       gui.json provider 병합(멱등) + src/.../_glyphs.json (티어별 글리프 문자열)
"""
import colorsys
import json
import math
import os

from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "src", "fishing_success")
RP = os.path.expanduser("~/development/barkan-resourcepack")
OUTDIR = os.path.join(RP, "assets/barkan/textures/gui")
FONT_JSON = os.path.join(RP, "assets/barkan/font/gui.json")

SCALE = 4
GW, ROWS = 176, 3
GH = 114 + ROWS * 18
W, H = GW * SCALE, GH * SCALE          # 704 x 672

GRID_X, GRID_Y, CELL, COLS = 7, 17, 18, 9
INV_Y0 = 31 + ROWS * CELL
INV_ROWS_Y = [INV_Y0, INV_Y0 + CELL, INV_Y0 + 2 * CELL]
HOTBAR_Y = INV_Y0 + 58

COL_GUI = [59, 59, 58]                 # 합 176
ROW_GUI = [56, 56, 56]                 # 합 168
CODE0 = 0xE620                         # e600~e611 은 프로필/레벨허브/스킬트리가 선점
TILE_PREFIX = "fish_bg_"
CELL_IN, CELL_GRID = (10, 16, 20, 255), (26, 36, 42, 255)

# 아이템이 들어가는 칸 = 가운데 줄 5칸. 소켓 96px가 칸 피치 72px보다 커서
# 전 슬롯에 깔면 링이 겹쳐 벌집이 된다(2026-08-06 실측). 크기를 줄이면 안쪽
# 구멍(64px=아이템 크기)까지 줄어 물고기를 덮으므로 **배치**로 푼다.
SOCKET_SLOTS = list(range(11, 16))
GLOW_BAND_Y = 68                       # 광휘 밴드가 얹히는 y (슬롯 패널 상단)
GLOW_BAND_H = 216

# 소켓을 3줄로 깔 계획이던 시절 발주서가 y=140/212에 그어달라 했던 구분선.
# 소켓이 한 줄로 줄면서 나눌 행이 없어졌고, 남으면 소켓을 관통해 등급색과 싸운다.
# ★납품 원본은 건드리지 않고 빌드 산출물에서만 지운다.
HAIRLINE_BANDS = [(134, 146), (206, 218)]
HAIRLINE_SRC_DY = 26

TIERS = [
    {"id": "basic", "grades": ["E", "D", "C", "B"], "socket": None,               "glow": None,                     "gold": False},
    {"id": "weak",  "grades": ["A", "S"],           "socket": (0.78, 1.20, 1.05), "glow": ((120, 190, 255), 0.55),  "gold": False},
    {"id": "mid",   "grades": ["M", "L"],           "socket": (0.09, 1.30, 1.10), "glow": ((255, 170, 90), 0.75),   "gold": False},
    {"id": "max",   "grades": ["G"],                "socket": (0.12, 1.35, 1.15), "glow": ((255, 215, 120), 1.00),  "gold": True},
]


def slot_center(idx):
    c, r = idx % COLS, idx // COLS
    return ((GRID_X + CELL * c + CELL // 2) * SCALE,
            (GRID_Y + CELL * r + CELL // 2) * SCALE)


def erase_hairlines(im):
    px = im.load()
    for y0, y1 in HAIRLINE_BANDS:
        for y in range(y0, y1):
            for x in range(im.width):
                px[x, y] = px[x, y - HAIRLINE_SRC_DY]
    return im


def tint(im, hue, sat_mul, val_mul):
    """채도 있는 픽셀(=발광·강조)만 색상 회전. 무채색 금속은 그대로 둬 재질감을 지킨다."""
    out = im.copy()
    p = out.load()
    for y in range(im.height):
        for x in range(im.width):
            r, g, b, a = p[x, y]
            if a == 0:
                continue
            _, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
            if s > 0.12:
                nr, ng, nb = colorsys.hsv_to_rgb(hue, min(1.0, s * sat_mul), min(1.0, v * val_mul))
                p[x, y] = (int(nr * 255), int(ng * 255), int(nb * 255), a)
    return out


def make_glow(color, strength):
    """소켓 뒤로 퍼지는 광휘. ★아이템이 앉는 원은 뚫는다 — 안 뚫으면 물고기가 묻힌다."""
    band = Image.new("RGBA", (W, GLOW_BAND_H), (0, 0, 0, 0))
    p = band.load()
    cy = GLOW_BAND_H // 2
    cxs = [slot_center(i)[0] for i in SOCKET_SLOTS]
    for y in range(GLOW_BAND_H):
        for x in range(W):
            d = min(math.hypot(x - cx, (y - cy) * 1.7) for cx in cxs)
            v = max(0.0, 1.0 - d / 230.0) ** 2.2
            if v > 0.004:
                p[x, y] = (color[0], color[1], color[2], int(255 * v * strength))
    band = band.filter(ImageFilter.GaussianBlur(6))
    mask = Image.new("L", (W, GLOW_BAND_H), 255)
    md = ImageDraw.Draw(mask)
    for cx in cxs:
        md.ellipse([cx - 36, cy - 36, cx + 36, cy + 36], fill=0)
    mask = mask.filter(ImageFilter.GaussianBlur(9))
    band.putalpha(Image.composite(band.getchannel("A"), Image.new("L", (W, GLOW_BAND_H), 0), mask))
    return band


def goldify(im):
    """프레임(따뜻한 목재·금속)을 금색으로. 차가운 **패널 본체**는 건드리지 않는다.

    ★청록 액센트선도 같이 금으로 바꾼다. 안 바꾸면 금테두리 위에 청록 줄만 남아
      색이 싸운다. 패널 본체와 액센트선은 둘 다 차가운 색이라 색상만으로는 못
      가르지만 **밝기**로 갈린다(액센트선 v>0.35, 패널 본체 v≈0.15).
    """
    out = im.copy()
    p = out.load()
    for y in range(im.height):
        for x in range(im.width):
            r, g, b, a = p[x, y]
            _, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
            warm = r > g > b and r > 38
            cool_accent = b > r and s > 0.25 and v > 0.35
            if not (warm or cool_accent):
                continue
            nr, ng, nb = colorsys.hsv_to_rgb(0.115, min(1.0, s * 1.5 + 0.15),
                                             min(1.0, v * 1.55 + 0.05))
            p[x, y] = (int(nr * 255), int(ng * 255), int(nb * 255), a)
    return out


def draw_inventory(im):
    """플레이어 인벤 칸 — 경계선은 좌표당 한 번만(칸마다 그리면 내부선이 2배 두꺼워진다)."""
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
    for lx in cols_x + [cols_x[-1] + cell_px]:
        for k in range(t):
            x = lx - t // 2 + k
            for y in range(rows_y[0], rows_y[-1] + cell_px):
                px[x, y] = CELL_GRID
    for ly in rows_y + [rows_y[-1] + cell_px]:
        for k in range(t):
            y = ly - t // 2 + k
            for x in range(cols_x[0], cols_x[-1] + cell_px):
                px[x, y] = CELL_GRID


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


def merge_providers(new):
    d = json.load(open(FONT_JSON, encoding="utf-8"))
    kept = [p for p in d["providers"] if TILE_PREFIX not in str(p.get("file", ""))]
    d["providers"] = kept + new
    json.dump(d, open(FONT_JSON, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    return len(kept)


def main():
    base = Image.open(os.path.join(SRC, "bg_source.png")).convert("RGBA")
    assert base.size == (W, H), f"배경판 크기 {base.size} != {(W, H)}"
    erase_hairlines(base)
    sock0 = Image.open(os.path.join(SRC, "socket.png")).convert("RGBA")

    os.makedirs(OUTDIR, exist_ok=True)
    for f in os.listdir(OUTDIR):
        if f.startswith(TILE_PREFIX):
            os.remove(os.path.join(OUTDIR, f))

    provs, glyphs, code = [], {}, CODE0
    for tier in TIERS:
        im = goldify(base) if tier["gold"] else base.copy()
        if tier["glow"]:
            im.alpha_composite(make_glow(*tier["glow"]), (0, GLOW_BAND_Y))
        sock = tint(sock0, *tier["socket"]) if tier["socket"] else sock0
        for i in SOCKET_SLOTS:
            cx, cy = slot_center(i)
            im.alpha_composite(sock, (cx - sock.width // 2, cy - sock.height // 2))
        draw_inventory(im)

        g = []
        for i, (name, box, gw, gh, gx, gy) in enumerate(tiles()):
            crop = im.crop(box)
            assert max(crop.size) <= 256, f"{name} {crop.size} — 아틀라스 256px 초과"
            fn = f"{TILE_PREFIX}{tier['id']}_{name}"
            crop.save(os.path.join(OUTDIR, fn + ".png"))
            ch = chr(code)
            code += 1
            provs.append({"type": "bitmap", "file": f"barkan:gui/{fn}.png",
                          "ascent": 13 - gy, "height": gh, "chars": [ch]})
            g.append("\\uf801" if i == 0 else ("\\uf803" if gx == 0 else "\\uf802"))
            g.append(f"\\u{ord(ch):04x}")
        glyphs[tier["id"]] = {"grades": tier["grades"], "glyph": "".join(g)}
        im.save(os.path.join(SRC, f"_preview_{tier['id']}.png"))
        print(f"  {tier['id']:6} 등급 {','.join(tier['grades']):8} → 9타일"
              f"{'  +금테두리' if tier['gold'] else ''}")

    kept = merge_providers(provs)
    json.dump(glyphs, open(os.path.join(SRC, "_glyphs.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print(f"  gui.json: 기존 {kept}개 보존 + {len(provs)}개 등록 (U+{CODE0:04X}~U+{code-1:04X})")
    print(f"  티어별 글리프 → {os.path.join(SRC, '_glyphs.json')}")


if __name__ == "__main__":
    main()
