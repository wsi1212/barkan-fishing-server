#!/usr/bin/env python3
"""/레벨 허브 GUI 글리프(barkan:gui ) — 콘셉트 아트를 창 규격에 맞춰 후처리.

소스: gui-forge/src/level_hub_concept.png (1303x1207, 나무 프레임 + 상단 패널 + 하단 패널)
산출: assets/barkan/textures/gui/level_hub.png (176x168)

★허브는 27칸(3행)으로 맞춘다 — 상단 패널을 3행으로 잡으면 스킬 아이콘이 **가운데 행**에
  오고 메달리온 배경과 정확히 겹친다. 27칸에서도 가운데 행 중앙 5칸 = 슬롯 11~15라
  SkillManager.onHubClick(raw 11~15)은 수정 불필요.
★격자(슬롯 음각)는 플레이어 인벤·핫바에만 그린다. 상단 컨테이너는 깨끗한 패널로 두고
  메달리온만 얹는다 — 상단에 격자를 그리면 아트워크가 모눈종이가 된다.

27칸 창(176x168) 바닐라 좌표 — 슬롯 (sx,sy)의 텍스처 구멍은 (sx-1,sy-1) 18x18:
  컨테이너 3행 y17~70 (가운데 행 = y35~52) / "보관함" 라벨 y74 / 인벤 3행 y84~137
  홈 y138~141 / 핫바 y142~159 / 하단여백 y160~167 / 슬롯 가로 x7~168
  (imageHeight = 114 + rows*18, 인벤 y = 103 + 18k + (rows-4)*18, 핫바 y = 161 + (rows-4)*18)

기법은 섬상점과 동일 — 타이틀 비트맵 글리프로 창 전면을 덮는다.
  gui.json: ascent 13 (top = titleLabelY(6) + 7 - 13 = 0), height = 168 (렌더폭 = 텍스처폭)
  ★색 지정 필수(0xFFFFFF) — 안 주면 바닐라 라벨색 0x404040이 곱해져 밝기 25%가 된다.
"""
import os

from PIL import Image, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "src", "level_hub_concept.png")
OUT = os.path.expanduser(
    "~/development/barkan-resourcepack/assets/barkan/textures/gui/level_hub.png"
)
W, H = 176, 168

# ── 소스 구조 (측정값) ────────────────────────────────────────────────
SX_PANEL = (100, 1202)                # 패널 내부 가로 (청록 이너보더 안쪽)
MEDALLION = (558, 114, 748, 339)      # 3번(중앙) 메달리온 크롭
MED_BAND = (119, 349)                 # 메달리온이 걸친 세로 구간 (별 스파이크 포함, 지울 범위)
CLEAN_ROWS = (95, 116)                # 메달리온 위쪽 깨끗한 패널 행 — 지우기용 색 소스
# ★메달리온 사이를 타일링하면 안 된다: 원본 간격 224px < 메달리온 폭 186px라
#   "빈 구간"이 33px(x972~1004)뿐이고, 넓게 잡으면 옆 메달리온을 물어 격자로 복제된다.

# ── 세로 밴드: (대상 y0, 대상 y1, 소스 y0, 소스 y1) 끝 포함 ──────────
V_BANDS = [
    (0, 16, 24, 90),         # 상단 나무 프레임 + 청록 이너보더
    (17, 70, 91, 411),       # 상단 패널 내부 (컨테이너 3행) — 메달리온 지운 상태
    (71, 73, 423, 450),      # 나무 구분바
    (74, 83, 451, 468),      # 갭 — "보관함" 라벨(y74~81)이 여기 어두운 데 묻힌다
    (84, 159, 455, 1139),    # 하단 패널 내부 (인벤 3행 + 홈 + 핫바)
    (160, 167, 1140, 1176),  # 하단 나무 프레임
]
# ── 가로 밴드 ────────────────────────────────────────────────────────
H_BANDS = [
    (0, 6, 29, 99),          # 좌 나무 프레임 + 갭 + 이너보더
    (7, 168, 100, 1201),     # 패널 내부 = 슬롯 격자 폭
    (169, 175, 1202, 1272),  # 우 이너보더 + 갭 + 나무 프레임
]

# 슬롯 좌표
SLOT_X = [8 + c * 18 for c in range(9)]
ICON_ROW_Y = 36                        # 컨테이너 가운데 행 (셀 y35~52)
ICON_SLOTS = (11, 12, 13, 14, 15)      # 메달리온을 찍을 자리 (가운데 행 중앙 5칸)
INV_Y = [85, 103, 121]
HOTBAR_Y = 143

# 슬롯 셀 색 — 아트워크 팔레트에서 뽑음. 청록 하이라이트를 너무 밝게 하면
# 176px에서 격자가 청록 모눈종이처럼 튀어나온다(1차 시안 실패 원인).
CELL_IN = (10, 18, 22, 255)    # 패널보다 살짝 어두운 내부
CELL_SH = (4, 9, 11, 255)      # 위·좌 그림자
CELL_HL = (20, 44, 46, 255)    # 아래·우 청록 하이라이트

PANEL_LUM = 16                 # 상단 패널 배경 밝기 — 메달리온 키잉 기준값


def erase_medallions(src):
    """상단 패널의 메달리온 5개를 지운다 — 위쪽 깨끗한 행들의 **열별 평균색**으로 밴드를 덮는다.
    열별로 채우니 패널의 좌우 비네팅이 유지되고 반복 패턴이 생기지 않는다.
    (원본 간격 224px ≠ 슬롯 피치 18px라 지운 뒤 아이콘 자리에 다시 찍는다.)"""
    out = src.copy()
    px = out.load()
    y0, y1 = MED_BAND
    r0, r1 = CLEAN_ROWS
    n = r1 - r0
    for x in range(SX_PANEL[0], SX_PANEL[1]):
        acc = [0, 0, 0]
        for y in range(r0, r1):
            c = px[x, y]
            for i in range(3):
                acc[i] += c[i]
        col = (acc[0] // n, acc[1] // n, acc[2] // n, 255)
        for y in range(y0, y1):
            px[x, y] = col
    return out


def band_resample(src):
    """세로·가로 밴드를 각각 독립 스케일로 리샘플 — 프레임 두께를 지키면서 패널을 규격에 맞춘다."""
    hb = Image.new("RGBA", (W, src.height))
    for tx0, tx1, sx0, sx1 in H_BANDS:
        strip = src.crop((sx0, 0, sx1 + 1, src.height))
        hb.paste(strip.resize((tx1 - tx0 + 1, src.height), Image.LANCZOS), (tx0, 0))
    out = Image.new("RGBA", (W, H))
    for ty0, ty1, sy0, sy1 in V_BANDS:
        strip = hb.crop((0, sy0, W, sy1 + 1))
        out.paste(strip.resize((W, ty1 - ty0 + 1), Image.LANCZOS), (0, ty0))
    return out


def medallion_sprite(src, size=18):
    """메달리온을 밝기 키잉으로 뽑아 스프라이트로 — 배경(패널)은 투명하게.
    통째로 붙이면 소스 패널의 비네팅이 따라와 밝은 사각 패치로 보인다."""
    med = src.crop(MEDALLION).resize((size, size), Image.LANCZOS)
    med = med.filter(ImageFilter.UnsharpMask(radius=1, percent=120, threshold=1))
    px = med.load()
    for y in range(size):
        for x in range(size):
            r, g, b, _ = px[x, y]
            lum = (r * 2 + g * 5 + b) // 8
            px[x, y] = (r, g, b, max(0, min(255, (lum - PANEL_LUM) * 6)))
    return med


def slot_cell(px, sx, sy):
    """슬롯 한 칸(18x18) 음각 — 위·좌 그림자 / 아래·우 청록 하이라이트."""
    for y in range(sy - 1, sy + 17):
        for x in range(sx - 1, sx + 17):
            px[x, y] = CELL_IN
    for x in range(sx - 1, sx + 17):
        px[x, sy - 1] = CELL_SH
        px[x, sy + 16] = CELL_HL
    for y in range(sy - 1, sy + 17):
        px[sx - 1, y] = CELL_SH
        px[sx + 16, y] = CELL_HL
    px[sx - 1, sy + 16] = CELL_IN
    px[sx + 16, sy - 1] = CELL_IN


def main():
    src = Image.open(SRC).convert("RGBA")
    base = band_resample(erase_medallions(src))
    # LANCZOS 축소로 뭉개진 나무결·금속 디테일을 되살린다 (7배 축소라 필수).
    base = base.filter(ImageFilter.UnsharpMask(radius=1.2, percent=90, threshold=2))
    px = base.load()

    # 격자는 플레이어 인벤 + 핫바만 (36칸). 상단 컨테이너 3행은 패널 그대로 둔다.
    for sx in SLOT_X:
        for sy in INV_Y:
            slot_cell(px, sx, sy)
        slot_cell(px, sx, HOTBAR_Y)

    # 메달리온을 아이콘 슬롯(가운데 행)에 다시 찍는다 — 칸 18x18에 꽉 채워 아이콘과 정합.
    med = medallion_sprite(src, 18)
    for s in ICON_SLOTS:
        base.alpha_composite(med, (SLOT_X[s - 9] - 1, ICON_ROW_Y - 1))

    base.save(OUT)
    print(f"저장: {OUT} ({base.width}x{base.height})")
    print("★gui.json: level_hub ascent 13 / height 168 / file barkan:gui/level_hub.png")
    print("★SkillManager: 허브 인벤 27칸 + 배경 채움판 제거 + 드래그 가드 필요")


if __name__ == "__main__":
    main()
