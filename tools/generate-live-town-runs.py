#!/usr/bin/env python3
"""Export town blocks from the running Paper world and build runs8 payloads.

The Anvil files on disk are not guaranteed to contain the current in-memory
world (unsaved edits, displays and live chunk state can differ), so the map
must be generated from AIBuilder's running-world structure export endpoint.
The endpoint is intentionally requested in small 48x48 tiles to keep each
response below the bridge's safe size limit.
"""

from __future__ import annotations

import argparse
import base64
import concurrent.futures
import gzip
import io
import json
import struct
import time
import urllib.request
from pathlib import Path

from nbtlib import File


ROOT = Path(__file__).resolve().parents[1]
MAP_DATA = ROOT / "website" / "assets" / "map-data.js"
OUT = ROOT / "website" / "assets"
BRIDGE = "http://127.0.0.1:25599/structure_export"
TILE = 48
Y_MIN, Y_MAX = 60, 255
SURFACE_FLOOR = 60
SLUGS = {
    "사막마을": "desert-town",
    "스폰도시": "spawn-city",
    "상단마을": "upper-town",
    "왕도": "royal-city",
    "항구": "harbor",
}


def read_map_data():
    source = MAP_DATA.read_text()
    start = source.index("{")
    end = source.rindex("}") + 1
    return json.loads(source[start:end])


def post_export(world: str, x1: int, z1: int, x2: int, z2: int):
    body = json.dumps({"world": world, "x1": x1, "y1": Y_MIN, "z1": z1, "x2": x2, "y2": Y_MAX, "z2": z2}).encode()
    for attempt in range(5):
        try:
            request = urllib.request.Request(BRIDGE, data=body, headers={"content-type": "application/json"}, method="POST")
            with urllib.request.urlopen(request, timeout=180) as response:
                result = json.load(response)
            if not result.get("ok"):
                raise RuntimeError(result)
            return result
        except Exception:
            if attempt == 4:
                raise
            time.sleep(2.0 * (attempt + 1))


def add_export(result, x1: int, z1: int, columns: dict[tuple[int, int], dict[int, str]], legend: list[str], legend_index: dict[str, int]):
    raw = gzip.decompress(base64.b64decode(result["nbt_base64"]))
    root = File.parse(io.BytesIO(raw))
    size_x, size_y, size_z = (int(v) for v in root["size"])
    palette = [str(item["Name"]) for item in root["palette"]]
    for block in root["blocks"]:
        state = int(block["state"])
        material = palette[state] if 0 <= state < len(palette) else "minecraft:air"
        if material in {"minecraft:air", "minecraft:cave_air", "minecraft:void_air"}:
            continue
        pos = block["pos"]
        local_x, local_y, local_z = (int(v) for v in pos)
        if not (0 <= local_x < size_x and 0 <= local_y < size_y and 0 <= local_z < size_z):
            continue
        key = (x1 + local_x, z1 + local_z)
        columns.setdefault(key, {})[Y_MIN + local_y] = material
        if material not in legend_index:
            legend_index[material] = len(legend)
            legend.append(material)


def encode_payload(area, world: str, cache_dir: Path):
    x1, x2, z1, z2 = (int(value) for value in area["bounds"])
    columns: dict[tuple[int, int], dict[int, str]] = {}
    legend: list[str] = []
    legend_index: dict[str, int] = {}
    total_tiles = ((x2 - x1) // TILE + 1) * ((z2 - z1) // TILE + 1)
    tiles = []
    for tile_z in range(z1, z2 + 1, TILE):
        for tile_x in range(x1, x2 + 1, TILE):
            tiles.append((tile_x, tile_z, min(tile_x + TILE - 1, x2), min(tile_z + TILE - 1, z2)))
    # The bridge spends most of its time serialising/compressing the response;
    # a small pool keeps a full town scan practical without flooding Paper.
    cache_dir.mkdir(parents=True, exist_ok=True)
    pending = []
    for tile_x, tile_z, ex, ez in tiles:
        cache = cache_dir / f"{world}-{tile_x}-{tile_z}-{ex}-{ez}.json"
        if cache.exists():
            result = json.loads(cache.read_text())
            add_export(result, tile_x, tile_z, columns, legend, legend_index)
            print(f"  {area['id']}: cached ({tile_x},{tile_z})", flush=True)
        else:
            pending.append((tile_x, tile_z, ex, ez, cache))
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        futures = {pool.submit(post_export, world, tx, tz, ex, ez): (tx, tz, cache) for tx, tz, ex, ez, cache in pending}
        for tile_no, future in enumerate(concurrent.futures.as_completed(futures), 1):
            tile_x, tile_z, cache = futures[future]
            result = future.result()
            cache.write_text(json.dumps(result, separators=(",", ":")))
            add_export(result, tile_x, tile_z, columns, legend, legend_index)
            print(f"  {area['id']}: fetched {tile_no}/{len(pending)} ({tile_x},{tile_z}) blocks={len(result.get('nbt_base64', ''))}", flush=True)

    runs: list[tuple[int, int, int, int, int]] = []
    column_runs: list[tuple[int, int, int, int, int, int]] = []
    for (x, z), values in columns.items():
        top = max(values)
        bottom = min(values)
        # This is a visual scan of the real block columns. The lower bound is
        # still recorded only at the visible floor so buried chunks never make
        # the isometric side walls look like floating ruins.
        visible_bottom = max(bottom, SURFACE_FLOOR)
        side_material = values.get(visible_bottom)
        if side_material is None:
            above = [y for y in values if y >= visible_bottom]
            side_material = values[min(above)] if above else values[top]
        column_runs.append((x - x1, z - z1, visible_bottom, top, legend_index[values[top]], legend_index[side_material]))
        y = bottom
        while y <= top:
            material = values.get(y)
            if material is None:
                y += 1
                continue
            end = y + 1
            while end <= top and values.get(end) == material and end - y < 255:
                end += 1
            runs.append((x - x1, z - z1, y - Y_MIN, end - y, legend_index[material]))
            y = end

    run_bytes = bytearray(len(runs) * 8)
    for index, (x, z, y, length, material) in enumerate(runs):
        struct.pack_into(">HHBBH", run_bytes, index * 8, x, z, y, length, material)
    column_bytes = bytearray(len(column_runs) * 10)
    for index, (x, z, bottom, top, top_material, side_material) in enumerate(column_runs):
        struct.pack_into(">HHBBHH", column_bytes, index * 10, x, z, bottom - Y_MIN, top - bottom + 1, top_material, side_material)

    return {
        "region": {"id": f"{SLUGS[area['id']]}-scan", "x1": x1, "x2": x2, "z1": z1, "z2": z2},
        "format": "runs8",
        "xOrigin": x1,
        "zOrigin": z1,
        "yOrigin": Y_MIN,
        "width": x2 - x1 + 1,
        "depth": z2 - z1 + 1,
        "legend": legend,
        "count": len(runs),
        "details": base64.b64encode(run_bytes).decode("ascii"),
        "columnCount": len(column_runs),
        "columnStride": 10,
        "surfaceFloor": SURFACE_FLOOR,
        "columns": base64.b64encode(column_bytes).decode("ascii"),
        "scannedAt": "2026-08-21T00:00:00+09:00",
        "note": "실행 중 Paper 월드의 AIBuilder structure_export 전체 블록 스캔; 공기 블록 제외, 비공기 구간만 압축 저장",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--world", default="world")
    parser.add_argument("--town", action="append", choices=sorted(SLUGS), help="only scan this town; repeatable")
    parser.add_argument("--cache-dir", type=Path, default=Path("/tmp/barkan-live-export-cache"))
    args = parser.parse_args()
    towns = [area for area in read_map_data()["areas"] if area.get("id") in SLUGS and (not args.town or area["id"] in args.town)]
    for area in towns:
        print(f"{area['id']}: exporting live blocks from {args.world}", flush=True)
        payload = encode_payload(area, args.world, args.cache_dir)
        target = OUT / f"town-detail-{SLUGS[area['id']]}.json"
        target.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
        print(f"{area['id']}: columns={payload['columnCount']} runs={payload['count']} legend={len(payload['legend'])} bytes={target.stat().st_size}", flush=True)


if __name__ == "__main__":
    main()
