#!/usr/bin/env python3
"""Build full voxel run payloads from the local Paper Anvil world.

Unlike mc_topdown_map this walks every block in Y=0..255 and preserves air
gaps by writing contiguous non-air runs per (x,z) column.
"""

from __future__ import annotations

import base64
import gzip
import io
import json
import math
import struct
import zlib
from pathlib import Path

from nbtlib import File


ROOT = Path(__file__).resolve().parents[1]
WORLD = ROOT.parent.parent.parent / "world"
MAP_DATA = ROOT / "website" / "assets" / "map-data.js"
OUT = ROOT / "website" / "assets"
Y_MIN, Y_MAX = 0, 255
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


def read_chunk(region_path: Path, local_index: int):
    if not region_path.exists():
        return None
    with region_path.open("rb") as fh:
        header = fh.read(8192)
        offset = int.from_bytes(header[local_index * 4 : local_index * 4 + 3], "big")
        if offset == 0:
            return None
        fh.seek(offset * 4096)
        length = int.from_bytes(fh.read(4), "big")
        compression = fh.read(1)[0]
        compressed = fh.read(length - 1)
    if compression == 2:
        raw = zlib.decompress(compressed)
    elif compression == 1:
        raw = gzip.decompress(compressed)
    else:
        raw = compressed
    return File.parse(io.BytesIO(raw))


def block_index(data, bits, index):
    bit = index * bits
    word = bit >> 6
    shift = bit & 63
    value = data[word] >> shift
    if shift + bits > 64:
        value |= data[word + 1] << (64 - shift)
    return value & ((1 << bits) - 1)


def chunk_columns(root):
    """Return {(local_x, local_z): [material-or-None for y=0..255]}."""
    columns = {}
    if root is None:
        return columns
    for section in root["sections"]:
        section_y = int(section["Y"])
        section_min = section_y * 16
        section_max = section_min + 15
        if section_max < Y_MIN or section_min > Y_MAX:
            continue
        states = section.get("block_states")
        if states is None:
            continue
        palette = [str(item["Name"]) for item in states["palette"]]
        if not palette:
            continue
        data = [int(value) & ((1 << 64) - 1) for value in states.get("data", [])]
        if len(palette) == 1 and not data:
            bits = 0
        else:
            bits = max(4, math.ceil(math.log2(len(palette))))
        for local_z in range(16):
            for local_x in range(16):
                column = None
                for local_y in range(16):
                    y = section_min + local_y
                    if y < Y_MIN or y > Y_MAX:
                        continue
                    if bits == 0:
                        material = palette[0]
                    else:
                        palette_index = block_index(data, bits, (local_y << 8) | (local_z << 4) | local_x)
                        material = palette[palette_index] if palette_index < len(palette) else palette[0]
                    if material in ("minecraft:air", "minecraft:cave_air", "minecraft:void_air"):
                        continue
                    if column is None:
                        column = columns.setdefault((local_x, local_z), [None] * (Y_MAX - Y_MIN + 1))
                    column[y - Y_MIN] = material
    return columns


def encode_runs(bounds):
    x1, x2, z1, z2 = bounds
    legend = []
    legend_index = {}
    runs = []
    column_runs = []
    region_cache = {}

    def material_id(material):
        if material not in legend_index:
            legend_index[material] = len(legend)
            legend.append(material)
        return legend_index[material]

    cx_min, cx_max = x1 // 16, x2 // 16
    cz_min, cz_max = z1 // 16, z2 // 16
    for chunk_z in range(cz_min, cz_max + 1):
        for chunk_x in range(cx_min, cx_max + 1):
            rx, rz = chunk_x // 32, chunk_z // 32
            region_key = (rx, rz)
            if region_key not in region_cache:
                region_cache[region_key] = WORLD / "region" / f"r.{rx}.{rz}.mca"
            root = read_chunk(region_cache[region_key], (chunk_z % 32) * 32 + (chunk_x % 32))
            columns = chunk_columns(root)
            for (local_x, local_z), values in columns.items():
                x, z = chunk_x * 16 + local_x, chunk_z * 16 + local_z
                if x < x1 or x > x2 or z < z1 or z > z2:
                    continue
                top = max((index for index, value in enumerate(values) if value is not None), default=-1)
                if top >= 0:
                    bottom = top
                    while bottom > 0 and values[bottom - 1] is not None:
                        bottom -= 1
                    column_runs.append((x - x1, z - z1, bottom, top, material_id(values[top])))
                y = 0
                while y <= Y_MAX - Y_MIN:
                    if values[y] is None:
                        y += 1
                        continue
                    material = values[y]
                    end = y + 1
                    while end <= Y_MAX - Y_MIN and values[end] == material and end - y < 255:
                        end += 1
                    # 8 bytes: x(u16), z(u16), y(u8), run length(u8), material(u16)
                    runs.append((x - x1, z - z1, y, end - y, material_id(material)))
                    y = end

    payload = bytearray(len(runs) * 8)
    for index, (x, z, y, length, material) in enumerate(runs):
        offset = index * 8
        struct.pack_into(">HHBBH", payload, offset, x, z, y, length, material)
    column_payload = bytearray(len(column_runs) * 8)
    for index, (x, z, bottom, top, material) in enumerate(column_runs):
        offset = index * 8
        struct.pack_into(">HHBBH", column_payload, offset, x, z, bottom, top - bottom + 1, material)
    return legend, runs, base64.b64encode(payload).decode("ascii"), len(column_runs), base64.b64encode(column_payload).decode("ascii")


def main():
    data = read_map_data()
    towns = [area for area in data["areas"] if area.get("id") in SLUGS]
    for area in towns:
        x1, x2, z1, z2 = map(int, area["bounds"])
        legend, runs, encoded, column_count, columns_encoded = encode_runs((x1, x2, z1, z2))
        payload = {
            "region": {"id": f"{SLUGS[area['id']]}-scan", "x1": x1, "x2": x2, "z1": z1, "z2": z2},
            "format": "runs8",
            "xOrigin": x1,
            "zOrigin": z1,
            "yOrigin": Y_MIN,
            "width": x2 - x1 + 1,
            "depth": z2 - z1 + 1,
            "legend": legend,
            "count": len(runs),
            "details": encoded,
            "columnCount": column_count,
            "columns": columns_encoded,
            "scannedAt": "2026-08-21T00:00:00+09:00",
            "note": "로컬 Paper Anvil 청크 전체 블록 스캔; 비공기 연속 구간만 압축 저장",
        }
        target = OUT / f"town-detail-{SLUGS[area['id']]}.json"
        target.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
        print(area["id"], "bounds", (x1, x2, z1, z2), "runs", len(runs), "legend", len(legend), "bytes", target.stat().st_size)


if __name__ == "__main__":
    main()
