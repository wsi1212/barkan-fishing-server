"""Densify the empty forest-to-mountain buffer around the prod Honor Hall.

This deliberately targets only four exterior strips.  They begin outside the
existing Honor Hall forest/build footprint, so the temple, its paths, and the
open statue garden remain untouched.  Native trees only grow from grass/dirt
surfaces, naturally stopping before the stone face of the enclosure.
"""
import json
import sys
import urllib.request
from pathlib import Path

BASE = 'http://127.0.0.1:25597'
WORLD = 'honor_hall'
OUT = Path(__file__).resolve().parent

# The v4 forest ends at x/z -891..-646.  These strips begin five blocks beyond
# it and run to the inner lip of the terrain enclosure (about 160 blocks away).
STRIPS = [
    ('north', -930, -608, -927, -896),
    ('south', -930, -608, -641, -610),
    ('west',  -929, -896, -895, -643),
    ('east',  -641, -608, -895, -643),
]
TREE_TYPES = ['oak', 'big_oak', 'birch', 'tall_birch', 'azalea']
UNDERSTORY = [
    {'material': 'minecraft:short_grass', 'weight': 55},
    {'material': 'minecraft:fern', 'weight': 16},
    {'material': 'minecraft:dandelion', 'weight': 8},
    {'material': 'minecraft:cornflower', 'weight': 7},
    {'material': 'minecraft:azure_bluet', 'weight': 7},
    {'material': 'minecraft:lilac', 'weight': 4},
    {'material': 'minecraft:rose_bush', 'weight': 3},
]


def post(path, body, timeout=300):
    request = urllib.request.Request(
        BASE + path,
        data=json.dumps({'world': WORLD, **body}).encode(),
        headers={'Content-Type': 'application/json'},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        result = json.load(response)
    if result.get('error') or result.get('ok') is False:
        raise RuntimeError(result)
    return result


def checkpoint():
    for side, x1, x2, z1, z2 in STRIPS:
        # Checkpoints have a bounded volume.  Split the long strips into
        # 100-block pieces so every rollback snapshot fits independently.
        for index, xa in enumerate(range(x1, x2 + 1, 100)):
            xb = min(x2, xa + 99)
            name = f'honor_hall_forest_gap_before_{side}{index}_20260916'
            post('/save_checkpoint', {
                'name': name, 'x1': xa, 'x2': xb, 'y1': -64, 'y2': 40,
                'z1': z1, 'z2': z2,
            })
            print('checkpoint', name, flush=True)


def height_preflight():
    # These strips must sit outside the known temple bbox.  Report their
    # extrema for an auditable preflight, rather than altering terrain.
    summary = {}
    for side, x1, x2, z1, z2 in STRIPS:
        heights = post('/heightmap', {
            'x1': x1, 'x2': x2, 'z1': z1, 'z2': z2,
            'heightmap_type': 'world_surface',
        })['heights']
        flat = [v for row in heights for v in row]
        summary[side] = {'min_y': min(flat), 'max_y': max(flat), 'cells': len(flat)}
    return summary


def install():
    result = {'trees': {}, 'understory': {}}
    for index, (side, x1, x2, z1, z2) in enumerate(STRIPS):
        # Five-block cells make a wall of canopy while retaining a few natural
        # gaps.  Seeded calls make the same pass reproducible.
        result['trees'][side] = post('/plant_trees', {
            'x1': x1, 'x2': x2, 'z1': z1, 'z2': z2,
            'tree_types': TREE_TYPES, 'density': 0.76, 'min_spacing': 5,
            'seed': 916220 + index * 101,
        })
    for index, (side, x1, x2, z1, z2) in enumerate(STRIPS):
        # Per-surface placement means foliage gets flowers/grass only in clear
        # ground pockets, never floating inside the new canopy.
        result['understory'][side] = post('/scatter_blocks', {
            'x1': x1, 'x2': x2, 'z1': z1, 'z2': z2,
            'blocks': UNDERSTORY, 'density': 0.20,
            'seed': 916720 + index * 101, 'on_surface': True,
        })
    return result


def verify_canopy():
    """Count columns now covered above the former terrain surface."""
    from mountain_ring import GROUND, profile
    verified = {}
    for side, x1, x2, z1, z2 in STRIPS:
        rows = post('/heightmap', {
            'x1': x1, 'x2': x2, 'z1': z1, 'z2': z2,
            'heightmap_type': 'world_surface',
        })['heights']
        canopy, cells = 0, 0
        for ix, row in enumerate(rows):
            for iz, actual in enumerate(row):
                p = profile(x1 + ix, z1 + iz)
                terrain = GROUND if p is None else GROUND + p[0]
                canopy += actual > terrain
                cells += 1
        verified[side] = {'canopy_columns': canopy, 'cells': cells}
    return verified


def main():
    preflight = height_preflight()
    checkpoint()
    result = install()
    canopy = verify_canopy()
    report = {
        'world': WORLD,
        'strips': [{
            'side': side, 'x1': x1, 'x2': x2, 'z1': z1, 'z2': z2,
        } for side, x1, x2, z1, z2 in STRIPS],
        'preflight_surface_heights': preflight,
        'tree_types': TREE_TYPES,
        'result': result,
        'canopy_verification': canopy,
        'restart_performed': False,
    }
    OUT.joinpath('prod-forest-gap-fill-report.json').write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + '\n'
    )
    print(json.dumps(report, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
