#!/usr/bin/env python3
"""운영 regions.json을 웹 항해 지도 형식으로 변환한다."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent
LIVE = ROOT.parents[2] / "BlockShip"
OUT = ROOT / "assets" / "map-data.js"
TOWNS = {"스폰도시", "사막마을", "상단마을", "왕도"}
OCEANS = {"대양", "원양", "바르칸_연안", "심해_협곡", "따뜻한_바다"}
POIS = {"오아시스", "광산", "카지노", "기억의_연못", "붉은_골짜기", "부두", "은빛_갈매기호"}


def rectangle(points: list[tuple[int, int]], pad: int = 0) -> list[list[int]]:
    xs, zs = zip(*points)
    min_x, max_x = min(xs), max(xs)
    min_z, max_z = min(zs), max(zs)
    if min_x == max_x:
        min_x -= max(6, pad); max_x += max(6, pad)
    if min_z == max_z:
        min_z -= max(6, pad); max_z += max(6, pad)
    return [[min_x - pad, min_z - pad], [max_x + pad, min_z - pad], [max_x + pad, max_z + pad], [min_x - pad, max_z + pad]]


def shape_points(region: dict) -> tuple[list[list[int]], list[list[int]]]:
    polygon = region.get("polygon") or []
    if len(polygon) >= 3:
        return [[int(x), int(z)] for x, z in polygon], [[int(x), int(z)] for x, z in polygon]
    points3d = region.get("points3d") or []
    if points3d:
        projected = [(int(point[0]), int(point[2])) for point in points3d]
        return rectangle(projected, 3), [[x, z] for x, z in projected]
    raw = [region.get("pos1"), region.get("pos2")]
    projected = [(int(point[0]), int(point[2])) for point in raw if isinstance(point, list) and len(point) >= 3]
    return rectangle(projected, 0), [[x, z] for x, z in projected]


def category(identifier: str) -> str:
    if identifier in TOWNS:
        return "town"
    if identifier in OCEANS:
        return "ocean"
    if identifier in POIS or "동굴_" in identifier:
        return "poi"
    return "region"


def build(data_dir: Path) -> dict:
    regions = json.loads((data_dir / "regions.json").read_text(encoding="utf-8"))
    areas = []
    for identifier, region in regions.items():
        if identifier.startswith(("개인섬_", "길드섬_")) or region.get("world", "world") != "world":
            continue
        polygon, anchors = shape_points(region)
        if not polygon:
            continue
        xs = [point[0] for point in polygon]
        zs = [point[1] for point in polygon]
        pos = region.get("pos1") or [sum(xs) // len(xs), 64, sum(zs) // len(zs)]
        areas.append({
            "id": identifier,
            "name": region.get("displayName") or identifier.replace("_", " "),
            "world": region.get("world", "world"), "category": category(identifier),
            "requiredLevel": region.get("requiredLevel", 0), "parent": region.get("parentIsland"),
            "anchor": [int(pos[0]), int(pos[1]), int(pos[2])],
            "bounds": [min(xs), max(xs), min(zs), max(zs)], "polygon": polygon,
            **({"polygonBreaks": region["polygonBreaks"]} if region.get("polygonBreaks") else {}),
        })
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return {"version": f"prod-regions.json · {stamp}", "world": "world", "projection": "Minecraft X/Z → SVG X/Y", "areas": areas}


def load() -> dict:
    text = OUT.read_text(encoding="utf-8")
    return json.loads(text[text.index("{"):text.rindex("}") + 1])


def validate(data_dir: Path) -> list[str]:
    expected = build(data_dir)
    actual = load()
    return ["지도 영역이 운영 regions.json과 다름"] if actual.get("areas") != expected.get("areas") else []


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, default=LIVE, help="regions.json이 있는 운영 BlockShip 데이터 폴더")
    parser.add_argument("--check", action="store_true", help="파일을 쓰지 않고 운영 원본과 대조")
    args = parser.parse_args()
    if args.check:
        errors = validate(args.data)
        if errors:
            print("\n".join(f"ERROR: {error}" for error in errors))
            return 1
        print(f"PASS: 지도 영역 {len(load()['areas'])}개")
        return 0
    payload = build(args.data)
    OUT.write_text("window.BARKAN_MAP_DATA = " + json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + ";\n", encoding="utf-8")
    errors = validate(args.data)
    if errors:
        print("\n".join(f"ERROR: {error}" for error in errors))
        return 1
    print(f"map updated: 지도 영역 {len(payload['areas'])}개")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
