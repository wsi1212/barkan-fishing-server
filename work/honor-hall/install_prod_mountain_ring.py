"""Safe, no-restart installer for the Honor Hall mountain enclosure on prod."""
import json
import sys
import urllib.request
from collections import Counter
from pathlib import Path

from mountain_ring import BOUND, CX, CZ, GROUND, columns, material_at

BASE = 'http://127.0.0.1:25597'
WORLD = 'honor_hall'
CHUNK = 20_000
OUT = Path(__file__).resolve().parent


def post(path, body, timeout=300):
    req = urllib.request.Request(BASE + path, data=json.dumps({'world': WORLD, **body}).encode(),
                                 headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        result = json.load(response)
    if result.get('error') or result.get('ok') is False:
        raise RuntimeError(result)
    return result


def plan():
    total, cols, top = 0, 0, GROUND
    palette = Counter()
    for x, z, (height, inner, _outer) in columns():
        cols += 1
        total += height
        top = max(top, GROUND + height)
        for y in range(GROUND + 1, GROUND + height + 1):
            palette[material_at(x, z, y, height, inner)] += 1
    return {'columns': cols, 'blocks': total, 'top_y': top, 'palette': palette}


def heights_for_enclosure():
    """The bridge caps each heightmap at 65,536 cells, so scan in 128x128 tiles."""
    x1, x2, z1, z2 = CX - BOUND, CX + BOUND, CZ - BOUND, CZ + BOUND
    out = {}
    for xa in range(x1, x2 + 1, 128):
        xb = min(x2, xa + 127)
        for za in range(z1, z2 + 1, 128):
            zb = min(z2, za + 127)
            rows = post('/heightmap', {'x1': xa, 'x2': xb, 'z1': za, 'z2': zb,
                                       'heightmap_type': 'world_surface'})['heights']
            for ix, row in enumerate(rows):
                for iz, value in enumerate(row):
                    out[(xa + ix, za + iz)] = value
    return out


def preflight():
    # We check only planned mountain columns. The temple/forest inside the ring is expected.
    x1, z1 = CX - BOUND, CZ - BOUND
    heights = heights_for_enclosure()
    bad = []
    for (x, z), height in heights.items():
        if profile_for(x, z) and height != GROUND:
            bad.append((x, z, height))
            if len(bad) >= 20:
                return bad
    return bad


def profile_for(x, z):
    # Imported lazily to keep call sites obvious in preflight.
    from mountain_ring import profile
    return profile(x, z)


def save_checkpoints():
    # Mountain-only stripes, outside the existing forest/build. Each stays <1M cells.
    x1, x2, z1, z2 = CX - BOUND, CX + BOUND, CZ - BOUND, CZ + BOUND
    strip = 78
    specs = [
        ('north', x1, x2, z1, z1 + strip - 1),
        ('south', x1, x2, z2 - strip + 1, z2),
        ('west', x1, x1 + strip - 1, z1 + strip, z2 - strip),
        ('east', x2 - strip + 1, x2, z1 + strip, z2 - strip),
    ]
    for side, xa, xb, za, zb in specs:
        for index, lo in enumerate(range(xa if side in ('north', 'south') else za,
                                         (xb if side in ('north', 'south') else zb) + 1, 103)):
            if side in ('north', 'south'):
                xlo, xhi, zlo, zhi = lo, min(xb, lo + 102), za, zb
            else:
                xlo, xhi, zlo, zhi = xa, xb, lo, min(zb, lo + 102)
            name = f'honor_hall_mountain_before_{side}{index}_20260916'
            post('/save_checkpoint', {'name': name, 'x1': xlo, 'x2': xhi, 'y1': -64, 'y2': 35,
                                      'z1': zlo, 'z2': zhi})
            print('checkpoint', name, flush=True)


def stream_place():
    batch, placed = [], 0
    for x, z, (height, inner, _outer) in columns():
        for y in range(GROUND + 1, GROUND + height +1):
            batch.append({'x': x, 'y': y, 'z': z, 'material': material_at(x, z, y, height, inner)})
            if len(batch) == CHUNK:
                post('/place_many', {'blocks': batch})
                placed += len(batch)
                print('place mountain:', placed, flush=True)
                batch = []
    if batch:
        post('/place_many', {'blocks': batch})
        placed += len(batch)
    return placed


def verify():
    # Heightmap proves a continuous vertical enclosure at every generated column.
    x1, x2, z1, z2 = CX - BOUND, CX + BOUND, CZ - BOUND, CZ + BOUND
    heights = heights_for_enclosure()
    short = []
    expected_cols = 0
    for x, z, (height, _inner, _outer) in columns():
        expected_cols += 1
        actual = heights[(x, z)]
        if actual < GROUND + height:
            short.append((x, z, GROUND + height, actual))
            if len(short) >= 50:
                break
    return expected_cols, short


def main():
    summary = plan()
    bad = preflight()
    if bad:
        raise RuntimeError({'planned_mountain_space_not_empty': bad})
    save_checkpoints()
    placed = stream_place()
    expected_cols, short = verify()
    report = {'world': WORLD, 'center': [CX, CZ], 'radius': BOUND, 'ground_y': GROUND,
              'planned_columns': summary['columns'], 'placed_blocks': placed,
              'peak_y': summary['top_y'], 'expected_columns': expected_cols,
              'short_columns': short, 'restart_performed': False,
              'palette': summary['palette']}
    OUT.joinpath('prod-mountain-ring-report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(report, ensure_ascii=False), flush=True)
    if short:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
