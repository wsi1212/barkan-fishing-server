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


SYMBOLS = [
    (0x2600, "uni2600", sun),        # ☀ 낮
    (0x2601, "uni2601", cloud),      # ☁ 맑음/흐림
    (0x2602, "uni2602", umbrella),   # ☂ 비
    (0x26A1, "uni26A1", bolt),       # ⚡ 뇌우
    (0x2744, "uni2744", snowflake),  # ❄ 눈보라
    (0x224B, "uni224B", waves),      # ≋ 모래바람
    (0x263D, "uni263D", crescent),   # ☽ 밤
]


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
