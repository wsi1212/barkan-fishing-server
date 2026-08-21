#!/usr/bin/env python3
"""Build streamable, block-accurate map tiles from the live Paper world.

The public map is static, so the browser cannot call AIBuilder directly.  This
job is the bridge between the running world and ``website/assets/map-tiles``:
each 256x256 world-block tile is exported in 48x48 sub-requests, compressed
into the same runs8 payload used by the town detail maps, and indexed in a
small manifest.  Tile jobs are independent and may be run in parallel without
holding the whole island in memory.

Examples:
  python3 tools/generate-live-map-tiles.py --tiles 0,2 256,2 --workers 2
  python3 tools/generate-live-map-tiles.py --priority --workers 2
  python3 tools/generate-live-map-tiles.py --all --workers 2
"""

from __future__ import annotations

import argparse
import base64
import concurrent.futures
import gzip
import io
import json
import math
import struct
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from nbtlib import File


ROOT = Path(__file__).resolve().parents[1]
MAP_DATA = ROOT / "website" / "assets" / "map-data.js"
OUT = ROOT / "website" / "assets" / "map-tiles"
CACHE = Path("/tmp/barkan-live-map-tile-cache")
BRIDGE = "http://127.0.0.1:25599/structure_export"
TILE_SIZE = 256
SUBTILE = 48
Y_MIN, Y_MAX = 60, 255
SURFACE_FLOOR = 60
HIDDEN_BLOCKS = {"minecraft:light", "minecraft:barrier"}
AIR_BLOCKS = {"minecraft:air", "minecraft:cave_air", "minecraft:void_air"}


def read_map_data() -> dict:
    source = MAP_DATA.read_text()
    start = source.index("{")
    end = source.rindex("}") + 1
    return json.loads(source[start:end])


def island_bounds(data: dict) -> tuple[int, int, int, int]:
    island = next(area for area in data["areas"] if area.get("id") == "바르칸")
    x1, x2, z1, z2 = (int(value) for value in island["bounds"])
    return x1, x2, z1, z2


def tile_origin(value: int) -> int:
    return math.floor(value / TILE_SIZE) * TILE_SIZE


def tile_bounds(tx: int, tz: int, bounds: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
    island_x1, island_x2, island_z1, island_z2 = bounds
    x1 = max(tx, island_x1)
    x2 = min(tx + TILE_SIZE - 1, island_x2)
    z1 = max(tz, island_z1)
    z2 = min(tz + TILE_SIZE - 1, island_z2)
    return x1, x2, z1, z2


def post_export(world: str, x1: int, z1: int, x2: int, z2: int) -> dict:
    body = json.dumps({
        "world": world,
        "x1": x1,
        "y1": Y_MIN,
        "z1": z1,
        "x2": x2,
        "y2": Y_MAX,
        "z2": z2,
    }).encode()
    for attempt in range(6):
        try:
            request = urllib.request.Request(
                BRIDGE,
                data=body,
                headers={"content-type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(request, timeout=240) as response:
                result = json.load(response)
            if not result.get("ok"):
                raise RuntimeError(result)
            return result
        except Exception:
            if attempt == 5:
                raise
            time.sleep(2.0 * (attempt + 1))


def add_export(
    result: dict,
    x1: int,
    z1: int,
    columns: dict[tuple[int, int], dict[int, str]],
    legend: list[str],
    legend_index: dict[str, int],
) -> None:
    raw = gzip.decompress(base64.b64decode(result["nbt_base64"]))
    root = File.parse(io.BytesIO(raw))
    size_x, size_y, size_z = (int(value) for value in root["size"])
    palette = [str(item["Name"]) for item in root["palette"]]
    for block in root["blocks"]:
        state = int(block["state"])
        material = palette[state] if 0 <= state < len(palette) else "minecraft:air"
        if material in AIR_BLOCKS or material in HIDDEN_BLOCKS:
            continue
        local_x, local_y, local_z = (int(value) for value in block["pos"])
        if not (0 <= local_x < size_x and 0 <= local_y < size_y and 0 <= local_z < size_z):
            continue
        key = (x1 + local_x, z1 + local_z)
        columns.setdefault(key, {})[Y_MIN + local_y] = material
        if material not in legend_index:
            legend_index[material] = len(legend)
            legend.append(material)


def encode_tile(tile: tuple[int, int], bounds: tuple[int, int, int, int], world: str, cache_dir: Path, request_workers: int) -> dict:
    tx, tz = tile
    x1, x2, z1, z2 = tile_bounds(tx, tz, bounds)
    if x1 > x2 or z1 > z2:
        raise ValueError(f"tile outside island: {tile}")

    subtile_jobs: list[tuple[int, int, int, int, Path]] = []
    cache_dir.mkdir(parents=True, exist_ok=True)
    for sz in range(z1, z2 + 1, SUBTILE):
        for sx in range(x1, x2 + 1, SUBTILE):
            ex = min(sx + SUBTILE - 1, x2)
            ez = min(sz + SUBTILE - 1, z2)
            cache = cache_dir / f"{world}-{sx}-{sz}-{ex}-{ez}.json"
            subtile_jobs.append((sx, sz, ex, ez, cache))

    columns: dict[tuple[int, int], dict[int, str]] = {}
    legend: list[str] = []
    legend_index: dict[str, int] = {}
    pending: list[tuple[int, int, int, int, Path]] = []
    cached = 0
    for sx, sz, ex, ez, cache in subtile_jobs:
        if cache.exists():
            try:
                add_export(json.loads(cache.read_text()), sx, sz, columns, legend, legend_index)
                cached += 1
                continue
            except Exception:
                cache.unlink(missing_ok=True)
        pending.append((sx, sz, ex, ez, cache))

    with concurrent.futures.ThreadPoolExecutor(max_workers=request_workers) as pool:
        futures = {
            pool.submit(post_export, world, sx, sz, ex, ez): (sx, sz, ex, ez, cache)
            for sx, sz, ex, ez, cache in pending
        }
        for index, future in enumerate(concurrent.futures.as_completed(futures), 1):
            sx, sz, _ex, _ez, cache = futures[future]
            result = future.result()
            cache.write_text(json.dumps(result, separators=(",", ":")))
            add_export(result, sx, sz, columns, legend, legend_index)
            print(f"tile {tx},{tz}: {index}/{len(pending)} subtiles fetched", flush=True)

    runs: list[tuple[int, int, int, int, int]] = []
    column_runs: list[tuple[int, int, int, int, int, int]] = []
    for (x, z), values in columns.items():
        top = max(values)
        bottom = min(values)
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

    scanned_at = datetime.now(timezone.utc).isoformat()
    return {
        "region": {"id": f"map-tile-{tx}-{tz}", "x1": x1, "x2": x2, "z1": z1, "z2": z2},
        "format": "runs8",
        "tileSize": TILE_SIZE,
        "tileX": tx,
        "tileZ": tz,
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
        "scannedAt": scanned_at,
        "source": "live Paper world via AIBuilder structure_export",
        "subtiles": len(subtile_jobs),
        "cachedSubtiles": cached,
    }


def parse_tile(value: str) -> tuple[int, int]:
    try:
        x, z = (int(part.strip()) for part in value.split(",", 1))
        return tile_origin(x), tile_origin(z)
    except Exception as exc:
        raise argparse.ArgumentTypeError("tile must be X,Z (world coordinates)") from exc


def all_tiles(bounds: tuple[int, int, int, int]) -> list[tuple[int, int]]:
    x1, x2, z1, z2 = bounds
    return [
        (tx, tz)
        for tz in range(tile_origin(z1), tile_origin(z2) + 1, TILE_SIZE)
        for tx in range(tile_origin(x1), tile_origin(x2) + 1, TILE_SIZE)
    ]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--world", default="world")
    parser.add_argument("--tiles", nargs="+", type=parse_tile, help="tile origins as X,Z; repeatable")
    parser.add_argument("--priority", action="store_true", help="scan the four tiles around spawn city first")
    parser.add_argument("--all", action="store_true", help="queue every tile covering the island")
    parser.add_argument("--workers", type=int, default=2, help="parallel tile jobs (default: 2)")
    parser.add_argument("--request-workers", type=int, default=3, help="parallel 48x48 bridge requests per tile")
    parser.add_argument("--cache-dir", type=Path, default=CACHE)
    args = parser.parse_args()
    data = read_map_data()
    bounds = island_bounds(data)

    selected: list[tuple[int, int]] = []
    if args.tiles:
        selected.extend(args.tiles)
    if args.priority:
        # Spawn city is x=231..587, z=701..1147: four 256-block tiles cover
        # the city and its harbour edge while keeping the first batch small.
        selected.extend([(0, 512), (256, 512), (0, 768), (256, 768)])
    if args.all:
        selected.extend(all_tiles(bounds))
    if not selected:
        parser.error("choose --tiles, --priority, or --all")
    selected = list(dict.fromkeys(selected))

    OUT.mkdir(parents=True, exist_ok=True)
    print(f"queue: {len(selected)} tile(s), workers={args.workers}, requests/tile={args.request_workers}", flush=True)
    records: list[dict] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        futures = {
            pool.submit(encode_tile, tile, bounds, args.world, args.cache_dir, max(1, args.request_workers)): tile
            for tile in selected
        }
        for number, future in enumerate(concurrent.futures.as_completed(futures), 1):
            tx, tz = futures[future]
            payload = future.result()
            target = OUT / f"tile-x{tx}-z{tz}.json"
            target.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
            records.append({
                # The renderer addresses tiles by grid index. Keep the
                # world-space origin alongside it so a manifest remains
                # unambiguous for negative coordinates too.
                "tx": tx // TILE_SIZE,
                "tz": tz // TILE_SIZE,
                "xOrigin": tx,
                "zOrigin": tz,
                "x1": payload["region"]["x1"],
                "x2": payload["region"]["x2"],
                "z1": payload["region"]["z1"],
                "z2": payload["region"]["z2"],
                "url": f"/assets/map-tiles/{target.name}",
                "count": payload["count"],
                "columnCount": payload["columnCount"],
                "bytes": target.stat().st_size,
                "scannedAt": payload["scannedAt"],
            })
            print(f"done {number}/{len(selected)} tile {tx},{tz}: columns={payload['columnCount']} runs={payload['count']} bytes={target.stat().st_size}", flush=True)

    manifest_path = OUT / "index.json"
    existing: dict = {}
    if manifest_path.exists():
        try:
            existing = json.loads(manifest_path.read_text())
        except json.JSONDecodeError:
            existing = {}
    def record_key(item: dict) -> tuple[int, int]:
        tx = item.get("tx", item.get("tileX"))
        tz = item.get("tz", item.get("tileZ"))
        # Migrate the first experimental manifest, which stored world-space
        # origins in tileX/tileZ instead of grid indices.
        if "tx" not in item and abs(int(tx)) >= TILE_SIZE:
            tx = int(tx) // TILE_SIZE
        if "tz" not in item and abs(int(tz)) >= TILE_SIZE:
            tz = int(tz) // TILE_SIZE
        return int(tx), int(tz)

    by_key = {record_key(item): item for item in existing.get("tiles", [])}
    by_key.update({record_key(item): item for item in records})
    manifest = {
        "version": "map-tiles.v1",
        "world": args.world,
        "tileSize": TILE_SIZE,
        "yMin": Y_MIN,
        "yMax": Y_MAX,
        "bounds": {"x1": bounds[0], "x2": bounds[1], "z1": bounds[2], "z2": bounds[3]},
        "tiles": sorted(by_key.values(), key=lambda item: record_key(item)[::-1]),
        "updatedAt": datetime.now(timezone.utc).isoformat(),
        "source": "live Paper world via AIBuilder structure_export",
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, separators=(",", ":")))
    print(f"manifest: {manifest_path} ({len(manifest['tiles'])} ready tile(s))", flush=True)


if __name__ == "__main__":
    main()
