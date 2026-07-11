#!/usr/bin/env python3
"""카지노 대형 소품 생성기 — 슬롯머신 캐비닛 + 룰렛 휠/마커.

- 슬롯 캐비닛: elements 모델(본체+마퀴+레버) + 128px 텍스처. 월드 배치용
  ItemDisplay 모델(barkan:casino/slot_cabinet). 클릭 → 기존 GUI 슬롯 게임.
- 룰렛 휠: 유럽식 37섹터 순서/색 + 숫자 텍스처(256px) 원반 모델
  (barkan:casino/roulette_wheel). 회전은 서버가 transformation으로.
- 마커: 휠 위 당첨 지점 골드 화살촉(barkan:casino/roulette_marker).
"""

import json
import math
import os
from PIL import Image, ImageDraw, ImageFont

RP = os.path.expanduser("~/development/barkan-resourcepack")
STAGING = os.environ.get("PROP_STAGING", os.path.expanduser("~/Desktop/casino-cards-preview"))

FONT_BOLD = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"

# 유럽식 휠 순서 (RouletteRules와 동일 색 규칙: 0=초록, RED_SET 빨강, 나머지 검정)
WHEEL_ORDER = [0, 32, 15, 19, 4, 21, 2, 25, 17, 34, 6, 27, 13, 36, 11, 30,
               8, 23, 10, 5, 24, 16, 33, 1, 20, 14, 31, 9, 22, 18, 29, 7,
               28, 12, 35, 3, 26]
RED_SET = {1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36}

RED = (188, 44, 42, 255)
BLACK = (30, 30, 34, 255)
GREEN = (24, 128, 70, 255)
GOLD = (226, 172, 58, 255)
GOLD_DK = (156, 110, 28, 255)
CAB_RED = (146, 30, 34, 255)
CAB_DARK = (96, 20, 24, 255)
NAVY = (28, 30, 52, 255)
WHITE = (248, 246, 240, 255)


def save(img, rel):
    # ★텍스처는 minecraft:item/ 아래여야 아이템 아틀라스에 잡힘(모델/아이템 id는 barkan 유지).
    for base in (os.path.join(RP, "assets/minecraft/textures/item"), os.path.join(STAGING, "tex")):
        path = os.path.join(base, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        img.save(path)


def write_model(rel, obj):
    path = os.path.join(RP, f"assets/barkan/models/{rel}.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(obj, f, separators=(",", ":"))
    item = os.path.join(RP, f"assets/barkan/items/{rel}.json")
    os.makedirs(os.path.dirname(item), exist_ok=True)
    with open(item, "w") as f:
        json.dump({"model": {"type": "minecraft:model", "model": f"barkan:{rel}"}}, f, separators=(",", ":"))


# ===== 룰렛 휠 =====

def gen_wheel():
    S = 256
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    cx = cy = S / 2
    r_outer = 126
    r_ring = 118      # 섹터 바깥
    r_inner = 58      # 섹터 안쪽
    d.ellipse([cx - r_outer, cy - r_outer, cx + r_outer, cy + r_outer], fill=GOLD_DK)
    d.ellipse([cx - r_outer + 4, cy - r_outer + 4, cx + r_outer - 4, cy + r_outer - 4], fill=GOLD)
    step = 360.0 / len(WHEEL_ORDER)
    # 섹터: 0번 섹터 중심이 12시(-90°)에 오게
    for i, num in enumerate(WHEEL_ORDER):
        a0 = -90 - step / 2 + i * step
        color = GREEN if num == 0 else RED if num in RED_SET else BLACK
        d.pieslice([cx - r_ring, cy - r_ring, cx + r_ring, cy + r_ring], a0, a0 + step, fill=color)
    d.ellipse([cx - r_inner, cy - r_inner, cx + r_inner, cy + r_inner], fill=NAVY)
    d.ellipse([cx - r_inner + 4, cy - r_inner + 4, cx + r_inner - 4, cy + r_inner - 4], fill=(40, 44, 72, 255))
    # 중앙 골드 허브 + 얇은 십자(바늘) — 굵던 6px→2px, 짧게(반경 20). 유저 "바늘 너무 굵음"
    d.ellipse([cx - 9, cy - 9, cx + 9, cy + 9], fill=GOLD)
    for ang in (0, 90):
        rad = math.radians(ang)
        dx, dy = math.cos(rad) * 20, math.sin(rad) * 20
        d.line([(cx - dx, cy - dy), (cx + dx, cy + dy)], fill=GOLD, width=2)
    d.ellipse([cx - 4, cy - 4, cx + 4, cy + 4], fill=GOLD_DK)  # 중심 핀
    # 숫자 (섹터 중앙 반경, 방사 방향 회전) — 크게(28)+검정 외곽선으로 대비(흰+흰=뭉개짐 수정)
    font = ImageFont.truetype(FONT_BOLD, 28)
    for i, num in enumerate(WHEEL_ORDER):
        ang = -90 + i * step
        rad = math.radians(ang)
        tx = cx + math.cos(rad) * 90
        ty = cy + math.sin(rad) * 90
        tile = Image.new("RGBA", (44, 34), (0, 0, 0, 0))
        td = ImageDraw.Draw(tile)
        td.text((22, 17), str(num), font=font, fill=WHITE, anchor="mm",
                stroke_width=3, stroke_fill=(16, 16, 20, 255))
        rotated = tile.rotate(-(ang + 90), expand=True, resample=Image.BICUBIC)
        img.alpha_composite(rotated, (int(tx - rotated.width / 2), int(ty - rotated.height / 2)))
    save(img, "casino/roulette_wheel.png")

    write_model("casino/roulette_wheel", {
        "textures": {"0": "minecraft:item/casino/roulette_wheel", "particle": "#0"},
        "elements": [{
            "from": [0, 0, 0], "to": [16, 1, 16],
            "faces": {
                "up": {"uv": [0, 0, 16, 16], "texture": "#0"},
                "down": {"uv": [16, 0, 0, 16], "texture": "#0"},
                # ★측면은 투명 모서리 픽셀(원 밖=알파0)을 샘플 → 짤린 텍스처 띠 제거(안 보임).
                "north": {"uv": [0, 0, 1, 1], "texture": "#0"},
                "south": {"uv": [0, 0, 1, 1], "texture": "#0"},
                "west": {"uv": [0, 0, 1, 1], "texture": "#0"},
                "east": {"uv": [0, 0, 1, 1], "texture": "#0"},
            },
        }],
    })

    # 마커(골드 화살촉) — 단색 텍스처 재사용
    marker = Image.new("RGBA", (16, 16), GOLD)
    save(marker, "casino/gold.png")
    write_model("casino/roulette_marker", {
        "textures": {"0": "minecraft:item/casino/gold", "particle": "#0"},
        "elements": [
            {"from": [7, 0, 4], "to": [9, 1.5, 10],
             "faces": {f: {"uv": [0, 0, 4, 4], "texture": "#0"} for f in
                       ("up", "down", "north", "south", "west", "east")}},
            {"from": [6.2, 0, 8.5], "to": [9.8, 1.5, 12],
             "faces": {f: {"uv": [0, 0, 4, 4], "texture": "#0"} for f in
                       ("up", "down", "north", "south", "west", "east")}},
        ],
    })


# ===== 슬롯 캐비닛 =====

def _seven(d, cx, cy, s, color):
    d.line([(cx - s * 0.4, cy - s * 0.45), (cx + s * 0.42, cy - s * 0.45)], fill=color, width=3)
    d.line([(cx + s * 0.42, cy - s * 0.45), (cx - s * 0.1, cy + s * 0.5)], fill=color, width=3)


def _cherry(d, cx, cy, s):
    d.ellipse([cx - s * 0.45, cy, cx - s * 0.05, cy + s * 0.4], fill=(214, 40, 40, 255))
    d.ellipse([cx + 1, cy + s * 0.05, cx + s * 0.42, cy + s * 0.46], fill=(214, 40, 40, 255))
    d.line([(cx - s * 0.24, cy + s * 0.05), (cx, cy - s * 0.45)], fill=(50, 120, 50, 255), width=2)
    d.line([(cx + s * 0.2, cy + s * 0.1), (cx, cy - s * 0.45)], fill=(50, 120, 50, 255), width=2)


def _bell(d, cx, cy, s):
    d.pieslice([cx - s * 0.4, cy - s * 0.45, cx + s * 0.4, cy + s * 0.35], 180, 360, fill=GOLD)
    d.rectangle([cx - s * 0.4, cy - s * 0.05, cx + s * 0.4, cy + s * 0.18], fill=GOLD)
    d.ellipse([cx - s * 0.08, cy + s * 0.18, cx + s * 0.08, cy + s * 0.34], fill=GOLD_DK)


def gen_slot_cabinet():
    S = 128
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # ── 전면 (0,0)-(48,96): 12×24px 면 → 4배 해상도 ──
    d.rectangle([0, 0, 48, 96], fill=CAB_RED)
    d.rectangle([0, 0, 47, 95], outline=GOLD, width=2)
    # 마퀴
    d.rectangle([4, 4, 44, 18], fill=NAVY, outline=GOLD, width=2)
    f = ImageFont.truetype(FONT_BOLD, 11)
    d.text((24, 11), "777", font=f, fill=GOLD, anchor="mm", stroke_width=1, stroke_fill=GOLD)
    # 스크린 + 릴 3창
    d.rectangle([4, 22, 44, 52], fill=(16, 16, 20, 255), outline=GOLD_DK, width=2)
    for i, sym in enumerate(("seven", "cherry", "bell")):
        x0 = 7 + i * 13
        d.rectangle([x0, 26, x0 + 11, 48], fill=WHITE, outline=(120, 120, 128, 255))
        cx, cy = x0 + 5.5, 37
        if sym == "seven":
            _seven(d, cx, cy, 9, (200, 30, 30, 255))
        elif sym == "cherry":
            _cherry(d, cx, cy, 10)
        else:
            _bell(d, cx, cy, 10)
    # 코인 슬롯/버튼
    d.rectangle([8, 58, 40, 64], fill=NAVY, outline=GOLD_DK)
    d.ellipse([10, 70, 20, 80], fill=(52, 160, 84, 255), outline=(20, 90, 44, 255), width=2)
    d.ellipse([28, 70, 38, 80], fill=(214, 60, 52, 255), outline=(120, 26, 24, 255), width=2)
    d.rectangle([16, 84, 32, 90], fill=GOLD, outline=GOLD_DK)  # 코인 트레이

    # ── 측면 (48,0)-(80,96): 8×24px ──
    d.rectangle([48, 0, 80, 96], fill=CAB_DARK)
    d.rectangle([48, 0, 79, 95], outline=GOLD_DK, width=2)
    d.rectangle([54, 20, 74, 76], fill=CAB_RED, outline=GOLD_DK)

    # ── 상/하면 (80,0)-(128,32)/(80,32)-(128,64), 후면 (80,64)-(128,128) ──
    d.rectangle([80, 0, 128, 32], fill=CAB_RED)
    d.rectangle([80, 0, 127, 31], outline=GOLD, width=2)
    d.rectangle([80, 32, 128, 64], fill=CAB_DARK)
    d.rectangle([80, 64, 128, 128], fill=CAB_DARK)
    d.rectangle([80, 64, 127, 127], outline=GOLD_DK, width=2)

    # 레버용 단색
    d.rectangle([0, 100, 16, 116], fill=(150, 152, 160, 255))  # 스틱 회색
    d.rectangle([16, 100, 32, 116], fill=(214, 60, 52, 255))   # 볼 빨강

    save(img, "casino/slot_cabinet.png")

    def face(u0, v0, u1, v1):
        return {"uv": [u0, v0, u1, v1], "texture": "#0"}

    # 텍스처 좌표계: 128px → uv 0~16 (8px = 1uv)
    FRONT = face(0, 0, 6, 12)
    SIDE = face(6, 0, 10, 12)
    TOP = face(10, 0, 16, 4)
    BOTTOM = face(10, 4, 16, 8)
    BACK = face(10, 8, 16, 16)
    STICK = face(0, 12.5, 2, 14.5)
    BALL = face(2, 12.5, 4, 14.5)

    write_model("casino/slot_cabinet", {
        "textures": {"0": "minecraft:item/casino/slot_cabinet", "particle": "#0"},
        "elements": [
            # 본체 12×24×8 (x2..14, y0..24, z4..12) — 남쪽(+z, south)이 정면
            {"from": [2, 0, 4], "to": [14, 24, 12],
             "faces": {"north": BACK, "south": FRONT, "west": SIDE, "east": SIDE,
                       "up": TOP, "down": BOTTOM}},
            # 마퀴 챙
            {"from": [1.4, 21.5, 3.2], "to": [14.6, 24.4, 12.4],
             "faces": {"north": BACK, "south": face(0, 0, 6, 1.6), "west": SIDE, "east": SIDE,
                       "up": TOP, "down": BOTTOM}},
            # 레버 스틱 (오른쪽 측면)
            {"from": [14, 12, 7.2], "to": [15.4, 13.4, 8.8],
             "faces": {f: STICK for f in ("north", "south", "west", "east", "up", "down")}},
            {"from": [14.6, 13.4, 7.4], "to": [15.8, 19, 8.6],
             "faces": {f: STICK for f in ("north", "south", "west", "east", "up", "down")}},
            # 레버 볼
            {"from": [14.1, 19, 6.9], "to": [16.3, 21.2, 9.1],
             "faces": {f: BALL for f in ("north", "south", "west", "east", "up", "down")}},
        ],
    })


if __name__ == "__main__":
    gen_wheel()
    gen_slot_cabinet()
    print("완료: barkan:casino/{roulette_wheel, roulette_marker, slot_cabinet} → RP + 스테이징")
