#!/usr/bin/env python3
"""배포된 Bedrock 팩에서 지정 아이콘만 안전하게 롤백한다."""
from __future__ import annotations

import argparse
import json
import tempfile
import zipfile
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline-map", type=Path, required=True)
    parser.add_argument("--baseline-pack", type=Path, required=True)
    parser.add_argument("--out-map", type=Path, required=True)
    parser.add_argument("--out-pack", type=Path, required=True)
    parser.add_argument("--item", action="append", required=True)
    args = parser.parse_args()
    removed = set(args.item)
    doc = json.loads(args.baseline_map.read_text(encoding="utf-8"))
    items = {
        base: [definition for definition in definitions
               if definition.get("bedrock_options", {}).get("icon") not in removed]
        for base, definitions in doc["items"].items()
    }
    items = {base: definitions for base, definitions in items.items() if definitions}
    active_icons = {definition.get("bedrock_options", {}).get("icon")
                    for definitions in items.values() for definition in definitions}

    with tempfile.TemporaryDirectory(prefix="barkan-bedrock-rollback-") as tmp:
        stage = Path(tmp) / "pack"
        with zipfile.ZipFile(args.baseline_pack) as archive:
            archive.extractall(stage)
        texture_path = stage / "textures/item_texture.json"
        texture_doc = json.loads(texture_path.read_text(encoding="utf-8"))
        texture_data = texture_doc["texture_data"]
        for icon in removed - active_icons:
            entry = texture_data.pop(icon, None)
            if entry and (png := stage / f"{entry['textures']}.png").is_file():
                png.unlink()
        texture_path.write_text(json.dumps(texture_doc, ensure_ascii=False, indent=2), encoding="utf-8")
        manifest_path = stage / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        rev = int(manifest["header"]["version"][2]) + 1
        manifest["header"]["version"][2] = rev
        for module in manifest.get("modules", []):
            module["version"][2] = rev
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        args.out_map.parent.mkdir(parents=True, exist_ok=True)
        args.out_map.write_text(json.dumps({"format_version": "2", "items": items},
                                           ensure_ascii=False, indent=2), encoding="utf-8")
        with zipfile.ZipFile(args.out_pack, "w", zipfile.ZIP_DEFLATED) as archive:
            for file in sorted(stage.rglob("*")):
                if file.is_file():
                    archive.write(file, file.relative_to(stage).as_posix())
    print(f"제거: {', '.join(args.item)} / 정의 {sum(map(len, items.values()))}개 / 팩 1.0.{rev}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
