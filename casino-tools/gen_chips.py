#!/usr/bin/env python3
"""바르칸 카지노 칩 생성기 (casino-rework.md §2.5).

액면 4종(천/만/십만/백만). ★item/generated 평면 스프라이트 — 프레임을 꽉 채운 둥근
칩을 그리고 바깥은 투명. 알파 컷아웃이 원형을 만든다(예전 elements 사각 상자는 모서리
투명이 사각으로 보였음). ChipRenderer가 눕혀(rotX -90) 테이블 위 원반으로 표시.
텍스처는 minecraft:item/chip/ 아래(아이템 아틀라스 포함).
출력: assets/{minecraft/textures/item/chip, barkan/models/chip, barkan/items/chip}
"""

import json
import math
import os
from PIL import Image, ImageDraw, ImageFont

SS = 4
TEX = 64
C = TEX * SS
CX = C // 2

RP = os.path.expanduser("~/development/barkan-resourcepack")
STAGING = os.environ.get("CHIP_STAGING", os.path.expanduser("~/Desktop/casino-cards-preview"))

CHIPS = {  # id: (라벨, 본색, 진한 테두리색)
    "chip_1k":   ("천",   (198, 204, 214, 255), (120, 128, 142, 255)),
    "chip_10k":  ("만",   (226, 172, 58, 255),  (150, 108, 24, 255)),
    "chip_100k": ("십만", (63, 167, 94, 255),   (30, 104, 54, 255)),
    "chip_1m":   ("백만", (79, 169, 216, 255),  (34, 102, 144, 255)),
}
WHITE = (250, 250, 246, 255)
INK = (28, 32, 38, 255)

HANGUL_FONTS = [
    "/System/Library/Fonts/AppleSDGothicNeo.ttc",
    "/System/Library/Fonts/Supplemental/AppleGothic.ttf",
]


def hangul_font(size):
    for path in HANGUL_FONTS:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except OSError:
                continue
    raise SystemExit("한글 폰트 없음")


def chip_texture(label, color, dark):
    """프레임(64px)을 꽉 채운 둥근 포커칩. 바깥 = 투명."""
    img = Image.new("RGBA", (C, C), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    R = 30 * SS  # 바깥 반지름 (프레임 32 중 30 = 여백 최소)

    # 바깥 테두리 링
    d.ellipse([CX - R, CX - R, CX + R, CX + R], fill=dark)
    # 흰 에지 대시 8개 (포커칩 특유)
    for i in range(8):
        a0 = i * 45 + 8
        d.pieslice([CX - R, CX - R, CX + R, CX + R], a0, a0 + 26, fill=WHITE)
    # 본체
    body = R * 0.80
    d.ellipse([CX - body, CX - body, CX + body, CX + body], fill=color, outline=WHITE, width=2 * SS)
    # 중앙 흰 원 + 링
    core = R * 0.56
    d.ellipse([CX - core, CX - core, CX + core, CX + core], fill=WHITE, outline=dark, width=SS)
    core2 = R * 0.48
    d.ellipse([CX - core2, CX - core2, CX + core2, CX + core2], fill=color)
    inner = R * 0.40
    d.ellipse([CX - inner, CX - inner, CX + inner, CX + inner], fill=WHITE)
    # 액면 라벨
    size = int((20 if len(label) == 1 else 14) * SS)
    f = hangul_font(size)
    d.text((CX, CX + SS), label, font=f, fill=INK, anchor="mm")

    out = img.resize((TEX, TEX), Image.LANCZOS)
    # 알파 이진화 — 컷아웃 가장자리 프린지 방지(원형 유지)
    out.putalpha(out.getchannel("A").point(lambda v: 255 if v >= 128 else 0))
    return out


def main():
    for cid, (label, color, dark) in CHIPS.items():
        tex = chip_texture(label, color, dark)
        for base in (os.path.join(RP, "assets/minecraft/textures/item/chip"),
                     os.path.join(STAGING, "chip")):
            os.makedirs(base, exist_ok=True)
            tex.save(os.path.join(base, f"{cid}.png"))
        # 모델 = item/generated 평면 스프라이트 (알파가 원형을 만든다)
        model = {"parent": "minecraft:item/generated",
                 "textures": {"layer0": f"minecraft:item/chip/{cid}"}}
        mp = os.path.join(RP, f"assets/barkan/models/chip/{cid}.json")
        ip = os.path.join(RP, f"assets/barkan/items/chip/{cid}.json")
        os.makedirs(os.path.dirname(mp), exist_ok=True)
        os.makedirs(os.path.dirname(ip), exist_ok=True)
        with open(mp, "w") as f:
            json.dump(model, f, separators=(",", ":"))
        with open(ip, "w") as f:
            json.dump({"model": {"type": "minecraft:model", "model": f"barkan:chip/{cid}"}},
                      f, separators=(",", ":"))
    print(f"완료: 칩 {len(CHIPS)}종(item/generated 원형) → RP + {STAGING}/chip")


if __name__ == "__main__":
    main()
