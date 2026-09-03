#!/usr/bin/env python3
"""보스 블록 빌드 스캔 → <name>_scan.json (blockstate 포함).

AIBuilder HTTP 브리지(/get_region + /get_block)로 매번 다시 뽑는다 — 스캔 사본을
손으로 갱신하지 않는다. /get_region 은 material 만 주므로, 기하가 상태에 좌우되는
블록(계단·판유리·군집·상자 등)만 /get_block 으로 blockstate 를 채운다.

사용: python3 scan_boss.py <name> <world> x1 y1 z1 x2 y2 z2
"""
import json, os, sys, urllib.request
from concurrent.futures import ThreadPoolExecutor

URL = os.environ.get("AIBUILDER_URL", "http://127.0.0.1:25599")
HERE = os.path.dirname(os.path.abspath(__file__))

# 기하가 blockstate 에 좌우되는 블록 = 개별 조회 대상. 그 외는 풀큐브로 취급.
STATEFUL_SUFFIX = ("_stairs", "_slab", "_pane", "_wall", "_fence", "_door", "_trapdoor",
                   "_bud", "_cluster", "_chest", "_log", "_stem", "_hyphae", "_wood",
                   "_sign", "_rod", "_amethyst_bud")
STATEFUL_EXACT = {"ender_chest", "chain", "iron_chain", "lantern", "amethyst_cluster",
                  "bone_block", "basalt", "polished_basalt", "hay_block", "muddy_mangrove_roots"}


def post(path, payload):
    req = urllib.request.Request(URL + path, method="POST",
                                 data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)


def is_stateful(mat):
    m = mat.removeprefix("minecraft:")
    return m in STATEFUL_EXACT or m.endswith(STATEFUL_SUFFIX)


def main():
    if len(sys.argv) != 9:
        sys.exit(__doc__)
    name, world = sys.argv[1], sys.argv[2]
    x1, y1, z1, x2, y2, z2 = map(int, sys.argv[3:9])
    box = dict(world=world, x1=x1, y1=y1, z1=z1, x2=x2, y2=y2, z2=z2)
    reg = post("/get_region", box)
    blocks = reg["blocks"]
    print(f"region: {len(blocks)} non-air")

    todo = [b for b in blocks if is_stateful(b["material"])]
    print(f"stateful fetch: {len(todo)}")

    def fetch(b):
        d = post("/get_block", dict(world=world, x=b["x"], y=b["y"], z=b["z"]))
        return b, d["data"]

    got = {}
    with ThreadPoolExecutor(max_workers=6) as ex:
        for b, data in ex.map(fetch, todo):
            got[(b["x"], b["y"], b["z"])] = data

    cells = {}
    for b in blocks:
        k = (b["x"], b["y"], b["z"])
        cells[f"{k[0]},{k[1]},{k[2]}"] = got.get(k, b["material"])

    out = {"world": world, "bbox": [x1, y1, z1, x2, y2, z2],
           "count": len(cells), "cells": cells}
    p = os.path.join(HERE, f"{name}_scan.json")
    json.dump(out, open(p, "w"), separators=(",", ":"), sort_keys=True)
    print("wrote", p)

    from collections import Counter
    c = Counter(v.split("[")[0].removeprefix("minecraft:") for v in cells.values())
    for m, n in c.most_common():
        print(f"  {n:4d} {m}")


if __name__ == "__main__":
    main()
