#!/usr/bin/env python3
"""Paper Anvil 월드를 웹 3D 지도 지형 스냅샷으로 변환한다.

기본 동작은 동기화된 로컬 월드의 Anvil 파일을 직접 읽는다. AIBuilder의
region_topdown은 큰 지역을 Paper 메인 스레드에서 처리하므로 고해상도 요청이 서버
워치독을 건드릴 수 있다. 호환성 확인 외에는 --bridge를 사용하지 않는다.
"""
from __future__ import annotations

import argparse
import base64
import gzip
import io
import json
import math
import struct
import urllib.request
import zlib
from functools import lru_cache
from datetime import datetime, timezone
from pathlib import Path

from nbtlib import File


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "website" / "assets" / "terrain-data.js"
SERVER_ROOT = ROOT.parents[2]
DEFAULT_WORLD = SERVER_ROOT / "world"
DEFAULT_REGIONS = SERVER_ROOT / "plugins" / "BlockShip" / "regions.json"
AIR = {"minecraft:air", "minecraft:cave_air", "minecraft:void_air"}
MIN_Y = -64


def flatten(rows: list[list[int]], width: int, depth: int, label: str) -> list[int]:
    if len(rows) != depth or any(len(row) != width for row in rows):
        raise ValueError(f"{label} 크기가 {width}x{depth}와 일치하지 않습니다")
    return [int(value) for row in rows for value in row]


def fetch_snapshot(bridge: str, region: str, max_resolution: int) -> dict:
    body = json.dumps({"region": region, "max_resolution": max_resolution}).encode()
    request = urllib.request.Request(
        bridge.rstrip("/") + "/region_topdown",
        data=body,
        headers={"content-type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=300) as response:
        return json.load(response)


def point_in_polygon(x: int, z: int, polygon: list[list[int]]) -> bool:
    inside = False
    j = len(polygon) - 1
    for i, (xi, zi, *_) in enumerate(polygon):
        xj, zj = polygon[j][:2]
        if (zi > z) != (zj > z) and x < (xj - xi) * (z - zi) / ((zj - zi) or 1e-9) + xi:
            inside = not inside
        j = i
    return inside


class AnvilSurface:
    def __init__(self, world: Path):
        self.region_dir = world / "region"

    @lru_cache(maxsize=32768)
    def chunk(self, chunk_x: int, chunk_z: int):
        region_path = self.region_dir / f"r.{chunk_x // 32}.{chunk_z // 32}.mca"
        if not region_path.exists():
            return None
        local_index = (chunk_z % 32) * 32 + (chunk_x % 32)
        with region_path.open("rb") as handle:
            handle.seek(local_index * 4)
            location = handle.read(4)
            if len(location) != 4:
                return None
            sector = int.from_bytes(location[:3], "big")
            if sector == 0:
                return None
            handle.seek(sector * 4096)
            length = int.from_bytes(handle.read(4), "big")
            compression = handle.read(1)[0]
            compressed = handle.read(length - 1)
        if compression == 2:
            raw = zlib.decompress(compressed)
        elif compression == 1:
            raw = gzip.decompress(compressed)
        elif compression == 3:
            raw = compressed
        else:
            raise ValueError(f"지원하지 않는 Anvil 압축 형식: {compression}")
        return File.parse(io.BytesIO(raw))

    @staticmethod
    def packed_value(values, index: int, bits: int) -> int:
        values_per_long = 64 // bits
        word = int(values[index // values_per_long]) & ((1 << 64) - 1)
        return (word >> ((index % values_per_long) * bits)) & ((1 << bits) - 1)

    def top(self, x: int, z: int) -> tuple[str, int]:
        root = self.chunk(x // 16, z // 16)
        if root is None:
            return "minecraft:air", -1
        heightmaps = root.get("Heightmaps")
        if not heightmaps or "WORLD_SURFACE" not in heightmaps:
            return "minecraft:air", -1
        local_x, local_z = x % 16, z % 16
        column_index = local_z * 16 + local_x
        y = MIN_Y + self.packed_value(heightmaps["WORLD_SURFACE"], column_index, 9) - 1
        section = next((value for value in root["sections"] if int(value["Y"]) == y // 16), None)
        if section is None or "block_states" not in section:
            return "minecraft:air", y
        states = section["block_states"]
        palette = [str(value["Name"]) for value in states["palette"]]
        data = states.get("data", [])
        # nbtlib's LongArray has NumPy-style truthiness: a non-empty array whose
        # first packed word is zero can evaluate as false. Check its length so
        # multi-entry palettes are still decoded instead of falling back to air.
        if len(palette) == 1 or len(data) == 0:
            material = palette[0]
        else:
            bits = max(4, math.ceil(math.log2(len(palette))))
            block_index = ((y % 16) * 16 + local_z) * 16 + local_x
            palette_index = self.packed_value(data, block_index, bits)
            material = palette[palette_index] if palette_index < len(palette) else palette[0]
        return ("minecraft:air" if material in AIR else material), y


def scan_anvil(world: Path, regions_path: Path, region_id: str, max_resolution: int) -> dict:
    regions = json.loads(regions_path.read_text(encoding="utf-8"))
    region = regions.get(region_id)
    if not region:
        raise ValueError(f"regions.json에 없는 지역입니다: {region_id}")
    polygon = region.get("polygon") or []
    if len(polygon) < 3:
        raise ValueError(f"다각형 지역만 오프라인 스캔할 수 있습니다: {region_id}")
    xs = [int(point[0]) for point in polygon]
    zs = [int(point[1]) for point in polygon]
    x_min, x_max, z_min, z_max = min(xs), max(xs), min(zs), max(zs)
    region_width, region_depth = x_max - x_min + 1, z_max - z_min + 1
    cell_size = max(1, math.ceil(max(region_width, region_depth) / max_resolution))
    grid_width = math.ceil(region_width / cell_size)
    grid_depth = math.ceil(region_depth / cell_size)
    legend = ["minecraft:air"]
    legend_index = {legend[0]: 0}
    grid: list[list[int]] = []
    heights: list[list[int]] = []
    mask: list[list[int]] = []
    surface = AnvilSurface(world)

    for grid_z in range(grid_depth):
        material_row: list[int] = []
        height_row: list[int] = []
        mask_row: list[int] = []
        world_z = min(z_max, z_min + grid_z * cell_size + cell_size // 2)
        for grid_x in range(grid_width):
            world_x = min(x_max, x_min + grid_x * cell_size + cell_size // 2)
            inside = point_in_polygon(world_x, world_z, polygon)
            mask_row.append(1 if inside else 0)
            if not inside:
                material_row.append(0)
                height_row.append(-1)
                continue
            material, y = surface.top(world_x, world_z)
            if material not in legend_index:
                legend_index[material] = len(legend)
                legend.append(material)
            material_row.append(legend_index[material])
            height_row.append(y)
        grid.append(material_row)
        heights.append(height_row)
        mask.append(mask_row)
        if (grid_z + 1) % 32 == 0 or grid_z + 1 == grid_depth:
            print(f"terrain rows: {grid_z + 1}/{grid_depth}", flush=True)

    return {
        "region_id": region_id,
        "display_name": region.get("displayName") or region_id,
        "world": region.get("world", "world"),
        "shape": "polygon",
        "x_origin": x_min,
        "z_origin": z_min,
        "region_width": region_width,
        "region_depth": region_depth,
        "cell_size": cell_size,
        "grid_width": grid_width,
        "grid_depth": grid_depth,
        "legend": legend,
        "grid": grid,
        "heights": heights,
        "in_region_mask": mask,
    }


def encode_snapshot(raw: dict, source: str, max_resolution: int) -> dict:
    width = int(raw["grid_width"])
    depth = int(raw["grid_depth"])
    materials = flatten(raw["grid"], width, depth, "grid")
    heights = flatten(raw["heights"], width, depth, "heights")
    mask = flatten(raw["in_region_mask"], width, depth, "in_region_mask")
    legend = [str(value) for value in raw["legend"]]

    if len(legend) > 256 or any(value < 0 or value >= len(legend) or value > 255 for value in materials):
        raise ValueError("재료 범례가 웹 지도의 uint8 인코딩 범위를 벗어났습니다")
    if any(value not in (0, 1) for value in mask):
        raise ValueError("영역 마스크에는 0과 1만 있어야 합니다")
    shifted_heights = [value + 128 for value in heights]
    if any(value < 0 or value > 65535 for value in shifted_heights):
        raise ValueError("높이가 웹 지도의 uint16 인코딩 범위를 벗어났습니다")

    height_bytes = bytearray(len(shifted_heights) * 2)
    for index, value in enumerate(shifted_heights):
        struct.pack_into("<H", height_bytes, index * 2, value)

    return {
        "version": "prod-terrain-snapshot.v1",
        "scannedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": f"{source} (max_resolution={max_resolution})",
        "region": raw.get("region_id"),
        "world": raw.get("world"),
        "xOrigin": int(raw["x_origin"]),
        "zOrigin": int(raw["z_origin"]),
        "cellSize": int(raw["cell_size"]),
        "gridWidth": width,
        "gridDepth": depth,
        "legend": legend,
        "materials": base64.b64encode(bytes(materials)).decode("ascii"),
        "heights": base64.b64encode(height_bytes).decode("ascii"),
        "mask": base64.b64encode(bytes(mask)).decode("ascii"),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bridge", help="호환용 AIBuilder HTTP 브리지; 생략하면 Anvil 파일을 직접 읽음")
    parser.add_argument("--world-path", type=Path, default=DEFAULT_WORLD)
    parser.add_argument("--regions", type=Path, default=DEFAULT_REGIONS)
    parser.add_argument("--region", default="바르칸")
    parser.add_argument("--max-resolution", type=int, default=350, help="기존 공개 지도와 같은 약 8블록 해상도")
    parser.add_argument("--output", type=Path, default=OUT)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if args.bridge:
        raw = fetch_snapshot(args.bridge, args.region, args.max_resolution)
        source = f"AIBuilder region_topdown {args.bridge.rstrip('/')}"
    else:
        raw = scan_anvil(args.world_path, args.regions, args.region, args.max_resolution)
        source = f"Paper Anvil snapshot {args.world_path}"
    payload = encode_snapshot(raw, source, args.max_resolution)
    encoded = (
        f"/* AIBuilder region_topdown snapshot: {args.region}, max_resolution={args.max_resolution} */\n"
        "window.BARKAN_TERRAIN_DATA = "
        + json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        + ";\n"
    )
    print(
        f"terrain scanned: {payload['gridWidth']}x{payload['gridDepth']}, "
        f"cell={payload['cellSize']}, legend={len(payload['legend'])}, bytes={len(encoded.encode())}"
    )
    if not args.dry_run:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        temporary = args.output.with_suffix(args.output.suffix + ".tmp")
        temporary.write_text(encoded, encoding="utf-8")
        temporary.replace(args.output)
        print(f"terrain updated: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
