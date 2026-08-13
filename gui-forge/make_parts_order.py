#!/usr/bin/env python3
"""분리 발주 시트 — **배경 한 장 + 액자 한 장**을 따로 주문한다.

## 왜 형식을 바꿨나
'이 판 위에 격자를 그려 달라'로 여덟 번 받았고 한 번도 72px 격자에 안 맞았다. 받은 판에서
격자를 떼어 옮기면 이번엔 판을 가로지르는 장식(책 접힘선·기둥·걸쇠)이 잘렸다.
격자 없는 배경과 액자 한 장을 따로 받아 **좌표는 코드가 잡으면**(assemble_plate.py)
어긋날 여지가 없다 — 도감 두 판이 그렇게 0px 이 됐다.

## 두 장을 만든다
  · _order_bg.png    배경. 칸을 **그리지 않는다**. 액자가 덮을 자리만 표시해 둔다.
  · _order_frame.png 액자. 마젠타 바탕에 한 칸짜리 액자만. 역할이 다르면 여러 종.

## 액자 크기를 숫자로 박는 이유
assemble_plate 는 구멍을 찾아 **구멍 한 변의 1/16 만 테두리로 남기고 잘라낸다**(최종 72px
칸에서 테두리가 사방 4px 이므로). 그보다 두껍게 그린 테두리는 버려진다 — 그래서 시트에
구멍 384 · 테두리 24 를 못박아 준다.

사용: python3 make_parts_order.py <판이름 ...>
산출: src/<이름>/_order_bg.png · _order_frame.png
"""
import os
import sys
import textwrap

from PIL import Image, ImageDraw

import make_order_sheets as O
import make_page_layouts as L

HERE = os.path.dirname(os.path.abspath(__file__))
S, GX, GY, CELL, COLS = L.SCALE, L.GRID_X, L.GRID_Y, L.CELL, L.COLS
BG, INK, DIM, HI, WARN = O.BG, O.INK, O.DIM, O.HI, O.WARN
PANEL_W = O.PANEL_W

PLATE_BG = (38, 40, 46, 255)
EDGE = (150, 152, 162, 255)
KEEP = (232, 196, 96, 255)          # 액자가 덮을 자리(건드려도 가려지는 곳)
REGION = (210, 212, 222, 255)

# 액자 시트 규격 — 이 숫자가 곧 assemble_plate 의 잘라내기 기준이다
F_CANVAS, F_HOLE, F_BORDER = 512, 384, 24
KEY = (255, 0, 255, 255)

# 역할 → 액자 이름·설명. 그 화면에 있는 역할만 시트에 실린다.
FRAME_KINDS = {
    "입력": ("넣는 칸", "플레이어가 인벤토리에서 끌어다 넣는 자리. '진열장'이 아니라 "
                    "'꽂는 홈'으로 - 얕은 요람, 가죽 끈 고리, 놋쇠 클립 같은."),
    "홈": ("일반 칸", "우리가 아이콘을 올리는 자리. 조용한 액자. 플레이어 인벤토리 "
                   "36칸도 이 액자를 쓴다 - 그래서 무늬가 세면 아래쪽이 시끄러워진다."),
    "목록": ("목록 칸", "여러 개가 격자로 붙는다. 테두리가 세면 판 전체가 그물처럼 보인다."),
}


def hatch(d, box, color, step=14):
    """사선 해치 - '여기 뭔가 온다'를 색면 없이 알린다(아래 재질이 보이게)."""
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    for k in range(0, w + h, step):
        # ★칸 안으로 잘라야 한다. 안 자르면 선이 칸 밖으로 삐져나가 '건드리지 말 자리'의
        #   경계가 흐려진다(2026-08-13 첫 시트에서 실측).
        ax, ay = x0 + min(k, w), y0 + max(0, k - w)
        bx, by = x0 + max(0, k - h), y0 + min(k, h)
        d.line([ax, ay, bx, by], fill=color, width=1)
    d.rectangle(box, outline=color, width=2)


def bg_plate(name):
    """배경 발주용 뼈대 - 칸은 안 그린다. 액자가 덮을 자리만 해치로."""
    rows, roles, _ = L.PAGES[name]
    W, H = 176 * S, (114 + rows * CELL) * S
    im = Image.new("RGBA", (W, H), PLATE_BG)
    d = ImageDraw.Draw(im, "RGBA")
    d.rectangle([6, 6, W - 7, H - 7], outline=EDGE, width=4)
    d.rounded_rectangle([GX * S, L.TITLE_Y0, (GX + CELL * COLS) * S - 1, L.TITLE_Y1],
                        radius=8, outline=REGION, width=3)
    boxes = []
    for slot, (role, _) in sorted(roles.items()):
        if role == "장식":
            continue
        r, c = divmod(slot, COLS)
        x0, y0 = (GX + CELL * c) * S, (GY + CELL * r) * S
        boxes.append((x0, y0, x0 + CELL * S - 1, y0 + CELL * S - 1))
    inv_y0 = 30 + rows * CELL
    for gy in (inv_y0, inv_y0 + CELL, inv_y0 + 2 * CELL, inv_y0 + 58):
        for c in range(COLS):
            x0 = (GX + CELL * c) * S
            boxes.append((x0, gy * S, x0 + CELL * S - 1, gy * S + CELL * S - 1))
    for b in boxes:
        hatch(d, b, KEEP)
    return im, len(boxes)


def frame_plate(kinds):
    """액자 발주용 판 - 마젠타 캔버스에 구멍 자리만 표시. 종류만큼 나란히."""
    gap, top = 40, 74                                # top = 치수 글자를 얹을 띠
    W = F_CANVAS * len(kinds) + gap * (len(kinds) - 1)
    im = Image.new("RGBA", (W, F_CANVAS + top), (26, 26, 30, 255))
    d = ImageDraw.Draw(im, "RGBA")
    o = (F_CANVAS - F_HOLE - 2 * F_BORDER) // 2      # 액자 외곽까지의 여백
    for i, kind in enumerate(kinds):
        x = i * (F_CANVAS + gap)
        # ★치수·번호는 마젠타 **밖**에 적는다. 캔버스 안에 적어 두면 그 글자까지 그림으로
        #   여겨 남기거나 지우느라 액자가 뭉개진다(발주 사고의 단골).
        # ★한 줄에 다 넣으면 캔버스 폭(512)을 넘어 옆 판 글자와 겹친다 - 두 줄로 나눈다.
        d.text((x + 4, 8), f"{i + 1}번 - {FRAME_KINDS[kind][0]}", font=O.font(26), fill=HI)
        d.text((x + 4, 42), f"캔버스 {F_CANVAS}x{F_CANVAS} · 액자 외곽 {F_HOLE + 2 * F_BORDER}"
                        f" · 구멍 {F_HOLE}", font=O.font(20), fill=DIM)
        d.rectangle([x, top, x + F_CANVAS - 1, top + F_CANVAS - 1], fill=KEY)
        # 액자 외곽 / 구멍 - 두 사각형 사이가 테두리를 그릴 띠다
        d.rectangle([x + o, top + o, x + F_CANVAS - o - 1, top + F_CANVAS - o - 1],
                    outline=(80, 80, 90, 255), width=2)
        hx, hy = x + o + F_BORDER, top + o + F_BORDER
        d.rectangle([hx, hy, hx + F_HOLE - 1, hy + F_HOLE - 1],
                    fill=(40, 40, 46, 255), outline=(120, 200, 255, 255), width=2)
        d.text((hx + 10, hy + 10), "구멍 = 비운다", font=O.font(24), fill=(150, 210, 255))
    return im


HEAD_BG = [
    ("t", "이 판은 '배경'이다 - 칸을 그리지 말 것"),
    ("p", "칸(액자)은 따로 받아서 우리가 코드로 얹는다. 여태 격자를 그려 받은 판이"),
    ("p", "여덟 번 다 72px 에 안 맞아서 방식을 바꿨다."),
    ("w", "★노란 해치 자리에 액자가 덮인다 - 거기에 장식을 그리지 말 것"),
    ("w", "  덮여서 안 보이거나, 액자 사이로 삐져나와 어긋난 것처럼 보인다"),
    ("w", "  그 자리는 재질(나무·금속결)만 이어지게 두면 된다"),
    ("w", "★해치 영역을 가로지르는 장식(관·기둥·끈·접힘선)도 금지 - 액자에 잘린다"),
    ("s", ""),
    ("p", "해치 밖은 전부 네 몫이다. 위 제목 띠, 좌우 프레임, 칸이 없는 줄 -"),
    ("p", "여기서 화면의 성격을 만든다."),
    ("s", ""),
    ("w", "캔버스 크기 그대로. 1px 도 다르면 안 된다"),
    ("w", "투명 픽셀 0 - 둥근 모서리 바깥도 어두운 색으로"),
    ("w", "글자 금지 - 글자는 코드가 찍는다"),
]

HEAD_FRAME = [
    ("t", "이 판은 '액자'다 - 한 칸만 크게"),
    ("p", "마젠타(#FF00FF) 바탕은 투명 처리용이다. 액자 밖은 마젠타 그대로 둘 것."),
    ("w", f"★구멍 {F_HOLE}px · 테두리 {F_BORDER}px · 액자 외곽 {F_HOLE + 2 * F_BORDER}px"),
    ("w", f"  테두리를 {F_BORDER}px 보다 두껍게 그리면 그 바깥은 잘려 나간다"),
    ("w", "  (최종 칸은 72px 이고 테두리로 쓸 수 있는 건 사방 4px 뿐이다)"),
    ("w", "★구멍 안은 완전히 비운다 - 아이콘이 그 위에 얹힌다"),
    ("w", "  음영·긁힘·바닥 질감도 넣지 말 것. 아이콘 뒤가 지저분해진다"),
    ("s", ""),
    ("p", "네 변과 네 모서리가 이어 붙는다. 칸들은 맞닿아 격자선처럼 보이므로"),
    ("p", "위/아래, 좌/우 테두리는 서로 대칭이어야 한다 - 한쪽만 두꺼우면 줄이 어긋나 보인다."),
    ("p", "모서리 장식(못·리벳)은 네 곳 다 같게. 한 곳만 크면 격자 전체가 그걸 반복한다."),
    ("s", ""),
    ("w", "글자 금지 · 그림자를 액자 밖(마젠타)으로 흘리지 말 것"),
]


def sheet(plate, title, size_note, sections, out, theme=None):
    lines = 0
    for kind, text in sections:
        lines += {"s": 0.4, "t": 1.6}.get(kind, 0)
        if kind not in ("s", "t"):
            lines += max(1, len(textwrap.wrap(text, 34)))
    wrapped = [w for line in (theme[1:] if theme else []) for w in textwrap.wrap(line, 40)]
    need = 170 + int(lines * 30) + 40 + 34 + 26 * len(wrapped) + 30
    W, H = plate.width + PANEL_W, max(plate.height + 40, need)
    im = Image.new("RGBA", (W, H), BG + (255,))
    im.alpha_composite(plate, (0, (H - plate.height) // 2))
    d = ImageDraw.Draw(im)
    d.line([plate.width, 0, plate.width, H], fill=(70, 70, 78, 255), width=3)
    x, y = plate.width + 28, 26
    d.text((x, y), title, font=O.font(38), fill=HI); y += 54
    d.text((x, y), size_note, font=O.font(20), fill=DIM); y += 20
    d.text((x, y + 8), "이 오른쪽 설명은 잘라내고 왼쪽만 쓰면 된다", font=O.font(20), fill=DIM); y += 46
    for kind, text in sections:
        if kind == "s":
            y += 12; continue
        if kind == "t":
            y += 8; d.text((x, y), text, font=O.font(26), fill=HI); y += 38; continue
        col = {"p": INK, "k": DIM, "w": WARN, "hi": HI}[kind]
        mark = {"k": "· ", "w": "! ", "hi": "", "p": ""}[kind]
        for i, line in enumerate(textwrap.wrap(mark + text, 34) or [""]):
            d.text((x + (0 if i == 0 else 20), y), line, font=O.font(22), fill=col)
            y += 30
    if theme:
        y += 28
        d.text((x, y), theme[0], font=O.font(24), fill=HI); y += 34
        for line in wrapped:
            d.text((x, y), line, font=O.font(19), fill=DIM); y += 26
    im.convert("RGB").save(out)
    print(f"  {os.path.basename(out):16} {W}x{H} → {out}")


def build(name):
    rows, roles, _ = L.PAGES[name]
    title, body = O.SHEETS[name]
    theme = O.THEMES.get(name)
    out_dir = os.path.join(HERE, "src", name)
    os.makedirs(out_dir, exist_ok=True)

    plate, n = bg_plate(name)
    sheet(plate, f"발주 1/2 · 배경 - {title}",
          f"{plate.width} x {plate.height} · 액자 자리 {n}칸은 비워 둔다",
          HEAD_BG + [("s", "")] + body, os.path.join(out_dir, "_order_bg.png"), theme)

    kinds = [r for r in ("입력", "홈", "목록") if any(x == r for x, _ in roles.values())]
    fplate = frame_plate(kinds)
    detail = []
    for i, k in enumerate(kinds):
        nm, desc = FRAME_KINDS[k]
        cnt = sum(1 for x, _ in roles.values() if x == k)
        detail.append(("hi", f"{i + 1}번 - {nm} ({cnt}칸)"))
        detail += [("p", w) for w in textwrap.wrap(desc, 34)]
        detail.append(("s", ""))
    sheet(fplate, f"발주 2/2 · 액자 {len(kinds)}종 - {title}",
          f"각 {F_CANVAS} x {F_CANVAS} · 따로따로 {len(kinds)}장으로 줘도 된다",
          HEAD_FRAME + [("s", ""), ("t", "이 화면에 필요한 액자")] + detail,
          os.path.join(out_dir, "_order_frame.png"), theme)


if __name__ == "__main__":
    for n in sys.argv[1:] or ["workbench"]:
        build(n)
