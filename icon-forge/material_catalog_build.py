#!/usr/bin/env python3
"""Build material catalog assets and model JSONs for the resource pack."""
from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent
MANIFEST = ROOT / "material_manifest.json"
PROCESSED = ROOT / "imagegen-materials" / "processed"
PACK = Path("/Users/user/development/barkan-resourcepack")
TEXTURES = PACK / "assets/minecraft/textures/item/barkan_icon"
MODELS = PACK / "assets/barkan/models/barkan_icon"
ITEMS = PACK / "assets/barkan/items/barkan_icon"


def sha10(*parts: str) -> str:
    return hashlib.sha1("\0".join(parts).encode("utf-8")).hexdigest()[:10]


def validate_texture(path: Path) -> None:
    try:
        with Image.open(path) as image:
            image = image.convert("RGBA")
            if image.size not in ((128, 128), (256, 256)):
                raise ValueError(f"expected 128x128 or 256x256, got {image.size}")
            if image.getchannel("A").getbbox() is None:
                raise ValueError("empty alpha")
    except Exception as exc:
        raise ValueError(f"invalid material texture {path}: {exc}") from exc


def main() -> None:
    entries = json.loads(MANIFEST.read_text(encoding="utf-8"))
    for folder in (TEXTURES, MODELS, ITEMS):
        folder.mkdir(parents=True, exist_ok=True)

    for entry in entries:
        mat_id = entry["id"]
        slug = entry["slug"]
        code = sha10("재료", mat_id)
        stem = f"catalog_material_{code}"
        source = PROCESSED / f"{slug}.png"
        texture = TEXTURES / f"{stem}.png"
        model = MODELS / f"{stem}.json"
        item = ITEMS / f"{stem}.json"
        if source.is_file():
            shutil.copy2(source, texture)
        elif texture.is_file():
            # Some catalog icons predate the ImageGen source archive. Preserve
            # the already-installed artwork while still rebuilding its wiring.
            print(f"reuse existing texture: {mat_id} ({texture.name})")
        else:
            raise FileNotFoundError(source)
        validate_texture(texture)
        model.write_text(json.dumps({
            "parent": "minecraft:item/generated",
            "textures": {"layer0": f"minecraft:item/barkan_icon/{stem}"},
        }, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        item.write_text(json.dumps({
            "model": {"type": "minecraft:model", "model": f"barkan:barkan_icon/{stem}"},
        }, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    print(f"built {len(entries)} material catalog icons")
    for entry in entries:
        print(entry["id"], sha10("재료", entry["id"]))


if __name__ == "__main__":
    main()
