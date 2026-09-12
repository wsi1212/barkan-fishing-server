#!/usr/bin/env python3
"""scarecrow-manifest.json -> 3D 모델/아틀라스/GUI 아이콘/CraftEngine 설정/검수 렌더."""
import json
import os
import sys
from pathlib import Path

from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
SKILL = HERE.parent / ".claude" / "skills" / "pixel-art" / "scripts"
sys.path.insert(0, str(SKILL))
sys.path.insert(0, str(HERE))

from painters import REGISTRY
from render_textured import assert_camera_convention, render

SERVER = HERE.parent
while SERVER.name != "07de2d81-991a-47e2-b62d-06c0d1b5150a":
    if SERVER.parent == SERVER:
        raise SystemExit("서버 루트를 찾지 못했습니다")
    SERVER = SERVER.parent
CE = SERVER / "plugins" / "CraftEngine" / "resources" / "barkan_furniture"
OUT = HERE / "out"


def crisp_icon(raw_path: Path, output_path: Path) -> None:
    icon = Image.open(raw_path).convert("RGBA")
    bounds = icon.getbbox()
    if bounds:
        icon = icon.crop(bounds)
    side = max(icon.size)
    square = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    square.paste(icon, ((side - icon.width) // 2, (side - icon.height) // 2), icon)
    icon = square.resize((30, 30), Image.Resampling.LANCZOS)
    padded = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
    padded.paste(icon, (1, 1), icon)
    px = padded.load()
    for y in range(32):
        for x in range(32):
            r, g, b, a = px[x, y]
            px[x, y] = (r, g, b, 255 if a > 96 else 0)
    original = list(padded.get_flattened_data())
    for y in range(32):
        for x in range(32):
            r, g, b, a = original[y * 32 + x]
            if a == 0:
                continue
            edge = any(nx < 0 or nx >= 32 or ny < 0 or ny >= 32 or original[ny * 32 + nx][3] == 0
                       for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)))
            if edge:
                px[x, y] = (int(r * 0.55), int(g * 0.55), int(b * 0.55), 255)
    padded.save(output_path)


def make_contact(paths: list[Path], output: Path) -> None:
    labels = ["3/4", "front", "side"]
    canvas = Image.new("RGBA", (3 * 360, 400), (30, 34, 38, 255))
    draw = ImageDraw.Draw(canvas)
    for i, (path, label) in enumerate(zip(paths, labels)):
        image = Image.open(path).convert("RGBA").resize((340, 340), Image.Resampling.NEAREST)
        canvas.alpha_composite(image, (i * 360 + 10, 10))
        draw.text((i * 360 + 16, 365), label, fill=(230, 230, 225, 255))
    canvas.save(output)


def main() -> None:
    manifest = json.loads((HERE / "scarecrow-manifest.json").read_text(encoding="utf-8"))
    assert_camera_convention()
    painter, kwargs = REGISTRY[manifest["painter"]]
    atlas, elements = painter(**kwargs, seed=manifest["seed"])
    model = {
        "textures": {"0": manifest["texture"], "particle": manifest["texture"]},
        "elements": elements,
        "display": {"fixed": {"rotation": [0, 0, 0], "translation": [0, 0, 0], "scale": [1, 1, 1]}},
    }

    model_path = CE / "resourcepack/assets/barkan/models/item/furniture/farm/scarecrow.json"
    texture_path = CE / "resourcepack/assets/barkan/textures/furniture/farm/scarecrow.png"
    icon_model_path = CE / "resourcepack/assets/barkan/models/item/furniture/farm/icon/scarecrow.json"
    icon_texture_path = CE / "resourcepack/assets/barkan/textures/furniture/farm/icon/scarecrow.png"
    config_path = CE / "configuration/scarecrow.yml"
    for path in (model_path, texture_path, icon_model_path, icon_texture_path, config_path):
        path.parent.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(exist_ok=True)

    atlas.save(texture_path)
    model_path.write_text(json.dumps(model, indent=2), encoding="utf-8")
    icon_model_path.write_text(json.dumps({
        "parent": "minecraft:item/generated",
        "textures": {"layer0": manifest["icon_texture"]},
    }, indent=2), encoding="utf-8")

    raw_icon = OUT / "scarecrow_icon_raw.png"
    stats = render(model_path, texture_path, raw_icon,
                   yaw=manifest["icon_yaw"], pitch=manifest["icon_pitch"], size=256)
    down_ratio = stats["down"] / max(1, sum(stats.values()))
    if down_ratio > 0.25:
        raise SystemExit(f"아이콘 카메라가 너무 낮습니다: 밑면 {down_ratio:.1%}")
    crisp_icon(raw_icon, icon_texture_path)
    raw_icon.unlink()

    views = [OUT / "scarecrow_render.png", OUT / "scarecrow_front.png", OUT / "scarecrow_side.png"]
    render(model_path, texture_path, views[0], yaw=30, pitch=20, size=640)
    render(model_path, texture_path, views[1], yaw=0, pitch=4, size=640)
    render(model_path, texture_path, views[2], yaw=90, pitch=4, size=640)
    make_contact(views, OUT / "scarecrow_contact.png")

    config_path.write_text(f'''# pixel-forge/build_scarecrow.py 생성 — 설치형 바닐라 작물 오프라인 성장 설비
items:
  {manifest["item_id"]}:
    data:
      item_name: "<!i><gold>{manifest["name"]}</gold>"
      lore:
        - "<!i><dark_gray>[농사 설비]</dark_gray>"
        - "<!i><gray>주변 <white>16×16×16</white>의 일반 작물이</gray>"
        - "<!i><gray>섬이 비어 있는 동안에도 자랍니다.</gray>"
        - ""
        - "<!i><yellow>우클릭: 적용 범위 10초 보기</yellow>"
    model:
      type: minecraft:select
      property: minecraft:display_context
      cases:
        - when: gui
          model:
            type: minecraft:model
            model: {manifest["icon_model"]}
      fallback:
        type: minecraft:model
        model: {manifest["model"]}
    behavior:
      type: furniture_item
      rules:
        ground: {{rotation: any, alignment: center}}
      furniture:
        events:
          - template: default:rotatable_furniture_8
        settings:
          item: {manifest["item_id"]}
          hit_times: 2
          sounds: {{break: minecraft:block.wood.break, place: minecraft:block.wood.place, hit: minecraft:block.wood.hit}}
        variants:
          ground:
            elements:
              - item: {manifest["item_id"]}
                display_transform: FIXED
                billboard: FIXED
                translation: 0,{manifest["world_translation_y"]},0
                scale: {manifest["world_scale"]}
                shadow_radius: 0.8
                shadow_strength: 0.25
            hitboxes:
              - position: 0,0,0
                type: interaction
                invisible: true
                blocks_building: true
                interactive: true
                width: 1.5
                height: 2.0
        loot:
          template: default:loot_table/furniture
          arguments: {{item: {manifest["item_id"]}}}
''', encoding="utf-8")
    print(f"OK — {len(elements)} elements, atlas {atlas.size}, icon down {down_ratio:.1%}")
    print(OUT / "scarecrow_contact.png")


if __name__ == "__main__":
    main()
