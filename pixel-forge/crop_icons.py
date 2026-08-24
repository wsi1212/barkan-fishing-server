#!/usr/bin/env python3
"""특수작물 씨앗/수확물 아이콘 생성기.

논리 32×32 픽셀로 그린 뒤 2배 nearest 업스케일해 64×64 원본으로 저장한다.
인게임 슬롯에서 16px로 축소되더라도 실루엣과 하이라이트가 남도록 외곽선은
선택적으로만 쓰고, 씨앗과 수확물을 같은 팔레트 문법으로 묶는다.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path("/Users/user/development/barkan-resourcepack")
TEX = ROOT / "assets/minecraft/textures/item/barkan_icon"
MODELS = ROOT / "assets/barkan/models/barkan_icon"
ITEMS = ROOT / "assets/barkan/items/barkan_icon"
S = 2
W = 32


PALETTE = {
    "wheat": {"seed": (172, 125, 48), "seed_hi": (229, 193, 84), "main": (218, 170, 52), "hi": (255, 220, 100), "dark": (109, 72, 30), "leaf": (104, 128, 42)},
    "carrot": {"seed": (166, 105, 38), "seed_hi": (226, 161, 60), "main": (225, 103, 32), "hi": (255, 157, 52), "dark": (117, 55, 28), "leaf": (57, 128, 54)},
    "potato": {"seed": (153, 114, 62), "seed_hi": (208, 166, 96), "main": (179, 132, 73), "hi": (226, 184, 110), "dark": (92, 64, 42), "leaf": (75, 119, 53)},
    "tomato": {"seed": (142, 87, 53), "seed_hi": (211, 142, 75), "main": (203, 48, 45), "hi": (243, 94, 66), "dark": (104, 35, 39), "leaf": (46, 116, 54)},
    "cabbage": {"seed": (91, 115, 58), "seed_hi": (161, 178, 83), "main": (105, 164, 91), "hi": (169, 208, 121), "dark": (47, 90, 59), "leaf": (68, 130, 72)},
    "mushroom": {"seed": (104, 76, 48), "seed_hi": (174, 126, 72), "main": (151, 92, 54), "hi": (206, 139, 84), "dark": (67, 46, 38), "leaf": (109, 138, 70)},
    "melon": {"seed": (90, 115, 48), "seed_hi": (159, 171, 72), "main": (217, 67, 56), "hi": (255, 123, 76), "dark": (73, 107, 48), "leaf": (61, 132, 64)},
}


def canvas() -> tuple[Image.Image, ImageDraw.ImageDraw]:
    im = Image.new("RGBA", (W, W), (0, 0, 0, 0))
    return im, ImageDraw.Draw(im)


def rect(d, box, fill):
    d.rectangle(tuple(int(v) for v in box), fill=fill)


def poly(d, points, fill):
    d.polygon([(int(x), int(y)) for x, y in points], fill=fill)


def line(d, points, fill, width=1):
    d.line([(int(x), int(y)) for x, y in points], fill=fill, width=width)


def seed_icon(eng: str) -> Image.Image:
    p = PALETTE[eng]
    im, d = canvas()
    # 작은 흙 그림자: 씨앗이 떠 보이지 않게 하고, 작물별 포인트 색으로 구분
    poly(d, [(6, 23), (8, 19), (13, 18), (18, 20), (25, 19), (28, 23), (25, 26), (10, 26)], (50, 43, 37, 255))
    rect(d, (9, 23, 24, 25), (82, 57, 38, 255))
    # 세 알의 씨앗. 각도와 크기를 조금씩 달리해 '작물 머리'와 구분되는 아이콘으로 만든다.
    seeds = [
        ([(8, 18), (10, 13), (14, 11), (16, 15), (14, 19), (10, 20)], 0),
        ([(15, 21), (16, 16), (20, 13), (23, 16), (22, 21), (18, 23)], 1),
        ([(20, 13), (22, 9), (26, 8), (27, 12), (25, 15), (22, 15)], 2),
    ]
    for pts, idx in seeds:
        poly(d, pts, (36, 32, 29, 255))
        inner = [(x + (1 if x < 20 else 0), y + 1) for x, y in pts[1:-1]]
        poly(d, inner, p["seed"])
        rect(d, (pts[1][0] + 1, pts[1][1] + 1, pts[1][0] + 2, pts[1][1] + 2), p["seed_hi"])
    # 작은 싹 포인트 — 토마토/멜론은 잎색, 나머지는 작물의 잎색을 사용
    line(d, [(14, 11), (13, 7), (11, 5)], p["leaf"], 2)
    line(d, [(13, 7), (16, 5)], p["leaf"], 2)
    rect(d, (12, 5, 13, 6), p["leaf"])
    # 상단 림라이트와 바닥 픽셀로 작은 슬롯에서도 형태가 유지되게 한다.
    rect(d, (7, 22, 9, 23), (113, 94, 61, 255))
    rect(d, (24, 24, 26, 25), (35, 31, 29, 255))
    return im.resize((W * S, W * S), Image.Resampling.NEAREST)


def wheat(d, p):
    # 묶음 줄기와 3개의 이삭
    for x, lean in [(10, -2), (15, 0), (20, 2)]:
        line(d, [(16, 24), (x, 8 + lean)], p["dark"], 2)
        line(d, [(16, 23), (x + 1, 9 + lean)], p["main"], 1)
        poly(d, [(x, 7 + lean), (x - 2, 10 + lean), (x, 12 + lean), (x + 2, 10 + lean)], p["hi"])
        for yy in (10 + lean, 13 + lean, 16 + lean):
            poly(d, [(x, yy), (x - 3, yy + 2), (x - 1, yy + 3), (x + 1, yy + 1)], p["main"])
            poly(d, [(x, yy), (x + 3, yy + 2), (x + 1, yy + 3), (x - 1, yy + 1)], p["hi"])
    rect(d, (12, 21, 20, 24), p["dark"])
    rect(d, (13, 21, 19, 22), p["hi"])
    rect(d, (14, 23, 18, 24), p["main"])


def carrot(d, p):
    poly(d, [(11, 8), (15, 10), (20, 17), (18, 25), (14, 27), (9, 23), (8, 16)], p["dark"])
    poly(d, [(12, 10), (16, 11), (19, 17), (17, 24), (14, 25), (10, 22), (10, 16)], p["main"])
    poly(d, [(13, 11), (16, 12), (17, 16), (14, 17), (11, 15)], p["hi"])
    line(d, [(14, 12), (12, 20)], (244, 128, 37, 255), 1)
    line(d, [(16, 12), (17, 20)], (159, 65, 31, 255), 1)
    line(d, [(13, 11), (11, 6)], p["dark"], 2)
    line(d, [(15, 11), (15, 5)], p["leaf"], 2)
    line(d, [(17, 12), (20, 7)], p["dark"], 2)
    rect(d, (10, 5, 12, 7), p["leaf"])
    rect(d, (14, 4, 16, 6), (72, 152, 61, 255))
    rect(d, (19, 6, 21, 8), p["leaf"])


def potato(d, p):
    shapes = [
        ([(7, 14), (10, 9), (17, 8), (23, 11), (26, 17), (23, 23), (16, 26), (9, 23), (6, 19)], p["dark"]),
        ([(9, 14), (11, 11), (16, 10), (21, 12), (24, 17), (21, 21), (16, 24), (10, 21), (8, 18)], p["main"]),
        ([(14, 13), (17, 11), (21, 13), (21, 17), (18, 19), (14, 17)], p["hi"]),
    ]
    for pts, col in shapes: poly(d, pts, col)
    for x, y in [(11, 16), (17, 21), (20, 15), (14, 12)]:
        rect(d, (x, y, x + 1, y + 1), p["dark"])
    rect(d, (8, 18, 9, 20), (214, 166, 94, 255))
    line(d, [(13, 10), (12, 6)], p["leaf"], 2)
    line(d, [(16, 10), (18, 5)], p["leaf"], 2)
    rect(d, (10, 5, 13, 7), (97, 143, 56, 255))
    rect(d, (17, 4, 19, 6), p["leaf"])


def tomato(d, p):
    poly(d, [(10, 11), (14, 8), (21, 9), (25, 14), (24, 21), (19, 25), (12, 24), (8, 19)], p["dark"])
    poly(d, [(11, 12), (15, 10), (20, 11), (23, 15), (22, 20), (18, 23), (13, 22), (10, 18)], p["main"])
    poly(d, [(12, 13), (15, 11), (18, 12), (16, 17), (12, 17)], p["hi"])
    rect(d, (18, 19, 20, 21), (166, 36, 43, 255))
    poly(d, [(16, 11), (14, 7), (11, 8), (13, 11), (16, 10), (18, 7), (21, 9), (20, 12)], p["leaf"])
    rect(d, (15, 5, 17, 8), p["dark"])


def cabbage(d, p):
    poly(d, [(7, 15), (10, 10), (15, 8), (21, 10), (25, 15), (24, 22), (19, 26), (11, 25), (7, 21)], p["dark"])
    poly(d, [(9, 15), (12, 11), (16, 10), (20, 12), (23, 16), (22, 21), (18, 24), (12, 23), (9, 20)], p["main"])
    poly(d, [(12, 14), (16, 11), (20, 14), (21, 18), (18, 22), (13, 21), (11, 18)], p["hi"])
    line(d, [(16, 12), (16, 21)], p["leaf"], 1)
    line(d, [(11, 16), (19, 15)], p["leaf"], 1)
    line(d, [(12, 21), (20, 18)], (74, 137, 75, 255), 1)
    rect(d, (8, 19, 10, 21), (75, 133, 73, 255))


def mushroom(d, p):
    # 갓과 줄기를 분리해 16px에서도 버섯으로 읽히게 한다.
    poly(d, [(6, 14), (8, 9), (13, 6), (20, 6), (25, 10), (27, 15), (24, 18), (8, 18)], p["dark"])
    poly(d, [(8, 13), (10, 10), (14, 8), (19, 8), (23, 11), (25, 15), (22, 16), (10, 16)], p["main"])
    poly(d, [(11, 11), (14, 9), (18, 9), (16, 13), (11, 14)], p["hi"])
    rect(d, (13, 16, 21, 25), p["dark"])
    poly(d, [(15, 16), (20, 16), (21, 24), (18, 26), (14, 23)], (224, 202, 158, 255))
    rect(d, (15, 17, 18, 19), (248, 230, 180, 255))
    for x, y in [(12, 12), (18, 10), (22, 14)]: rect(d, (x, y, x + 1, y + 1), (236, 185, 112, 255))


def melon(d, p):
    # 수확물은 실제 산출물인 멜론 조각 형태로 고정한다.
    poly(d, [(7, 8), (25, 8), (25, 23), (22, 26), (10, 26), (7, 22)], p["dark"])
    poly(d, [(9, 10), (23, 10), (23, 21), (20, 24), (11, 24), (9, 21)], p["main"])
    line(d, [(12, 11), (12, 22)], p["hi"], 1)
    line(d, [(16, 10), (16, 23)], (255, 143, 88, 255), 1)
    line(d, [(20, 10), (20, 22)], (177, 42, 47, 255), 1)
    rect(d, (9, 22, 23, 25), (84, 153, 56, 255))
    rect(d, (11, 22, 21, 23), (153, 190, 70, 255))
    for x, y in [(13, 15), (18, 13), (19, 18), (15, 20)]:
        rect(d, (x, y, x + 1, y + 2), (71, 53, 42, 255))


HARVESTERS = {"wheat": wheat, "carrot": carrot, "potato": potato, "tomato": tomato,
              "cabbage": cabbage, "mushroom": mushroom, "melon": melon}


def harvest_icon(eng: str) -> Image.Image:
    im, d = canvas()
    HARVESTERS[eng](d, PALETTE[eng])
    return im.resize((W * S, W * S), Image.Resampling.NEAREST)


def write_icon(eng: str, kind: str, im: Image.Image) -> None:
    TEX.mkdir(parents=True, exist_ok=True)
    MODELS.mkdir(parents=True, exist_ok=True)
    ITEMS.mkdir(parents=True, exist_ok=True)
    name = f"crop_{eng}_{kind}"
    im.save(TEX / f"{name}.png")
    model = {"parent": "minecraft:item/generated", "textures": {"layer0": f"minecraft:item/barkan_icon/{name}"}}
    (MODELS / f"{name}.json").write_text(json.dumps(model, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    item = {"model": {"type": "minecraft:model", "model": f"barkan:barkan_icon/{name}"}}
    (ITEMS / f"{name}.json").write_text(json.dumps(item, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


def main() -> None:
    for eng in HARVESTERS:
        write_icon(eng, "seed", seed_icon(eng))
        write_icon(eng, "harvest", harvest_icon(eng))
    print(f"OK — {len(HARVESTERS)}작물 × 씨앗/수확물 = {len(HARVESTERS) * 2} icons (64×64)")


if __name__ == "__main__":
    main()
