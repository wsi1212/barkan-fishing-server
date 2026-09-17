"""Scoped dev-only installer for the approved Honor Hall v4 blueprint.

It deliberately never touches prod. Before use, make MCP checkpoints with names
honor_v4_before_install_{nw,ne,sw,se}; this script only replaces the dedicated
Honor Hall build envelope X/Z -123..122, Y65..107.
"""
import importlib.util
import json
import sys
import urllib.request
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE = 'http://127.0.0.1:25598'
WORLD = 'honor_hall'
ORIGIN = (-123, 64, -123)
X1, X2, Y1, Y2, Z1, Z2 = -123, 122, 65, 107, -123, 122
CHUNK = 10_000


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


def inspect_live():
    """Sparse, 16-cell scan stays below the bridge's 200k-cell request limit."""
    live = {}
    for x1 in range(X1, X2 + 1, 62):
        x2 = min(X2, x1 + 61)
        for z1 in range(Z1, Z2 + 1, 62):
            z2 = min(Z2, z1 + 61)
            result = post('/inspect_volume', {
                'x1': x1, 'x2': x2, 'y1': Y1, 'y2': Y2,
                'z1': z1, 'z2': z2, 'format': 'sparse', 'include_air': False,
            })
            for dx, dy, dz, index in result['blocks']:
                live[(x1 + dx, Y1 + dy, z1 + dz)] = result['legend'][index]
    return live


def send(entries, label):
    total = len(entries)
    for start in range(0, total, CHUNK):
        chunk = entries[start:start + CHUNK]
        post('/place_many', {'blocks': chunk})
        print(f'{label}: {min(start + len(chunk), total)}/{total}', flush=True)


def main():
    expected = expected_blocks()
    assert len(expected) == 411728, len(expected)
    assert all(X1 <= x <= X2 and Y1 - 1 <= y <= Y2 and Z1 <= z <= Z2 for x, y, z in expected)
    live = inspect_live()
    # Existing construction is in the exact dedicated envelope. Ground at Y64 is
    # intentionally preserved/repainted by the new blueprint; only old above-floor
    # material is removed before the new ordered blocks are placed.
    cleanup = [
        {'x': x, 'y': y, 'z': z, 'material': 'air'}
        for (x, y, z), actual in live.items()
        if (x, y, z) not in expected
    ]
    send(cleanup, 'Clear prior Honor Hall blocks')
    solids = [
        {'x': x, 'y': y, 'z': z, 'material': material}
        for (x, y, z), material in sorted(expected.items(), key=lambda kv: (kv[0][1], kv[0][2], kv[0][0]))
        if root(material) != 'minecraft:water'
    ]
    liquids = [
        {'x': x, 'y': y, 'z': z, 'material': material}
        for (x, y, z), material in expected.items() if root(material) == 'minecraft:water'
    ]
    send(solids, 'Install v4 solid geometry')
    send(liquids, 'Fill v4 contained water')
    actual = inspect_live()
    mismatches = [
        {'pos': position, 'expected': material, 'actual': actual.get(position, 'minecraft:air')}
        for position, material in expected.items()
        if root(material) != actual.get(position, 'minecraft:air')
    ]
    report = {
        'world': WORLD, 'expected_blocks': len(expected), 'mismatches': len(mismatches),
        'samples': mismatches[:50],
        'palette': Counter(root(material) for material in expected.values()),
    }
    (HERE / 'installation-v4-report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(report, ensure_ascii=False), flush=True)
    if mismatches:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
