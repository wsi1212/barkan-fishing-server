#!/usr/bin/env python3
"""룰렛 구슬(아이보리 볼) 리소스팩 자산 생성 — 텍스처 + 3D 모델 + 아이템 정의.

★교차평면(X자) 금지 규약을 지켜 **부피 모델**로 만든다: 3개 박스를 축마다 겹쳐
   3D '플러스' 형태 → 작은 크기에서 모서리 깎인 구슬로 보인다(면 6개짜리 큐브보다 둥글다).

텍스처는 한 장으로 면별 음영을 준다:
  · 좌상 8×8 = 위면(하이라이트)  · 우상 8×8 = 측면(수직 램프)  · 좌하 8×8 = 아래면(그림자)
모델의 각 면이 해당 영역만 UV로 물어서, 위는 밝고 아래는 어두운 실제 구슬 음영이 난다.

산출 경로 (RP 소스 = ~/development/barkan-resourcepack):
  assets/minecraft/textures/item/casino/roulette_ball.png
  assets/barkan/models/casino/roulette_ball.json
  assets/barkan/items/casino/roulette_ball.json     (item_model = barkan:casino/roulette_ball)
"""

import json
from pathlib import Path

from PIL import Image

RP = Path.home() / "development" / "barkan-resourcepack"

# 아이보리(상아) 램프 — 채도 낮게, 5단계
HI = (255, 253, 247, 255)
LIGHT = (243, 236, 222, 255)
MID = (226, 216, 197, 255)
SHADE = (199, 186, 164, 255)
DEEP = (166, 152, 130, 255)


def draw_texture(path: Path):
    im = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    px = im.load()

    # ── 좌상 8×8: 위면. 좌상단에 광원 하이라이트가 오는 둥근 음영
    for y in range(8):
        for x in range(8):
            d = ((x - 2.6) ** 2 + (y - 2.6) ** 2) ** 0.5
            px[x, y] = HI if d < 1.6 else LIGHT if d < 3.4 else MID if d < 5.2 else SHADE

    # ── 우상 8×8: 측면. 위→아래 수직 램프(위가 밝고 아래로 갈수록 어둡게)
    for y in range(8):
        band = (LIGHT, LIGHT, MID, MID, MID, SHADE, SHADE, DEEP)[y]
        for x in range(8):
            # 좌우 끝은 한 단계 더 어둡게 → 원통형 실루엣 느낌
            edge = x in (0, 7)
            px[8 + x, y] = {LIGHT: MID, MID: SHADE, SHADE: DEEP, DEEP: DEEP}[band] if edge else band

    # ── 좌하 8×8: 아래면. 전체 그림자
    for y in range(8):
        for x in range(8):
            d = ((x - 4) ** 2 + (y - 4) ** 2) ** 0.5
            px[x, 8 + y] = SHADE if d < 2.2 else DEEP

    # ── 우하 8×8: 미사용(투명 유지)
    path.parent.mkdir(parents=True, exist_ok=True)
    im.save(path)
    return im.size


def faces(up_uv, side_uv, down_uv):
    return {
        "up": {"uv": up_uv, "texture": "#0"},
        "down": {"uv": down_uv, "texture": "#0"},
        "north": {"uv": side_uv, "texture": "#0"},
        "south": {"uv": side_uv, "texture": "#0"},
        "west": {"uv": side_uv, "texture": "#0"},
        "east": {"uv": side_uv, "texture": "#0"},
    }


def draw_model(path: Path):
    up = [0, 0, 8, 8]      # 좌상 = 밝은 위면
    side = [8, 0, 16, 8]   # 우상 = 측면 램프
    down = [0, 8, 8, 16]   # 좌하 = 어두운 아래면

    # 지름 5px 구슬: 축마다 긴 박스 3개를 겹친 3D 플러스(모서리 깎인 구)
    c = 8.0
    long_half, short_half = 2.5, 1.5
    elements = [
        {  # x축 방향으로 긴 박스
            "from": [c - long_half, c - short_half, c - short_half],
            "to": [c + long_half, c + short_half, c + short_half],
            "faces": faces(up, side, down),
        },
        {  # y축
            "from": [c - short_half, c - long_half, c - short_half],
            "to": [c + short_half, c + long_half, c + short_half],
            "faces": faces(up, side, down),
        },
        {  # z축
            "from": [c - short_half, c - short_half, c - long_half],
            "to": [c + short_half, c + short_half, c + long_half],
            "faces": faces(up, side, down),
        },
    ]
    model = {
        "textures": {"0": "minecraft:item/casino/roulette_ball", "particle": "#0"},
        "elements": elements,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(model, separators=(",", ":")), encoding="utf-8")


def draw_item_def(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(
        {"model": {"type": "minecraft:model", "model": "barkan:casino/roulette_ball"}},
        separators=(",", ":")), encoding="utf-8")


def main():
    tex = RP / "assets/minecraft/textures/item/casino/roulette_ball.png"
    model = RP / "assets/barkan/models/casino/roulette_ball.json"
    item = RP / "assets/barkan/items/casino/roulette_ball.json"
    size = draw_texture(tex)
    draw_model(model)
    draw_item_def(item)
    print(f"texture {tex} {size}")
    print(f"model   {model}")
    print(f"item    {item}")


if __name__ == "__main__":
    main()
