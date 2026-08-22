#!/usr/bin/env python3
"""Remove visited region IDs that are not present in the authoritative regions.json."""

from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 4:
        print(f"usage: {sys.argv[0]} REGIONS_JSON PLAYERDATA_DIR BACKUP_DIR", file=sys.stderr)
        return 2

    regions_path = Path(sys.argv[1])
    playerdata_dir = Path(sys.argv[2])
    backup_dir = Path(sys.argv[3])

    with regions_path.open(encoding="utf-8") as stream:
        regions = json.load(stream)
    valid_ids = set(regions.keys())
    if not valid_ids:
        raise RuntimeError("regions.json contains no region IDs; refusing to modify player data")
    if not playerdata_dir.is_dir():
        raise RuntimeError(f"playerdata directory does not exist: {playerdata_dir}")
    if backup_dir.exists() and any(backup_dir.iterdir()):
        raise RuntimeError(f"backup directory is not empty: {backup_dir}")
    backup_dir.mkdir(parents=True, exist_ok=False)

    changed_files = 0
    removed_count = 0
    for path in sorted(playerdata_dir.glob("*.json")):
        with path.open(encoding="utf-8") as stream:
            data = json.load(stream)
        visited = data.get("visitedRegions")
        if not isinstance(visited, list):
            continue

        cleaned = []
        seen = set()
        removed = []
        for region_id in visited:
            if isinstance(region_id, str) and region_id in valid_ids and region_id not in seen:
                cleaned.append(region_id)
                seen.add(region_id)
            else:
                removed.append(region_id)

        if not removed:
            continue

        shutil.copy2(path, backup_dir / path.name)
        data["visitedRegions"] = cleaned
        temp_path = path.with_name(path.name + ".region-clean.tmp")
        try:
            with temp_path.open("w", encoding="utf-8") as stream:
                json.dump(data, stream, ensure_ascii=False, indent=2)
                stream.write("\n")
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temp_path, path)
        finally:
            if temp_path.exists():
                temp_path.unlink()

        changed_files += 1
        removed_count += len(removed)
        print(f"{path.name}: removed {removed!r}")

    print(f"valid region IDs: {len(valid_ids)}")
    print(f"changed player files: {changed_files}")
    print(f"removed visited region entries: {removed_count}")
    print(f"backup: {backup_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
