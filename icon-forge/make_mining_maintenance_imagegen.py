#!/usr/bin/env python3
"""ImageGen 원본 4분할을 정비 계열의 실제 리소스팩 배지로 설치한다.

`make_mining_maintenance_badges.py`의 단순 16px 재드로잉본은 더 이상 출력에 쓰지 않는다.
여기서는 승인된 ImageGen 원본의 각 사분면을 투명 여백 기준으로 정규화해 64px로 만들고,
기존 상태 규약(_locked/_avail/_maxed)과 모델·아이템 정의를 함께 갱신한다.
"""
from __future__ import annotations

import json
from io import BytesIO
from pathlib import Path

from PIL import Image

from make_skill_states import avail, locked, maxed


HERE = Path(__file__).resolve().parent
SOURCE = HERE / "imagegen-mining-maintenance/mining_maintenance_concept.png"
RP = Path("~/development/barkan-resourcepack").expanduser()
TEX = RP / "assets/minecraft/textures/item/barkan_icon"
MODELS = RP / "assets/barkan/models/barkan_icon"
ITEMS = RP / "assets/barkan/items/barkan_icon"
TEMPLATE = "skill_mining_vein_scan"
OUT = HERE / "out"

# ImageGen 2×2 시트의 읽는 순서는 곧 스킬 트리의 정비 가지 순서다.
ICONS = (
    ("skill_mining_maintenance", (0, 0, 627, 627)),
    ("skill_mining_protective_coating", (627, 0, 1254, 627)),
    ("skill_mining_emergency_repair", (0, 627, 627, 1254)),
    ("skill_mining_artisan_touch", (627, 627, 1254, 1254)),
)


def content_bbox(image: Image.Image) -> tuple[int, int, int, int]:
    """저알파 글로우가 시트 전체를 점유하지 않도록 alpha 16 이상만 내용으로 잡는다."""
    alpha = image.getchannel("A").point(lambda value: 255 if value >= 16 else 0)
    bbox = alpha.getbbox()
    if bbox is None:
        raise ValueError("ImageGen 사분면에 불투명한 배지가 없습니다")
    return bbox


def normalize(quadrant: Image.Image) -> Image.Image:
    """원본의 1~2px 고스트 알파를 버리고, 기존 64px 배지와 같은 60px 실루엣으로 맞춘다."""
    source = quadrant.crop(content_bbox(quadrant))
    alpha = source.getchannel("A").point(lambda value: 255 if value >= 16 else 0)
    source.putalpha(alpha)
    source.thumbnail((60, 60), Image.Resampling.LANCZOS)
    out = Image.new("RGBA", (64, 64))
    out.alpha_composite(source, ((64 - source.width) // 2, (64 - source.height) // 2))
    return out


def write_definition(icon_id: str) -> None:
    """기존 스킬 배지의 1.332 GUI 배율/oversized 규약을 그대로 상속한다."""
    with (MODELS / f"{TEMPLATE}.json").open(encoding="utf-8") as handle:
        model = json.load(handle)
    model["textures"]["layer0"] = f"minecraft:item/barkan_icon/{icon_id}"
    with (MODELS / f"{icon_id}.json").open("w", encoding="utf-8") as handle:
        json.dump(model, handle, ensure_ascii=False, indent=2)
        handle.write("\n")

    with (ITEMS / f"{TEMPLATE}.json").open(encoding="utf-8") as handle:
        item = json.load(handle)
    item["model"]["model"] = f"barkan:barkan_icon/{icon_id}"
    with (ITEMS / f"{icon_id}.json").open("w", encoding="utf-8") as handle:
        json.dump(item, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def main() -> None:
    if not SOURCE.is_file():
        raise SystemExit(f"ImageGen 원본 없음: {SOURCE}")
    for path in (TEX, MODELS, ITEMS, MODELS / f"{TEMPLATE}.json", ITEMS / f"{TEMPLATE}.json"):
        if not path.exists():
            raise SystemExit(f"리소스팩 기준 파일 없음: {path}")

    sheet = Image.new("RGBA", (512, 512))
    source = Image.open(SOURCE).convert("RGBA")
    if source.size != (1254, 1254):
        raise SystemExit(f"예상하지 못한 ImageGen 원본 크기: {source.size}")

    OUT.mkdir(parents=True, exist_ok=True)
    for index, (icon_id, box) in enumerate(ICONS):
        base = normalize(source.crop(box))
        variants = {
            icon_id: base,
            icon_id + "_locked": locked(base),
            icon_id + "_avail": avail(base),
            icon_id + "_maxed": maxed(base),
        }
        for variant_id, image in variants.items():
            image.save(TEX / f"{variant_id}.png")
            write_definition(variant_id)
        sheet.alpha_composite(base.resize((256, 256), Image.Resampling.NEAREST),
                              ((index % 2) * 256, (index // 2) * 256))
        print(f"✓ {icon_id}: ImageGen 원본 → 64px + 상태 4종")
    sheet.save(OUT / "mining_maintenance_imagegen_pack.png")
    print(f"리뷰 시트: {OUT / 'mining_maintenance_imagegen_pack.png'}")


if __name__ == "__main__":
    main()
