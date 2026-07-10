#!/usr/bin/env python3
"""바르칸 카지노 칩 생성기 (casino-rework.md §2.5).

액면 4종(천/만/십만/백만 — GUI BETS 사다리 대응 색)을 elements 원반 모델로 생성.
모델 원판 = 8×1.5×8px(scale 1에서 지름 0.5블록) — 표시 크기는 ItemDisplay
transform으로 제어(권장 scale 0.5 → 지름 0.25블록, 스택 간격 0.047블록).

텍스처 64×64 레이아웃: 좌상 32×32 = 상/하면 디스크(uv 0,0,8,8),
y32~38px 밴드 = 측면 스트라이프(uv 0,8,8,9.5).
출력: assets/barkan/{textures,models,items}/chip/chip_{1k,10k,100k,1m}
"""

import json
import math
import os
from PIL import Image, ImageDraw, ImageFont

SS = 4
TEX = 64
C = TEX * SS

RP = os.path.expanduser("~/development/barkan-resourcepack")
STAGING = os.environ.get("CHIP_STAGING", os.path.expanduser("~/Desktop/casino-cards-preview"))

CHIPS = {  # id: (단위 라벨, 본색, 진한 테두리색)
    "chip_1k":   ("천",   (198, 204, 214, 255), (128, 136, 150, 255)),
    "chip_10k":  ("만",   (226, 172, 58, 255),  (158, 112, 28, 255)),
    "chip_100k": ("십만", (63, 167, 94, 255),   (34, 110, 58, 255)),
    "chip_1m":   ("백만", (79, 169, 216, 255),  (38, 106, 148, 255)),
}
WHITE = (250, 250, 246, 255)
INK = (32, 36, 42, 255)

HANGUL_FONTS = [
    "/System/Library/Fonts/AppleSDGothicNeo.ttc",
    "/System/Library/Fonts/Supplemental/AppleGothic.ttf",
    "/System/Library/Fonts/Supplemental/NanumGothic.ttc",
]


def hangul_font(size):
    for path in HANGUL_FONTS:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except OSError:
                continue
    raise SystemExit("한글 폰트를 찾지 못했습니다")


def chip_texture(label, color, dark):
    img = Image.new("RGBA", (C, C), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # ── 상면 디스크 (0,0)-(32,32) 영역, 중심 (16,16), 반지름 15.5px ──
    cx = cy = 16 * SS
    r = 15.5 * SS
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=color, outline=dark, width=SS)
    # 흰 대시 8개 (포커칩 에지 마크)
    for i in range(8):
        a0 = i * 45 + 10
        d.pieslice([cx - r, cy - r, cx + r, cy + r], a0, a0 + 25, fill=WHITE)
    # 중심 원 복원 + 흰 링
    inner = r * 0.72
    d.ellipse([cx - inner, cy - inner, cx + inner, cy + inner],
              fill=color, outline=WHITE, width=SS)
    core = r * 0.58
    d.ellipse([cx - core, cy - core, cx + core, cy + core], fill=WHITE)
    # 단위 라벨 (한글) — 2자는 축소
    size = int((15 if len(label) == 1 else 10.5) * SS)
    f = hangul_font(size)
    d.text((cx, cy + 0.5 * SS), label, font=f, fill=INK, anchor="mm",
           stroke_width=max(1, SS // 2), stroke_fill=INK)

    # ── 측면 밴드 y 32~38px: 본색 + 흰 세그먼트 ──
    y0, y1 = 32 * SS, 38 * SS
    d.rectangle([0, y0, 32 * SS, y1], fill=dark)
    seg = 4 * SS
    for x in range(0, 32 * SS, seg * 2):
        d.rectangle([x, y0, x + seg, y1], fill=WHITE)

    out = img.resize((TEX, TEX), Image.LANCZOS)
    out.putalpha(out.getchannel("A").point(lambda v: 255 if v >= 128 else 0))
    return out


MODEL = {
    "textures": {"0": None, "particle": "#0"},
    "elements": [{
        "from": [4, 0, 4], "to": [12, 1.5, 12],
        "faces": {
            "up":    {"uv": [0, 0, 8, 8], "texture": "#0"},
            "down":  {"uv": [0, 0, 8, 8], "texture": "#0"},
            "north": {"uv": [0, 8, 8, 9.5], "texture": "#0"},
            "south": {"uv": [0, 8, 8, 9.5], "texture": "#0"},
            "west":  {"uv": [0, 8, 8, 9.5], "texture": "#0"},
            "east":  {"uv": [0, 8, 8, 9.5], "texture": "#0"},
        },
    }],
}


def main():
    for cid, (label, color, dark) in CHIPS.items():
        tex = chip_texture(label, color, dark)
        for base in (os.path.join(RP, "assets/barkan/textures/chip"),
                     os.path.join(STAGING, "chip")):
            os.makedirs(base, exist_ok=True)
            tex.save(os.path.join(base, f"{cid}.png"))
        model = json.loads(json.dumps(MODEL))
        model["textures"]["0"] = f"barkan:chip/{cid}"
        mp = os.path.join(RP, f"assets/barkan/models/chip/{cid}.json")
        ip = os.path.join(RP, f"assets/barkan/items/chip/{cid}.json")
        os.makedirs(os.path.dirname(mp), exist_ok=True)
        os.makedirs(os.path.dirname(ip), exist_ok=True)
        with open(mp, "w") as f:
            json.dump(model, f, separators=(",", ":"))
        with open(ip, "w") as f:
            json.dump({"model": {"type": "minecraft:model", "model": f"barkan:chip/{cid}"}},
                      f, separators=(",", ":"))
    print(f"완료: 칩 {len(CHIPS)}종 → RP + 스테이징 {STAGING}/chip")


if __name__ == "__main__":
    main()
