#!/usr/bin/env python3
"""BlockShip fish/runtime ↔ Java model ↔ resourcepack 전수조사 매니페스트."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


def strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, list):
        for item in value:
            yield from strings(item)
    elif isinstance(value, dict):
        for item in value.values():
            yield from strings(item)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fish-json", type=Path, required=True)
    ap.add_argument("--registry", type=Path, required=True)
    ap.add_argument("--resourcepack", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    data = json.loads(args.fish_json.read_text(encoding="utf-8"))
    fish = data["fish"]
    regions = {name: set(strings(value)) for name, value in data["regions"].items()}
    environments = {name: set(strings(value)) for name, value in data["environment"].items()}
    assigned = set().union(*regions.values(), *environments.values())
    registry = dict(re.findall(r'm\.put\("([^"]+)"\s*,\s*"([^"]+)"\)', args.registry.read_text(encoding="utf-8")))
    fish_dir = args.resourcepack / "assets/minecraft/textures/item/fish"
    model_dir = args.resourcepack / "assets/minecraft/models/item/fish"

    entries = []
    for name in sorted(fish):
        value = fish[name]
        mid = registry.get(name, "")
        entries.append({
            "name": name,
            "model_id": mid,
            "regions": sorted(region for region, names in regions.items() if name in names),
            "environments": sorted(env for env, names in environments.items() if name in names),
            "quest": value.get("quest") if isinstance(value, dict) else None,
            "has_java_mapping": bool(mid),
            "has_model": bool(mid) and (model_dir / f"{mid}.json").is_file(),
            "has_texture": bool(mid) and (fish_dir / f"{mid}.png").is_file(),
        })

    result = {
        "generated_from": {
            "fish_json": str(args.fish_json),
            "registry": str(args.registry),
            "resourcepack": str(args.resourcepack),
        },
        "summary": {
            "fish_definitions": len(fish),
            "region_definitions": len(regions),
            "environment_pools": len(environments),
            "assigned_fish": len(assigned),
            "orphan_fish": len(set(fish) - assigned),
            "java_registry_entries": len(registry),
            "runtime_without_java_mapping": sum(not row["has_java_mapping"] for row in entries),
            "runtime_with_complete_pack_chain": sum(row["has_java_mapping"] and row["has_model"] and row["has_texture"] for row in entries),
        },
        "environment": {name: sorted(names) for name, names in environments.items()},
        "missing_java_mapping": [row for row in entries if not row["has_java_mapping"]],
        "entries": entries,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result["summary"], ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
