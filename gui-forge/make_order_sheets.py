#!/usr/bin/env python3
"""발주 시트 - 뼈대판 + 지시문을 한 장의 그림으로 굽는다.

발주서(.md)와 뼈대판(.png)을 따로 넘기면 **그림을 못 찾는 일이 생긴다**(2026-08-08).
그림 한 장에 지시문까지 얹어 두면 그 한 장만으로 작업이 된다.

왼쪽 = 실제 크기 뼈대판(여기에 덧칠) · 오른쪽 = 규칙과 컨셉.
★오른쪽 설명판은 **참고용이라 잘라내고 왼쪽만 쓰면 된다** - 시트에도 그렇게 적어 둔다.

사용: python3 make_order_sheets.py [이름 ...]
산출: src/<이름>/_order.png
"""
import os
import sys
import textwrap

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
RP = os.path.expanduser("~/development/barkan-resourcepack")
FONT_TTF = os.path.join(RP, "assets/barkan/font/aggro_bold.ttf")
PANEL_W = 720
BG, INK, DIM, HI, WARN = (26, 26, 30), (238, 238, 242), (168, 168, 176), (255, 208, 96), (255, 130, 110)

COMMON = [
    ("t", "그리는 법"),
    ("p", "왼쪽 판을 열어서 그 위에 재질과 분위기만 입힌다."),
    ("p", "칸을 새로 그리거나 옮기지 말 것 - 이미 정확한 좌표로 파여 있다."),
    ("s", ""),
    ("k", "큰 황토색 판 = 큰 버튼. 안은 비운다(아이콘은 우리가 올림)"),
    ("k", "회색 = 홈. 우리가 아이콘을 올린다"),
    ("k", "초록 = 넣는 칸. 회색과 확실히 구분되게"),
    ("k", "파랑 = 목록. 얕은 홈, 안쪽은 조용하게"),
    ("k", "빈 자리 = 장식. 마음껏"),
    ("s", ""),
    ("t", "어기면 게임에서 깨진다"),
    ("w", "캔버스 크기 그대로. 1px도 다르면 안 된다"),
    ("w", "투명 픽셀 0 - 둥근 모서리 바깥도 어두운 색으로"),
    ("w", "맨 아래 큰 사각형(플레이어 인벤)에 격자 금지"),
    ("w", "제목 글자 금지 - 코드가 찍는다"),
    ("w", "좌우 프레임은 한쪽 16px 이내"),
]

SHEETS = {
    "smithy": ("대장간 허브", [
        ("p", "NPC에게 말 걸면 처음 나오는 화면. 작업대가 넷뿐이라 2x2로 두고"),
        ("p", "사이와 바깥에 한 칸씩 여백을 뒀다."),
        ("s", ""),
        ("hi", "★비어 있는 곳이 이 화면의 주인공이다."),
        ("p", "타일 사이 골, 좌우 여백, 위 한 줄 - 전부 이어진 대장간 내부로."),
        ("p", "모루 · 풀무 · 화덕 · 물통 · 걸린 집게와 망치 · 세워둔 쇠막대."),
        ("p", "타일 4개는 그 공간에 박아 넣은 놋쇠 명판처럼. 안은 비운다."),
        ("p", "오른쪽 위 홈 하나는 닫기 버튼 자리."),
    ]),
    "crafting": ("조합대", [
        ("p", "왼쪽에 레시피 목록(5x5), 오른쪽에 3x3 제작 그리드."),
        ("p", "왼쪽은 벽에 붙인 도면/장부, 오른쪽 3x3은 작업판으로 갈라 보이게."),
        ("hi", "3x3은 한 덩어리로 묶여 보여야 한다 - 조합대라는 게 읽혀야 한다."),
        ("p", "아래쪽 홈 하나가 제작 버튼 - 눌러야 할 것처럼 강조."),
    ]),
    "disassemble": ("부품 분해", [
        ("p", "넣고 → 갈기. 가운데 3x7 초록칸에 부술 부품·재료를 넣고"),
        ("p", "그 아래 가운데 홈 하나가 「갈기」 버튼이다. 그게 전부다."),
        ("s", ""),
        ("hi", "★칸이 적은 대신 배경이 넓다."),
        ("p", "숫돌 · 정 · 모루 위 부서진 쇳조각 · 쇳가루를 넉넉하게."),
        ("p", "21칸은 하나의 분쇄 상판으로 묶여 보이게(칸마다 액자 금지)."),
        ("p", "갈기 홈은 이 화면의 유일한 동작 - 가장 눈에 띄게."),
    ]),
    "forge": ("재료 제작소", [
        ("p", "분해의 반대. 위 한 줄에 홈 둘(분해로 가기 · 닫기), 아래 36칸 목록."),
        ("p", "거푸집 · 도가니 · 정련. 분해가 부수는 방이면 여기는 빚는 방이다."),
        ("p", "분해창과 짝이라 색은 이어지되 도구가 반대면 좋다."),
    ]),
    "enhance": ("낚싯대 강화", [("p", "이미 납품 완료 - 만듦새·색의 기준이 되는 화면이다.")]),
}

THEME = ("컨셉 - 대장간 한 채를 네 방으로",
         "강화창이 용광로 앞(뜨겁고 위험)이었다면 나머지는 그 대장간의 다른 구석이다.",
         "같은 재질(그을린 돌 · 달군 쇠 · 주황 불빛)을 쓰되 방마다 도구가 다르다.",
         "허브만 넓은 전경, 나머지 셋은 작업대 앞 클로즈업.")


def font(px, bold=True):
    try:
        return ImageFont.truetype(FONT_TTF, px)
    except Exception:
        return ImageFont.load_default()


def build(name):
    title, body = SHEETS[name]
    plate_path = os.path.join(HERE, "src", name, "_template.png")
    plate = Image.open(plate_path).convert("RGBA")
    lines = 0
    for kind, text in body + [("s", "")] + COMMON:
        lines += {"s": 0.4, "t": 1.5}.get(kind, 0)
        if kind not in ("s", "t"):
            lines += max(1, len(textwrap.wrap(text, 34)))
    need = 170 + int(lines * 30) + 150            # 머리말 + 본문 + 컨셉 블록
    W, H = plate.width + PANEL_W, max(plate.height, need)
    im = Image.new("RGBA", (W, H), BG + (255,))
    im.alpha_composite(plate, (0, (H - plate.height) // 2))
    d = ImageDraw.Draw(im)
    d.line([plate.width, 0, plate.width, H], fill=(70, 70, 78, 255), width=3)

    x, y = plate.width + 28, 26
    d.text((x, y), f"발주 - {title}", font=font(38), fill=HI); y += 54
    d.text((x, y), f"{plate.width} x {plate.height} · 왼쪽 판 위에 덧칠", font=font(20), fill=DIM); y += 20
    d.text((x, y + 8), "이 오른쪽 설명은 잘라내고 왼쪽만 쓰면 된다", font=font(20), fill=DIM); y += 46

    for kind, text in body + [("s", "")] + COMMON:
        if kind == "s":
            y += 12; continue
        if kind == "t":
            y += 8
            d.text((x, y), text, font=font(26), fill=HI); y += 38; continue
        col = {"p": INK, "k": DIM, "w": WARN, "hi": HI}[kind]
        mark = {"k": "· ", "w": "! ", "hi": "", "p": ""}[kind]
        for i, line in enumerate(textwrap.wrap(mark + text, 34) or [""]):
            d.text((x + (0 if i == 0 else 20), y), line, font=font(22), fill=col)
            y += 30

    y = H - 132
    d.text((x, y), THEME[0], font=font(24), fill=HI); y += 34
    for line in THEME[1:]:
        d.text((x, y), line, font=font(19), fill=DIM); y += 26

    out = os.path.join(HERE, "src", name, "_order.png")
    im.convert("RGB").save(out)
    print(f"  {name:12} {W}x{H} → {out}")


if __name__ == "__main__":
    for n in (sys.argv[1:] or ["smithy", "crafting", "disassemble", "forge"]):
        build(n)
