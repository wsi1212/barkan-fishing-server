#!/usr/bin/env python3
"""오른쪽 위 상태 HUD(소지금·레벨·캐시) 그림을 굽는다.

★판은 새로 그리지 않고 대화창 명패(dialogue-nameplate.png)에서 늘려 만든다.
  같은 손이 그린 것처럼 보이게 하려는 것이고, 실제로 이미 인게임에서 검증된 아트다.
  늘리는 방법은 "띠 반복"이 아니라 "안쪽 구간 resize" — 반복하면 같은 얼룩이 되풀이된다
  (2026-08-08 대화창 판에서 실제로 그 지적을 받았다).

★아이콘은 직접 그리지 않는다. src/status_icons/ 의 납품 아트(128px)를 여기서 내려 쓴다.
  (처음엔 원/별/마름모를 절차적으로 그렸는데 반려됐다 — 그 코드는 지웠다.)
  내릴 때 16px 로 간다: 14px 이하면 레벨 아이콘의 "LV" 글자가 뭉개져 못 읽는다(실측 비교).

★버프 판(우상단 정보바 아래, 먹은 요리 버프를 포션 효과처럼 표시)도 여기서 굽는다.
  판은 스탯 줄 수(1~3)만큼 높이가 다른 3장이고, 스탯 아이콘은 src/icons/stats/ 납품 아트를
  높이 16px 로 내려서 sequence 프레임으로 쓴다.

산출: ops/prod/betterhud/assets/status/ 에 png (상태·장소 5장 + 버프 13장)
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
# 아이콘이 16px 이라 줄 간격을 18px 로 벌려야 겹치지 않는다.
# 3줄 x 18 = 54 + 나무테 15 -> 72. 폭도 124 로 넓혔다(글자 "999,999,999원" 이 78px 라
# 110 짜리 판에서는 4px 넘쳤다). ★160 이 글리프 아틀라스 상한.
PLATE_W, PLATE_H = 124, 72

# 왼쪽 위 판(위치·환경)은 2줄이지만 더 넓어야 한다.
# "바르칸 > 폭포_뒤_동굴_2층" 같은 지역명이 나오는데 110px 로는 어림도 없다.
# ★단 160 을 넘기면 글리프 아틀라스에 못 들어가 통째로 사라진다 — 150 이 상한선이다.
# 150 은 상한이지 적정치가 아니었다. 가운데 정렬로 바꾸고 나니 좌우 여백이 22px 씩 남아
# 붕 떠 보여서 124 로 좁혔다(오른쪽 상태판과 폭이 같아지는 덤도 있다).
# ★하한은 "가장 작게(x0.5)" 단계가 정한다 — 작은 글자는 글리프 반올림 때문에 폭이
#   비례해서 줄지 않는다(x1.0 에서 78px 인 최장 지역명이 x0.5 에서 39 가 아니라 47).
#   124 x 0.5 = 62 에 47 이 들어가 좌우 7px 씩 남는다. 더 좁히면 글자가 테두리에 닿는다.
PLACE_W, PLACE_H = 124, 42
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
    im = _stretch_v(Image.open(SRC).convert("RGBA"), PLATE_H)
    return _stretch_h(im, PLATE_W)


def build_place_plate():
    """왼쪽 위 판 — 가로도 같이 늘린다. 세로 먼저 늘리고 가로를 늘려야
    모서리 장식(볼트)이 안 눌린다(반대로 하면 볼트가 타원이 된다)."""
    im = _stretch_v(Image.open(SRC).convert("RGBA"), PLACE_H)
    return _stretch_h(im, PLACE_W)


ICON_SRC = os.path.join(HERE, "src", "status_icons")
ICON_BOX = 16           # 긴 변 기준. 14 이하면 "LV" 가 안 읽힌다.


def import_icon(fname):
    """납품 128px 아트를 16px 픽셀아트로 내린다.

    ★그냥 resize 하면 안티에일리어싱이 남아 뭉갠 젤리가 된다. 면적평균(BOX)으로 내린 뒤
      **알파를 이진화하고 색 수를 줄여서** 각을 세운다. 색 수 제한이 곧 픽셀아트 느낌이다.
    ★가로세로 비를 유지한다 — 지폐(캐시)는 가로로 길어서 정사각으로 맞추면 찌그러진다.
    ★투명 여백은 잘라서 내보낸다. BetterHud 가 어차피 잘라내고 x 는 되돌려주지만
      y 는 안 되돌려주므로, 여백을 남기면 그 줄만 위로 떠 버린다.
    """
    im = Image.open(os.path.join(ICON_SRC, fname)).convert("RGBA")
    im = im.crop(im.split()[3].getbbox())
    k = ICON_BOX / max(im.width, im.height)
    w, h = max(1, round(im.width * k)), max(1, round(im.height * k))
    small = im.resize((w, h), Image.BOX)
    quant = small.convert("RGB").quantize(colors=10, method=Image.MEDIANCUT).convert("RGB")
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    sp, qp, op = small.load(), quant.load(), out.load()
    for y in range(h):
        for x in range(w):
            op[x, y] = (*qp[x, y], 255) if sp[x, y][3] >= 128 else (0, 0, 0, 0)
    return out


# 경험치 바 — 텍스트 "||||" 대신 진짜 게이지. BetterHud 가 type:listener 로 비율만큼 잘라 그린다.
# ★빈 바와 채움 바는 반드시 같은 크기여야 한다. 크기가 다르면 잘리는 기준이 어긋나 삐뚤어진다.
BAR_W, BAR_H = 32, 8   # ★가장 작은 단계에서 "Lv.100" 에 달라붙지 않는 최대 폭. 44 -> 40 -> 36 -> 32


def bar_empty(w=BAR_W, h=BAR_H):
    """빈 홈. 크림색 양피지 위에 파인 것처럼 보이게 위쪽을 더 어둡게(안쪽 그림자)."""
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, w - 1, h - 1], fill=(122, 104, 72, 255))     # 테두리
    d.rectangle([1, 1, w - 2, h - 2], fill=(168, 148, 110, 255))    # 바닥
    d.line([(1, 1), (w - 2, 1)], fill=(138, 118, 84, 255))          # 안쪽 그림자
    return im


# 채움 색 (바닥, 윗면 하이라이트, 아랫면 그늘).
FILL_TEAL = ((38, 128, 118), (86, 190, 172), (24, 92, 88))     # 경험치 — 레벨 줄과 같은 계열
FILL_AMBER = ((186, 132, 44), (232, 190, 108), (128, 86, 22))  # 버프 남은시간 — 음식·불 계열


def bar_fill(w=BAR_W, h=BAR_H, colors=FILL_TEAL):
    """채움. 경험치 줄이 청록 계열이라 같은 계열로 간다(아이콘·글자와 색이 따로 놀지 않게).

    ★빈 홈과 **똑같은 크기를 꽉 채워야 한다.** 가장자리를 투명하게 두면 BetterHud 가
      그만큼 잘라내는데, 가로 여백은 x 로 되돌려주지만 **세로 여백은 안 되돌려준다**.
      그래서 채움만 1px 위로 떠서 홈과 어긋난다(실제로 그렇게 만들었다가 발견).
      '안쪽에 들어찬' 느낌은 투명 대신 어두운 테두리 색으로 낸다.
    """
    base, top, bottom = colors
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, w - 1, h - 1], fill=(122, 104, 72, 255))     # 홈 테두리와 같은 색
    d.rectangle([1, 1, w - 2, h - 2], fill=(*base, 255))
    d.line([(1, 1), (w - 2, 1)], fill=(*top, 255))                  # 윗면 하이라이트
    d.line([(1, h - 2), (w - 2, h - 2)], fill=(*bottom, 255))       # 아랫면 그늘
    return im


# ═══════════════════ 버프 판 (우상단 정보바 아래) ═══════════════════
# 먹은 요리의 버프를 포션 효과처럼 상시 표시한다. 스탯 줄 수(1~3)만큼 판 높이가 달라진다 —
# 한 줄짜리 버프에 3줄 판을 붙이면 아래가 텅 빈다.
# ★높이 계산식은 ops/prod/betterhud/gen_hud_sizes.py 의 BUFF 와 같아야 한다.
#   (좌표 권위는 저쪽, 여기는 그 좌표에 맞는 판을 굽는 쪽)
BUFF_W = 124                   # 정보바·장소바와 같은 폭 — 오른쪽 위에 나란히 놓이므로 통일한다
BUFF_ROW0 = 45                 # 첫 스탯 줄 중심 (이름 15 · 시간바 29 다음)
BUFF_ROW_DY = 19               # 스탯 줄 간격. 아이콘 16px + 위아래 숨통 3px
BUFF_BOTTOM = 18               # 마지막 줄 아래 여백. 정보바 판(마지막 줄 52 / 높이 72 = 20)에 맞춘 값
BUFF_BAR_W, BUFF_BAR_H = 60, 8  # 시간 게이지. 오른쪽에 "9:32" 를 놓을 자리를 남긴 폭이다


def buff_plate_h(rows):
    return BUFF_ROW0 + BUFF_ROW_DY * (rows - 1) + BUFF_BOTTOM


def build_buff_plate(rows):
    im = _stretch_v(Image.open(SRC).convert("RGBA"), buff_plate_h(rows))
    return _stretch_h(im, BUFF_W)


# 스탯 아이콘 — 납품 아트를 그대로 내려 쓴다(직접 그리지 않는다).
# ★키 순서 = BetterHud sequence 프레임 순서 = 자바 BuffStats.STATS 순서. 세 곳이 어긋나면
#   경험치 버프에 판매가 아이콘이 뜬다. 순서를 바꾸려면 세 곳을 같이 바꿀 것.
BUFF_STAT_ICONS = [
    ("exp", "experience_bonus.png"),
    ("size", "size_bonus.png"),
    ("gradeup", "tier_up.png"),
    ("escape", "escape_reduction.png"),
    ("crit", "critical_chance.png"),
    ("double", "double_catch.png"),
    ("sell", "sell_price_bonus.png"),
    ("difficulty", "difficulty_reduction.png"),
]
STAT_ICON_SRC = os.path.join(HERE, "src", "icons", "stats")
# ★납품 해상도(128)를 그대로 내보낸다. 16px 로 미리 줄이면 안 된다 —
#   GUI 에서 이 아이콘들이 선명한 이유가 HD 텍스처이기 때문이고(슬롯은 16 GUI px 인데
#   텍스처는 128px), BetterHud 도 같은 원리로 "표시 크기 x HD" 로 구워서 쓴다.
#   실제로 16px 로 내려 봤더니 물고기·번개·방패가 죄다 뭉개져 구분이 안 됐다.
STAT_ICON_H = 128


def import_stat_icon(fname):
    """스탯 아이콘을 '높이 128px 고정 · 가로 가운데' HD 원본으로 내보낸다.

    ★높이 기준이다(긴 변 기준이 아니다). sequence 는 한 자리에서 프레임을 갈아끼우는데,
      BetterHud 는 **세로 여백을 잘라내고 되돌려주지 않으므로** 프레임 높이가 다르면
      아이콘이 버프에 따라 위아래로 튄다. 높이를 고정하면 그 문제가 사라진다.
    ★가로는 반대다 — 잘라낸 왼쪽 여백을 x 에 되돌려 더해준다(HudImageParser). 그래서
      정사각 캔버스에 가운데로 놓으면 폭이 다른 아이콘들(경험치 75 / 더블 145)이
      같은 세로축에 정렬된다. 안 그러면 좁은 아이콘만 왼쪽으로 쏠려 축이 흔들린다.
    ★표시 크기(16px)로 줄이는 건 gen_hud_sizes.py 가 단계별로 한다.
    """
    im = Image.open(os.path.join(STAT_ICON_SRC, fname)).convert("RGBA")
    im = im.crop(im.split()[3].getbbox())
    k = STAT_ICON_H / im.height
    im = im.resize((max(1, round(im.width * k)), STAT_ICON_H), Image.LANCZOS)
    box_w = max(STAT_ICON_H, im.width)      # 정사각(=표시 16x16)이 기본, 넘치면 그 폭 그대로
    out = Image.new("RGBA", (box_w, STAT_ICON_H), (0, 0, 0, 0))
    out.alpha_composite(im, ((box_w - im.width) // 2, 0))
    return out


def main():
    os.makedirs(OUT, exist_ok=True)
    made = [("status-plate.png", build_plate()),
            ("place-plate.png", build_place_plate()),
            ("icon-coin.png", import_icon("money.png")),
            ("icon-star.png", import_icon("level.png")),
            ("icon-gem.png", import_icon("cash.png")),
            ("exp-bar-empty.png", bar_empty()),
            ("exp-bar-fill.png", bar_fill()),
            ("buff-bar-empty.png", bar_empty(BUFF_BAR_W, BUFF_BAR_H)),
            ("buff-bar-fill.png", bar_fill(BUFF_BAR_W, BUFF_BAR_H, FILL_AMBER))]
    made += [(f"buff-plate-{n}.png", build_buff_plate(n)) for n in (1, 2, 3)]
    made += [(f"icon-stat-{key}.png", import_stat_icon(f)) for key, f in BUFF_STAT_ICONS]
    for name, im in made:
        hd = name.startswith("icon-stat-")     # HD 원본 — 표시 크기는 gen_hud_sizes.py 가 정한다
        # ★파일명은 소문자만. 대문자가 하나만 섞여도 폰트 파일 전체가 거부되고 HUD가 통째로 사라진다.
        assert name == name.lower(), name
        assert im.height > 1, "height 1 글리프는 폰트 전체를 무효화한다"
        assert hd or im.width <= 160, f"{name} 폭 {im.width} — 160 넘으면 아틀라스에서 조용히 사라진다"
        im.save(os.path.join(OUT, name))
        print(f"  {name}  {im.width}x{im.height}")
    print(f"-> {OUT}")


if __name__ == "__main__":
    main()
