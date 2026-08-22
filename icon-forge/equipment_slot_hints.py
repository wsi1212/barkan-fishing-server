#!/usr/bin/env python3
"""ImageGen 원본에서 장비 장착 슬롯용 실루엣 5종을 추출하고 RP에 설치한다.

생성 원본은 투명 배경을 요청했지만 ImageGen이 바둑판을 실제 픽셀로 굽는 경우가
있으므로, 밝은 무채색 바탕을 제거한 뒤 각 아이콘을 32x32 투명 텍스처로 정리한다.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from PIL import Image


HERE = Path(__file__).resolve().parent
SOURCE = HERE / "source" / "equipment_slot_hints_imagegen.png"
OUT = HERE / "out" / "equipment_slot_hints"
RP = Path("/Users/user/Downloads/barkan-resourcepack")

SLOTS = (
    ("reel", "릴"),
    ("line", "줄"),
    ("hook", "바늘"),
    ("bait", "미끼"),
    ("bobber", "찌"),
)


def dark_pixel(rgb: tuple[int, int, int]) -> bool:
    r, g, b = rgb
    mean = (r + g + b) / 3
    chroma = max(rgb) - min(rgb)
    # ImageGen의 바둑판은 밝고 거의 무채색이다. 아이콘의 밝은 강철 하이라이트
    # 는 225 아래라 유지되고, 바깥의 흰/회색 칸은 제거된다.
    return mean < 225 or chroma > 24


def find_bbox(image: Image.Image, x0: int, x1: int) -> tuple[int, int, int, int]:
    rgb = image.convert("RGB")
    points = [
        (x, y)
        for y in range(rgb.height)
        for x in range(x0, x1)
        if dark_pixel(rgb.getpixel((x, y)))
    ]
    if not points:
        raise RuntimeError(f"실루엣을 찾지 못했습니다: x={x0}..{x1}")
    xs, ys = zip(*points)
    return min(xs), min(ys), max(xs) + 1, max(ys) + 1


def make_icon(image: Image.Image, bbox: tuple[int, int, int, int]) -> Image.Image:
    crop = image.crop(bbox).convert("RGBA")
    px = crop.load()
    for y in range(crop.height):
        for x in range(crop.width):
            r, g, b, _ = px[x, y]
            px[x, y] = (r, g, b, 0 if not dark_pixel((r, g, b)) else 255)

    # 슬롯 안에서 장착된 아이콘보다 한 단계 물러난 안내 실루엣 크기.
    max_side = 26
    scale = min(max_side / crop.width, max_side / crop.height)
    size = (max(1, round(crop.width * scale)), max(1, round(crop.height * scale)))
    crop = crop.resize(size, Image.Resampling.LANCZOS)
    # 가장자리의 잔여 반투명 바탕 픽셀을 제거한다.
    alpha = crop.getchannel("A")
    alpha = alpha.point(lambda a: 0 if a < 80 else 255)
    # ImageGen은 미세한 그라데이션을 많이 넣으므로, 슬롯에서 픽셀 램프가
    # 뭉개지지 않도록 12색 안쪽의 차분한 재질 팔레트로 줄인다.
    rgb = crop.convert("RGB").quantize(
        colors=12, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE
    ).convert("RGB")
    crop = Image.merge("RGBA", (*rgb.split(), alpha))

    out = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
    out.alpha_composite(crop, ((32 - crop.width) // 2, (32 - crop.height) // 2))
    return out


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ": ")) + "\n")


def main(install: bool = False) -> None:
    if not SOURCE.exists():
        raise SystemExit(f"원본이 없습니다: {SOURCE}")

    image = Image.open(SOURCE).convert("RGBA")
    # 생성 결과의 실제 아이콘 열 위치를 자동으로 읽는다. 칸 사이 간격이 바뀌어도
    # 밝은 바탕으로부터 안정적으로 분리할 수 있다.
    columns = []
    active = []
    for x in range(image.width):
        has_dark = any(dark_pixel(image.getpixel((x, y))[:3]) for y in range(image.height))
        if has_dark:
            active.append(x)
        elif active:
            columns.append((active[0], active[-1] + 1))
            active = []
    if active:
        columns.append((active[0], active[-1] + 1))
    if len(columns) != len(SLOTS):
        raise SystemExit(f"실루엣 열 수가 예상과 다릅니다: {columns}")

    OUT.mkdir(parents=True, exist_ok=True)
    texture_dir = RP / "assets/minecraft/textures/item/barkan_icon"
    model_dir = RP / "assets/barkan/models/barkan_icon"
    item_dir = RP / "assets/barkan/items/barkan_icon"
    if install:
        for path in (texture_dir, model_dir, item_dir):
            path.mkdir(parents=True, exist_ok=True)

    for (slot_id, _label), (x0, x1) in zip(SLOTS, columns):
        icon = make_icon(image, find_bbox(image, x0, x1))
        output = OUT / f"equip_hint_{slot_id}.png"
        icon.save(output)
        if not install:
            continue
        icon.save(texture_dir / output.name)
        model_id = f"equip_hint_{slot_id}"
        write_json(model_dir / f"{model_id}.json", {
            "parent": "minecraft:item/generated",
            "textures": {"layer0": f"minecraft:item/barkan_icon/{model_id}"},
        })
        write_json(item_dir / f"{model_id}.json", {
            "model": {"type": "minecraft:model", "model": f"barkan:barkan_icon/{model_id}"},
        })
        print(f"✓ {model_id} → {texture_dir / output.name}")


if __name__ == "__main__":
    main(install="--install" in sys.argv)
