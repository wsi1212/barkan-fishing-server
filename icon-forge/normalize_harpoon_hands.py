#!/usr/bin/env python3
"""카탈로그 작살을 인벤토리/손들기 모델 체인으로 맞춘다.

기존 작살은 display_context 선택 모델을 사용한다. 카탈로그 생성기는
인벤토리용 3종 세트를 안전하게 채우지만, 새 작살도 기존 규칙에 맞춰
손에 들었을 때의 held 텍스처와 모델을 함께 만들 필요가 있다.

기존 파일은 덮어쓰지 않는다. 직접 실행해도 새로 생성된 작살처럼 아직
선택 모델이 없는 항목만 보정된다.
"""
from __future__ import annotations

import json
from pathlib import Path

from PIL import Image

from catalog_build import PARTS, RP, icon_id


def _harpoons() -> list[str]:
    data = json.loads(PARTS.read_text(encoding="utf-8"))
    return list(data["parts"]["작살"])


def _held_texture(source: Path) -> Image.Image:
    src = Image.open(source).convert("RGBA")
    bbox = src.getchannel("A").getbbox()
    if bbox is None:
        raise SystemExit(f"투명 아이콘: {source}")
    crop = src.crop(bbox)
    canvas_size = (src.width * 2, src.height * 2)
    # 기존 hand-harpoon 자산과 같은 비율로, 2배 캔버스 안에서 읽히게 배치한다.
    target = min(canvas_size) * 0.68
    scale = min(target / crop.width, target / crop.height)
    size = (max(1, round(crop.width * scale)), max(1, round(crop.height * scale)))
    crop = crop.resize(size, Image.Resampling.LANCZOS)
    out = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
    out.alpha_composite(crop, ((canvas_size[0] - size[0]) // 2, (canvas_size[1] - size[1]) // 2))
    return out


def main() -> None:
    tex = RP / "assets/minecraft/textures/item/barkan_icon"
    models = RP / "assets/barkan/models/barkan_icon"
    items = RP / "assets/barkan/items/barkan_icon"
    created = 0

    for name in _harpoons():
        iid = icon_id("작살", name)
        catalog = tex / f"{iid}.png"
        item = items / f"{iid}.json"
        if not catalog.exists() or not item.exists():
            raise SystemExit(f"작살 카탈로그 세트 누락: {name} ({iid})")

        current = json.loads(item.read_text(encoding="utf-8"))
        model = current.get("model", {})
        if model.get("type") == "minecraft:select":
            continue
        expected_direct = {"type": "minecraft:model", "model": f"barkan:barkan_icon/{iid}"}
        if model != expected_direct:
            raise SystemExit(f"예상 밖 작살 item 정의: {item}")

        held_texture = tex / f"held_harpoon_{iid.removeprefix('catalog_harpoon_')}.png"
        held_model = models / f"held_harpoon_{iid.removeprefix('catalog_harpoon_')}.json"
        inventory_model = models / f"inventory_harpoon_{iid.removeprefix('catalog_harpoon_')}.json"
        if not held_texture.exists():
            _held_texture(catalog).save(held_texture)
        if not held_model.exists():
            held_model.write_text(json.dumps({
                "parent": "minecraft:item/handheld_rod",
                "textures": {"layer0": f"minecraft:item/barkan_icon/{held_texture.stem}"},
            }, ensure_ascii=False), encoding="utf-8")
        if not inventory_model.exists():
            inventory_model.write_text(json.dumps({
                "parent": "minecraft:item/generated",
                "textures": {"layer0": f"minecraft:item/barkan_icon/{iid}"},
            }, ensure_ascii=False), encoding="utf-8")

        definition = {
            "model": {
                "type": "minecraft:select",
                "property": "minecraft:display_context",
                "cases": [{
                    "when": ["thirdperson_lefthand", "thirdperson_righthand", "firstperson_lefthand", "firstperson_righthand"],
                    "model": {"type": "minecraft:model", "model": f"barkan:barkan_icon/{held_model.stem}"},
                }],
                "fallback": {"type": "minecraft:model", "model": f"barkan:barkan_icon/{inventory_model.stem}"},
            }
        }
        item.write_text(json.dumps(definition, ensure_ascii=False), encoding="utf-8")
        created += 1
        print(f"보정: {name} -> {iid}")

    print(f"작살 손들기 체인 보정 완료: {created}개")


if __name__ == "__main__":
    main()
