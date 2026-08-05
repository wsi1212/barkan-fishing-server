#!/usr/bin/env python3
"""특성 트리 **공용** 배경 조립 — 원본 아트에서 노드/선을 걷어낸 빈 판을 만든다.

산출: assets/barkan/textures/gui/tree_bg_r{0..3}c{0..2}.png (12타일)
      + src/skilltree/_providers.json, _glyph.txt (폰트 등록용 — 손계산 금지)

===============================================================================
설계 원칙 (2026-08-04 전면 재작성 — 패치 누적을 버리고 규칙을 명시)
===============================================================================
① 노드 소켓·연결선은 배경에 없다. 전부 **아이템 아이콘**으로 올린다.
   → 3계열/4계열/2페이지가 배경 1장을 공유한다. 새 숙련이 생겨도 아트 작업 0.

② 배경은 원본 아트에서 만든다. Codex 조각 9슬라이스 조립은 나무 색이 원본과 천지차이라 버렸다.

③ **진짜 원본은 1114x1412** 고해상도다(바탕화면 exec-c019...png). 352x408은 저해상도 파생본이라
   프레임 장식이 이미 죽어 있었다. 원본을 쓰면 좌프레임이 56 art px → 28 텍스처 px(0.5배 축소)로
   장식이 훨씬 살아난다.
   ★단 **비율이 다르다**: 원본 0.789 vs 창 0.863. 통째 리사이즈하면 프레임이 뭉개지고 슬롯
   격자와 안 맞는다 → **구간별 독립 스케일(측정 기반 9슬라이스)** 로 매핑한다.
   원본이 좌우 대칭으로 그려져 있어 별도 미러링이 필요 없다.

④ **원본을 최대한 건드리지 않는다.** 나무 기둥·테두리·소켓은 원본 그대로 두고
   **연결선(레일)만** 지운다. 지금까지 터진 것 전부가 "더 많이 지우려다" 생겼다:
     · 원(circle)으로 소켓 삭제 → 원본이 기둥에 파놓은 알코브(홈)가 빈 구멍으로 남아 찢어짐
     · row0 띠(36px) 복제 → 그 안의 불규칙이 36px마다 되풀이 → 테두리 점선, 기둥 삼각 노치
     · row0 한 줄 반복 → 세로로 완전 균일해져 **벽면이 일자 줄무늬**로 깨짐
   소켓을 남기면 아이콘이 그 위에 얹히는데, 원본이 애초에 그렇게 설계된 판이다(알코브+소켓).
   레일만 지우는 이유: 구워진 레일은 밝기가 고정이라 잠긴 경로도 켜진 것처럼 보인다.
   레일 칸(홀수 열)은 패널 벽면 한복판이라 row0 띠 복제로 지워도 티가 안 난다.

   대가: 계열 행이 3개인 트리는 4번째 행에 **빈 소켓 4개**가 남는다(레일은 없음).
   "아직 해금 안 된 자리"로 읽히고, 벽면을 깨는 것보다 낫다고 판단했다.

⑤ 해상도 = GUI × SCALE. 원본이 2배라 4배는 정수배 확대(무손실).
   폰트 아틀라스 256px 제한 → 3열 × 4행 12타일. 열 GUI 59/59/58 · 행 51×4.

좌표는 전부 GUI 기하에서 유도한다(하드코딩 금지 — 배율 바꿀 때 어긋난다).
"""
import json
import os

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
OUTDIR = os.path.expanduser("~/development/barkan-resourcepack/assets/barkan/textures/gui")
SRC_ART = os.path.join(HERE, "src", "skilltree", "tree_bg_source.png")   # 진짜 원본(1114x1412) 커밋본

SCALE = 4                       # GUI 배율 (원본 아트는 2배)
GW, GH = 176, 204               # GUI 창 크기
W, H = GW * SCALE, GH * SCALE

# ── GUI 기하 (MC 상자 규격) ─────────────────────────────────────
GRID_X, GRID_Y = 7, 17          # 슬롯 격자 원점
CELLG = 18                      # 칸 크기
COLS, ROWS = 9, 5               # 트리 창 = 9x5
INV_ROWS_Y = [121, 139, 157]    # 플레이어 인벤 3행 칸 top
HOTBAR_Y = 179

# ── 원본 구간 경계 (측정값, 1114x1412) → GUI 구간 ────────────
#   세로: 상단프레임 / 트리패널 / 구분밴드 / 인벤패널 / 하단프레임
#   가로: 좌프레임 / 패널 / 우프레임
V_BANDS = [((0, 55), (0, 17)), ((55, 866), (17, 107)), ((866, 900), (107, 121)),
           ((900, 1379), (121, 197)), ((1379, 1412), (197, 204))]
H_BANDS = [((0, 56), (0, 7)), ((56, 1060), (7, 169)), ((1060, 1114), (169, 176))]

# 소켓·레일을 덮을 깨끗한 패널 텍스처 (측정: 최대 밝기 23 = 완전 무장식)
CLEAN_BOX = (300, 100, 900, 210)
# 지울 영역 (원본 좌표) — 소켓 4행 + 레일 + 근원.
#   ★2차 실사고: y920까지 늘렸다가 **구분 밴드(y866~900)를 통째로 삼켜서 나무 밴드가
#     사라졌다.** 4행 링이 y899까지 뻗은 건 실제로 원래 나무 밴드가 그 위를 덮어서
#     안 보이던 부분이었다 — 거기까지 지울 필요가 없었다. 밴드 시작(866) 직전까지만.
#   ★root box도 x35로 좁혔다가 **좌프레임(0~56)을 침범**해 나무에 네모난 자국이 남았다.
#     프레임을 안 건드리도록 x60(패널 시작) 이상만 지운다.
#   ★3차 실사고: 우측 x1070까지 지웠더니 **패널 우측 가장자리의 장식 테두리(좌측 근원
#     주변과 대칭인 청록 발광+삼각 스파이크 띠, x1048부터 시작)를 절반 삼켰다.**
#     열별 밝기 스캔으로 확인: 4열 소켓 링은 x968에서 끝나고, 그 테두리 띠는 x1048에서
#     시작 — 사이 968~1048은 완전히 빈 안전지대. 우측 경계를 그 안전지대 안(1010)으로.
ERASE = [(190, 200, 1010, 862), (60, 335, 260, 560)]

# ★2배(SH=상+좌 어두움 / HL=하+우 밝음) 비대칭 베벨이었다. SH는 CELL_IN과 거의 구분이
#   안 될 만큼 어두워 안 보이고, HL만 밝게 도드라져 매 칸의 하단·우측에 밝은 선이 남았다.
#   그 밝은 선이 "다음 칸의 왼쪽·위 여백"처럼 읽혀 매 칸마다 여백 있는 것처럼 보였다
#   (실사고 스크린샷 확인). 4면 전부 같은 톤(GRID)의 얇은 선으로 통일 — 비대칭 착시 제거.
CELL_IN, CELL_GRID = (10, 16, 20, 255), (26, 36, 42, 255)

COL_GUI = [59, 59, 58]          # 타일 열 (합 176)
ROW_GUI = [51, 51, 51, 51]      # 타일 행 (합 204)


def tile_boxes():
    out, gy = [], 0
    for r, gh in enumerate(ROW_GUI):
        gx = 0
        for c, gw in enumerate(COL_GUI):
            out.append((f"r{r}c{c}", (gx * SCALE, gy * SCALE,
                                      (gx + gw) * SCALE, (gy + gh) * SCALE), gw, gh, (gx, gy)))
            gx += gw
        gy += gh
    return out


def erase_nodes(art):
    """소켓·레일을 깨끗한 패널 텍스처로 덮는다(원본 좌표에서). 노드·선은 아이템이 담당."""
    cx0, cy0, cx1, cy1 = CLEAN_BOX
    patch = art.crop(CLEAN_BOX)
    for x0, y0, x1, y1 in ERASE:
        for y in range(y0, y1, patch.height):
            for x in range(x0, x1, patch.width):
                art.paste(patch.crop((0, 0, min(patch.width, x1 - x),
                                      min(patch.height, y1 - y))), (x, y))
    return art


def piecewise_scale(art):
    """③ 구간별 독립 스케일 — 프레임은 살리고 패널만 크게 줄인다."""
    out = Image.new("RGBA", (W, H))
    for (ay0, ay1), (gy0, gy1) in V_BANDS:
        for (ax0, ax1), (gx0, gx1) in H_BANDS:
            tw, th = (gx1 - gx0) * SCALE, (gy1 - gy0) * SCALE
            out.paste(art.crop((ax0, ay0, ax1, ay1)).resize((tw, th), Image.LANCZOS),
                      (gx0 * SCALE, gy0 * SCALE))
    return out


def fill_black_corners(art):
    """(★현재 미사용 — main()에서 호출 안 함)

    둥근 프레임 바깥의 검은 모서리를 nearest-fill로 채워보려 했으나, **우상단 모서리에는
    원본 프레임 장식(해골 모티프, 은색/구리색)이 있다.** 이 함수가 그 장식의 밝은 픽셀을
    소스로 집어 프레임 바깥 검은 영역까지 끌고 나가 버려서, 게임에서 보면 해골 장식 일부가
    프레임 밖으로 스며나온 회색 돌기처럼 보였다(실사고 스크린샷 확인).
    작은 검은 삼각 모서리를 그대로 두는 편이 이 부작용보다 훨씬 낫다 — 그래서 호출을 뺐다.
    함수는 참고용으로 남겨둔다.
    """
    return art


def fill_cell(px, x0, y0):
    """칸 내부만 채운다 — 테두리는 draw_grid_lines()가 **경계당 한 번만** 그린다.

    ★이전엔 칸마다 자기 4면에 독립적으로 2px 테두리를 그렸다. 인접한 두 칸이 만나는
      경계에서는 그게 합쳐져 4px(2+2)가 되는데, 창틀에 붙은 바깥 경계는 이웃이 없어
      2px뿐이다. 내부 격자선이 바깥 테두리보다 두 배 두꺼워지는 비일관성이 실제
      게임에서 '깨져 보인다'는 제보로 확인됐다(스킬 선택 화면과 비교해서 확실히 드러남).
      경계선을 좌표당 정확히 한 번만 긋도록 분리한다.
    """
    n = CELLG * SCALE
    for y in range(y0, y0 + n):
        for x in range(x0, x0 + n):
            px[x, y] = CELL_IN


def draw_grid_lines(px, cols_x, rows_y, cell_px):
    """세로선은 각 열 경계마다, 가로선은 각 행 경계마다 **정확히 한 번씩만** 긋는다.

    rows_y: 서로 이어진(칸 사이 빈틈 없는) 행 top y 좌표 리스트 — 이 블록 안에서만
    가로선을 잇는다. 인벤 3행과 핫바처럼 사이에 갭이 있는 블록은 따로 호출한다.
    """
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


def main():
    art = Image.open(SRC_ART).convert("RGBA")
    if art.size != (V_BANDS[-1][0][1] and H_BANDS[-1][0][1], V_BANDS[-1][0][1]):
        pass                                    # 크기 검증은 아래 경계 합으로 대체
    assert H_BANDS[-1][0][1] == art.width and V_BANDS[-1][0][1] == art.height, \
        f"원본 크기 {art.size} 가 측정 경계와 다르다"

    erase_nodes(art)
    im = piecewise_scale(art)

    px = im.load()
    for gy in INV_ROWS_Y + [HOTBAR_Y]:
        for c in range(COLS):
            fill_cell(px, (GRID_X + CELLG * c) * SCALE, gy * SCALE)
    cell_px = CELLG * SCALE
    cols_x = [(GRID_X + CELLG * c) * SCALE for c in range(COLS)]
    draw_grid_lines(px, cols_x, [y * SCALE for y in INV_ROWS_Y], cell_px)   # 인벤 3행
    draw_grid_lines(px, cols_x, [HOTBAR_Y * SCALE], cell_px)                # 핫바(별도 블록)

    os.makedirs(OUTDIR, exist_ok=True)
    for f in os.listdir(OUTDIR):
        if f.startswith("tree_bg_"):
            os.remove(os.path.join(OUTDIR, f))
    providers, glyph, code = [], [], 0xE606
    for i, (name, box, gw, gh, (gx, gy)) in enumerate(tile_boxes()):
        crop = im.crop(box)
        assert max(crop.size) <= 256, f"{name} {crop.size} — 아틀라스 256px 초과"
        crop.save(os.path.join(OUTDIR, f"tree_bg_{name}.png"))
        ch = chr(code + i)
        providers.append({"type": "bitmap", "file": f"barkan:gui/tree_bg_{name}.png",
                          "ascent": 13 - gy, "height": gh, "chars": [ch]})
        glyph.append("\\uf801" if i == 0 else ("\\uf803" if gx == 0 else "\\uf802"))
        glyph.append(f"\\u{ord(ch):04x}")
    sd = os.path.join(HERE, "src", "skilltree")
    json.dump(providers, open(os.path.join(sd, "_providers.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    open(os.path.join(sd, "_glyph.txt"), "w", encoding="utf-8").write("".join(glyph))
    im.save(os.path.join(sd, "_preview_full.png"))
    print(f"tree_bg_* 12타일 ({SCALE}배, 좌우 대칭, 레일만 제거)")


if __name__ == "__main__":
    main()
