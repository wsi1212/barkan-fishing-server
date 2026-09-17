"""Exact recipe export for Honor Hall v4.

Design only: the companion installer owns snapshots, scoped cleanup and placement.
World origin when installed is (-123, 64, -123); local y=1 is the walking floor Y65.
"""
import json
from pathlib import Path


def build(api):
    data = json.loads(Path(__file__).with_name('honor-hall-v4-blueprint.json').read_text())
    assert data['status'] == 'DESIGN_NOT_DEPLOYED'
    palette = [entry['block'] for entry in data['palette']]
    s = api.create(246, 42, 246)
    for x, y, z, length, palette_index, _group_index in data['runs']:
        for dx in range(length):
            api.set(s, (x + 123 + dx, y + 1, z + 123), palette[palette_index])
    return s
