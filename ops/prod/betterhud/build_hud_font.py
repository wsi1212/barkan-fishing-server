#!/usr/bin/env python3
"""어그로체에 HUD 용 날씨·시간 기호 7자를 추가한 폰트를 만든다.

★왜 필요한가: 어그로체는 글리프가 12,271자나 있는데 ☀ ☁ ☂ ⚡ ❄ ≋ ☽ 만 없다.
  BetterHud 폰트에 없는 글자는 MC 기본 폰트로 폴백되는데, **폴백 글리프는 BetterHud 의
  위치 인코딩(거대 음수 ascent)을 안 달고 있어서 셰이더가 못 옮긴다** — 그 글자만
  화면 위 보스바 자리에 덩그러니 찍힌다(2026-08-10 실제 사고).
  대안이던 use-unifont 는 한글까지 유니폰트로 바꿔버려서 반려됐다(글꼴이 완전히 달라진다).

★원본을 덮어쓰지 않는다. 원본 + 기호 -> HUD 전용 TTF 를 **매번 다시 뽑는다.**
  원본에 직접 넣으면 폰트를 갱신할 때 추가분이 조용히 사라지고 원인을 못 찾는다.

★남의 폰트에서 글리프를 복사하지 않는다(그쪽 라이선스가 또 얽힌다). 직접 그린다.
  어그로체는 획이 매우 두꺼운 기하학 산세리프라, 얇은 선으로 그리면 확 튄다.
  그래서 전부 꽉 찬 덩어리로 그리고, 실사용 크기(10px)에서 읽히는지로 판정한다.

사용:  python3 build_hud_font.py [출력.ttf]
      python3 build_hud_font.py [원본.ttf] [출력.ttf]
"""
import math
import os
import sys

from fontTools.ttLib import TTFont
from fontTools.pens.ttGlyphPen import TTGlyphPen

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_SRC = os.path.expanduser("~/development/barkan-resourcepack/assets/barkan/font/aggro_medium.ttf")
DEFAULT_DST = os.path.join(HERE, "assets", "fonts", "aggro_medium_hud.ttf")

# 이 폰트의 기호 규격(●★ 에서 실측): advance 940, 중심 (470, 300), 반지름 약 400.
ADV = 940
CX, CY, R = 470, 300, 400


def cw(pts):
    """윤곽을 시계방향으로 정규화한다.

    ★TrueType 은 non-zero winding 이라 **겹치는 윤곽의 방향이 서로 반대면 겹친 부분이
      파인다.** 구름(원3+사각)과 눈송이(막대3)의 가운데가 뚫렸던 원인이 이것이다.
      구멍을 낼 때만 일부러 반대로 돌린다(초승달).
    """
    area = sum((pts[i][0] * pts[(i + 1) % len(pts)][1] - pts[(i + 1) % len(pts)][0] * pts[i][1])
               for i in range(len(pts)))
    return pts if area < 0 else pts[::-1]      # 폰트 좌표는 y 가 위 -> 음수 면적이 시계방향


def ccw(pts):
    return pts[::-1] if cw(pts) is pts else pts


def circle(cx, cy, r, n=40, ccw=False):
    step = (2 * math.pi / n) * (1 if ccw else -1)      # 기본은 시계방향(바깥 윤곽)
    return [(round(cx + r * math.cos(i * step)), round(cy + r * math.sin(i * step)))
            for i in range(n)]


def ring_sector(cx, cy, r0, r1, a0, a1, n=6):
    """부채꼴 띠(광선용). 각도는 도(degree)."""
    out = []
    for i in range(n + 1):
        a = math.radians(a0 + (a1 - a0) * i / n)
        out.append((round(cx + r1 * math.cos(a)), round(cy + r1 * math.sin(a))))
    for i in range(n, -1, -1):
        a = math.radians(a0 + (a1 - a0) * i / n)
        out.append((round(cx + r0 * math.cos(a)), round(cy + r0 * math.sin(a))))
    return out


def bar(cx, cy, length, thick, deg):
    """중심을 지나는 두꺼운 막대(눈송이용)."""
    a = math.radians(deg)
    dx, dy = math.cos(a) * length / 2, math.sin(a) * length / 2
    nx, ny = -math.sin(a) * thick / 2, math.cos(a) * thick / 2
    return [(round(cx - dx + nx), round(cy - dy + ny)), (round(cx + dx + nx), round(cy + dy + ny)),
            (round(cx + dx - nx), round(cy + dy - ny)), (round(cx - dx - nx), round(cy - dy - ny))]


def wave_band(y, thick, x0=70, x1=870, amp=70, n=24):
    """물결 띠(모래바람 ≋ 용). 위/아래 폴리라인을 이어 닫는다."""
    top, bot = [], []
    for i in range(n + 1):
        t = i / n
        x = x0 + (x1 - x0) * t
        yy = y + amp * math.sin(t * 2 * math.pi)
        top.append((round(x), round(yy + thick / 2)))
        bot.append((round(x), round(yy - thick / 2)))
    return top + bot[::-1]


def sun():
    # ★원반과 광선 사이 틈이 크면 톱니바퀴로 보인다. 원반을 키우고 광선을 바짝 붙인다.
    c = [circle(CX, CY, 250)]
    for k in range(8):                                  # 광선 8 갈래
        a = k * 45
        c.append(ring_sector(CX, CY, 268, 400, a - 11, a + 11))
    return [cw(x) for x in c]


def cloud():
    return [cw(x) for x in (circle(340, 300, 165), circle(480, 370, 200), circle(640, 305, 150),
                            [(300, 145), (690, 145), (690, 320), (300, 320)])]


def umbrella():
    canopy = ring_sector(CX, 300, 0, 390, 0, 180, n=20)   # 반원 덮개
    stem = [(438, -95), (502, -95), (502, 300), (438, 300)]
    hook = [(320, -95), (438, -95), (438, -20), (370, -20), (370, 40), (320, 40)]
    return [cw(canopy), cw(stem), cw(hook)]


def bolt():
    return [cw([(600, 700), (250, 250), (430, 250), (330, -100), (700, 360), (500, 360)])]


def snowflake():
    return [cw(bar(CX, CY, 780, 125, 90)), cw(bar(CX, CY, 780, 125, 30)),
            cw(bar(CX, CY, 780, 125, 150))]


def waves():
    return [cw(wave_band(480, 95)), cw(wave_band(300, 95)), cw(wave_band(120, 95))]


def crescent():
    # 바깥 원(시계) - 안쪽 원(반시계) = 초승달. 겹치는 부분이 파인다.
    # 바깥은 시계, 안쪽은 반시계 -> 겹친 부분이 파여 초승달이 된다.
    # ★안쪽 원을 너무 많이 겹치면 달이 실오라기처럼 얇아진다. 오프셋을 줄여 두툼하게.
    return [cw(circle(CX, CY, 400)), ccw(circle(CX + 215, CY + 40, 330))]



# ===== 날씨/시간 전용 글리프 17종 (U+EA00~EA10) =====
# ★왜 유니코드 기호가 아니라 전용 코드포인트인가:
#   ☀ 하나를 낮·열대야·땡볕이, ⚡ 를 뇌우·태풍이 나눠 쓰고 있었다(색만 달랐다).
#   8px 에서 색만으로 가르는 건 약하다. 전용 코드포인트를 쓰면 17종이 각자 모양을 갖는다.
# ★같은 코드포인트를 메인 리소스팩이 컬러 비트맵으로도 갖고 있다
#   (barkan-resourcepack/tools/gen_weather_glyphs.py, U+EA00~EA10).
#   그래서 채팅(minecraft:default)은 컬러, HUD(이 폰트)는 단색 — 코드포인트 하나로 양쪽이 산다.
# ★한 글리프 안에서 색을 나눌 수는 없다(MC 폰트 렌더러는 컬러 테이블을 안 읽는다).
#   아이콘별 색은 호출부의 § 코드가 그대로 준다.

def _drop(cx, cy, w, h):
    """물방울 — 위가 뾰족하고 아래가 둥근 쐐기."""
    return [(round(cx), round(cy + h / 2)),
            (round(cx + w / 2), round(cy - h / 6)),
            (round(cx + w / 4), round(cy - h / 2)),
            (round(cx - w / 4), round(cy - h / 2)),
            (round(cx - w / 2), round(cy - h / 6))]


def _hbar(y, thick, x0, x1):
    return [(round(x0), round(y + thick / 2)), (round(x1), round(y + thick / 2)),
            (round(x1), round(y - thick / 2)), (round(x0), round(y - thick / 2))]


def _cloud_at(cy, scale=1.0):
    """cloud() 를 위아래로 옮기고 줄인 것 — 아래에 비/번개를 놓을 자리를 만든다."""
    def s(v, base):
        return base + (v - base) * scale
    return [circle(s(340, 470), cy, 165 * scale), circle(s(480, 470), cy + 70 * scale, 200 * scale),
            circle(s(640, 470), cy + 5 * scale, 150 * scale),
            [(round(s(300, 470)), round(cy - 155 * scale)), (round(s(690, 470)), round(cy - 155 * scale)),
             (round(s(690, 470)), round(cy + 20 * scale)), (round(s(300, 470)), round(cy + 20 * scale))]]


def w_day():        # 낮 — 원반 + 광선 8
    return sun()


def w_clear():      # 맑음 — 광선 없는 맨 원반 (낮보다 광학적으로 가볍다)
    return [cw(circle(CX, CY, 330))]


def w_scorch():     # 땡볕 — 해 + 달아오른 아지랑이
    # ★굵은 광선 4갈래는 «십자가»로 읽힌다. 광선은 낮처럼 8갈래로 두고,
    #   구분은 «아래의 아지랑이»로 낸다(열대야가 달+아지랑이인 것과 짝).
    c = [circle(CX, 420, 215)]
    for k in range(8):
        a = k * 45
        c.append(ring_sector(CX, 420, 232, 350, a - 13, a + 13))
    return [cw(x) for x in c] + [cw(wave_band(-40, 100, 110, 830, amp=50))]


def w_dusk():       # 저녁 — 지평선에 반쯤 잠긴 해 (반원 + 지평선)
    # ★온전한 원반을 막대에 얹으면 «아령»으로 읽힌다. 반원으로 잘라 지평선에 걸친다.
    c = [ring_sector(CX, 150, 0, 330, 0, 180, n=20)]
    for a in (150, 90, 30):
        c.append(ring_sector(CX, 150, 355, 460, a - 13, a + 13))
    c.append(_hbar(110, 105, 70, 870))
    return [cw(x) for x in c]


def w_night():      # 밤 — 초승달
    return crescent()


def w_dawn():       # 새벽 — 지는 달 + 뜨는 해
    # ★«초승달 + 가로막대»는 열대야(초승달 + 아지랑이)와 실루엣이 겹친다.
    #   아래를 반원(뜨는 해)으로 바꿔 «달이 지고 해가 뜬다»로 읽히게 한다.
    return [cw(circle(285, 500, 265)), ccw(circle(420, 528, 222)),
            cw(ring_sector(655, 15, 0, 250, 0, 180, n=18)),
            cw(_hbar(-25, 90, 370, 870))]


def w_tropical():   # 열대야 — 초승달 + 피어오르는 열기 한 줄
    return [cw(circle(CX, 400, 300)), ccw(circle(CX + 165, 432, 248)),
            cw(wave_band(-30, 95, 110, 830, amp=55))]


def w_rain():       # 비 — 구름 + 물방울 3
    c = [cw(x) for x in _cloud_at(360, 0.82)]
    for x in (250, 470, 690):
        c.append(cw(_drop(x, 40, 130, 210)))
    return c


def w_thunder():    # 뇌우 — 구름 + 번개
    c = [cw(x) for x in _cloud_at(400, 0.80)]
    c.append(cw([(560, 260), (300, -60), (440, -60), (360, -290), (640, 30), (490, 30)]))
    return c


def w_typhoon():    # 태풍 — 구름 + 비스듬히 몰아치는 빗줄기 3
    c = [cw(x) for x in _cloud_at(400, 0.80)]
    for x in (230, 440, 650):
        c.append(cw(bar(x, 30, 300, 95, 62)))
    return c


def w_coaldust():   # 탄광먼지 — 각진 탄가루 덩이 + 떨어지는 알갱이 2 (구름 계열과 실루엣을 가른다)
    lump = [(150, 300), (300, 480), (560, 500), (760, 340), (700, 170), (400, 130), (190, 190)]
    return [cw(lump), cw(_hbar(20, 110, 240, 400)), cw(_hbar(-60, 110, 520, 680))]


def w_fog():        # 안개 — 흐르는 가로 층 3
    # ★두께가 같고 길이도 비슷하면 «≡ 햄버거 메뉴»가 된다. 길이·두께·좌우를 전부 어긋낸다.
    # 계단처럼 좌우로 크게 밀어 «가운데를 관통하는 막대»가 없게 만든다 — 그게 ≡ 로 읽히는 조건이다.
    return [cw(_hbar(470, 100, 390, 870)), cw(_hbar(260, 92, 70, 560)),
            cw(_hbar(50, 108, 300, 810))]


def w_meteor():     # 유성우 — 평행 유성 2 (머리는 진행방향인 좌하단, 꼬리는 삼각형)
    # ★막대 꼬리는 굵기가 일정해 «사탕지팡이»가 된다. 뒤로 갈수록 좁아져야 유성이다.
    out = []
    for (hx, hy, ln, r) in ((215, 20, 430, 105), (615, 300, 300, 80)):
        out.append(cw(circle(hx, hy, r)))
        ex, ey = hx + ln * 0.72, hy + ln * 0.72       # 45도 우상향 꼬리 끝
        out.append(cw([(round(hx - r * 0.7), round(hy + r * 0.7)),
                       (round(ex), round(ey)),
                       (round(hx + r * 0.7), round(hy - r * 0.7))]))
    return out


def w_aurora():     # 오로라 — 위아래로 흐르는 커튼 3
    out = []
    for x in (200, 470, 740):
        pts = []
        n = 14
        for i in range(n + 1):
            t = i / n
            y = -100 + 800 * t
            xx = x + 85 * math.sin(t * 1.6 * math.pi)
            pts.append((round(xx + 55), round(y)))
        for i in range(n, -1, -1):
            t = i / n
            y = -100 + 800 * t
            xx = x + 85 * math.sin(t * 1.6 * math.pi)
            pts.append((round(xx - 55), round(y)))
        out.append(cw(pts))
    return out


def w_tide():       # 만조 — 보름달 + 밀려오는 물결 2
    # ★달이 물결에 닿으면 물결의 «점»처럼 붙어 보인다. 위로 확실히 떼어 놓는다.
    return [cw(circle(690, 560, 160)),
            cw(wave_band(150, 105, 70, 870, amp=62)),
            cw(wave_band(-30, 105, 70, 870, amp=62))]


def w_sand():       # 모래바람 — 물결 띠 3 (≋ 와 같은 형태)
    return waves()


def w_blizzard():   # 눈보라 — 눈결정
    return snowflake()


WEATHER = [
    (0xEA00, "barkanDay",      w_day),
    (0xEA01, "barkanDusk",     w_dusk),
    (0xEA02, "barkanNight",    w_night),
    (0xEA03, "barkanDawn",     w_dawn),
    (0xEA04, "barkanClear",    w_clear),
    (0xEA05, "barkanRain",     w_rain),
    (0xEA06, "barkanThunder",  w_thunder),
    (0xEA07, "barkanFog",      w_fog),
    (0xEA08, "barkanMeteor",   w_meteor),
    (0xEA09, "barkanAurora",   w_aurora),
    (0xEA0A, "barkanTide",     w_tide),
    (0xEA0B, "barkanTropical", w_tropical),
    (0xEA0C, "barkanScorch",   w_scorch),
    (0xEA0D, "barkanSand",     w_sand),
    (0xEA0E, "barkanTyphoon",  w_typhoon),
    (0xEA0F, "barkanBlizzard", w_blizzard),
    (0xEA10, "barkanCoalDust", w_coaldust),
]

SYMBOLS = [
    (0x2600, "uni2600", sun),        # ☀ 낮
    (0x2601, "uni2601", cloud),      # ☁ 맑음/흐림
    (0x2602, "uni2602", umbrella),   # ☂ 비
    (0x26A1, "uni26A1", bolt),       # ⚡ 뇌우
    (0x2744, "uni2744", snowflake),  # ❄ 눈보라
    (0x224B, "uni224B", waves),      # ≋ 모래바람
    (0x263D, "uni263D", crescent),   # ☽ 밤
] + WEATHER


def main(dst=DEFAULT_DST, src=DEFAULT_SRC):
    font = TTFont(src)
    glyf, hmtx = font["glyf"], font["hmtx"]
    order = font.getGlyphOrder()
    added = [n for _, n, _ in SYMBOLS if n not in order]
    font.setGlyphOrder(list(order) + added)

    for cp, name, maker in SYMBOLS:
        pen = TTGlyphPen(None)
        for pts in maker():
            pen.moveTo(pts[0])
            for p in pts[1:]:
                pen.lineTo(p)
            pen.closePath()
        glyf[name] = pen.glyph()
        xs = [p[0] for c in maker() for p in c]
        hmtx[name] = (ADV, min(xs))
        for table in font["cmap"].tables:
            if table.isUnicode():
                table.cmap[cp] = name

    os.makedirs(os.path.dirname(dst), exist_ok=True)
    font.save(dst)
    print(f"원본: {src}")
    print(f"저장: {dst}")
    print("추가한 글자:", " ".join(chr(cp) for cp, _, _ in SYMBOLS))


if __name__ == "__main__":
    args = sys.argv[1:]
    if len(args) > 2:
        raise SystemExit("사용법: build_hud_font.py [출력.ttf] 또는 build_hud_font.py [원본.ttf] [출력.ttf]")
    if len(args) == 1:
        main(dst=args[0])
    elif len(args) == 2:
        main(src=args[0], dst=args[1])
    else:
        main()
