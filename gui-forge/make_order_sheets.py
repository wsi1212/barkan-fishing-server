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

import make_page_layouts as L

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
    ("legend", ""),          # 그 화면에 실제로 있는 역할만 자동으로 채운다
    ("s", ""),
    ("t", "어기면 게임에서 깨진다"),
    ("w", "캔버스 크기 그대로. 1px도 다르면 안 된다"),
    ("w", "투명 픽셀 0 - 둥근 모서리 바깥도 어두운 색으로"),
    ("hard", ""),            # 화면 종류별 주의문 (아래 HARD)
    ("w", "글자 금지 - 글자는 코드가 찍는다"),
]

# 상자 창(우리가 띄우는 GUI)과 바닐라 인벤토리는 지키는 게 다르다.
HARD = {
    "chest": [("w", "맨 아래 큰 사각형(플레이어 인벤)에 격자 금지"),
              ("w", "좌우 프레임은 한쪽 16px 이내")],
    "inventory": [("w", "칸을 옮기거나 크기를 바꾸지 말 것 - 좌표가 코드에 박혀 있다"),
                  ("w", "왼쪽 테두리는 28px 이내 (방어구 칸이 바로 붙어 있다)"),
                  ("w", "창 밖(오른쪽·아래 어두운 부분)으로 그림이 넘어가면 안 된다")],
}

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
    "iceshop": ("아이스박스 상점", [
        ("p", "아이스박스를 한 단계씩 올리는 화면. 3행 중 가운데 줄 9칸만 진열이고"),
        ("p", "위아래 한 줄씩은 여백이다. 홈은 그 9개 + 왼쪽 위 뒤로가기 하나."),
        ("p", "잔액·진주 보유량은 제목 줄에 뜨고 닫기는 Esc라 버튼이 없다."),
        ("p", "왼쪽 위 홈 하나는 보관함으로 돌아가는 뒤로가기 자리다."),
        ("s", ""),
        ("hi", "★가운데 9칸이 주인공, 위아래 여백이 조연이다."),
        ("p", "9칸은 왼쪽에서 오른쪽으로 좋아지는 계단처럼 - 왼쪽은 소박한 나무 선반,"),
        ("p", "오른쪽으로 갈수록 얼음이 두껍고 서리가 짙어지게."),
        ("p", "마지막 칸만은 전설급이라 티가 나도 좋다(빛나는 테두리 정도)."),
        ("p", "위아래 여백은 진열대를 감싸는 창고로 - 위는 고드름 매달린 천장,"),
        ("p", "아래는 성에 낀 바닥이나 얼음 벽돌 단. 진열이 공중에 뜨지 않게."),
    ]),
    "skillhub": ("스킬 허브 - 재작업", [
        ("p", "받은 그림(오른쪽 아래 참고)은 재질·색·구도 다 좋다. 그대로 간다."),
        ("p", "고칠 건 하나뿐이다 - 액자 5개의 간격이 어긋나 있다."),
        ("s", ""),
        ("hi", "★액자 다섯의 간격이 76px인데 72px 이어야 한다."),
        ("p", "게임은 아이템을 정확히 72px 간격에 그린다. 그래서 지금 그림이면"),
        ("p", "양 끝 아이콘이 액자 밖으로 9px씩 삐져나온다."),
        ("p", "액자 중심 x = 208 · 280 · 352 · 424 · 496 (가운데는 이미 맞다)."),
        ("p", "세로 중심 y = 176 도 이미 맞다 - 건드리지 말 것."),
        ("s", ""),
        ("hi", "★액자 안쪽 구멍은 한 변 68px 이상."),
        ("p", "지금 52px 이라 64px 짜리 아이콘이 테두리를 덮는다."),
        ("p", "테두리는 그만큼 바깥으로 - 액자 바깥 한 변 72px 까지 써도 된다."),
        ("s", ""),
        ("p", "왼쪽 판의 회색 홈이 정확한 자리다. 그 위에 액자를 얹으면 된다."),
    ]),
    "skilltree": ("특성 트리", [
        ("p", "스킬 하나를 눌렀을 때 나오는 상세. 0행에 버튼 4개(이전·정보·다음·초기화),"),
        ("p", "그 아래는 전부 특성 노드와 연결선이다 - 왼쪽 열에는 근원 노드가"),
        ("p", "하나 있고 거기서 세로 연결선이 아래로 뻗어 각 갈래로 이어진다."),
        ("s", ""),
        ("hi", "★점선 안(1~4행 전체, 왼쪽 열 포함)에는 홈을 파지 말 것."),
        ("p", "노드와 연결선이 칸 밖까지 넘쳐 그려지는 아이콘이라, 소켓 테두리가 있으면"),
        ("p", "선과 겹쳐 지저분해진다. 그 영역은 평평한 판이어야 한다."),
        ("p", "판은 조용하게 - 특성 아이콘이 주인공이고 배경은 벽지다."),
        ("p", "성좌도·설계도·족보 같은 느낌. 은은한 결이나 격자 정도까지만."),
        ("s", ""),
        ("hi", "★검은 여백을 만들지 말 것."),
        ("p", "지금 판의 가장 큰 불만이 그거다. 어둡게 하되 재질이 보이게."),
    ]),
    "inventory": ("생존 인벤토리 (E 키)", [
        ("p", "지금까지 그린 건 우리가 띄우는 창이었고, 이건 클라이언트가 그리는"),
        ("p", "바닐라 인벤토리다. 칸 위치가 코드에 박혀 있어 못 옮긴다 -"),
        ("p", "왼쪽 판의 회색 칸이 정확한 자리이고, 1px도 어긋나면 아이템이 튄다."),
        ("s", ""),
        ("hi", "★파란 사각형 안에는 플레이어 3D 모델이 그려진다."),
        ("p", "그 뒤에 깔 배경만 그린다 - 인물 사진을 넣을 액자라고 생각하면 된다."),
        ("p", "가운데를 밝게 두면 캐릭터가 산다. 무늬를 빼곡히 넣지 말 것."),
        ("s", ""),
        ("hi", "★빨간 사각형에는 바닐라 레시피책 버튼이 얹힌다."),
        ("p", "장식을 넣어도 가려지니 조용히 둘 것."),
        ("s", ""),
        ("hi", "★칸을 네 무리로 읽히게."),
        ("p", "왼쪽 세로 4칸(방어구) · 그 아래 하나(보조손) · 오른쪽 위 2x2+결과(조합)"),
        ("p", "· 아래 3x9 가방과 한 줄 띄운 단축바. 무리마다 테두리나 바닥이 다르면 좋다."),
        ("p", "단축바 한 줄은 특히 도드라지게 - 손에 쥔 것들이다."),
    ]),
    "enhance": ("낚싯대 강화", [("p", "이미 납품 완료 - 만듦새·색의 기준이 되는 화면이다.")]),
}

THEME_SMITHY = ("컨셉 - 대장간 한 채를 네 방으로",
         "강화창이 용광로 앞(뜨겁고 위험)이었다면 나머지는 그 대장간의 다른 구석이다.",
         "같은 재질(그을린 돌 · 달군 쇠 · 주황 불빛)을 쓰되 방마다 도구가 다르다.",
         "허브만 넓은 전경, 나머지 셋은 작업대 앞 클로즈업.")
THEME_ICE = ("컨셉 - 얼음 창고의 진열대",
             "아이스박스 보관함(src/icebox/bg_source.png)과 같은 방이다 - 그 화면의",
             "성에·고드름·푸른 얼음을 그대로 쓰되, 여기는 사러 온 손님이 보는 진열대다.",
             "9칸이 나무에서 전설까지 한 줄로 오르는 계단처럼 읽히면 성공.")
THEME_SKILL = ("컨셉 - 성장의 방",
               "허브는 다섯 갈래를 고르는 무대, 트리는 그중 하나를 파고드는 벽면이다.",
               "두 장이 같은 재질·같은 색으로 이어져야 한 시스템으로 읽힌다.",
               "밝고 정적인 톤 - 대장간(뜨거움)·아이스박스(차가움)와 구분되게.")
THEME_INV = ("컨셉 - 항해사의 장비함",
             "바르칸은 섬과 배의 서버다. 인벤토리는 그 항해사가 늘 여는 궤짝이면 좋겠다.",
             "젖은 나무 갑판 · 놋쇠 경첩과 못 · 밧줄 · 유리 아래 비치는 청록 물빛.",
             "색은 이미 쓰는 것들과 맞춘다 - 어두운 목탄·놋쇠·청록(대장간/스킬창 계열).",
             "★어둡되 검은 여백은 금지. 재질이 보이는 어둠으로.")
THEMES = {"iceshop": THEME_ICE, "skillhub": THEME_SKILL, "skilltree": THEME_SKILL,
          "inventory": THEME_INV}

# 재작업 시트용 - 오른쪽 설명판 아래에 「이 그림 기준」으로 축소해 붙인다.
# 받은 그림을 말로만 가리키면 못 찾는다(발주서/그림 분리 사고와 같은 이유).
REFERENCE = {"skillhub": ("src/skillhub/bg_source_rebuild.png",
                          "받은 그림 - 재질·색·구도는 이대로")}


def font(px, bold=True):
    try:
        return ImageFont.truetype(FONT_TTF, px)
    except Exception:
        return ImageFont.load_default()


LEGEND = {
    "타일": "큰 황토색 판 = 큰 버튼. 안은 비운다(아이콘은 우리가 올림)",
    "홈": "회색 = 홈. 우리가 아이콘을 올린다",
    "입력": "초록 = 넣는 칸. 회색과 확실히 구분되게",
    "목록": "파랑 = 목록. 얕은 홈, 안쪽은 조용하게",
    "장식": "빈 자리 = 장식. 마음껏",
}


def legend_for(name):
    if name not in L.PAGES:          # 상자 창이 아닌 화면(바닐라 인벤토리 등)
        return [("k", "회색 = 아이템이 들어가는 칸. 안은 비운다"),
                ("k", "파랑 = 플레이어 3D 모델 자리 · 빨강 = 바닐라 버튼 자리"),
                ("k", "그 밖 = 장식. 마음껏")]
    rows, roles, default = L.PAGES[name]
    used = {r for r, _ in roles.values()} | {default}
    if L.TILES.get(name): used.add("타일")
    return [("k", LEGEND[r]) for r in ("타일", "홈", "입력", "목록", "장식") if r in used]


def build(name):
    title, body = SHEETS[name]
    plate_path = os.path.join(HERE, "src", name, "_template.png")
    plate = Image.open(plate_path).convert("RGBA")
    lines = 0
    sections = body + [("s", "")] + COMMON
    hard = HARD["inventory" if name == "inventory" else "chest"]
    sections = [x for k, t in sections
                for x in (legend_for(name) if k == "legend" else hard if k == "hard" else [(k, t)])]
    for kind, text in sections:
        lines += {"s": 0.4, "t": 1.5}.get(kind, 0)
        if kind not in ("s", "t"):
            lines += max(1, len(textwrap.wrap(text, 34)))
    theme = THEMES.get(name, THEME_SMITHY)
    wrapped = [w for line in theme[1:] for w in textwrap.wrap(line, 40)]
    ref = REFERENCE.get(name)
    ref_h = 0
    if ref:
        ri = Image.open(os.path.join(HERE, ref[0])).convert("RGBA")
        rw = PANEL_W - 56
        ri = ri.resize((rw, round(ri.height * rw / ri.width)), Image.LANCZOS)
        ref_h = ri.height + 60
    need = 170 + int(lines * 30) + 40 + 34 + 26 * len(wrapped) + 30 + ref_h
    W, H = plate.width + PANEL_W, max(plate.height, need)
    im = Image.new("RGBA", (W, H), BG + (255,))
    im.alpha_composite(plate, (0, (H - plate.height) // 2))
    d = ImageDraw.Draw(im)
    d.line([plate.width, 0, plate.width, H], fill=(70, 70, 78, 255), width=3)

    x, y = plate.width + 28, 26
    d.text((x, y), f"발주 - {title}", font=font(38), fill=HI); y += 54
    d.text((x, y), f"{plate.width} x {plate.height} · 왼쪽 판 위에 덧칠", font=font(20), fill=DIM); y += 20
    d.text((x, y + 8), "이 오른쪽 설명은 잘라내고 왼쪽만 쓰면 된다", font=font(20), fill=DIM); y += 46

    for kind, text in sections:
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

    y += 28
    d.text((x, y), theme[0], font=font(24), fill=HI); y += 34
    for line in wrapped:
        d.text((x, y), line, font=font(19), fill=DIM); y += 26

    if ref:
        y += 30
        d.text((x, y), ref[1], font=font(20), fill=DIM); y += 28
        im.alpha_composite(ri, (x, y))

    out = os.path.join(HERE, "src", name, "_order.png")
    im.convert("RGB").save(out)
    print(f"  {name:12} {W}x{H} → {out}")


if __name__ == "__main__":
    for n in (sys.argv[1:] or ["smithy", "crafting", "disassemble", "forge"]):
        build(n)
