#!/usr/bin/env python3
"""바르칸 카지노 카드 텍스처 생성기 (casino-rework.md §5).

트럼프 52장+뒷면, 섯다 화투 실제 덱 20장(피 제외: 광·열끗·띠)+뒷면을 모바일 카드게임식
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

STYLE_RP = "a"              # RP에 통합할 트럼프 스타일 (2026-07-11 유저 확정: A 빅인덱스)

RP = os.environ.get("CARD_RP", os.path.expanduser("~/Downloads/barkan-resourcepack"))
STAGING = os.environ.get("CARD_STAGING", os.path.expanduser("~/Desktop/casino-cards-preview"))
HW_ATLAS_SOURCE = os.environ.get(
    "HW_ATLAS_SOURCE", os.path.join(os.path.dirname(__file__), "assets", "hwatu-reference-atlas.png"))
HW_ART_SOURCE = os.environ.get(
    "HW_ART_SOURCE", os.path.join(os.path.dirname(__file__), "assets", "hwatu-seotda-generated.png"))
HW_ART_SOURCE_B = os.environ.get(
    "HW_ART_SOURCE_B", os.path.join(os.path.dirname(__file__), "assets", "hwatu-seotda-generated-b.png"))
HW_ART = None
HW_ART_B = None
HW_ATLAS = None

FONT_BOLD = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
FONT_CJK = "/System/Library/Fonts/Hiragino Sans GB.ttc"

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
        origin = (CX0 + 4.5 * SS, CY0 + 3.5 * SS)
        d.text(origin, label, font=f, fill=color,
               anchor="la", stroke_width=stroke, stroke_fill=color)
        if rank in ("6", "9"):
            # ★6/9 밑줄 — 뒤집혀도 구분되게. 실제 렌더된 글리프 바운딩박스 기준(폰트metrics 추측 X).
            l, t, r, b = d.textbbox(origin, label, font=f, anchor="la", stroke_width=stroke)
            gap = max(1, int(2 * SS))
            uw = max(2, int(2.6 * SS))
            d.line([(l, b + gap), (r, b + gap)], fill=color, width=uw)
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
    """송(松) — 솔잎 다발 실루엣(삼각형 통짜 대신 부채꼴 침엽 다발 2단) + 줄기."""
    dark, light = (26, 84, 46, 255), (52, 128, 72, 255)
    import math
    def needle_fan(fx, fy, fs, color, n=7, spread=150):
        for i in range(n):
            ang = math.radians(-90 - spread / 2 + spread * i / (n - 1))
            ex, ey = fx + math.cos(ang) * fs, fy + math.sin(ang) * fs
            d.line([(fx, fy), (ex, ey)], fill=color, width=max(1, int(s * 0.045)))
    needle_fan(cx, cy + s * 0.06, s * 0.56, dark, n=9, spread=170)
    needle_fan(cx - s * 0.06, cy - s * 0.30, s * 0.40, light, n=7, spread=150)
    d.rectangle([cx - s * 0.06, cy + s * 0.04, cx + s * 0.06, cy + s * 0.54], fill=(90, 60, 32, 255))


def icon_bird(d, cx, cy, s, with_blossom=True):
    """조(鳥) — 매조: 나는 새 + (2월 정규패는) 매화 가지 곁들임."""
    navy = (40, 52, 92, 255)
    navy_lt = (66, 82, 128, 255)
    d.ellipse([cx - s * 0.42, cy - s * 0.16, cx + s * 0.30, cy + s * 0.30], fill=navy)  # 몸통
    d.ellipse([cx + s * 0.10, cy - s * 0.42, cx + s * 0.44, cy - s * 0.08], fill=navy)  # 머리
    d.polygon([(cx + s * 0.40, cy - s * 0.30), (cx + s * 0.58, cy - s * 0.22),
               (cx + s * 0.40, cy - s * 0.16)], fill=(226, 150, 40, 255))               # 부리
    d.polygon([(cx - s * 0.40, cy), (cx - s * 0.62, cy - s * 0.18),
               (cx - s * 0.34, cy - s * 0.12)], fill=navy)                              # 꼬리
    d.ellipse([cx - s * 0.10, cy - s * 0.10, cx + s * 0.14, cy + s * 0.10], fill=navy_lt)  # 날개 하이라이트
    if with_blossom:
        _petals(d, cx - s * 0.52, cy - s * 0.40, s * 0.6, 5, 0.26, 0.20,
                (240, 150, 175, 255), (250, 226, 120, 255))


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
    """4월 흑싸리·7월 홍싸리 — (vine 시도가 64px에서 안 읽혀 원래 형태 유지, 검증됨)."""
    def f(d, cx, cy, s):
        for dx, ang in ((-0.30, -0.35), (0.0, 0.0), (0.30, 0.35)):
            bx = cx + s * dx
            d.ellipse([bx - s * 0.14, cy - s * 0.10, bx + s * 0.14, cy + s * 0.42], fill=color)
            d.polygon([(bx - s * 0.13, cy), (bx + s * 0.13, cy), (bx + s * ang * 0.4, cy - s * 0.5)], fill=color)
    return f


def icon_orchid(d, cx, cy, s):
    """5월 난초 — 잎(호) + 야츠하시(지그재그 다리)."""
    g = (58, 128, 70, 255)
    w = int(s * 0.10)
    d.arc([cx - s * 0.55, cy - s * 0.45, cx + s * 0.15, cy + s * 0.5], 250, 20, fill=g, width=w)
    d.arc([cx - s * 0.15, cy - s * 0.55, cx + s * 0.55, cy + s * 0.5], 160, 290, fill=g, width=w)
    d.arc([cx - s * 0.32, cy - s * 0.30, cx + s * 0.32, cy + s * 0.55], 220, 320, fill=g, width=w)
    plank = (120, 78, 40, 255)
    zig = [(cx - s * 0.5, cy + s * 0.58), (cx - s * 0.2, cy + s * 0.42),
           (cx + s * 0.1, cy + s * 0.58), (cx + s * 0.42, cy + s * 0.42)]
    d.line(zig, fill=plank, width=max(1, int(s * 0.09)))


def icon_peony(d, cx, cy, s):
    """6월 모란 — (나비 시도가 64px에서 벌레처럼 보여 제거, 작약만 유지)."""
    _petals(d, cx, cy, s, 6, 0.27, 0.21, (196, 62, 110, 255), (250, 200, 90, 255))


def icon_moon(d, cx, cy, s):
    """8월 공산 — 보름달 + 기러기 + 억새."""
    d.ellipse([cx - s * 0.44, cy - s * 0.48, cx + s * 0.44, cy + s * 0.40], fill=(238, 200, 92, 255))
    d.ellipse([cx - s * 0.30, cy - s * 0.36, cx + s * 0.20, cy + s * 0.12], fill=(248, 224, 150, 255))
    geese = (60, 56, 60, 255)
    for gx, gy, gs in ((cx - s * 0.55, cy - s * 0.60, 0.10), (cx - s * 0.30, cy - s * 0.70, 0.08)):
        d.line([(gx - gs * s, gy), (gx, gy - gs * s * 0.6), (gx + gs * s, gy)], fill=geese, width=max(1, int(s * 0.045)))
    d.chord([cx - s * 0.62, cy + s * 0.10, cx + s * 0.62, cy + s * 0.78], 180, 360, fill=(52, 60, 88, 255))
    grass = (30, 36, 40, 255)
    for gx, ang in ((-0.30, -18), (-0.05, 6), (0.24, 20)):
        ex = cx + s * gx + s * 0.16 * (ang / 20)
        d.line([(cx + s * gx, cy + s * 0.70), (ex, cy + s * 0.12)], fill=grass, width=max(1, int(s * 0.045)))


def icon_chrys(d, cx, cy, s):
    """9월 국준 — 방사형 꽃잎(둥근 점 나열은 64px에서 구슬처럼 보여 원래 선형 유지)."""
    import math
    y = (232, 178, 48, 255)
    for i in range(8):
        ang = math.tau * i / 8
        d.line([(cx, cy), (cx + math.cos(ang) * s * 0.44, cy + math.sin(ang) * s * 0.44)],
               fill=y, width=int(s * 0.12))
    cr = s * 0.15
    d.ellipse([cx - cr, cy - cr, cx + cr, cy + cr], fill=(150, 96, 26, 255))


MAPLE_LOBES = [
    (0.00, -1.00), (0.30, -0.55), (0.62, -0.68), (0.42, -0.20), (0.78, 0.15),
    (0.30, 0.42), (0.16, 0.62), (0.00, 0.50), (-0.16, 0.62), (-0.30, 0.42),
    (-0.78, 0.15), (-0.42, -0.20), (-0.62, -0.68), (-0.30, -0.55),
]
MAPLE_TIPS = [0, 2, 4, 10, 12]  # 위 좌표 리스트에서 잎끝(뾰족한 점)의 인덱스


def icon_maple(d, cx, cy, s):
    """10월 단풍 — 별모양(대칭) 대신 손으로 배치한 비대칭 단풍잎 윤곽(5갈래+밑동 오목+잎맥)."""
    o = (206, 92, 34, 255)
    o_dk = (150, 60, 20, 255)
    oy = cy - s * 0.04
    pts = [(cx + dx * s * 0.62, oy + dy * s * 0.58) for dx, dy in MAPLE_LOBES]
    d.polygon(pts, fill=o)
    base = (cx, oy + 0.50 * s * 0.58)
    for i in MAPLE_TIPS:
        d.line([base, pts[i]], fill=o_dk, width=max(1, int(s * 0.035)))
    d.line([(cx, oy + s * 0.30), (cx, oy + s * 0.56)], fill=(120, 60, 26, 255), width=int(s * 0.08))


HW_ICONS = {1: icon_pine, 2: icon_bird, 3: icon_cherry, 4: icon_drops((36, 38, 44, 255)),
            5: icon_orchid, 6: icon_peony, 7: icon_drops((172, 70, 48, 255)),
            8: icon_moon, 9: icon_chrys, 10: icon_maple}


def draw_gwang_mark(d, cx, cy, r):
    """실제 섯다 광패처럼 빨간 광(光) 원표를 그린다."""
    d.ellipse([cx - r, cy - r, cx + r, cy + r],
              fill=(190, 32, 30, 255), outline=(116, 24, 24, 255), width=SS)
    font = ImageFont.truetype(FONT_CJK, int(r * 1.28))
    d.text((cx, cy + int(0.5 * SS)), "光", font=font, anchor="mm",
           fill=(255, 246, 220, 255), stroke_width=max(1, SS // 2),
           stroke_fill=(255, 246, 220, 255))


def hwatu_card(month, gwang, variant=0):
    img, d = new_canvas()
    # 실제 화투 도상에 가까운 원화 시트를 카드 얼굴에 넣는다. 숫자는 생성 모델에 맡기지
    # 않고 아래에서 픽셀 합성해, 64px에서도 모든 월이 정확히 읽히도록 한다.
    art = hwatu_art_panel(month, variant)
    if art is None:
        card_base(d, face=HW_FACE)
        HW_ICONS[month](d, MID, CY0 + CARD_H * 0.745, 19 * SS)
    else:
        mask = Image.new("L", (CARD_W, CARD_H), 0)
        ImageDraw.Draw(mask).rounded_rectangle(
            [0, 0, CARD_W - 1, CARD_H - 1], RADIUS, fill=255)
        art.putalpha(mask)
        img.paste(art, (CX0, CY0), art)

    # 오른쪽 위 고정 숫자 배지 — 화투 그림과 겹쳐도 월 식별이 흔들리지 않는다.
    badge = 16 * SS
    bx1, by0 = CX1 - 1 * SS, CY0 + 1 * SS
    bx0, by1 = bx1 - badge, by0 + badge
    d.rounded_rectangle([bx0, by0, bx1, by1], radius=1.2 * SS,
                        fill=(249, 240, 208, 255), outline=(92, 30, 28, 255), width=SS)
    text_center(d, ((bx0 + bx1) / 2, (by0 + by1) / 2), str(month), int(15 * SS),
                HW_NUM, badge - 2 * SS, stroke_ratio=0.02)
    if gwang:
        d.rounded_rectangle([CX0, CY0, CX1, CY1], RADIUS, outline=GOLD, width=int(2.4 * SS))
        bx, by, br = CX1 - 9 * SS, CY1 - 9 * SS, 7 * SS
        draw_gwang_mark(d, bx, by, br)
    return img


def hwatu_art_panel(month, variant=0):
    """실제 48장 화투 아틀라스에서 월별 섯다 패널을 잘라낸다.

    첨부된 근본 폐 이미지는 8열×6행, 월별 4장씩(1~12월) row-major 배열이다.
    섯다 20장은 각 월의 첫 두 장만 쓰므로 (month-1)*4 + variant 위치를 사용한다.
    아틀라스가 없을 때만 이전 생성 시트 경로로 폴백한다.
    """
    global HW_ATLAS, HW_ART, HW_ART_B

    if HW_ATLAS is None and os.path.exists(HW_ATLAS_SOURCE):
        try:
            HW_ATLAS = Image.open(HW_ATLAS_SOURCE).convert("RGBA")
        except Exception as ex:
            print(f"경고: 실제 화투 아틀라스 로드 실패({HW_ATLAS_SOURCE}): {ex}")
            HW_ATLAS = False

    if HW_ATLAS is not None and HW_ATLAS is not False:
        width, height = HW_ATLAS.size
        if width < 8 or height < 6:
            print(f"경고: 화투 아틀라스 크기가 너무 작다: {HW_ATLAS.size}")
            return None
        card_index = (month - 1) * 4 + variant
        col, row = card_index % 8, card_index // 8
        x0 = round(col * width / 8)
        x1 = round((col + 1) * width / 8)
        y0 = round(row * height / 6)
        y1 = round((row + 1) * height / 6)
        # 원본이 픽셀 카드 스프라이트이므로 먼저 최근접 확대하고, 마지막 64px 축소에서만
        # LANCZOS를 적용해 실제 도안의 선명한 픽셀 경계를 보존한다.
        return HW_ATLAS.crop((x0, y0, x1, y1)).resize((CARD_W, CARD_H), Image.Resampling.NEAREST)

    source_path = HW_ART_SOURCE_B if variant == 1 else HW_ART_SOURCE
    if variant == 1 and HW_ART_B is None:
        if not os.path.exists(source_path):
            return None
        try:
            HW_ART_B = Image.open(source_path).convert("RGBA")
        except Exception as ex:
            print(f"경고: 화투 B 원화 시트 로드 실패({source_path}): {ex}")
            return None
    if variant != 1 and HW_ART is None:
        if not os.path.exists(source_path):
            return None
        try:
            HW_ART = Image.open(source_path).convert("RGBA")
        except Exception as ex:
            print(f"경고: 화투 원화 시트 로드 실패({source_path}): {ex}")
            return None

    # imagegen 산출물(1983×793)의 패널 경계. 패널 사이의 밝은 거터는 버리고, 각 패널의
    # 원본 붉은 프레임까지 포함해 44×60 카드에 세로로 맞춘다. B 시트는 월별 카드 폭이
    # 일정하지 않으며, 카드 사이 거터가 다음 카드의 왼쪽 프레임과 가까워서 시트 전체
    # 셀 범위를 쓰면 오른쪽 흰 띠와 다음 카드 프레임이 섞인다. 실제 붉은 외곽 프레임
    # 기준으로 월별 패널을 자른다.
    if variant == 1:
        x_ranges = [(44, 380), (426, 760), (802, 1137), (1180, 1526), (1570, 1939)]
        y_ranges = [(26, 377), (405, 766)]
    else:
        x_ranges = [(45, 380), (427, 780), (823, 1158), (1205, 1558), (1598, 1942)]
        y_ranges = [(28, 380), (407, 763)]
    idx = month - 1
    row, col = divmod(idx, 5)
    left, right = x_ranges[col]
    top, bottom = y_ranges[row]
    source = HW_ART_B if variant == 1 else HW_ART
    panel = source.crop((left, top, right, bottom)).resize((CARD_W, CARD_H), Image.Resampling.LANCZOS)
    return panel


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
                   "textures": {"layer0": f"minecraft:item/card/{card_id}"}}, f, separators=(",", ":"))
    with open(item, "w") as f:
        json.dump({"model": {"type": "minecraft:model", "model": f"barkan:card/{card_id}"}},
                  f, separators=(",", ":"))


def main():
    # ★텍스처는 minecraft:item/ 아래여야 아이템 아틀라스에 자동 포함됨(barkan:card/는 아틀라스 밖→missing).
    #   모델/아이템 정의는 barkan:card/ 유지, layer0만 minecraft:item/card/를 가리킨다.
    rp_tex = os.path.join(RP, "assets/minecraft/textures/item/card")
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

    # 실제 섯다 20장 — 1·3월은 광+띠, 8월은 광+열끗, 나머지는 열끗+띠.
    # 비교용으로 1·3·8월의 미사용 A 패널도 함께 생성해 원화 선택지를 보존한다.
    for month in range(1, 11):
        cid = f"hw_{month}"
        save_tex(hwatu_card(month, False),
                 os.path.join(STAGING, "hw", f"{cid}.png"), os.path.join(rp_tex, f"{cid}.png"))
        ids.append(cid)
        cid = f"hw_{month}b"
        save_tex(hwatu_card(month, False, 1),
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
