#!/usr/bin/env python3
"""레시피 두루마리 아이콘 v2 — 슬롯 꽉 채움 + 굵고 진한 기호 (v1 반려: 작고 흐림).

바닐라 banner_pattern이 16px 슬롯을 꽉 채우고 심볼이 굵고 진한 걸 벤치마크. 32px 캔버스를
두루마리로 거의 다 채우고, 심볼은 2~3px 굵기·고대비 다크로 그린다. 등급 색 씰(seal)로
같은 카테고리 항목 구분(등급 인자 있을 때). 슬롯 16px에서 반드시 검증.
"""
import os, math
from PIL import Image
N = 32

CREAM, CREAM_SH, CREAM_SH2 = "f1eddc", "d8cfb0", "bcae86"
OUT = "463528"                     # 진한 갈색 외곽(고대비)
WOOD, WOOD_HI, WOOD_SH = "8a6d3f", "a88a52", "5e4526"
DOWEL, DOWEL_DK = "6b4a28", "43301c"

GRADE = {"E": "9aa0a6", "D": "6fae3f", "C": "3a86c8", "B": "9a5cd0", "A": "e0a020", "S": "d23b2b"}


def hx(h):
    h = h.lstrip("#"); return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), 255)


def put(im, x, y, c):
    x, y = int(round(x)), int(round(y))
    if 0 <= x < N and 0 <= y < N:
        im.putpixel((x, y), hx(c) if isinstance(c, str) else c)


def rect(im, x0, y0, x1, y1, c):
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            put(im, x, y, c)


def thick(im, pts, c, r=1):
    for (x, y) in pts:
        for dx in range(-r, r + 1):
            for dy in range(-r, r + 1):
                if dx * dx + dy * dy <= r * r + (1 if r > 1 else 0):
                    put(im, x + dx, y + dy, c)


AGE = "d8cca6"      # 에이징 얼룩
AGE2 = "c8b98c"     # 진한 얼룩/데클


def _roll(im, y0, y1):
    """말린 나무 롤 + 양끝 축(dowel) — 원통감(위 하이라이트/아래 그림자)."""
    rect(im, 3, y0, 28, y1, WOOD)
    for x in range(3, 29):
        put(im, x, y0, OUT); put(im, x, y0 + 1, WOOD_HI); put(im, x, y1, OUT); put(im, x, y1 - 1, WOOD_SH)
    for (a, b) in [(0, 4), (27, 31)]:              # 양끝 축(캔버스 끝까지)
        rect(im, a, y0 + 1, b, y1 - 1, DOWEL)
        for y in range(y0 + 1, y1):
            put(im, a, y, DOWEL_DK); put(im, b, y, DOWEL_DK)
        for x in range(a, b + 1):
            put(im, x, y0 + 1, WOOD_HI); put(im, x, y1 - 1, DOWEL_DK)


def scroll_base(grade=None):
    """양끝 두루마리(위·아래 롤) + 에이징 양피지 = 진짜 스크롤 느낌."""
    im = Image.new("RGBA", (N, N), (0, 0, 0, 0))
    # 양피지 몸통 y6~26 (위·아래 롤 사이)
    rect(im, 4, 6, 27, 26, CREAM)
    # 에이징: 세로 얼룩 몇 줄 + 얼룩점(결정적)
    for x in (8, 9, 16, 22, 23):
        for y in range(7, 26):
            if (x + y) % 3 == 0:
                put(im, x, y, AGE)
    for sx, sy in [(11, 10), (19, 14), (14, 21), (24, 9), (7, 18)]:
        put(im, sx, sy, AGE2)
    # 좌우 데클(우글쭈글) 가장자리 + 외곽
    for y in range(6, 27):
        put(im, 3, y, OUT); put(im, 28, y, OUT)
        put(im, 4, y, AGE2 if y % 2 else CREAM_SH); put(im, 27, y, AGE2 if y % 3 else CREAM_SH)
    # 위/아래 롤 + 롤에 눌린 커브 그림자
    _roll(im, 1, 6)
    _roll(im, 26, 31)
    for x in range(4, 28):
        put(im, x, 6, WOOD_SH); put(im, x, 26, WOOD_SH)   # 롤 밑/위 그림자
        put(im, x, 7, "f4eede")                            # 커브 하이라이트(살짝 말림)
    # 등급 씰(왁스 도장) — 우하단, 스크롤 위에 얹힘
    if grade and grade in GRADE:
        gc = GRADE[grade]
        for dx in range(-2, 3):
            for dy in range(-2, 3):
                if dx * dx + dy * dy <= 4:
                    put(im, 23 + dx, 22 + dy, gc)
        put(im, 22, 21, "ffffff"); put(im, 23, 22, OUT)
    return im


# ── 굵고 진한 기호 (양피지 중앙 x7~24, y14~28), 2~3px ──
def sym_rod(im, ac):
    pts = [(9, 27), (11, 25), (13, 23), (15, 21), (17, 19), (19, 17), (21, 15)]
    thick(im, pts, ac, 1)
    put(im, 22, 14, "d23b2b"); put(im, 23, 13, "e0642c"); put(im, 22, 13, "ffcf5a")  # 불붙은 팁
    thick(im, [(9, 27), (10, 28)], OUT, 1)  # 손잡이


def sym_reel(im, ac):
    cx, cy, r = 15, 21, 5
    for a in range(0, 360, 12):
        put(im, cx + math.cos(math.radians(a)) * r, cy + math.sin(math.radians(a)) * r, ac)
        put(im, cx + math.cos(math.radians(a)) * (r - 1), cy + math.sin(math.radians(a)) * (r - 1), ac)
    thick(im, [(cx, cy)], ac, 1)
    thick(im, [(cx + 6, cy - 4)], ac, 1)  # 크랭크 knob


def sym_line(im, ac):
    for x in range(7, 25):
        y = 21 + round(3 * math.sin((x - 7) * 0.7))
        put(im, x, y, ac); put(im, x, y + 1, ac)


def sym_hook(im, ac):                                           # 파치먼트 y6~26 중앙(≈16)
    for y in range(9, 20):
        put(im, 16, y, ac); put(im, 17, y, ac)                 # 샤프트 2px
    thick(im, [(15, 20), (14, 20), (13, 19), (13, 18), (14, 17)], ac, 0)  # J
    thick(im, [(16, 17)], ac, 0)                                # 미늘
    rect(im, 15, 8, 18, 9, ac)                                  # 고리


def sym_bobber(im, ac):
    cx = 15
    rect(im, cx - 2, 9, cx + 2, 13, "d23b2b")                  # 상단 빨강(굵게)
    put(im, cx - 1, 10, "ff6a4a")
    for y in range(14, 23):
        put(im, cx, y, ac); put(im, cx + 1, y, ac)            # 안테나 2px
    thick(im, [(cx, 21)], ac, 1)


def sym_bait(im, ac):
    for i, x in enumerate(range(8, 24, 1)):
        y = 16 + round(2.5 * math.sin((x - 8) * 0.8))
        put(im, x, y, ac); put(im, x, y + 1, ac)
    put(im, 23, 14, "3a3140"); put(im, 22, 14, "3a3140")       # 머리


def sym_trap(im, ac):
    for i, y in enumerate(range(10, 22)):
        w = 3 + i // 2
        put(im, 15 - w, y, ac); put(im, 16 + w, y, ac)         # 좌우 벽
        if y == 21:
            for x in range(15 - w, 16 + w + 1):
                put(im, x, y, ac)                              # 바닥
    for x in range(11, 21, 3):
        for y in range(12, 21):
            put(im, x, y, ac)                                  # 세로살


CATS = {
    "rod":    (sym_rod,    "5a3d22"),
    "reel":   (sym_reel,   "36424e"),
    "line":   (sym_line,   "255a7a"),
    "hook":   (sym_hook,   "45505a"),
    "bobber": (sym_bobber, "4a3a2a"),
    "bait":   (sym_bait,   "3d6a22"),
    "trap":   (sym_trap,   "6a4a26"),
}

# 바닐라 아이템 텍스처를 회색 도장으로(유저 지시): rod/reel/line/bait는 실제 아이콘, 나머지는 손그림.
VAN = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vanilla_ref")
STAMP = {"rod": "fishing_rod.png", "reel": "clock_00.png", "line": "string.png", "bait": "slime_ball.png"}


def gray_stamp(im, texfile, box=(8, 8, 15)):
    """바닐라 텍스처를 회색+살짝 진하게(양피지 대비) 만들어 양피지 중앙에 도장."""
    src = Image.open(os.path.join(VAN, texfile)).convert("RGBA")
    ox, oy, size = box
    src = src.resize((size, size), Image.LANCZOS)
    sp = src.load()
    for y in range(size):
        for x in range(size):
            r, g, b, a = sp[x, y]
            if a < 40:
                continue
            lum = int(0.299 * r + 0.587 * g + 0.114 * b)
            v = int(lum * 0.5 + 20)                 # 진한 회색(크림 위 가독)
            put(im, ox + x, oy + y, (v, v, max(0, v - 4), 255))  # 아주 살짝 웜(잉크 느낌)


def main():
    HERE = os.path.dirname(os.path.abspath(__file__))
    out = os.path.join(HERE, "out", "recipe"); os.makedirs(out, exist_ok=True)
    def draw(im, key, fn, ac):
        if key in STAMP:
            gray_stamp(im, STAMP[key])              # 바닐라 아이콘 회색 도장
        else:
            fn(im, ac)                              # 손그림 심볼(hook/bobber/trap)

    icons = {}
    for key, (fn, ac) in CATS.items():
        base = scroll_base(); draw(base, key, fn, ac)   # 씰 없는 폴백
        base.save(os.path.join(out, f"{key}.png")); icons[key] = base
        for g in GRADE:                             # 카테고리×등급 (씰 색) — 파일명 소문자(NamespacedKey 규약)
            im = scroll_base(g); draw(im, key, fn, ac)
            im.save(os.path.join(out, f"{key}_{g.lower()}.png"))
    # 리뷰용 등급 샘플(낚싯대)
    grades = {}
    for g in ["E", "D", "C", "B", "A", "S"]:
        im = scroll_base(g); sym_rod(im, CATS["rod"][1]); grades[g] = im
    # 콘택트시트
    def sheet(d, name, sc=8):
        cols = len(d); pad = 8
        b = Image.new("RGBA", (cols * (N * sc) + (cols + 1) * pad, N * sc + pad * 2), (205, 205, 205, 255))
        for i, im in enumerate(d.values()):
            b.alpha_composite(im.resize((N * sc, N * sc), Image.NEAREST), (pad + i * (N * sc + pad), pad))
        b.convert("RGB").save(os.path.join(out, name))
    sheet(icons, "sheet.png")
    sheet(grades, "grades.png")
    # ★ 진짜 슬롯 크기(16px) 검증 — 회색 슬롯에 실제 표시크기
    SLOT = (139, 139, 139, 255); s2 = 7
    allv = list(icons.values()) + list(grades.values())
    cols = len(allv)
    b = Image.new("RGBA", (cols * (18 * s2) + 8, 18 * s2 + 8), (198, 198, 198, 255))
    for i, im in enumerate(allv):
        real = im.resize((16, 16), Image.LANCZOS)
        cell = Image.new("RGBA", (18, 18), SLOT); cell.alpha_composite(real, (1, 1))
        b.alpha_composite(cell.resize((18 * s2, 18 * s2), Image.NEAREST), (4 + i * (18 * s2), 4))
    b.convert("RGB").save(os.path.join(out, "slots16.png"))
    print("recipe v2 →", out)


if __name__ == "__main__":
    main()
