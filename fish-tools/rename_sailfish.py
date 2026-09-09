#!/usr/bin/env python3
"""Merge the erroneous '돗새치' spelling into the canonical '돛새치'.

The data previously defined both spellings as separate fish.  The former is the
one wired to the custom texture, so its specification wins; references to the
second entry are retained, but de-duplicated within every catch pool and quest
fish-list.  Run with --write only after reviewing the dry-run output.
"""

from __future__ import annotations

import argparse
import json
from collections import OrderedDict
from pathlib import Path
from typing import Any


ROOT = Path("/Users/user/Library/Application Support/feather/player-server/servers/07de2d81-991a-47e2-b62d-06c0d1b5150a/plugins/Skript/scripts")
TARGETS = {
    "fish.json": (
        Path("/Users/user/development/blockship-plugin/fish.json"),
        ROOT / "ops/blockship-data/fish.json",
        ROOT.parent.parent / "BlockShip/fish.json",
    ),
    "item-flavor.json": (
        Path("/Users/user/development/blockship-plugin/item-flavor.json"),
        ROOT / "ops/blockship-data/item-flavor.json",
        ROOT.parent.parent / "BlockShip/item-flavor.json",
    ),
    "quests.json": (
        Path("/Users/user/development/blockship-plugin/quests.json"),
        ROOT / "ops/blockship-data/quests.json",
        ROOT.parent.parent / "BlockShip/quests.json",
    ),
}
OLD = "돗새치"
NEW = "돛새치"


def rename_string(value: str) -> str:
    value = value.replace(OLD, NEW)
    # Quest reward lists are semicolon-delimited name=size pairs.  Merge the
    # spelling collision while retaining the first (previously textured) value.
    if f"{NEW}=" not in value or ";" not in value:
        return value
    fields = value.split(";")
    seen: set[str] = set()
    cleaned: list[str] = []
    for field in fields:
        name = field.split("=", 1)[0]
        if name == NEW and name in seen:
            continue
        if name == NEW:
            seen.add(name)
        cleaned.append(field)
    return ";".join(cleaned)


def transform(value: Any) -> Any:
    if isinstance(value, str):
        return rename_string(value)
    if isinstance(value, list):
        converted = [transform(item) for item in value]
        # Catch pools are lists of names.  Preserve ordering while merging the
        # typo and canonical spelling into a single roll candidate.
        seen_sailfish = False
        result = []
        for item in converted:
            if item == NEW:
                if seen_sailfish:
                    continue
                seen_sailfish = True
            result.append(item)
        return result
    if isinstance(value, dict):
        return OrderedDict((rename_string(str(key)), transform(item)) for key, item in value.items())
    return value


def transform_fish(data: OrderedDict[str, Any]) -> OrderedDict[str, Any]:
    fish = data["fish"]
    if OLD not in fish:
        if NEW not in fish:
            raise ValueError("fish.json contains neither sailfish spelling")
        # The migration already ran.  Keeping this path idempotent makes the
        # command suitable for validation in CI and repeated local runs.
        return transform(data)
    merged = OrderedDict()
    for name, spec in fish.items():
        if name == OLD:
            merged[NEW] = transform(spec)
        elif name == NEW:
            # The duplicate, untextured definition loses to the typo's live
            # definition, keeping the existing fish's balance and model link.
            continue
        else:
            merged[name] = transform(spec)
    data = transform(data)
    data["fish"] = merged
    return data


def load(path: Path) -> OrderedDict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=OrderedDict)


def write(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def validate(fish: OrderedDict[str, Any], flavor: OrderedDict[str, Any], quests: OrderedDict[str, Any]) -> None:
    assert OLD not in json.dumps(fish, ensure_ascii=False)
    assert OLD not in json.dumps(flavor, ensure_ascii=False)
    assert OLD not in json.dumps(quests, ensure_ascii=False)
    assert list(fish["fish"]).count(NEW) == 1
    assert NEW in flavor["물고기"]
    for region in fish["regions"].values():
        for pool in region.values():
            assert pool.count(NEW) <= 1


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true", help="apply changes instead of only validating")
    args = parser.parse_args()
    migrated_by_file: dict[str, list[OrderedDict[str, Any]]] = {}
    for filename, paths in TARGETS.items():
        migrated_by_file[filename] = []
        for path in paths:
            data = load(path)
            migrated = transform_fish(data) if filename == "fish.json" else transform(data)
            migrated_by_file[filename].append(migrated)
            if args.write:
                write(path, migrated)
            print(f"{'updated' if args.write else 'checked'} {path}")
    for index in range(len(TARGETS["fish.json"])):
        validate(
            migrated_by_file["fish.json"][index],
            migrated_by_file["item-flavor.json"][index],
            migrated_by_file["quests.json"][index],
        )
    print("✓ 돗새치 → 돛새치 migration is internally consistent")


if __name__ == "__main__":
    main()
