#!/usr/bin/env python3
"""완성된 트리 배경 아트(352x408) 후처리 — 나무 기둥 손상 복원 + 인벤 칸 음각 + 4타일 분할.

입력: ~/Downloads/barkan_skilltree_gui_{A,B,C}_detailrestored5.png (352x408, 슬롯 격자 정합 확인됨)
산출: assets/barkan/textures/gui/tree_{4br,3br,p2}_{tl,tr,bl,br}.png

아트가 이미 규격에 맞게 나왔으므로 재조립은 하지 않는다. 하는 일은 3가지뿐:
  ① 좌우 나무 기둥의 끊긴 구간을 같은 기둥의 깨끗한 나뭇결로 메움 (세로 결이라 y만 옮겨 복사)
  ② 플레이어 인벤 3행 + 핫바 칸 음각 (아트는 평평한 패널로 받았다)
  ③ 4타일 분할 — MC 폰트 아틀라스가 256px라 352x408을 한 글리프로 못 넣는다
     이음선 x=97(GUI) / y=107 → 194x214 · 158x214 · 194x194 · 158x194
     advance = round(폭 x height/높이)+1 = 98/80, ascent 13(위)/-94(아래)

GUI 좌표(2배): 칸 = (14+36*col, 34+36*row) 36x36 / 인벤 3행 칸 top y=240·276·312 / 핫바 356
"""
import os

from PIL import Image

SRC_DIR = os.path.expanduser("~/Downloads")
OUTDIR = os.path.expanduser("~/development/barkan-resourcepack/assets/barkan/textures/gui")
JOBS = [("4br", "barkan_skilltree_gui_A_detailrestored5.png"),
        ("3br", "barkan_skilltree_gui_B_detailrestored5.png"),
        ("p2", "barkan_skilltree_gui_C_detailrestored5.png")]

# ── 좌우 나무 기둥 테이퍼 ─────────────────────────────────────────
# 원본은 기둥 안쪽 경계가 들쭉날쭉하다(생성 노이즈). 구간마다 **양 끝은 두껍고 가운데로 갈수록
# 얇아지는** 매끄러운 곡선으로 다시 잡는다 — 손상 부위 땜질보다 이게 근본 해결이다.
#   구간은 구분바로 나뉜 상·하 두 개. 각 구간에서 t=0/1(끝)에 THICK, t=0.5(중앙)에 THIN.
WOOD_SPANS = [(34, 213), (239, 389)]             # (2배 좌표) 상단 패널 / 하단 패널 구간
WOOD_OUT = 6                                     # 기둥 바깥쪽 시작 x (프레임 하이라이트 뒤)
WOOD_THICK, WOOD_THIN = 21, 15
# 근원 소켓은 x12부터라 테이퍼(중앙 15px)에 왼쪽이 물린다. 폭을 줄이는 대신 **원본에서 근원만
# 키잉해 다시 얹는다** — 기둥은 매끄러운 테이퍼 그대로, 근원은 안 덮인다.
ROOT_BOX = (8, 96, 60, 152)      # 근원 주변 (2배 좌표)
ROOT_KEY_LUM = 34                # 이 밝기 이상만 근원으로 간주 (패널·나무는 이보다 어둡다)
# 근원 소켓은 칸 중심 GUI(16,62) = 2배(32,124)에 반지름 ~20. 사각 박스로 뜨면 좌상단 모서리에
# 원본의 들쭉날쭉한 나무 파편이 같이 넘어온다 → 원형 마스크 + 어두운 주황(나무) 제외.
ROOT_C, ROOT_R = (32, 124), 23
TAPER_P = 1.6                                    # 곡률 (1=선형, 클수록 중앙이 넓게 얇아짐)

INV_CELL_Y = [240, 276, 312]                     # 인벤 3행 칸 top (2배)
HOTBAR_Y = 356
CELL_X0, CELL_W, CELL_N = 14, 36, 9
CELL_IN, CELL_SH, CELL_HL = (12, 22, 28, 255), (5, 11, 14, 255), (26, 64, 70, 255)

TILES = [("tl", (0, 0, 194, 214)), ("tr", (194, 0, 352, 214)),
         ("bl", (0, 214, 194, 408)), ("br", (194, 214, 352, 408))]


WOOD_SAMPLE = (6, 300, 22, 372)      # 깨끗한 나뭇결 조각 (좌측 하단 구간) — 세로 타일링용


def taper_wood(im):
    """기둥을 통째로 다시 깐다 — 깨끗한 나뭇결 조각을 세로 타일링하고 테이퍼로 폭을 잡는다.

    ★원본 경계를 따라 재단하는 방식(앞선 시안 2회)은 실패했다: 원본 경계 자체가 들쭉날쭉하고
      근원 주변엔 파인 자리가 있어 곡선을 못 따라간다. 원본 위에 새로 깔면 그 손상까지 덮인다.
    패널 배경색은 같은 행의 어두운 픽셀(x55~80 최소 휘도)에서 뽑아 잘려나간 자리를 메운다.
    """
    px = im.load()
    W = im.width
    sx0, sy0, sx1, sy1 = WOOD_SAMPLE
    sample = [[im.getpixel((x, y)) for x in range(sx0, sx1)] for y in range(sy0, sy1)]
    sh, sw = len(sample), len(sample[0])

    for y0, y1 in WOOD_SPANS:
        span = y1 - y0
        for y in range(y0, y1 + 1):
            t = (y - y0) / span
            edge = int(round(WOOD_THIN + (WOOD_THICK - WOOD_THIN) * (2 * abs(t - 0.5)) ** TAPER_P))
            row = sample[(y - y0) % sh]
            width = edge - WOOD_OUT + 1
            panel = min((px[x, y] for x in range(55, 81)), key=lambda c: c[0] + c[1] * 2 + c[2])
            for side in (0, 1):
                gx = (lambda x: x) if side == 0 else (lambda x: W - 1 - x)
                for i in range(width):                      # 나뭇결을 목표 폭으로 가로 리샘플
                    px[gx(WOOD_OUT + i)] if False else None
                    px[gx(WOOD_OUT + i), y] = row[min(sw - 1, int(i * sw / width))]
                for x in range(edge + 1, 25):               # 남는 자리는 패널색
                    px[gx(x), y] = panel
    return im


def restore_root(im, original):
    """원본에서 근원 소켓만 밝기 키잉으로 뽑아 같은 자리에 얹는다 (테이퍼 나무 위로)."""
    box = original.crop(ROOT_BOX).convert("RGBA")
    px = box.load()
    for y in range(box.height):
        for x in range(box.width):
            r, g, b, _ = px[x, y]
            lum = (r * 2 + g * 5 + b) // 8
            gx, gy = ROOT_BOX[0] + x, ROOT_BOX[1] + y
            out = (gx - ROOT_C[0]) ** 2 + (gy - ROOT_C[1]) ** 2 > ROOT_R ** 2
            wood = r > b + 25 and lum < 90         # 어두운·중간 주황 = 나무 (밝은 금색 링은 통과)
            if out or wood or lum < ROOT_KEY_LUM:
                px[x, y] = (0, 0, 0, 0)
            else:
                px[x, y] = (r, g, b, min(255, (lum - ROOT_KEY_LUM) * 8))
    im.alpha_composite(box, (ROOT_BOX[0], ROOT_BOX[1]))
    return im


def slot_cell(px, x0, y0):
    for y in range(y0, y0 + CELL_W):
        for x in range(x0, x0 + CELL_W):
            px[x, y] = CELL_IN
    for k in range(2):                            # 2배라 테두리 2px = GUI 1px
        for x in range(x0, x0 + CELL_W):
            px[x, y0 + k] = CELL_SH
            px[x, y0 + CELL_W - 1 - k] = CELL_HL
        for y in range(y0, y0 + CELL_W):
            px[x0 + k, y] = CELL_SH
            px[x0 + CELL_W - 1 - k, y] = CELL_HL


ENTRY_ROWS_Y = [88, 124, 160, 196]   # p2 노드 4행 중심 (2배)
ENTRY_X0, ENTRY_SRC_X = 14, 40       # 진입선 시작 x / 단면을 뜰 기준 x(1행의 깨끗한 구간)
ENTRY_REF_ROW = 1                    # 길이가 온전한 행
ENTRY_X1 = 88                        # 노드 소켓 왼쪽 림
ENTRY_HALF = 5                       # 선 단면 반높이


def normalize_left_entries(im):
    """p2: 왼쪽 진입선 4개 길이를 맞춘다.

    생성기가 0행 x54~, 3행 x62~ 로 짧게 그려서 계단처럼 들쭉날쭉했다. 길이가 온전한
    1행에서 선 단면(세로 1픽셀 열)을 떠서 부족한 행의 x28..기존시작 구간에 채운다
    — 색·두께·글로우가 그대로라 이어붙인 티가 안 난다.
    """
    px = im.load()
    ry = ENTRY_ROWS_Y[ENTRY_REF_ROW]
    strip = [px[ENTRY_SRC_X, ry + dy] for dy in range(-ENTRY_HALF, ENTRY_HALF + 1)]

    def teal(c):
        r, g, b = c[:3]
        return b > 70 and g > 60 and b > r + 25

    # 기준 행이 실제로 어디서 시작하는지 측정 — 상수로 박으면 어긋난다(0~2행은 나무기둥
    # 경계 x16부터 시작했고 3행만 x62였다).
    x0 = ENTRY_X0
    for x in range(ENTRY_X0, 90):
        if any(teal(px[x, ry + dy]) for dy in (-2, -1, 0, 1, 2)):
            x0 = x
            break

    for cy in ENTRY_ROWS_Y:
        # ★행마다 "첫 teal"을 찾는 방식은 실패했다: 0행에는 세로 장식선이 x28을 지나가서
        #   거기서 멈춰 중간이 빈 채로 남았다. 노드 왼쪽 림(x88)까지 무조건 다시 깐다.
        for x in range(x0, ENTRY_X1 + 1):
            for i, dy in enumerate(range(-ENTRY_HALF, ENTRY_HALF + 1)):
                px[x, cy + dy] = strip[i]

    # 진입선 사이 여백에 남은 흰 잡티(1~2px) 제거 — 주변보다 크게 밝고 이웃이 전부 어두우면
    # 이웃 중간값으로 덮는다. 소켓 림·선은 범위(x26~100, 선 밴드 제외) 밖이라 안 건드린다.
    bands = [(cy - ENTRY_HALF - 2, cy + ENTRY_HALF + 2) for cy in ENTRY_ROWS_Y]
    def lum(c): return (c[0] * 2 + c[1] * 5 + c[2]) // 8
    for y in range(40, 208):
        if any(a <= y <= b for a, b in bands):
            continue
        for x in range(26, 101):
            nb = [px[x + dx, y + dy] for dx in (-2, -1, 1, 2) for dy in (-2, -1, 1, 2)]
            m = sorted(lum(c) for c in nb)[len(nb) // 2]
            if lum(px[x, y]) > m + 55:
                px[x, y] = sorted(nb, key=lum)[len(nb) // 2]
    return im


def main():
    for key, fname in JOBS:
        p = os.path.join(SRC_DIR, fname)
        im = Image.open(p).convert("RGBA")
        if im.size != (352, 408):
            raise SystemExit(f"{fname}: 352x408이 아님 {im.size}")
        original = im.copy()
        taper_wood(im)
        if key != "p2":                       # 2페이지는 근원이 없다
            restore_root(im, original)
        else:
            normalize_left_entries(im)
        px = im.load()
        for cy in INV_CELL_Y + [HOTBAR_Y]:
            for c in range(CELL_N):
                slot_cell(px, CELL_X0 + CELL_W * c, cy)
        for suf, box in TILES:
            tile = im.crop(box)
            tile.save(os.path.join(OUTDIR, f"tree_{key}_{suf}.png"))
        print(f"  tree_{key}_* : 기둥 테이퍼(좌우) + 인벤 36칸 + 4타일 "
              f"{TILES[0][1][2]}x{TILES[0][1][3]} 등 저장")


if __name__ == "__main__":
    main()
