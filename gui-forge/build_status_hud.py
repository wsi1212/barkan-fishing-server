#!/usr/bin/env python3
"""오른쪽 위 상태 HUD(소지금·레벨·캐시) 그림을 굽는다.

★판은 새로 그리지 않고 대화창 명패(dialogue-nameplate.png)에서 늘려 만든다.
  같은 손이 그린 것처럼 보이게 하려는 것이고, 실제로 이미 인게임에서 검증된 아트다.
  늘리는 방법은 "띠 반복"이 아니라 "안쪽 구간 resize" — 반복하면 같은 얼룩이 되풀이된다
  (2026-08-08 대화창 판에서 실제로 그 지적을 받았다).

★아이콘은 색만 바꾼 같은 모양을 쓰지 않는다. 실루엣을 다르게 간다:
  소지금=원(동전) · 레벨=별 · 캐시=마름모(보석). 색이 안 보여도 구분된다.

산출: ops/prod/betterhud/assets/status/ 에 png 4장
사용:  python3 build_status_hud.py
"""
import os

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "src", "dialogue", "dialogue-nameplate.png")
OUT = os.path.abspath(os.path.join(HERE, "..", "ops", "prod", "betterhud", "assets", "status"))

# 명패 실측(열이 아니라 행 프로파일로 뽑음): 0~4 위 나무테 · 7~24 양피지 · 26~31 아래 나무테.
# 10~21 이 밝기 162 로 완전히 균일해서, 늘려도 티가 안 나는 구간이 여기다.
STRETCH = (10, 22)      # [시작, 끝) — 이 구간만 세로로 늘린다
PLATE_H = 56            # 3줄(소지금·레벨·캐시)이 들어갈 높이

# 왼쪽 위 판(위치·환경)은 2줄이지만 더 넓어야 한다.
# "바르칸 > 폭포_뒤_동굴_2층" 같은 지역명이 나오는데 110px 로는 어림도 없다.
# ★단 160 을 넘기면 글리프 아틀라스에 못 들어가 통째로 사라진다 — 150 이 상한선이다.
PLACE_W, PLACE_H = 150, 42
H_STRETCH = (30, 80)    # 명패 가로 방향으로 늘려도 티 안 나는 구간(양피지 안쪽)

SS = 8                  # 아이콘은 8배로 그린 뒤 줄여서 계단을 없앤다
ICON = 12


def _stretch_v(im, target_h):
    w, h = im.size
    a, b = STRETCH
    band = im.crop((0, a, w, b)).resize((w, (b - a) + (target_h - h)), Image.LANCZOS)
    out = Image.new("RGBA", (w, target_h))
    out.alpha_composite(im.crop((0, 0, w, a)), (0, 0))
    out.alpha_composite(band, (0, a))
    out.alpha_composite(im.crop((0, b, w, h)), (0, a + band.height))
    return out


def _stretch_h(im, target_w):
    w, h = im.size
    a, b = H_STRETCH
    band = im.crop((a, 0, b, h)).resize(((b - a) + (target_w - w), h), Image.LANCZOS)
    out = Image.new("RGBA", (target_w, h))
    out.alpha_composite(im.crop((0, 0, a, h)), (0, 0))
    out.alpha_composite(band, (a, 0))
    out.alpha_composite(im.crop((b, 0, w, h)), (a + band.width, 0))
    return out


def build_plate():
    return _stretch_v(Image.open(SRC).convert("RGBA"), PLATE_H)


def build_place_plate():
    """왼쪽 위 판 — 가로도 같이 늘린다. 세로 먼저 늘리고 가로를 늘려야
    모서리 장식(볼트)이 안 눌린다(반대로 하면 볼트가 타원이 된다)."""
    im = _stretch_v(Image.open(SRC).convert("RGBA"), PLACE_H)
    return _stretch_h(im, PLACE_W)


def _shrink(big, palette):
    """8배 그림을 12px 픽셀아트로 내린다.

    ★그냥 resize 만 하면 안티에일리어싱이 남아 뭉갠 젤리처럼 보인다(첫 시도에서 그랬다).
      면적평균(BOX)으로 내린 뒤 **알파를 이진화하고 색을 팔레트에 스냅**해서 각을 세운다.
      팔레트 스냅이 곧 색 수 제한이라, 인게임 12px 에서 형태가 또렷하게 읽힌다.
    """
    small = big.resize((ICON, ICON), Image.BOX)
    px = small.load()
    for y in range(ICON):
        for x in range(ICON):
            r, g, b, a = px[x, y]
            if a < 128:
                px[x, y] = (0, 0, 0, 0)
                continue
            best = min(palette, key=lambda c: (c[0]-r)**2 + (c[1]-g)**2 + (c[2]-b)**2)
            px[x, y] = (*best, 255)
    return small


GOLD = [(92, 58, 12), (168, 118, 32), (226, 176, 66), (248, 218, 134), (255, 244, 206)]
TEAL = [(14, 62, 66), (28, 118, 122), (58, 176, 176), (126, 226, 216), (214, 252, 244)]
VIOLET = [(52, 24, 82), (110, 58, 158), (168, 102, 226), (214, 170, 252), (250, 230, 255)]


def icon_coin():
    """소지금 — 정원(正圓) 동전. 사방 테두리를 두르고 왼쪽 위만 광택."""
    s = ICON * SS
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    # ★원만은 8배로 그려서 줄이지 않는다. 줄이는 순간 테두리 굵기가 방향마다 달라져
    #   원이 아니라 찌그러진 덩어리로 읽힌다(두 번 시도해서 두 번 다 그랬다).
    #   대신 12px 격자에서 반지름을 직접 판정해 링 두께를 사방 균일하게 만든다.
    del im, d, s
    out = Image.new("RGBA", (ICON, ICON), (0, 0, 0, 0))
    px = out.load()
    c = (ICON - 1) / 2.0
    for y in range(ICON):
        for x in range(ICON):
            dx, dy = x - c, y - c
            r = (dx * dx + dy * dy) ** 0.5
            if r > 5.7:
                continue
            if r > 4.55:
                col = GOLD[0]                       # 테두리 — 사방 균일
            elif (dx + 1.3) ** 2 + (dy + 1.5) ** 2 < 1.9 ** 2:
                col = GOLD[4]                       # 광택 심
            elif (dx + 1.1) ** 2 + (dy + 1.3) ** 2 < 3.1 ** 2:
                col = GOLD[3]                       # 광택 번짐
            elif r > 3.7:
                col = GOLD[1]                       # 가장자리 그늘
            else:
                col = GOLD[2]
            px[x, y] = (*col, 255)
    return out


def icon_star():
    """레벨 — 별. ★청록으로 간다: 금색이면 동전과 한눈에 안 구분된다(색+실루엣 둘 다 다르게)."""
    import math
    s = ICON * SS
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    # 안쪽 반지름을 크게(ro의 0.46) 잡아야 다리가 뭉툭해지지 않고 12px 에서도 별로 읽힌다.
    cx, cy, ro = s / 2, s / 2 + 0.3 * SS, 5.6 * SS
    ri = ro * 0.46

    def star(scale):
        p = []
        for i in range(10):
            ang = -math.pi / 2 + i * math.pi / 5
            r = (ro if i % 2 == 0 else ri) * scale
            p.append((cx + r * math.cos(ang), cy + r * math.sin(ang)))
        return p

    d.polygon(star(1.00), fill=TEAL[0] + (255,))
    d.polygon(star(0.80), fill=TEAL[2] + (255,))
    d.polygon(star(0.52), fill=TEAL[3] + (255,))
    d.polygon([(cx - 0.5 * SS, cy - 2.4 * SS), (cx + 0.5 * SS, cy - 2.4 * SS), (cx, cy - 0.6 * SS)],
              fill=TEAL[4] + (255,))
    return _shrink(im, TEAL)


def icon_gem():
    """캐시 — 마름모 보석. 윗면을 좁히고 아래 꼭짓점을 뾰족하게(풍선처럼 안 보이게)."""
    s = ICON * SS
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    cx = s / 2
    top, bot = 1.4 * SS, 10.9 * SS
    lft, rgt, shoulder = 2.3 * SS, 9.7 * SS, 4.6 * SS      # 어깨 폭을 좁혔다
    d.polygon([(cx, top), (rgt, shoulder), (cx, bot), (lft, shoulder)], fill=VIOLET[0] + (255,))
    d.polygon([(cx, top + 0.9 * SS), (rgt - 0.9 * SS, shoulder), (cx, bot - 1.0 * SS),
               (lft + 0.9 * SS, shoulder)], fill=VIOLET[2] + (255,))
    # 위 절단면 — 여기만 밝게 해야 "깎인 보석"으로 읽힌다
    d.polygon([(cx, top + 0.9 * SS), (rgt - 0.9 * SS, shoulder), (cx, shoulder + 0.7 * SS),
               (lft + 0.9 * SS, shoulder)], fill=VIOLET[3] + (255,))
    d.polygon([(cx, top + 1.3 * SS), (cx + 1.1 * SS, shoulder - 0.3 * SS), (cx, shoulder)],
              fill=VIOLET[4] + (255,))
    return _shrink(im, VIOLET)


def main():
    os.makedirs(OUT, exist_ok=True)
    made = [("status-plate.png", build_plate()),
            ("place-plate.png", build_place_plate()),
            ("icon-coin.png", icon_coin()),
            ("icon-star.png", icon_star()),
            ("icon-gem.png", icon_gem())]
    for name, im in made:
        # ★파일명은 소문자만. 대문자가 하나만 섞여도 폰트 파일 전체가 거부되고 HUD가 통째로 사라진다.
        assert name == name.lower(), name
        assert im.height > 1, "height 1 글리프는 폰트 전체를 무효화한다"
        assert im.width <= 160, f"{name} 폭 {im.width} — 160 넘으면 아틀라스에서 조용히 사라진다"
        im.save(os.path.join(OUT, name))
        print(f"  {name}  {im.width}x{im.height}")
    print(f"-> {OUT}")


if __name__ == "__main__":
    main()
