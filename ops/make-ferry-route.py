#!/usr/bin/env python3
"""페리 바다 항로 생성기 — 월드 region 파일에서 «배가 지날 수 있는 수면»을 직접 읽어 A* 로 항로를 뽑는다.

    python3 ops/make-ferry-route.py --from 402,944 --to 1153,-87 \
        --world "<서버>/world" --sea-y 60

왜 스크립트인가: 항로를 손으로 찍으면 «육지를 통과하는 배»가 나온다(좌표를 상상으로 적으면 반드시 그렇게 된다).
지형이 바뀌면 다시 돌리면 되고, 산출물(waypoints)을 레포에 박제하지 않는다.

판정 규약
  - 수면       : y == SEA_Y 가 물
  - 돛대 여유  : y SEA_Y+1 .. SEA_Y+CLEAR 가 전부 통과 가능(공기·물·해초)
  - 선체 폭    : 마스크를 침식(erode)해 여유를 확보. --erode 는 «셀» 단위이고 1셀 = STRIDE(2) 블록.
                 돛단배는 폭 7이라 최소 2셀(=4블록) 필요. 직선 단순화는 4셀로 한 번 더 조인다.
  - 해안 회피  : 해안에서 가까울수록 A* 비용에 벌점 → 항로가 물 한가운데로 다닌다.

결과는 `/페리설정 <노선> 경유지추가` 로 하나씩 찍는 대신 ferries.json 의
`waypoints`(+`seaY`)에 그대로 넣으면 된다. 서버는 «정지 상태»에서 편집할 것 —
가동 중에 고치면 FerryManager.save() 가 덮는다.
"""
from __future__ import annotations

import argparse
import collections
import heapq
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "imugi-boss"))
from anvil_read import read_chunk, section_blocks  # noqa: E402

STRIDE = 2
PASSABLE = ("air", "cave_air", "void_air", "water", "seagrass", "tall_seagrass",
            "kelp", "kelp_plant", "bubble_column")


def build_mask(world, x1, z1, x2, z2, sea_y, clear):
    """(mask, W, H) — 1 = 수면 + 돛대 여유 확보."""
    w = (x2 - x1) // STRIDE + 1
    h = (z2 - z1) // STRIDE + 1
    mask = bytearray(w * h)
    for cx in range(x1 >> 4, (x2 >> 4) + 1):
        for cz in range(z1 >> 4, (z2 >> 4) + 1):
            mca = f"{world}/region/r.{cx >> 5}.{cz >> 5}.mca"
            if not os.path.exists(mca):
                continue
            try:
                ch = read_chunk(mca, cx, cz)
            except Exception:
                continue
            if ch is None:
                continue
            secs = {s["Y"]: s for s in ch["sections"]}
            get = {}
            for sy in range(sea_y >> 4, ((sea_y + clear) >> 4) + 1):
                sec = secs.get(sy)
                get[sy] = section_blocks(sec) if sec is not None else None
            for x in range(max(x1, cx * 16), min(x2, cx * 16 + 15) + 1):
                if (x - x1) % STRIDE:
                    continue
                for z in range(max(z1, cz * 16), min(z2, cz * 16 + 15) + 1):
                    if (z - z1) % STRIDE:
                        continue
                    g = get.get(sea_y >> 4)
                    if g is None:
                        continue
                    if not g((((sea_y & 15) * 16 + (z & 15)) * 16) + (x & 15)).startswith("minecraft:water"):
                        continue
                    ok = True
                    for y in range(sea_y + 1, sea_y + clear + 1):
                        gy = get.get(y >> 4)
                        if gy is None:
                            continue
                        b = gy((((y & 15) * 16 + (z & 15)) * 16) + (x & 15)).split(":")[1].split("[")[0]
                        if b not in PASSABLE:
                            ok = False
                            break
                    if ok:
                        mask[((z - z1) // STRIDE) * w + (x - x1) // STRIDE] = 1
    return mask, w, h


def erode(mask, w, h, r):
    out = bytearray(mask)
    for i in range(len(mask)):
        if not mask[i]:
            continue
        cx, cz = i % w, i // w
        bad = False
        for dz in range(-r, r + 1):
            zz = cz + dz
            if zz < 0 or zz >= h:
                bad = True
                break
            base = zz * w
            for dx in range(-r, r + 1):
                xx = cx + dx
                if xx < 0 or xx >= w or not mask[base + xx]:
                    bad = True
                    break
            if bad:
                break
        if bad:
            out[i] = 0
    return out


def coast_distance(m, w, h):
    """각 항해가능 칸의 «해안까지 칸 수» (BFS)."""
    inf = 10 ** 9
    d = [inf] * (w * h)
    q = collections.deque()
    for i in range(w * h):
        if not m[i]:
            continue
        cx, cz = i % w, i // w
        for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, nz = cx + dx, cz + dz
            if not (0 <= nx < w and 0 <= nz < h) or not m[nz * w + nx]:
                d[i] = 0
                q.append(i)
                break
    while q:
        i = q.popleft()
        cx, cz = i % w, i // w
        for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, nz = cx + dx, cz + dz
            if not (0 <= nx < w and 0 <= nz < h):
                continue
            j = nz * w + nx
            if m[j] and d[j] == inf:
                d[j] = d[i] + 1
                q.append(j)
    return d


def astar(m, w, h, s, t, coast, coast_r, coast_w):
    tx, tz = t % w, t // w
    g = {s: 0.0}
    par = {}
    pq = [(0.0, s)]
    while pq:
        _, i = heapq.heappop(pq)
        if i == t:
            break
        cx, cz = i % w, i // w
        for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)):
            nx, nz = cx + dx, cz + dz
            if not (0 <= nx < w and 0 <= nz < h):
                continue
            j = nz * w + nx
            if not m[j]:
                continue
            step = 1.4142 if dx and dz else 1.0
            pen = max(0, coast_r - min(coast[j], coast_r)) * coast_w
            ng = g[i] + step + pen
            if ng < g.get(j, 1e18):
                g[j] = ng
                par[j] = i
                heapq.heappush(pq, (ng + math.hypot(nx - tx, nz - tz), j))
    if t not in g:
        return None
    p = [t]
    while p[-1] != s:
        p.append(par[p[-1]])
    return p[::-1]


def seg_ok(m, w, a, b):
    ax, az = a % w, a // w
    bx, bz = b % w, b // w
    n = max(abs(bx - ax), abs(bz - az))
    for k in range(n + 1):
        t = k / n if n else 0
        if not m[round(az + (bz - az) * t) * w + round(ax + (bx - ax) * t)]:
            return False
    return True


def simplify(path, w, tight, wide):
    """넓은 여유(wide)로 이을 수 있으면 길게, 안 되면 tight 로 — 항구 진입은 좁아도 통과시킨다."""
    out = [path[0]]
    i = 0
    while i < len(path) - 1:
        j = len(path) - 1
        while j > i + 1 and not seg_ok(wide, w, path[i], path[j]):
            j -= 1
        if j == i + 1:
            j = len(path) - 1
            while j > i + 1 and not seg_ok(tight, w, path[i], path[j]):
                j -= 1
        out.append(path[j])
        i = j
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--world", required=True, help="월드 폴더(region/ 을 담고 있는)")
    ap.add_argument("--from", dest="a", required=True, metavar="X,Z")
    ap.add_argument("--to", dest="b", required=True, metavar="X,Z")
    ap.add_argument("--sea-y", type=int, default=60)
    ap.add_argument("--clear", type=int, default=10, help="수면 위 확보할 높이(돛대)")
    ap.add_argument("--erode", type=int, default=2, help="셀 단위 여유(1셀=2블록). 돛단배(폭7)는 2 이상")
    ap.add_argument("--erode-wide", type=int, default=4, help="직선 구간에 요구할 넉넉한 여유")
    ap.add_argument("--margin", type=int, default=400, help="두 지점 바깥으로 넓힐 탐색 여백")
    ap.add_argument("--coast-radius", type=int, default=10)
    ap.add_argument("--coast-weight", type=float, default=1.6)
    ap.add_argument("--json", action="store_true", help="ferries.json 의 waypoints 배열로 출력")
    args = ap.parse_args()

    ax, az = (int(v) for v in args.a.split(","))
    bx, bz = (int(v) for v in args.b.split(","))
    x1, x2 = min(ax, bx) - args.margin, max(ax, bx) + args.margin
    z1, z2 = min(az, bz) - args.margin, max(az, bz) + args.margin
    x1 -= x1 % STRIDE
    z1 -= z1 % STRIDE

    print(f"[1/4] 스캔 x {x1}..{x2} z {z1}..{z2} (sea_y={args.sea_y})", file=sys.stderr)
    mask, w, h = build_mask(args.world, x1, z1, x2, z2, args.sea_y, args.clear)
    print(f"      수면칸 {sum(mask)}", file=sys.stderr)

    tight = erode(mask, w, h, args.erode)
    wide = erode(mask, w, h, args.erode_wide)
    print(f"[2/4] 침식 r={args.erode} → {sum(tight)} / r={args.erode_wide} → {sum(wide)}", file=sys.stderr)

    def cell(x, z):
        return ((z - z1) // STRIDE) * w + ((x - x1) // STRIDE)

    def xz(i):
        return (x1 + (i % w) * STRIDE, z1 + (i // w) * STRIDE)

    def nearest(x, z):
        for r in range(0, 300):
            for p in range(-r, r + 1):
                for q in ((-r, r) if r else (0,)):
                    for xx, zz in ((x + p, z + q), (x + q, z + p)):
                        if x1 <= xx <= x1 + (w - 1) * STRIDE and z1 <= zz <= z1 + (h - 1) * STRIDE:
                            i = cell(xx, zz)
                            if tight[i]:
                                return i
        return None

    s, t = nearest(ax, az), nearest(bx, bz)
    if s is None or t is None:
        sys.exit("출발/도착 근처에 항해 가능한 수면이 없습니다.")
    print(f"[3/4] 시작 {xz(s)} 도착 {xz(t)}", file=sys.stderr)

    coast = coast_distance(tight, w, h)
    path = astar(tight, w, h, s, t, coast, args.coast_radius, args.coast_weight)
    if path is None:
        sys.exit("두 지점이 바다로 이어져 있지 않습니다.")
    wp = [xz(i) for i in simplify(path, w, tight, wide)]
    length = sum(math.dist(wp[k], wp[k + 1]) for k in range(len(wp) - 1))

    # 검산 — 단순화한 직선이 실제로 물 위인가
    land = 0
    for k in range(len(wp) - 1):
        (px, pz), (qx, qz) = wp[k], wp[k + 1]
        n = int(max(abs(qx - px), abs(qz - pz)))
        for i in range(n + 1):
            u = i / n if n else 0
            if not mask[cell(round(px + (qx - px) * u), round(pz + (qz - pz) * u))]:
                land += 1
    print(f"[4/4] 경유지 {len(wp)}개 · 총 {length:.0f}블록 · 육지관통 샘플 {land}", file=sys.stderr)
    if land:
        sys.exit("검산 실패 — 항로가 육지를 지납니다. --erode 를 낮추거나 지형을 확인하세요.")

    if args.json:
        print(json.dumps([{"x": float(x), "z": float(z)} for x, z in wp], ensure_ascii=False, indent=2))
    else:
        for x, z in wp:
            print(f"{x} {z}")
        print(f"# {len(wp)} waypoints, {length:.0f} blocks", file=sys.stderr)


if __name__ == "__main__":
    main()
