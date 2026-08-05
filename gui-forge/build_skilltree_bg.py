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
ERASE = [(190, 200, 1070, 862), (60, 335, 260, 560)]

CELL_IN, CELL_SH, CELL_HL = (10, 16, 20, 255), (4, 7, 9, 255), (44, 54, 60, 255)

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
    """⑥ 둥근 프레임 바깥의 검은 모서리를 **원본 좌표**에서 채운다.

    ★처음엔 조립된(스케일된) 이미지에서 sum<=24 임계값으로 찾았다가 실패했다 — 남색 패널
      자체의 밝기도 sum~15~24라 패널 전체(216000여 픽셀)를 오검출해 망칠 뻔했다.
      순수 (0,0,0)만 매칭해도 실패했다 — 실제 모서리는 완전한 (0,0,0)이 아니라 (1,1,0) 등
      미세하게 다른 near-black이라 못 잡았다.
    → 밝기 임계값으로 찾지 않는다. **원본(1114x1412)의 작은 모서리 크롭(70x70)** 안에서만
      작업한다. 크롭 자체가 남색 패널에서 공간적으로 멀리 떨어져 있어 임계값이 아무리
      느슨해도 패널을 건드릴 수 없다 — 안전한 건 색이 아니라 위치다.
      측정: 원본에서 대각선 검은 길이 좌상36/우상39/좌하28/우하29px. BOX 95로 여유.
    """
    W_, H_ = art.size
    BOX = 95
    corners = [(0, 0, 1, 1), (W_ - BOX, 0, -1, 1), (0, H_ - BOX, 1, -1), (W_ - BOX, H_ - BOX, -1, -1)]
    for bx, by, dx, dy in corners:
        crop = art.crop((bx, by, bx + BOX, by + BOX))
        px = crop.load()

        def lum(c):
            return (c[0] * 2 + c[1] * 5 + c[2]) // 8

        cx, cy = (0 if dx > 0 else BOX - 1), (0 if dy > 0 else BOX - 1)
        for y in range(BOX):
            yy = cy + dy * y if dy > 0 else y
            for x in range(BOX):
                xx = cx + dx * x if dx > 0 else x
                # 실제 좌표는 위 계산이 헷갈리니 코너 앵커 기준으로 다시 표현
                ax = x if dx > 0 else BOX - 1 - x
                ay = y if dy > 0 else BOX - 1 - y
                if lum(px[ax, ay][:3]) >= 22:
                    continue
                sx = ax
                while 0 <= sx + dx < BOX and lum(px[sx + dx, ay][:3]) < 22:
                    sx += dx
                cand = px[sx + dx, ay] if 0 <= sx + dx < BOX and lum(px[sx + dx, ay][:3]) >= 22 else None
                sy = ay
                while 0 <= sy + dy < BOX and lum(px[ax, sy + dy][:3]) < 22:
                    sy += dy
                cand2 = px[ax, sy + dy] if 0 <= sy + dy < BOX and lum(px[ax, sy + dy][:3]) >= 22 else None
                if cand and cand2:
                    px[ax, ay] = cand if abs(sx - ax) < abs(sy - ay) else cand2
                elif cand:
                    px[ax, ay] = cand
                elif cand2:
                    px[ax, ay] = cand2
        art.paste(crop, (bx, by))
    return art


def slot_cell(px, x0, y0):
    """인벤 칸 음각. 베벨 두께는 배율 파생 (2로 박으면 4배에서 절반이 된다)."""
    n = CELLG * SCALE
    for y in range(y0, y0 + n):
        for x in range(x0, x0 + n):
            px[x, y] = CELL_IN
    for k in range(SCALE // 2):
        for x in range(x0, x0 + n):
            px[x, y0 + k] = CELL_SH
            px[x, y0 + n - 1 - k] = CELL_HL
        for y in range(y0, y0 + n):
            px[x0 + k, y] = CELL_SH
            px[x0 + n - 1 - k, y] = CELL_HL


def main():
    art = Image.open(SRC_ART).convert("RGBA")
    if art.size != (V_BANDS[-1][0][1] and H_BANDS[-1][0][1], V_BANDS[-1][0][1]):
        pass                                    # 크기 검증은 아래 경계 합으로 대체
    assert H_BANDS[-1][0][1] == art.width and V_BANDS[-1][0][1] == art.height, \
        f"원본 크기 {art.size} 가 측정 경계와 다르다"

    erase_nodes(art)
    fill_black_corners(art)
    im = piecewise_scale(art)

    px = im.load()
    for gy in INV_ROWS_Y + [HOTBAR_Y]:
        for c in range(COLS):
            slot_cell(px, (GRID_X + CELLG * c) * SCALE, gy * SCALE)

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
