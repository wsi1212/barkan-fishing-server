"""Read-only verification for the installed Honor Hall v4 blueprint."""
import json
from collections import Counter
from pathlib import Path
import install_v4


def root(material):
    return material.split('[', 1)[0]


def main():
    expected = install_v4.expected_blocks()
    # Installation cleanup begins at Y65; verification also includes the designed
    # terrain/path layer at Y64.
    install_v4.Y1 = 64
    actual = install_v4.inspect_live()
    mismatches = [
        {'pos': position, 'expected': material, 'actual': actual.get(position, 'minecraft:air')}
        for position, material in expected.items()
        if root(material) != actual.get(position, 'minecraft:air')
    ]
    report = {
        'world': install_v4.WORLD,
        'expected_blocks': len(expected),
        'mismatches': len(mismatches),
        'samples': mismatches[:50],
        'palette': Counter(root(material) for material in expected.values()),
    }
    Path(__file__).with_name('installation-v4-report.json').write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + '\n'
    )
    print(json.dumps(report, ensure_ascii=False), flush=True)
    if mismatches:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
