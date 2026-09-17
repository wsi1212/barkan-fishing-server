"""One-shot, no-restart prod installer for the approved Honor Hall v4.

Target is a read-verified empty, flat 246x246 area in prod honor_hall.
The HTTP target is a temporary local SSH tunnel to prod AIBuilder, never a live
jar replacement or server restart. Abort safely if any non-air block exists
above the target ground before placement.
"""
import importlib.util
import json
import sys
import urllib.request
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE = 'http://127.0.0.1:25597'
WORLD = 'honor_hall'
# Local visual y=-1 is the grass surface. Prod's untouched superflat surface is -61.
ORIGIN = (-891, -61, -891)
X1, X2, Y_GROUND, Y_TOP, Z1, Z2 = -891, -646, -61, -20, -891, -646
CHUNK = 5_000


def root(material):
    return material.split('[', 1)[0]


def post(path, body, timeout=180):
    req = urllib.request.Request(
        BASE + path,
        data=json.dumps({'world': WORLD, **body}).encode(),
        headers={'Content-Type': 'application/json'},
    )
    with urllib.request.urlopen(req, timeout=timeout) as response:
        result = json.load(response)
    if result.get('error') or result.get('ok') is False:
        raise RuntimeError(result)
    return result


def expected_blocks():
    spec = importlib.util.spec_from_file_location('honor_hall_v4_recipe', HERE / 'honor_hall_v4.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    sys.path.insert(0, '/Users/user/development/ai-builder-plugin/tools')
    from recipe_api import Api
    structure = module.build(Api())
    return {
        (x + ORIGIN[0], y + ORIGIN[1], z + ORIGIN[2]): material
        for (x, y, z), material in structure.blocks.items()
    }


def cells(y1, y2):
    for x1 in range(X1, X2 + 1, 62):
        for z1 in range(Z1, Z2 + 1, 62):
            yield x1, min(X2, x1 + 61), z1, min(Z2, z1 + 61), y1, y2


def scan(y1, y2):
    live = {}
    for x1, x2, z1, z2, ya, yb in cells(y1, y2):
        result = post('/inspect_volume', {
            'x1': x1, 'x2': x2, 'y1': ya, 'y2': yb,
            'z1': z1, 'z2': z2, 'format': 'sparse', 'include_air': False,
        })
        for dx, dy, dz, index in result['blocks']:
            live[(x1 + dx, ya + dy, z1 + dz)] = result['legend'][index]
    return live


def save_checkpoints():
    for suffix, xa, xb, za, zb in (
        ('nw', X1, -769, Z1, -769), ('ne', -768, X2, Z1, -769),
        ('sw', X1, -769, -768, Z2), ('se', -768, X2, -768, Z2),
    ):
        result = post('/save_checkpoint', {
            'name': f'honor_hall_v4_prod_before_{suffix}_20260916',
            'x1': xa, 'x2': xb, 'y1': -64, 'y2': Y_TOP, 'z1': za, 'z2': zb,
        })
        print('checkpoint', suffix, result, flush=True)


def send(entries, label):
    total = len(entries)
    for start in range(0, total, CHUNK):
        post('/place_many', {'blocks': entries[start:start + CHUNK]})
        print(f'{label}: {min(start + CHUNK, total)}/{total}', flush=True)


def main():
    expected = expected_blocks()
    assert len(expected) == 411728
    # Strict preflight: the target must be its untouched superflat layer + air.
    heights = post('/heightmap', {
        'x1': X1, 'x2': X2, 'z1': Z1, 'z2': Z2, 'heightmap_type': 'world_surface',
    })['heights']
    assert {height for row in heights for height in row} == {Y_GROUND}, 'target is not flat/unbuilt'
    above = scan(Y_GROUND + 1, Y_TOP)
    if above:
        raise RuntimeError({'target_not_empty': len(above), 'samples': list(above.items())[:20]})
    save_checkpoints()
    solids = [
        {'x': x, 'y': y, 'z': z, 'material': material}
        for (x, y, z), material in sorted(expected.items(), key=lambda kv: (kv[0][1], kv[0][2], kv[0][0]))
        if root(material) != 'minecraft:water'
    ]
    water = [
        {'x': x, 'y': y, 'z': z, 'material': material}
        for (x, y, z), material in expected.items() if root(material) == 'minecraft:water'
    ]
    send(solids, 'place solid')
    send(water, 'place water')
    actual = scan(Y_GROUND, Y_TOP)
    mismatches = [
        {'pos': position, 'expected': material, 'actual': actual.get(position, 'minecraft:air')}
        for position, material in expected.items()
        if root(material) != actual.get(position, 'minecraft:air')
    ]
    report = {
        'world': WORLD, 'origin': ORIGIN, 'bounds': [X1, Y_GROUND, Z1, X2, Y_TOP, Z2],
        'expected_blocks': len(expected), 'mismatches': len(mismatches), 'samples': mismatches[:50],
        'palette': Counter(root(material) for material in expected.values()),
        'restart_performed': False,
    }
    (HERE / 'prod-v4-installation-report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(report, ensure_ascii=False), flush=True)
    if mismatches:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
