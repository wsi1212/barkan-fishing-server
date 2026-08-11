#!/usr/bin/env python3
"""Build the 43 material catalog assets and model JSONs for the resource pack."""
from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MANIFEST = ROOT / "material_manifest.json"
PROCESSED = ROOT / "imagegen-materials" / "processed"
PACK = Path("/Users/user/development/barkan-resourcepack")
TEXTURES = PACK / "assets/minecraft/textures/item/barkan_icon"
MODELS = PACK / "assets/barkan/models/barkan_icon"
ITEMS = PACK / "assets/barkan/items/barkan_icon"


def sha10(*parts: str) -> str:
    return hashlib.sha1("\0".join(parts).encode("utf-8")).hexdigest()[:10]


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
        if not source.is_file():
            raise FileNotFoundError(source)
        shutil.copy2(source, texture)
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
