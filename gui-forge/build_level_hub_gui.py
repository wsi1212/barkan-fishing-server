#!/usr/bin/env python3
"""/레벨 허브 GUI 글리프(barkan:gui) — 콘셉트 아트를 창 규격에 맞춰 후처리 (2배 해상도).

소스: gui-forge/src/level_hub_concept.png (1303x1207)
산출: assets/barkan/textures/gui/level_hub_{tl,tr,bl,br}.png (4타일, 합 352x336)

── 왜 4타일인가 ────────────────────────────────────────────────────────
MC는 폰트 글리프를 256x256 아틀라스(FontTexture)에 스티칭한다. 한 변이 256을 넘으면
스티칭 실패 → missing-glyph 박스가 된다. 창 전체를 2배(352x336)로 그리려면 쪼개야 한다.
쪼갠 타일은 글리프 advance로 이어 붙인다:

  advance = round(텍스처폭 x height/텍스처높이) + 1      ← 끝의 +1이 글자 간격
  (검증: skin.json이 px.png 8x8을 height 1로 써서 advance 2 → SkinRenderer가 off(-1)로
   net 1px를 만든다. 프로덕션에서 동작 중인 값이라 이 공식이 맞다.)

  펜 시작 = titleLabelX(8) → \\uf801(-8)로 창 x=0
  A_top(advance 98) → \\uf802(-1) → B_top(advance 80) → \\uf803(-177) → 아래 행 반복

세로는 ascent가 잡는다: 글리프 top = titleLabelY(6) + 7 - ascent
  위 타일 ascent 13 → top y0 / 아래 타일 ascent -70 → top y83

★이음선 위치는 중앙 장식을 피한다: 세로선 x=97(중앙 메달리온/젬은 x88), 가로선 y=83
  (어두운 갭 — 1px 오차가 나도 안 보이는 자리). 둘 다 인벤 격자의 칸 경계와도 맞다.

── 창 규격 (27칸 = 176x168 GUI px) ──────────────────────────────────
슬롯 (sx,sy)의 텍스처 구멍은 (sx-1,sy-1) 18x18:
  컨테이너 3행 y17~70 (가운데 행 y35~52 = 아이콘 5개) / 인벤 3행 y84~137
  홈 y138~141 / 핫바 y142~159 / 프레임 링 7px / 슬롯 가로 x7~168
  (imageHeight = 114 + rows*18, 인벤 y = 103 + 18k + (rows-4)*18, 핫바 y = 161 + (rows-4)*18)

★격자는 플레이어 인벤·핫바에만 그린다 — 상단 컨테이너에 그리면 아트워크가 모눈종이가 된다.
★프레임은 9-slice로 처리: 모서리 블록만 등비 축소해 둥근 모서리와 금속 브래킷을 지킨다
  (밴드별 독립 스케일로 뭉개면 모서리가 정사각형으로 짤린다 — 1차 시안 실패 원인).
★모서리 바깥 어두운 여백까지 포함한다(잘라내지 않음) — 그래야 둥근 모서리가 드러난다.
  투명으로 두면 밑에 깔린 바닐라 회색 패널이 비쳐서 안 된다.
"""
import os

from PIL import Image, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "src", "level_hub_concept.png")
OUTDIR = os.path.expanduser("~/development/barkan-resourcepack/assets/barkan/textures/gui")

SCALE = 2                              # 2배 해상도
GW, GH = 176, 168                      # GUI px (27칸 창)
TW, TH = GW * SCALE, GH * SCALE         # 352 x 336 텍스처

FRAME_G = 7                            # 프레임 링 두께 (GUI px) = 슬롯 격자 시작 x7
FRAME_T = FRAME_G * SCALE              # 14 텍스처 px
CORNER_SRC = 100                       # 소스 모서리 블록 (여백 29 + 나무 프레임 71)

SEAM_X_G, SEAM_Y_G = 97, 83            # 타일 이음선 (GUI px)

# ── 소스 구조 (측정값) ────────────────────────────────────────────────
SX_PANEL = (100, 1202)                 # 패널 내부 가로 (청록 이너보더 안쪽)
SY_PANEL = (100, 1107)                 # 패널 내부 세로 (9-slice 안쪽 사각형)
MEDALLION = (558, 114, 748, 339)       # 3번(중앙) 메달리온 크롭
MED_BAND = (119, 349)                  # 메달리온이 걸친 세로 구간 (별 스파이크 포함)
CLEAN_ROWS = (95, 116)                 # 메달리온 위쪽 깨끗한 패널 행 — 지우기용 색 소스
# ★메달리온 사이를 타일링하면 안 된다: 원본 간격 224px < 메달리온 폭 186px라
#   "빈 구간"이 33px(x972~1004)뿐이고, 넓게 잡으면 옆 메달리온을 물어 격자로 복제된다.

# ── 패널 내부 세로 밴드: (GUI y0, GUI y1, 소스 y0, 소스 y1) 끝 포함 ──
INNER_V = [
    (7, 16, 100, 118),      # 상단 패널 위쪽 여백
    (17, 70, 119, 409),     # 컨테이너 3행 (메달리온 지운 패널)
    (71, 74, 410, 452),     # 패널 하단 청록 보더 + 나무 구분바
    (75, 83, 453, 470),     # 갭
    (84, 160, 471, 1107),   # 하단 패널 (인벤 3행 + 홈 + 핫바)
]

# 슬롯 좌표 (GUI px)
SLOT_X = [8 + c * 18 for c in range(9)]
ICON_ROW_Y = 36                        # 컨테이너 가운데 행
ICON_SLOTS = (11, 12, 13, 14, 15)
INV_Y = [85, 103, 121]
HOTBAR_Y = 143

# 슬롯 셀 색 — 청록 하이라이트를 밝게 하면 176px에서 격자가 모눈종이처럼 튄다.
CELL_IN = (10, 18, 22, 255)
CELL_SH = (4, 9, 11, 255)
CELL_HL = (20, 44, 46, 255)
PANEL_LUM = 16                         # 패널 배경 밝기 — 메달리온 키잉 기준

TILES = [  # (파일명, char, GUI 좌상단, GUI 크기)
    ("level_hub_tl.png", "", (0, 0), (SEAM_X_G, SEAM_Y_G)),
    ("level_hub_tr.png", "", (SEAM_X_G, 0), (GW - SEAM_X_G, SEAM_Y_G)),
    ("level_hub_bl.png", "", (0, SEAM_Y_G), (SEAM_X_G, GH - SEAM_Y_G)),
    ("level_hub_br.png", "", (SEAM_X_G, SEAM_Y_G), (GW - SEAM_X_G, GH - SEAM_Y_G)),
]


def erase_medallions(src):
    """상단 패널의 메달리온 5개를 지운다 — 위쪽 깨끗한 행들의 열별 평균색으로 밴드를 덮는다.
    열별로 채우니 패널의 좌우 비네팅이 유지되고 반복 패턴이 생기지 않는다."""
    out = src.copy()
    px = out.load()
    y0, y1 = MED_BAND
    r0, r1 = CLEAN_ROWS
    n = r1 - r0
    cols = []
    for x in range(SX_PANEL[0], SX_PANEL[1]):
        acc = [0, 0, 0]
        for y in range(r0, r1):
            c = px[x, y]
            for i in range(3):
                acc[i] += c[i]
        cols.append([v / n for v in acc])
    # 인접 열끼리 미세하게 달라 세로 줄무늬가 생기므로 가로로 평활화한다 (±R열 이동평균).
    R = 24
    sm = []
    for i in range(len(cols)):
        lo, hi = max(0, i - R), min(len(cols), i + R + 1)
        w = hi - lo
        sm.append(tuple(int(sum(cols[j][k] for j in range(lo, hi)) / w + 0.5) for k in range(3)))
    for i, x in enumerate(range(SX_PANEL[0], SX_PANEL[1])):
        col = (sm[i][0], sm[i][1], sm[i][2], 255)
        for y in range(y0, y1):
            px[x, y] = col
    return out


def build_frame(src, out):
    """9-slice 프레임 링 — 모서리는 등비(100x100 → 14x14), 변은 한 축만 늘린다."""
    sw, sh = src.size
    c, t = CORNER_SRC, FRAME_T
    corners = [
        ((0, 0, c, c), (0, 0)),                          # 좌상
        ((sw - c, 0, sw, c), (TW - t, 0)),               # 우상
        ((0, sh - c, c, sh), (0, TH - t)),               # 좌하
        ((sw - c, sh - c, sw, sh), (TW - t, TH - t)),    # 우하
    ]
    for box, pos in corners:
        out.paste(src.crop(box).resize((t, t), Image.LANCZOS), pos)
    # 가로 변 (모서리 사이) — 가로로만 늘림
    for sy0, sy1, ty in ((0, c, 0), (sh - c, sh, TH - t)):
        strip = src.crop((c, sy0, sw - c, sy1)).resize((TW - 2 * t, t), Image.LANCZOS)
        out.paste(strip, (t, ty))
    # 세로 변 — 세로로만 늘림
    for sx0, sx1, tx in ((0, c, 0), (sw - c, sw, TW - t)):
        strip = src.crop((sx0, c, sx1, sh - c)).resize((t, TH - 2 * t), Image.LANCZOS)
        out.paste(strip, (tx, t))


def build_inner(src, out):
    """패널 내부 — 가로는 통째로, 세로는 밴드별 독립 스케일로 슬롯 행에 맞춘다."""
    inner_w = (GW - 2 * FRAME_G) * SCALE          # 324
    for gy0, gy1, sy0, sy1 in INNER_V:
        strip = src.crop((SX_PANEL[0], sy0, SX_PANEL[1], sy1 + 1))
        h = (gy1 - gy0 + 1) * SCALE
        out.paste(strip.resize((inner_w, h), Image.LANCZOS), (FRAME_T, gy0 * SCALE))


def medallion_sprite(src, size):
    """메달리온을 밝기 키잉으로 뽑는다 — 배경(패널)은 투명. 통째로 붙이면 소스 비네팅이
    밝은 사각 패치로 보인다."""
    med = src.crop(MEDALLION).resize((size, size), Image.LANCZOS)
    med = med.filter(ImageFilter.UnsharpMask(radius=1, percent=120, threshold=1))
    px = med.load()
    for y in range(size):
        for x in range(size):
            r, g, b, _ = px[x, y]
            lum = (r * 2 + g * 5 + b) // 8
            px[x, y] = (r, g, b, max(0, min(255, (lum - PANEL_LUM) * 6)))
    return med


def slot_cell(px, gsx, gsy):
    """슬롯 한 칸 음각 (GUI 18x18 → 텍스처 36x36) — 위·좌 그림자 / 아래·우 청록 하이라이트."""
    x0, y0 = (gsx - 1) * SCALE, (gsy - 1) * SCALE
    n = 18 * SCALE
    for y in range(y0, y0 + n):
        for x in range(x0, x0 + n):
            px[x, y] = CELL_IN
    for k in range(SCALE):                         # 테두리 두께 = GUI 1px
        for x in range(x0, x0 + n):
            px[x, y0 + k] = CELL_SH
            px[x, y0 + n - 1 - k] = CELL_HL
        for y in range(y0, y0 + n):
            px[x0 + k, y] = CELL_SH
            px[x0 + n - 1 - k, y] = CELL_HL


def main():
    src = Image.open(SRC).convert("RGBA")
    clean = erase_medallions(src)

    out = Image.new("RGBA", (TW, TH), (0, 0, 0, 255))
    build_frame(clean, out)
    build_inner(clean, out)
    # 7배 축소라 나무결·금속 디테일이 뭉개진다 — 언샤프로 되살린다.
    out = out.filter(ImageFilter.UnsharpMask(radius=1.2, percent=90, threshold=2))

    px = out.load()
    for gsx in SLOT_X:                             # 격자는 인벤 + 핫바만
        for gsy in INV_Y:
            slot_cell(px, gsx, gsy)
        slot_cell(px, gsx, HOTBAR_Y)

    med = medallion_sprite(src, 18 * SCALE)        # 아이콘 칸(18x18)에 꽉 채움
    for s in ICON_SLOTS:
        gx = SLOT_X[s - 9] - 1
        out.alpha_composite(med, (gx * SCALE, (ICON_ROW_Y - 1) * SCALE))

    for name, ch, (gx, gy), (gw, gh) in TILES:
        tile = out.crop((gx * SCALE, gy * SCALE, (gx + gw) * SCALE, (gy + gh) * SCALE))
        tile.save(os.path.join(OUTDIR, name))
        adv = round(tile.width * gh / tile.height) + 1
        print(f"{name}: 텍스처 {tile.width}x{tile.height} → GUI {gw}x{gh} "
              f"(height={gh}, advance={adv}, char=U+{ord(ch):04X})")
    print("★gui.json 4타일 + space(-1,-177), SkillManager 타이틀 조립 필요")


if __name__ == "__main__":
    main()
