#!/usr/bin/env python3
"""스킬 특성 트리 GUI(45칸, 176x204) 레이아웃 가이드 생성 — 이미지 생성기에 첨부용.

MC 상자 GUI는 슬롯 좌표가 코드에 박혀 있어서 배경 아트의 노드 위치가 그 격자에
맞아야 한다(안 맞으면 노드 아이템이 그려진 소켓 밖에 뜬다).

슬롯 s → col = s%9, row = s//9
  ★칸(텍스처 구멍) 좌상단 = (7 + 18*col, 17 + 18*row), 18x18
    아이템 16x16은 그 안 (8 + 18*col, 18 + 18*row) — 칸이 아이템보다 1px 위·왼쪽에서 시작
    칸 중심 = (16 + 18*col, 26 + 18*row)
  검증: generic_54.png로 5행 창을 조립해 스캔하니 아이템 밝은 구간이 x=8,26,44…152에서
        시작 → 격자 x7~168, 프레임 좌 0~6 / 우 169~175 (마커는 칸 사각형에 원을 내접시켜
        반올림 오차를 없앤다)

SkillTreeManager.openTree 기준 실제 배치:
  0 뒤로 · 1 이전페이지 · 4 레벨정보 · 7 다음페이지 · 8 초기화   (상단 행)
  루트 = 슬롯 18 (좌측, row2)
  계열 노드 = 11/13/15/17, 20/22/24/26, 29/31/33/35, (낚시만) 38/40/42/44
  연결선 화살표 아이템 = 노드 사이 칸 + 계열 시작 왼쪽 (10/12/14/16, 19/21/23/25, ...)
  낚시 page1 = 잭팟 4개만 (11/20/29/38)
  플레이어 인벤 3행 y=121/139/157, 핫바 y=179 (칸 기준)

★2026-08-03: 6행 54칸 → 5행 45칸. 상단 UI 1행 + 계열 최대 4행이면 6행째가 늘 비어서 없앴다.
  없앤 건 45~53뿐이라 노드/화살표 슬롯 번호는 그대로. 창 높이 = 114 + 5*18 = 204.
"""
import os

from PIL import Image, ImageDraw, ImageFont

OUT = os.path.expanduser("~/Downloads")
GW, GH = 176, 204
FONT = "/System/Library/Fonts/AppleSDGothicNeo.ttc"

# 계열 노드 슬롯 (행별)
BRANCH_ROWS = [[11, 13, 15, 17], [20, 22, 24, 26], [29, 31, 33, 35], [38, 40, 42, 44]]
RAIL_ROWS = [[10, 12, 14, 16], [19, 21, 23, 25], [28, 30, 32, 34], [37, 39, 41, 43]]
ROOT = 18
UI_TOP = [0, 1, 4, 7, 8]
INV_ROWS = [[45 + i for i in range(9)]]      # 표시용(실제 플레이어 인벤은 별 좌표)
PLAYER_INV_Y = [121, 139, 157]
HOTBAR_Y = 179

C_BG = (18, 22, 26)
C_GRID = (70, 78, 86)
C_NODE = (60, 220, 220)
C_ROOT = (255, 205, 90)
C_RAIL = (40, 120, 130)
C_UI = (230, 80, 80)
C_INV = (120, 130, 140)
C_FRAME = (150, 110, 60)


def cell(s):
    """칸(텍스처 구멍) 좌상단 — 아이템 좌상단보다 1px 위·왼쪽."""
    return (7 + 18 * (s % 9), 17 + 18 * (s // 9))


def guide(layout, scale, label):
    """layout: 'branch4' | 'branch3' | 'page2'"""
    W, H = GW * scale, GH * scale
    im = Image.new("RGB", (W, H), C_BG)
    d = ImageDraw.Draw(im)
    f = ImageFont.truetype(FONT, max(10, scale * 3))
    fs = ImageFont.truetype(FONT, max(9, scale * 2))

    def box(x, y, w, h, col, width=1, fill=None):
        d.rectangle([x * scale, y * scale, (x + w) * scale - 1, (y + h) * scale - 1],
                    outline=col, width=width, fill=fill)

    # 프레임 링 7px
    box(0, 0, GW, GH, C_FRAME, max(1, scale // 3))
    box(7, 7, GW - 14, GH - 14, C_FRAME, max(1, scale // 4))
    d.text((9 * scale, 9 * scale), "프레임 7px", font=fs, fill=C_FRAME)

    # 전체 슬롯 격자 (옅게)
    for s in range(45):
        x, y = cell(s)
        box(x, y, 18, 18, C_GRID, 1)

    # 상단 UI 아이템 칸
    for s in UI_TOP:
        x, y = cell(s)
        box(x, y, 18, 18, C_UI, max(1, scale // 3))
    d.text((cell(0)[0] * scale, (cell(0)[1] - 6) * scale),
           "▼ 상단 UI 아이템 — 아트 넣지 말 것", font=fs, fill=C_UI)

    rows = {"branch4": BRANCH_ROWS, "branch3": BRANCH_ROWS[:3],
            "page2": [[11], [20], [29], [38]]}[layout]
    rails = {"branch4": RAIL_ROWS, "branch3": RAIL_ROWS[:3],
             "page2": [[10], [19], [28], [37]]}[layout]

    # 연결선 자리 (노드 사이 = 화살표 아이템)
    for rr in rails:
        for s in rr:
            x, y = cell(s)
            box(x, y, 18, 18, C_RAIL, max(1, scale // 4))

    # 노드 자리
    for rr in rows:
        for s in rr:
            x, y = cell(s)
            d.ellipse([x * scale, y * scale, (x + 18) * scale - 1, (y + 18) * scale - 1],
                      outline=C_NODE, width=max(1, scale // 2))
            d.text(((x + 1) * scale, (y + 1) * scale), str(s), font=fs, fill=C_NODE)

    # 루트
    x, y = cell(ROOT)
    d.ellipse([x * scale, y * scale, (x + 18) * scale - 1, (y + 18) * scale - 1],
              outline=C_ROOT, width=max(1, scale // 2))
    d.text(((x + 1) * scale, (y + 1) * scale), "root", font=fs, fill=C_ROOT)

    # 플레이어 인벤 / 핫바
    for gy in PLAYER_INV_Y + [HOTBAR_Y]:
        for c in range(9):
            box(7 + 18 * c, gy - 1, 18, 18, C_INV, 1)
    d.text((10 * scale, (PLAYER_INV_Y[0] - 9) * scale),
           "▼ 플레이어 인벤/핫바 — 장식 없는 패널 + 칸 음각만", font=fs, fill=C_INV)

    d.text((6 * scale, (GH - 12) * scale), label, font=f, fill=(235, 235, 240))
    return im


def overlay(art_path, layout, scale=5, brighten=2.2):
    """실제 생성된 아트워크 위에 목표 노드 자리를 겹친다 — 생성기에 "이 자리로 옮겨라"용.

    전체 슬롯 격자는 그리지 않는다(노이즈). 노드 원·루트·연결선 칸·상단 UI 칸만 표시.
    아트는 목표 창 비율(176x204)로 맞춘다 — 222로 만든 구본은 세로가 8% 눌려 보인다.
    """
    from PIL import ImageEnhance
    art = Image.open(os.path.expanduser(art_path)).convert("RGB")
    art = ImageEnhance.Brightness(art).enhance(brighten)
    im = art.resize((GW * scale, GH * scale), Image.LANCZOS)
    d = ImageDraw.Draw(im)
    fs = ImageFont.truetype(FONT, max(10, scale * 2))
    f = ImageFont.truetype(FONT, max(12, scale * 3))
    rows = {"branch4": BRANCH_ROWS, "branch3": BRANCH_ROWS[:3],
            "page2": [[11], [20], [29], [38]]}[layout]
    rails = {"branch4": RAIL_ROWS, "branch3": RAIL_ROWS[:3],
             "page2": [[10], [19], [28], [37]]}[layout]

    for rr in rails:                                  # 연결선 칸 (화살표 아이템)
        for sl in rr:
            x, y = cell(sl)
            d.rectangle([x * scale, y * scale, (x + 18) * scale - 1, (y + 18) * scale - 1],
                        outline=(60, 170, 180), width=max(1, scale // 3))
    for sl in UI_TOP:                                 # 상단 UI 칸
        x, y = cell(sl)
        d.rectangle([x * scale, y * scale, (x + 18) * scale - 1, (y + 18) * scale - 1],
                    outline=C_UI, width=max(2, scale // 2))
    for rr in rows:                                   # 노드 자리
        for sl in rr:
            x, y = cell(sl)
            d.ellipse([x * scale, y * scale, (x + 18) * scale - 1, (y + 18) * scale - 1],
                      outline=(255, 60, 60), width=max(2, scale // 2))
            d.text((x * scale + 2, y * scale + 1), str(sl), font=fs, fill=(255, 120, 120))
    x, y = cell(ROOT)                                 # 루트
    d.ellipse([x * scale, y * scale, (x + 18) * scale - 1, (y + 18) * scale - 1],
              outline=C_ROOT, width=max(2, scale // 2))
    d.text((x * scale + 2, y * scale + 1), "root", font=fs, fill=C_ROOT)
    for gy in PLAYER_INV_Y + [HOTBAR_Y]:              # 인벤/핫바 행 (옅게)
        d.rectangle([7 * scale, (gy - 1) * scale, 169 * scale, (gy + 17) * scale],
                    outline=(110, 120, 130), width=1)
    d.text((8 * scale, (GH - 10) * scale),
           "빨간 원 = 노드 / 금색 = 루트 / 청록 칸 = 연결선 / 캔버스 352x408",
           font=f, fill=(255, 230, 230))
    return im


def main():
    specs = [("branch4", "낚시 page1 — 근원 + 4계열x4노드"),
             ("branch3", "채굴/재배/요리/수집 page1 — 근원 + 3계열x4노드"),
             ("page2", "낚시 page2 — 잭팟 4개 (세로 한 줄)")]
    # 1) 생성기 첨부용 개별 가이드 (8배 = 1408x1776)
    for key, lab in specs:
        im = guide(key, 8, lab)
        p = os.path.join(OUT, f"skilltree_guide_{key}_1408x1632.png")
        im.save(p)
        print(f"저장: {p} ({im.width}x{im.height})")
    # 2) 한눈에 보는 대조 시트
    sheet = Image.new("RGB", (GW * 4 * 3 + 40, GH * 4 + 20), (12, 14, 16))
    for i, (key, lab) in enumerate(specs):
        sheet.paste(guide(key, 4, lab), (10 + i * (GW * 4 + 10), 10))
    p = os.path.join(OUT, "skilltree_guide_sheet.png")
    sheet.save(p)
    print(f"저장: {p} ({sheet.width}x{sheet.height})")

    # 3) 실제 아트워크 위 오버레이
    arts = [("branch4", "~/Downloads/barkan_skilltree_page1_4branches_connector_fixed_source.png"),
            ("branch3", "~/Downloads/barkan_skilltree_page1_3branches_divider_fixed_source.png"),
            ("page2", "~/Downloads/barkan_skilltree_page2_4nodes_source.png")]
    for key, art in arts:
        if not os.path.exists(os.path.expanduser(art)):
            print(f"  - {key}: 아트 없음 {art}"); continue
        im = overlay(art, key)
        p = os.path.join(OUT, f"skilltree_overlay_{key}.png")
        im.save(p)
        print(f"저장: {p} ({im.width}x{im.height})")


if __name__ == "__main__":
    main()
