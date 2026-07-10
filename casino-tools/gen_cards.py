#!/usr/bin/env python3
"""바르칸 카지노 카드 텍스처 생성기 (casino-rework.md §5).

트럼프 52장+뒷면, 섯다 화투 13장(월10+광3)+뒷면을 모바일 카드게임식
대형 글리프 디자인으로 생성한다. 4×(256px) 슈퍼샘플로 그린 뒤 LANCZOS로
64×64 다운스케일 — 카드 영역 44×60px, 인게임 ItemDisplay scale 0.44에서
0.30×0.41블록.

스타일:
  B "센터 스택" (기본 통합): 랭크 상단 중앙 대형 + 수트 하단 중앙 대형 — 가독성 최대
  A "빅 인덱스" (대안): 랭크 좌상 + 수트 우하 — 모바일 포커 룩

출력:
  1) RP 통합(스타일 B + 화투 + 뒷면): assets/barkan/{textures,models,items}/card/
     - items:  {"model":{"type":"minecraft:model","model":"barkan:card/<id>"}}  (이무기 규약)
     - models: parent=minecraft:item/generated, layer0=barkan:card/<id>
  2) 스테이징(A/B/화투 전부): 미리보기용 PNG만

스타일 교체: STYLE_RP = "a"로 바꿔 재실행(텍스처만 덮어씀, 모델/items 불변).
"""

import json
import os
from PIL import Image, ImageDraw, ImageFont, ImageChops

SS = 4                      # 슈퍼샘플 배율
CV = 64                     # 최종 캔버스(px)
C = CV * SS                 # 작업 캔버스 256
CARD_W, CARD_H = 44 * SS, 60 * SS
CX0, CY0 = (C - CARD_W) // 2, (C - CARD_H) // 2   # 카드 좌상 (40, 8)
CX1, CY1 = CX0 + CARD_W, CY0 + CARD_H
RADIUS = 6 * SS
MID = C // 2

STYLE_RP = "b"              # RP에 통합할 트럼프 스타일

RP = os.path.expanduser("~/development/barkan-resourcepack")
STAGING = os.environ.get("CARD_STAGING", os.path.expanduser("~/Desktop/casino-cards-preview"))

FONT_BOLD = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"

# 팔레트 (모바일 플랫 톤)
CARD_FACE = (252, 251, 246, 255)
CARD_EDGE = (203, 203, 212, 255)
RED = (222, 46, 46, 255)
BLACK = (30, 34, 40, 255)
BACK_BLUE = (42, 74, 140, 255)
BACK_BLUE_LN = (92, 124, 190, 255)
HW_FACE = (250, 244, 228, 255)
HW_NUM = (168, 32, 38, 255)
HW_BACK = (158, 40, 36, 255)
HW_BACK_LN = (206, 96, 84, 255)
GOLD = (226, 172, 58, 255)
GOLD_DK = (168, 118, 30, 255)

SUITS = {"s": ("스페이드", BLACK), "h": ("하트", RED), "d": ("다이아", RED), "c": ("클럽", BLACK)}
RANKS = ["a", "2", "3", "4", "5", "6", "7", "8", "9", "10", "j", "q", "k"]


def new_canvas():
    img = Image.new("RGBA", (C, C), (0, 0, 0, 0))
    return img, ImageDraw.Draw(img)


def card_base(d, face=CARD_FACE, edge=CARD_EDGE, edge_w=1.5):
    d.rounded_rectangle([CX0, CY0, CX1, CY1], RADIUS, fill=face,
                        outline=edge, width=int(edge_w * SS))


def fitted(text, size, max_w, stroke=0):
    """max_w 안에 들어올 때까지 폰트를 줄인다."""
    probe = ImageDraw.Draw(Image.new("RGBA", (4, 4)))
    while size > 8 * SS:
        f = ImageFont.truetype(FONT_BOLD, size)
        if probe.textlength(text, font=f) + stroke * 2 <= max_w:
            return f
        size -= SS
    return ImageFont.truetype(FONT_BOLD, size)


def text_center(d, xy, text, size, color, max_w, stroke_ratio=0.045):
    stroke = max(1, int(size * stroke_ratio))
    f = fitted(text, size, max_w, stroke)
    d.text(xy, text, font=f, fill=color, anchor="mm",
           stroke_width=stroke, stroke_fill=color)


# ===== 수트 도형 (box 중심 cx,cy / 한 변 s) =====

def draw_diamond(d, cx, cy, s, color):
    d.polygon([(cx, cy - s * 0.52), (cx + s * 0.40, cy),
               (cx, cy + s * 0.52), (cx - s * 0.40, cy)], fill=color)


def draw_heart(d, cx, cy, s, color, flip=False):
    r = s * 0.26
    sign = -1 if flip else 1
    lobe_y = cy - sign * s * 0.16
    for dx in (-r * 0.92, r * 0.92):
        d.ellipse([cx + dx - r, lobe_y - r, cx + dx + r, lobe_y + r], fill=color)
    d.polygon([(cx - s * 0.475, lobe_y + sign * r * 0.30),
               (cx + s * 0.475, lobe_y + sign * r * 0.30),
               (cx, cy + sign * s * 0.52)], fill=color)


def draw_stem(d, cx, cy, s, color):
    top = cy + s * 0.05
    base = cy + s * 0.52
    d.polygon([(cx - s * 0.05, top), (cx + s * 0.05, top),
               (cx + s * 0.16, base), (cx - s * 0.16, base)], fill=color)


def draw_spade(d, cx, cy, s, color):
    body_cy = cy - s * 0.06
    draw_heart(d, cx, body_cy, s * 0.88, color, flip=True)
    draw_stem(d, cx, cy - s * 0.02, s, color)


def draw_club(d, cx, cy, s, color):
    r = s * 0.22
    for dx, dy in ((0, -s * 0.22), (-s * 0.21, s * 0.02), (s * 0.21, s * 0.02)):
        d.ellipse([cx + dx - r, cy + dy - r, cx + dx + r, cy + dy + r], fill=color)
    draw_stem(d, cx, cy, s, color)


SUIT_DRAW = {"s": draw_spade, "h": draw_heart, "d": draw_diamond, "c": draw_club}


# ===== 트럼프 =====

def trump_card(suit, rank, style):
    img, d = new_canvas()
    card_base(d)
    color = SUITS[suit][1]
    label = rank.upper()
    if style == "b":
        # 센터 스택: 랭크 상단, 수트 하단 — 최대 크기
        text_center(d, (MID, CY0 + CARD_H * 0.285), label, int(35 * SS),
                    color, CARD_W * 0.86)
        SUIT_DRAW[suit](d, MID, CY0 + CARD_H * 0.715, 25 * SS, color)
    else:
        # 빅 인덱스: 랭크 좌상, 수트 우하
        stroke = max(1, int(25 * SS * 0.045))
        f = fitted(label, int(25 * SS), CARD_W * 0.62, stroke)
        d.text((CX0 + 4.5 * SS, CY0 + 3.5 * SS), label, font=f, fill=color,
               anchor="la", stroke_width=stroke, stroke_fill=color)
        SUIT_DRAW[suit](d, CX1 - 13.5 * SS, CY1 - 14.5 * SS, 21 * SS, color)
    return img


def lattice_back(face, line, inner_edge):
    """뒷면: 진한 바탕 + 사선 격자 + 안쪽 테두리 + 중앙 다이아."""
    img, d = new_canvas()
    card_base(d, face=face, edge=inner_edge, edge_w=1.5)
    lat = Image.new("RGBA", (C, C), (0, 0, 0, 0))
    ld = ImageDraw.Draw(lat)
    step = 8 * SS
    for k in range(-C, 2 * C, step):
        ld.line([(k, 0), (k + C, C)], fill=line, width=SS)
        ld.line([(k + C, 0), (k, C)], fill=line, width=SS)
    inset = 4 * SS
    mask = Image.new("L", (C, C), 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        [CX0 + inset, CY0 + inset, CX1 - inset, CY1 - inset], RADIUS - inset, fill=255)
    lat.putalpha(ImageChops.multiply(lat.getchannel("A"), mask))
    img.alpha_composite(lat)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([CX0 + inset, CY0 + inset, CX1 - inset, CY1 - inset],
                        RADIUS - inset, outline=inner_edge, width=SS)
    draw_diamond(d, MID, MID, 13 * SS, inner_edge)
    return img


# ===== 화투 (섯다) =====

def icon_pine(d, cx, cy, s):
    g = (34, 102, 58, 255)
    d.polygon([(cx, cy - s * 0.52), (cx + s * 0.42, cy + 0), (cx - s * 0.42, cy + 0)], fill=g)
    d.polygon([(cx, cy - s * 0.22), (cx + s * 0.5, cy + s * 0.34), (cx - s * 0.5, cy + s * 0.34)], fill=g)
    d.rectangle([cx - s * 0.07, cy + s * 0.34, cx + s * 0.07, cy + s * 0.52], fill=(96, 64, 34, 255))


def icon_bird(d, cx, cy, s):
    navy = (40, 52, 92, 255)
    d.ellipse([cx - s * 0.42, cy - s * 0.16, cx + s * 0.30, cy + s * 0.30], fill=navy)  # 몸통
    d.ellipse([cx + s * 0.10, cy - s * 0.42, cx + s * 0.44, cy - s * 0.08], fill=navy)  # 머리
    d.polygon([(cx + s * 0.40, cy - s * 0.30), (cx + s * 0.58, cy - s * 0.22),
               (cx + s * 0.40, cy - s * 0.16)], fill=(226, 150, 40, 255))               # 부리
    d.polygon([(cx - s * 0.40, cy), (cx - s * 0.62, cy - s * 0.18),
               (cx - s * 0.34, cy - s * 0.12)], fill=navy)                              # 꼬리


def _petals(d, cx, cy, s, n, r_ratio, petal_ratio, color, center_color):
    import math
    pr = s * petal_ratio
    for i in range(n):
        ang = math.tau * i / n - math.pi / 2
        px, py = cx + math.cos(ang) * s * r_ratio, cy + math.sin(ang) * s * r_ratio
        d.ellipse([px - pr, py - pr, px + pr, py + pr], fill=color)
    cr = s * 0.16
    d.ellipse([cx - cr, cy - cr, cx + cr, cy + cr], fill=center_color)


def icon_cherry(d, cx, cy, s):
    _petals(d, cx, cy, s, 5, 0.28, 0.22, (238, 130, 150, 255), (250, 226, 120, 255))


def icon_drops(color):
    def f(d, cx, cy, s):
        for dx, ang in ((-0.30, -0.35), (0.0, 0.0), (0.30, 0.35)):
            bx = cx + s * dx
            d.ellipse([bx - s * 0.14, cy - s * 0.10, bx + s * 0.14, cy + s * 0.42], fill=color)
            d.polygon([(bx - s * 0.13, cy), (bx + s * 0.13, cy), (bx + s * ang * 0.4, cy - s * 0.5)], fill=color)
    return f


def icon_orchid(d, cx, cy, s):
    g = (58, 128, 70, 255)
    w = int(s * 0.10)
    d.arc([cx - s * 0.55, cy - s * 0.45, cx + s * 0.15, cy + s * 0.5], 250, 20, fill=g, width=w)
    d.arc([cx - s * 0.15, cy - s * 0.55, cx + s * 0.55, cy + s * 0.5], 160, 290, fill=g, width=w)
    d.arc([cx - s * 0.32, cy - s * 0.30, cx + s * 0.32, cy + s * 0.55], 220, 320, fill=g, width=w)


def icon_peony(d, cx, cy, s):
    _petals(d, cx, cy, s, 6, 0.27, 0.21, (196, 62, 110, 255), (250, 200, 90, 255))


def icon_moon(d, cx, cy, s):
    d.ellipse([cx - s * 0.44, cy - s * 0.48, cx + s * 0.44, cy + s * 0.40], fill=(238, 200, 92, 255))
    d.chord([cx - s * 0.62, cy + s * 0.10, cx + s * 0.62, cy + s * 0.78], 180, 360, fill=(52, 60, 88, 255))


def icon_chrys(d, cx, cy, s):
    import math
    y = (232, 178, 48, 255)
    for i in range(8):
        ang = math.tau * i / 8
        d.line([(cx, cy), (cx + math.cos(ang) * s * 0.44, cy + math.sin(ang) * s * 0.44)],
               fill=y, width=int(s * 0.12))
    cr = s * 0.15
    d.ellipse([cx - cr, cy - cr, cx + cr, cy + cr], fill=(150, 96, 26, 255))


def icon_maple(d, cx, cy, s):
    import math
    o = (206, 92, 34, 255)
    pts = []
    for i in range(10):
        ang = math.tau * i / 10 - math.pi / 2
        r = s * (0.5 if i % 2 == 0 else 0.24)
        pts.append((cx + math.cos(ang) * r, cy + math.sin(ang) * r * 0.92))
    d.polygon(pts, fill=o)
    d.line([(cx, cy + s * 0.2), (cx, cy + s * 0.52)], fill=(120, 60, 26, 255), width=int(s * 0.09))


HW_ICONS = {1: icon_pine, 2: icon_bird, 3: icon_cherry, 4: icon_drops((36, 38, 44, 255)),
            5: icon_orchid, 6: icon_peony, 7: icon_drops((172, 70, 48, 255)),
            8: icon_moon, 9: icon_chrys, 10: icon_maple}


def draw_star(d, cx, cy, r, color):
    import math
    pts = []
    for i in range(10):
        ang = math.tau * i / 10 - math.pi / 2
        rr = r if i % 2 == 0 else r * 0.42
        pts.append((cx + math.cos(ang) * rr, cy + math.sin(ang) * rr))
    d.polygon(pts, fill=color)


def hwatu_card(month, gwang):
    img, d = new_canvas()
    card_base(d, face=HW_FACE)
    text_center(d, (MID, CY0 + CARD_H * 0.275), str(month), int(36 * SS),
                HW_NUM, CARD_W * 0.84)
    HW_ICONS[month](d, MID, CY0 + CARD_H * 0.745, 19 * SS)
    if gwang:
        d.rounded_rectangle([CX0, CY0, CX1, CY1], RADIUS, outline=GOLD, width=int(2.4 * SS))
        bx, by, br = CX1 - 9 * SS, CY1 - 9 * SS, 7 * SS
        d.ellipse([bx - br, by - br, bx + br, by + br], fill=GOLD, outline=GOLD_DK, width=SS)
        draw_star(d, bx, by, br * 0.62, (255, 252, 240, 255))
    return img


# ===== 출력 =====

def down(img):
    """LANCZOS 축소 후 알파 이진화 — ItemDisplay cutout 렌더링에서
    카드 외곽 반투명 픽셀이 프린지로 남지 않게 한다(내부 AA는 불투명이라 유지)."""
    out = img.resize((CV, CV), Image.LANCZOS)
    out.putalpha(out.getchannel("A").point(lambda v: 255 if v >= 128 else 0))
    return out


def save_tex(img, *paths):
    for p in paths:
        os.makedirs(os.path.dirname(p), exist_ok=True)
        down(img).save(p)


def write_rp_json(card_id):
    model = os.path.join(RP, f"assets/barkan/models/card/{card_id}.json")
    item = os.path.join(RP, f"assets/barkan/items/card/{card_id}.json")
    os.makedirs(os.path.dirname(model), exist_ok=True)
    os.makedirs(os.path.dirname(item), exist_ok=True)
    with open(model, "w") as f:
        json.dump({"parent": "minecraft:item/generated",
                   "textures": {"layer0": f"barkan:card/{card_id}"}}, f, separators=(",", ":"))
    with open(item, "w") as f:
        json.dump({"model": {"type": "minecraft:model", "model": f"barkan:card/{card_id}"}},
                  f, separators=(",", ":"))


def main():
    rp_tex = os.path.join(RP, "assets/barkan/textures/card")
    ids = []

    # 트럼프 52장 — A/B 스테이징 + 선택 스타일 RP
    for suit in SUITS:
        for rank in RANKS:
            cid = f"{suit}_{rank}"
            for style in ("a", "b"):
                img = trump_card(suit, rank, style)
                paths = [os.path.join(STAGING, style, f"{cid}.png")]
                if style == STYLE_RP:
                    paths.append(os.path.join(rp_tex, f"{cid}.png"))
                save_tex(img, *paths)
            ids.append(cid)

    # 뒷면 2종
    back = lattice_back(BACK_BLUE, BACK_BLUE_LN, (238, 240, 248, 255))
    save_tex(back, os.path.join(STAGING, "back", "back.png"), os.path.join(rp_tex, "back.png"))
    ids.append("back")
    hw_back = lattice_back(HW_BACK, HW_BACK_LN, (248, 232, 200, 255))
    save_tex(hw_back, os.path.join(STAGING, "back", "hw_back.png"), os.path.join(rp_tex, "hw_back.png"))
    ids.append("hw_back")

    # 화투 13장 (월 10 + 광 3) — 같은 월 일반 2장은 텍스처 공유
    for month in range(1, 11):
        cid = f"hw_{month}"
        save_tex(hwatu_card(month, False),
                 os.path.join(STAGING, "hw", f"{cid}.png"), os.path.join(rp_tex, f"{cid}.png"))
        ids.append(cid)
    for month in (1, 3, 8):
        cid = f"hw_{month}g"
        save_tex(hwatu_card(month, True),
                 os.path.join(STAGING, "hw", f"{cid}.png"), os.path.join(rp_tex, f"{cid}.png"))
        ids.append(cid)

    for cid in ids:
        write_rp_json(cid)
    print(f"완료: 텍스처 {len(ids)}종 RP 통합(스타일 {STYLE_RP.upper()}) + 스테이징 {STAGING}")
    print(f"  RP: {rp_tex} + models/card + items/card")


if __name__ == "__main__":
    main()
