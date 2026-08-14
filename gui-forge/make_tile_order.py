#!/usr/bin/env python3
"""타일형 허브(메뉴 계열) 분리 발주 — 배경 · 타일 액자 · 아이콘을 따로 받는다.

## 왜 형식을 또 바꾸나
메뉴·내 정보·상점은 **완성 목업 한 장**을 받아 거기서 아이콘을 뜯어내 우리 좌표에 다시
얹었다(compose_gui3_imagegen.lift_icon — 덩어리 분석으로 몰딩을 걷어내는 휴리스틱).
생성물의 타일 격자가 우리 격자와 안 맞아서 생긴 우회로다. 판(plate) 쪽에서 배경과 액자를
따로 받아 좌표를 코드가 잡자 0px 이 나왔으므로(assemble_plate), 타일도 같은 길로 간다.

## 세 조각
  1) 배경    타일이 없는 빈 판. 타일이 덮을 자리는 해치로 표시 — 거기엔 장식 금지.
  2) 타일 액자  한 장. 3열x2행(216x144) 로 줄여 6곳에 코드가 찍는다.
  3) 아이콘   타일마다 한 장(마젠타 바탕). 아래 라벨 띠를 뺀 자리에 비율 유지로 들어간다.
글자는 발주하지 않는다 — 아그로체로 코드가 굽는다(발주 글자는 폰트·자간이 매번 다르다).

사용: python3 make_tile_order.py <허브이름>
산출: src/<이름>/_order_bg.png · _order_tile.png · _order_icons.png
"""
import os
import sys
import textwrap

from PIL import Image, ImageDraw

import make_order_sheets as O
import make_page_layouts as L
import make_parts_order as P

HERE = os.path.dirname(os.path.abspath(__file__))
S, GX, GY, CELL, COLS = L.SCALE, L.GRID_X, L.GRID_Y, L.CELL, L.COLS
HI, DIM = O.HI, O.DIM

LABEL_BAND = 40          # 타일 아래 글자 전용 띠(compose_gui3_imagegen 과 같은 값)
ICON_CANVAS = 256        # 아이콘 발주 캔버스
KEY = (255, 0, 255, 255)

# 허브별 타일 설명 — 그림쟁이가 "무엇을 그리는지" 알아야 아이콘이 산다.
TILE_NOTE = {
    "guild": {
        "길드 섬": "길드 전용 섬으로 가는 문. 바다 위 작은 섬 + 깃발, 또는 부두의 나룻배.",
        "업그레이드": "길드 시설을 키우는 곳. 모루와 설계도, 올라가는 화살표.",
        "기부": "길드 계좌에 돈을 넣는다. 금화가 떨어지는 헌금함/금고.",
        "길드원": "명단과 접속 현황. 겹친 인물 실루엣 또는 명부.",
        "랭킹": "길드 순위. 단상·월계관·트로피.",
        "엠블럼": "길드 문장을 그리고 고친다. 방패꼴 문장 + 붓/팔레트.",
    },
}


def tile_boxes(name):
    for label, col, row, wc, hr in L.TILES[name]:
        x0, y0 = (GX + CELL * col) * S, (GY + CELL * row) * S
        yield label, (x0, y0, x0 + CELL * wc * S - 1, y0 + CELL * hr * S - 1)


def bg_plate(name):
    rows = 6
    W, H = 176 * S, (114 + rows * CELL) * S
    im = Image.new("RGBA", (W, H), P.PLATE_BG)
    d = ImageDraw.Draw(im, "RGBA")
    d.rectangle([6, 6, W - 7, H - 7], outline=P.EDGE, width=4)
    d.rounded_rectangle([GX * S, L.TITLE_Y0, (GX + CELL * COLS) * S - 1, L.TITLE_Y1],
                        radius=8, outline=P.REGION, width=3)
    n = 0
    for _, box in tile_boxes(name):
        P.hatch(d, box, P.KEEP, step=18)
        n += 1
    # 아래 아이콘 줄·상단 정보칸은 아이템이 올라간다 — 그 자리도 비워 둔다
    _, roles, _ = L.PAGES[name]
    for slot, (role, _lab) in sorted(roles.items()):
        if role == "장식":
            continue
        r, c = divmod(slot, COLS)
        x0, y0 = (GX + CELL * c) * S, (GY + CELL * r) * S
        P.hatch(d, (x0, y0, x0 + CELL * S - 1, y0 + CELL * S - 1), P.KEEP)
        n += 1
    inv_y0 = 30 + rows * CELL
    for gy in (inv_y0, inv_y0 + CELL, inv_y0 + 2 * CELL, inv_y0 + 58):
        for c in range(COLS):
            x0 = (GX + CELL * c) * S
            P.hatch(d, (x0, gy * S, x0 + CELL * S - 1, gy * S + CELL * S - 1), P.KEEP)
            n += 1
    return im, n


def tile_plate(name):
    """액자 두 장 — 큰 타일(3열x2행)과 작은 칸(1칸).

    ★작은 칸 액자를 같이 받아야 한다. 아래 아이콘 줄과 상단 정보칸도 '코드가 얹는' 자리로
      비워 두라고 해 놓고 정작 찍을 액자가 없으면, 그 칸들만 맨바닥이 된다(첫 시트의 구멍).
    """
    tw, th = CELL * 3 * S, CELL * 2 * S          # 216 x 144
    k = 2
    W, H = tw * k, th * k
    top = 74
    gap = 40
    small = P.F_CANVAS                            # 512 — 판(plate) 발주와 같은 규격
    im = Image.new("RGBA", (max(W, 1) + gap + small, max(H, small) + top), (26, 26, 30, 255))
    d = ImageDraw.Draw(im, "RGBA")
    # ── 오른쪽: 작은 칸 액자(구멍 384 · 테두리 24) ─ 판 발주와 같은 규격이라 조립기가 그대로 쓴다
    sx = W + gap
    d.text((sx + 4, 8), "2) 작은 칸 액자 1장", font=O.font(26), fill=HI)
    d.text((sx + 4, 42), f"캔버스 {small}x{small} · 액자 외곽 {P.F_HOLE + 2 * P.F_BORDER}"
                         f" · 구멍 {P.F_HOLE}", font=O.font(20), fill=DIM)
    d.rectangle([sx, top, sx + small - 1, top + small - 1], fill=KEY)
    o = (small - P.F_HOLE - 2 * P.F_BORDER) // 2
    d.rectangle([sx + o, top + o, sx + small - o - 1, top + small - o - 1],
                outline=(80, 80, 90, 255), width=2)
    hx, hy = sx + o + P.F_BORDER, top + o + P.F_BORDER
    d.rectangle([hx, hy, hx + P.F_HOLE - 1, hy + P.F_HOLE - 1],
                fill=(40, 40, 46, 255), outline=(120, 200, 255, 255), width=2)
    d.text((hx + 10, hy + 10), "구멍 = 비운다", font=O.font(24), fill=(150, 210, 255))
    # ★부제가 캔버스 폭(432)을 넘으면 오른쪽 액자 제목과 겹쳐 읽을 수 없게 된다(실측).
    d.text((4, 8), f"1) 큰 타일 액자 - {W}x{H}", font=O.font(26), fill=HI)
    d.text((4, 42), f"게임에선 {tw}x{th} 로 줄인다", font=O.font(20), fill=DIM)
    d.rectangle([0, top, W - 1, top + H - 1], fill=KEY)
    d.rectangle([6, top + 6, W - 7, top + H - 7], outline=(80, 80, 90, 255), width=2)
    band = LABEL_BAND * k
    d.rectangle([12, top + H - band, W - 13, top + H - 12], outline=(120, 200, 255, 255), width=2)
    d.text((22, top + H - band + 8), "라벨 띠 = 비운다(글자는 코드가)",
           font=O.font(22), fill=(150, 210, 255))
    d.rectangle([12, top + 12, W - 13, top + H - band - 6], outline=(150, 210, 255, 200), width=2)
    d.text((22, top + 20), "아이콘 자리", font=O.font(22), fill=(150, 210, 255))
    return im


def icons_plate(name):
    labels = [lab for lab, _ in tile_boxes(name)]
    gap, top = 30, 74
    W = ICON_CANVAS * len(labels) + gap * (len(labels) - 1)
    im = Image.new("RGBA", (W, ICON_CANVAS + top), (26, 26, 30, 255))
    d = ImageDraw.Draw(im, "RGBA")
    for i, lab in enumerate(labels):
        x = i * (ICON_CANVAS + gap)
        d.text((x + 4, 8), f"{i + 1}. {lab}", font=O.font(26), fill=HI)
        d.text((x + 4, 42), f"{ICON_CANVAS}x{ICON_CANVAS} · 마젠타 바탕", font=O.font(19), fill=DIM)
        d.rectangle([x, top, x + ICON_CANVAS - 1, top + ICON_CANVAS - 1], fill=KEY)
        d.rectangle([x + 16, top + 16, x + ICON_CANVAS - 17, top + ICON_CANVAS - 17],
                    outline=(120, 200, 255, 255), width=2)
    return im


HEAD_BG = [
    ("t", "이 판은 '배경'이다 - 타일을 그리지 말 것"),
    ("p", "타일(큰 버튼)과 아래 아이콘 칸은 따로 받아서 코드가 얹는다."),
    ("w", "★노란 해치 자리에 타일·칸이 덮인다 - 거기에 장식을 그리지 말 것"),
    ("w", "  해치를 가로지르는 장식(기둥·현수막 끈·사슬)도 금지 - 타일에 잘린다"),
    ("s", ""),
    ("p", "해치 밖이 네 몫이다. 제목 띠, 좌우 프레임, 타일 사이 여백 -"),
    ("p", "길드 회관의 분위기는 거기서 만든다."),
    ("s", ""),
    ("w", "캔버스 크기 그대로. 1px 도 다르면 안 된다"),
    ("w", "투명 픽셀 0 · 글자 금지(글자는 코드가 굽는다)"),
]

HEAD_TILE = [
    ("t", "액자 2장 - 큰 타일 · 작은 칸"),
    ("p", "큰 타일은 6곳에 같은 것을 찍는다. 그러니 '이 화면에서 여섯 번 반복돼도"),
    ("p", "안 질리는' 정도로만 꾸민다 - 모서리 장식은 네 곳 다 같게."),
    ("w", "★아래 라벨 띠(파란 칸)는 비운다 - 글자가 그 위에 얹힌다"),
    ("w", "★아이콘 자리도 비운다 - 아이콘은 따로 받아 코드가 가운데 놓는다"),
    ("w", "마젠타(#FF00FF) 밖으로 그림자를 흘리지 말 것"),
    ("s", ""),
    ("p", "눌린 상태·비활성 상태는 안 만든다 - 우리 GUI 는 상태 표현이 없다."),
    ("s", ""),
    ("t", "작은 칸 액자(오른쪽)"),
    ("p", "아래 버튼 줄 일곱 칸과 맨 윗줄 정보칸에 찍는다. 큰 타일과 같은 재질이되"),
    ("p", "장식은 훨씬 약하게 - 일곱 개가 붙어 서면 테두리만 보인다."),
    ("w", f"★구멍 {P.F_HOLE}px · 테두리 {P.F_BORDER}px - 이보다 두꺼우면 바깥이 잘려 나간다"),
]

HEAD_ICONS = [
    ("t", "타일 아이콘 - 타일마다 한 장"),
    ("p", "마젠타 바탕에 아이콘만. 파란 안내선 안에 들어오게 그린다."),
    ("w", "★배경·액자·글자 금지 - 액자는 따로 있고 글자는 코드가 굽는다"),
    ("w", "여섯 개가 한 화면에 나란히 선다 - 색·굵기·시점을 서로 맞출 것"),
    ("p", "게임에서는 세로 100px 남짓으로 줄어든다. 가는 선과 작은 글씨는 사라진다 -"),
    ("p", "실루엣만으로 구분되게."),
]


def build(name):
    out_dir = os.path.join(HERE, "src", name)
    os.makedirs(out_dir, exist_ok=True)
    theme = O.THEMES.get(name)

    plate, n = bg_plate(name)
    P.sheet(plate, f"발주 1/3 · 배경 - {name}",
            f"{plate.width} x {plate.height} · 해치 {n}곳은 비워 둔다",
            HEAD_BG, os.path.join(out_dir, "_order_bg.png"), theme)

    P.sheet(tile_plate(name), f"발주 2/3 · 액자 2장 - {name}",
            "큰 타일 1 (6곳) + 작은 칸 1 (정보칸·아래 버튼 줄)",
            HEAD_TILE, os.path.join(out_dir, "_order_tile.png"), theme)

    notes = []
    for i, (lab, _) in enumerate(tile_boxes(name)):
        notes.append(("hi", f"{i + 1}. {lab}"))
        desc = TILE_NOTE.get(name, {}).get(lab, "")
        notes += [("p", w) for w in textwrap.wrap(desc, 34)]
        notes.append(("s", ""))
    P.sheet(icons_plate(name), f"발주 3/3 · 타일 아이콘 - {name}",
            f"{ICON_CANVAS}x{ICON_CANVAS} x {len(L.TILES[name])}장 · 따로따로 줘도 된다",
            HEAD_ICONS + [("s", ""), ("t", "무엇을 그리나")] + notes,
            os.path.join(out_dir, "_order_icons.png"), theme)


if __name__ == "__main__":
    for n in sys.argv[1:] or ["guild"]:
        build(n)
