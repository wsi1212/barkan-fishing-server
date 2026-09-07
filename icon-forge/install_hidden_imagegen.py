#!/usr/bin/env python3
"""Install the ImageGen hidden-equipment icon set into the authoritative RP.

The source images are intentionally kept in imagegen-hidden/source/.  This script
only changes the 62 catalog textures, preserves the existing model/item JSON
chain, and emits a manifest plus 16px review copies for the item-icon gates.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from PIL import Image, ImageFilter


HERE = Path(__file__).resolve().parent
PLUGIN = Path("/Users/user/development/blockship-plugin")
RP = Path("/Users/user/development/barkan-resourcepack")
SOURCE = HERE / "imagegen-hidden" / "source"
FINAL = HERE / "imagegen-hidden" / "final"
REVIEW = HERE / "imagegen-hidden" / "review-16"
MANIFEST = HERE / "imagegen-hidden" / "manifest.json"

TYPE_KEY = {
    "낚싯대": "rod",
    "릴": "reel",
    "줄": "line",
    "바늘": "hook",
    "미끼": "bait",
    "찌": "bobber",
    "작살": "harpoon",
}
ORDER = list(TYPE_KEY)


def icon_id(kind: str, name: str) -> str:
    digest = hashlib.sha1((kind + "\0" + name).encode("utf-8")).hexdigest()[:10]
    return f"catalog_{TYPE_KEY[kind]}_{digest}"


def hidden_recipe_ids() -> set[str]:
    text = (PLUGIN / "src/test/java/com/blockship/crafting/HiddenEquipmentRecipeSelfTest.java").read_text()
    block = text.split("RESTORED_62 = Set.of((", 1)[1].split(").split(\" \")", 1)[0]
    ids: set[str] = set()
    for value in re.findall(r'"([^"]*)"', block):
        ids.update(value.split())
    if len(ids) != 62:
        raise SystemExit(f"RESTORED_62 목록이 62개가 아님: {len(ids)}")
    return ids


def load_rows() -> list[dict[str, str]]:
    parts = json.loads((PLUGIN / "parts.json").read_text(encoding="utf-8"))["parts"]
    recipes = json.loads((PLUGIN / "recipes.json").read_text(encoding="utf-8"))["recipes"]
    rows: list[dict[str, str]] = []
    for recipe_id in hidden_recipe_ids():
        recipe = recipes[recipe_id]
        if recipe.get("resultMode") == "rod":
            kind = "낚싯대"
            name = recipe.get("rodPartName") or recipe.get("displayName")
        else:
            kind = recipe.get("resultPartType")
            name = recipe.get("resultPartName")
        if kind not in TYPE_KEY or not name:
            raise SystemExit(f"아이콘 대상 해석 실패: {recipe_id}")
        fields = parts[kind][name].split("|", -1)
        rows.append(
            {
                "recipe": recipe_id,
                "type": kind,
                "name": name,
                "grade": fields[1],
                "origin": fields[6],
                "id": icon_id(kind, name),
            }
        )
    rows.sort(key=lambda row: (ORDER.index(row["type"]), row["name"]))
    return rows


def palette_reduce(im: Image.Image) -> Image.Image:
    """Keep the ImageGen silhouette but make it a hard-edged item icon."""
    im = im.convert("RGBA")
    if im.width != im.height:
        side = min(im.size)
        left = (im.width - side) // 2
        top = (im.height - side) // 2
        im = im.crop((left, top, left + side, top + side))

    im = im.resize((512, 512), Image.Resampling.LANCZOS)
    alpha = im.getchannel("A").point(lambda value: 255 if value >= 48 else 0)
    bbox = alpha.getbbox()
    if bbox is None:
        raise SystemExit("완전 투명 ImageGen 결과")

    # Quantize only the object crop so the transparent canvas does not consume
    # the palette with black background pixels.
    rgb = im.convert("RGB")
    crop = rgb.crop(bbox).quantize(colors=14, dither=Image.Dither.NONE).convert("RGB")
    canvas = Image.new("RGB", im.size, (18, 20, 30))
    canvas.paste(crop, bbox)

    # The icon skill forbids pure-black outlines. Replace only object pixels.
    pixels = canvas.load()
    for y in range(canvas.height):
        for x in range(canvas.width):
            if alpha.getpixel((x, y)) and pixels[x, y] == (0, 0, 0):
                pixels[x, y] = (18, 20, 30)
    return Image.merge("RGBA", (*canvas.split(), alpha))


def widen_bobber(im: Image.Image) -> Image.Image:
    """Keep a float vertical, but make its body survive a 16px slot."""
    alpha = im.getchannel("A")
    bbox = alpha.getbbox()
    if bbox is None:
        return im
    crop = im.crop(bbox)
    width = min(im.width, max(crop.width, round(crop.width * 2.30), round(im.width * 0.64)))
    crop = crop.resize((width, crop.height), Image.Resampling.NEAREST)
    out = Image.new("RGBA", im.size, (18, 20, 30, 0))
    x = (im.width - crop.width) // 2
    y = (im.height - crop.height) // 2
    out.alpha_composite(crop, (x, y))
    return out


def remove_isolated_pixels(im: Image.Image) -> Image.Image:
    """Remove single-pixel specks detached from an icon's silhouette.

    ImageGen sometimes leaves a lone sparkle or stray pixel outside a rod. The
    item-icon lint gate treats those as orphaned pixels; removing only pixels
    without any 8-neighbour keeps connected highlights and the source PNGs
    untouched.
    """
    im = im.copy().convert("RGBA")
    alpha = im.getchannel("A")
    px = alpha.load()
    remove: list[tuple[int, int]] = []
    for y in range(1, im.height - 1):
        for x in range(1, im.width - 1):
            if not px[x, y]:
                continue
            if not any(px[x + dx, y + dy] for dy in (-1, 0, 1) for dx in (-1, 0, 1) if (dx, dy) != (0, 0)):
                remove.append((x, y))
    for x, y in remove:
        px[x, y] = 0
    im.putalpha(alpha)
    return im


def thicken_rod(im: Image.Image) -> Image.Image:
    """Add a one-pixel-at-16px readability margin to very thin rods."""
    original = im.convert("RGBA")
    original_alpha = original.getchannel("A")
    grown_alpha = original_alpha.filter(ImageFilter.MaxFilter(3))
    out = original.copy()
    out.putalpha(grown_alpha)
    src = original.load()
    dst = out.load()
    for y in range(out.height):
        for x in range(out.width):
            if not original_alpha.getpixel((x, y)) and grown_alpha.getpixel((x, y)):
                nearest = None
                for radius in (1, 2):
                    candidates = []
                    for yy in range(max(0, y - radius), min(out.height, y + radius + 1)):
                        for xx in range(max(0, x - radius), min(out.width, x + radius + 1)):
                            if original_alpha.getpixel((xx, yy)):
                                candidates.append((abs(xx - x) + abs(yy - y), yy, xx))
                    if candidates:
                        nearest = min(candidates)
                        break
                if nearest is not None:
                    _, yy, xx = nearest
                    dst[x, y] = (*src[xx, yy][:3], 255)
    return out


def install(rows: list[dict[str, str]]) -> None:
    tex_dir = RP / "assets/minecraft/textures/item/barkan_icon"
    model_dir = RP / "assets/barkan/models/barkan_icon"
    item_dir = RP / "assets/barkan/items/barkan_icon"
    for directory in (FINAL, REVIEW, tex_dir):
        directory.mkdir(parents=True, exist_ok=True)

    for row in rows:
        source = SOURCE / f"{row['id']}.png"
        if not source.is_file():
            raise SystemExit(f"ImageGen 원본 누락: {row['type']}/{row['name']} ({source})")
        size = 256 if row["grade"] == "A" else 512 if row["grade"] == "S" else None
        if size is None:
            raise SystemExit(f"히든 대상에 예상 밖 등급: {row}")
        # palette_reduce() already performs the only filtered resize and then
        # hardens alpha.  NEAREST here preserves that binary alpha at both the
        # A=256px delivery size and the 16px slot review size.
        out = palette_reduce(Image.open(source)).resize((size, size), Image.Resampling.NEAREST)
        if row["type"] == "찌":
            out = widen_bobber(out)
        elif row["type"] == "낚싯대":
            out = thicken_rod(remove_isolated_pixels(out))
        final_path = FINAL / f"{row['id']}.png"
        rp_path = tex_dir / f"{row['id']}.png"
        out.save(final_path, format="PNG", optimize=True)
        out.save(rp_path, format="PNG", optimize=True)

        # Do not silently create a half-wired icon: the existing 1.21 item-model
        # chain must already be present for every generated texture.
        model = model_dir / f"{row['id']}.json"
        item = item_dir / f"{row['id']}.json"
        if not model.is_file() or not item.is_file():
            raise SystemExit(f"모델/아이템 정의 누락: {row['id']}")
        model_data = json.loads(model.read_text(encoding="utf-8"))
        layer0 = model_data.get("textures", {}).get("layer0")
        if layer0 != f"minecraft:item/barkan_icon/{row['id']}":
            raise SystemExit(f"layer0 불일치: {row['id']} -> {layer0}")
        item_data = json.loads(item.read_text(encoding="utf-8"))

        def model_refs(node: object) -> list[str]:
            if isinstance(node, dict):
                refs: list[str] = []
                if node.get("type") == "minecraft:model" and isinstance(node.get("model"), str):
                    refs.append(node["model"])
                for value in node.values():
                    refs.extend(model_refs(value))
                return refs
            if isinstance(node, list):
                refs: list[str] = []
                for value in node:
                    refs.extend(model_refs(value))
                return refs
            return []

        refs = model_refs(item_data.get("model", {}))
        if not refs:
            raise SystemExit(f"item model 참조 없음: {row['id']}")
        suffix = row["id"].removeprefix("catalog_harpoon_")
        allowed = {
            f"barkan:barkan_icon/{row['id']}",
            f"barkan:barkan_icon/held_harpoon_{suffix}",
            f"barkan:barkan_icon/inventory_harpoon_{suffix}",
        }
        if not set(refs).issubset(allowed):
            raise SystemExit(f"item model 불일치: {row['id']} -> {refs}")
        for ref in refs:
            model_name = ref.removeprefix("barkan:barkan_icon/")
            referenced = model_dir / f"{model_name}.json"
            if not referenced.is_file():
                raise SystemExit(f"item model 대상 파일 누락: {row['id']} -> {referenced}")
            referenced_data = json.loads(referenced.read_text(encoding="utf-8"))
            layer0_ref = referenced_data.get("textures", {}).get("layer0", "")
            if model_name.startswith("inventory_harpoon_") and layer0_ref != f"minecraft:item/barkan_icon/{row['id']}":
                raise SystemExit(f"작살 인벤토리 layer0 불일치: {row['id']} -> {layer0_ref}")

        review = remove_isolated_pixels(out.resize((16, 16), Image.Resampling.NEAREST))
        review.save(REVIEW / f"{row['id']}.png", format="PNG", optimize=True)
        row.update(
            {
                "source": str(source),
                "final": str(rp_path),
                "resolution": str(size),
            }
        )

    MANIFEST.write_text(
        json.dumps(
            {
                "generator": "OpenAI imagegen built-in",
                "source_style": "transparent Minecraft-inspired pixel art",
                "slot_resolution": 16,
                "rows": rows,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    rows = load_rows()
    install(rows)
    print(f"installed ImageGen hidden icons: {len(rows)} (A=256px, S=512px; slot=16px)")
