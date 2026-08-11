#!/usr/bin/env python3
"""prod 아우라 레퍼런스(초록/빨강 조각상) → 직선 리그 좌표의 아우라 셀 추출.

레퍼런스: prod flatroom (aura_w/aura_e.json 스캔). 초록 조각상(라임 유리)·빨강 조각상(빨간 유리)의
불꽃 다발(tuft)을 "척추 호길이 s + 좌우 오프셋 + 다발 내부 모양(로컬 프레임)"으로 수치화하고,
직선 빌드(straight_imugi_blocks.json)의 같은 s 위치 등마루에 재배치한다.
보라(3페)는 유저 위임(“너가 만들어서”) — 초록+빨강 레이아웃 합집합(가장 화려)으로 생성.

출력: aura_straight.json { "green": [[x,y,z],...], "red": ..., "purple": ... } (직선 빌드 월드좌표)
"""
import json, math, os
from collections import deque

HERE = os.path.dirname(os.path.abspath(__file__))
BODY_MATS = {"stripped_warped_hyphae", "prismarine", "prismarine_slab", "prismarine_wall",
             "dark_prismarine", "dark_prismarine_slab", "dark_prismarine_stairs",
             "red_nether_brick_slab", "red_nether_brick_stairs", "smooth_quartz_stairs",
             "white_wool", "lime_wool", "red_wool", "polished_blackstone_brick_wall",
             "sea_lantern", "end_portal_frame", "ender_chest"}

cells = {}
for f in ("aura_w.json", "aura_e.json"):
    for b in json.load(open(os.path.join(HERE, f)))["blocks"]:
        cells[(b["x"], b["y"], b["z"])] = b["material"].replace("minecraft:", "")

def neighbors(c, r=1):
    x, y, z = c
    for dx in range(-r, r + 1):
        for dy in range(-r, r + 1):
            for dz in range(-r, r + 1):
                if dx or dy or dz:
                    yield (x + dx, y + dy, z + dz)

# ---- 조각상 분리 ----
# 초록 조각상: z<-120 & x<66 (원본은 z>=-120 서쪽 열) / 빨강: x>=66 & z<-120
def statue_body(pred):
    return {c for c, m in cells.items() if m in BODY_MATS and pred(c)}

green_body = statue_body(lambda c: c[0] < 66 and c[2] <= -121)
red_body = statue_body(lambda c: c[0] >= 66 and c[2] <= -121)
green_glass = [c for c, m in cells.items() if m == "lime_stained_glass"]
red_glass = [c for c, m in cells.items() if m == "red_stained_glass"]
print(f"green: body {len(green_body)} glass {len(green_glass)} / red: body {len(red_body)} glass {len(red_glass)}")

def head_seed(body):
    eyes = [c for c in body if cells[c] == "ender_chest"]
    assert eyes, "head(eyes) not found"
    return eyes

def geodesic(body, seeds):
    d = {c: 0 for c in seeds}
    q = deque(seeds)
    while q:
        cur = q.popleft()
        for n in neighbors(cur):
            if n in body and n not in d:
                d[n] = d[cur] + 1
                q.append(n)
    # 미도달(분리) 셀은 최근접 도달셀 값
    for c in body:
        if c not in d:
            d[c] = min((abs(c[0]-k[0])+abs(c[1]-k[1])+abs(c[2]-k[2]) + v for k, v in d.items()),
                       default=0)
    mx = max(d.values()) or 1
    return {c: v / mx for c, v in d.items()}

def tangent_at(body, c, rad=3):
    pts = [p for p in body if abs(p[0]-c[0]) <= rad and abs(p[1]-c[1]) <= rad and abs(p[2]-c[2]) <= rad]
    if len(pts) < 3: return (0.0, 1.0)
    mx = sum(p[0] for p in pts) / len(pts); mz = sum(p[2] for p in pts) / len(pts)
    sxx = sum((p[0]-mx)**2 for p in pts); szz = sum((p[2]-mz)**2 for p in pts)
    sxz = sum((p[0]-mx)*(p[2]-mz) for p in pts)
    # 2D 공분산 주축 (수평 접선)
    th = 0.5 * math.atan2(2*sxz, sxx - szz)
    return (math.cos(th), math.sin(th))

def extract(body, glass, label):
    s_of = geodesic(body, head_seed(body))
    # 유리 다발(연결성분, 26이웃 r=2 — 떠 있는 불꽃 포함)
    left = set(glass); tufts = []
    while left:
        seed = left.pop(); comp = [seed]; q = deque([comp])
        q = deque([seed])
        while q:
            cur = q.popleft()
            for n in neighbors(cur, 2):
                if n in left:
                    left.remove(n); comp.append(n); q.append(n)
        tufts.append(comp)
    out = []
    for comp in tufts:
        base = min(comp, key=lambda c: (c[1], ))  # 최저 셀 = 다발 뿌리
        anchor = min(body, key=lambda b: (b[0]-base[0])**2 + (b[1]-base[1])**2 + (b[2]-base[2])**2)
        s = s_of[anchor]
        tx, tz = tangent_at(body, anchor)         # 수평 접선
        lxv, lzv = -tz, tx                        # 수평 좌우(법선)
        gap = base[1] - anchor[1]                 # 뿌리와 몸 사이 세로 간격(떠 있는 불꽃 보존)
        cellsL = []
        for c in comp:
            ox, oy, oz = c[0]-base[0], c[1]-base[1], c[2]-base[2]
            along = ox*tx + oz*tz
            lat = ox*lxv + oz*lzv
            cellsL.append((round(lat), oy, round(along)))
        # 앵커의 좌우 오프셋(척추에서 얼마나 옆인가) — 몸 국소 중심 대비
        near = [p for p in body if abs(p[0]-anchor[0]) <= 2 and abs(p[2]-anchor[2]) <= 2 and abs(p[1]-anchor[1]) <= 3]
        cx = sum(p[0] for p in near)/len(near); cz = sum(p[2] for p in near)/len(near)
        alat = (anchor[0]-cx)*lxv + (anchor[2]-cz)*lzv
        out.append({"s": round(s, 4), "lat": round(alat, 2), "gap": gap, "cells": cellsL, "n": len(comp)})
        print(f"  [{label}] tuft n={len(comp):2d} s={s:.2f} lat={alat:+.1f} gap={gap}")
    return out

print("tuft 추출:")
gT = extract(green_body, green_glass, "G")
rT = extract(red_body, red_glass, "R")

# ---- 직선 빌드에 재배치 ----
straight = {(b["x"], b["y"], b["z"]) for b in json.load(open(os.path.join(HERE, "straight_imugi_blocks.json")))}
# 직선 머리 = z 최대쪽. 지오데식 s (머리→꼬리)
zmax = max(c[2] for c in straight)
seeds = [c for c in straight if c[2] >= zmax - 1]
sS = geodesic(straight, seeds)
SPINE_X = 120.5

def place(tufts):
    placed = set()
    for t in tufts:
        # 같은 s의 직선 몸 셀 중, 요청 좌우(lat)에 가장 가까운 '등(top)' 셀
        cand = [c for c in straight if abs(sS[c] - t["s"]) < 0.03]
        if not cand:
            cand = sorted(straight, key=lambda c: abs(sS[c] - t["s"]))[:40]
        tops = [c for c in cand if (c[0], c[1] + 1, c[2]) not in straight]
        if not tops: tops = cand
        want_x = SPINE_X + t["lat"]
        anchor = max(tops, key=lambda c: (c[1], -abs(c[0] + 0.5 - want_x)))
        bx, by, bz = anchor[0], anchor[1] + 1 + max(0, t["gap"] - 1), anchor[2]
        for lat, oy, along in t["cells"]:
            # ★가로형(2026-07-10, 유저 피드백): 원래 세로로 솟던 불꽃(oy=수직) 다발을 along축 기준
            # 90° 눕혀 lat/oy를 교환 — 위로 치솟던 모양이 옆으로 퍼지는 리본이 된다("세로→가로").
            # 얇은 두께만 남기려 새 수직폭은 축소(0.4배), 새 좌우폭은 원래 높이를 그대로 사용.
            nlat = round(oy * 0.7)
            noy = round(lat * 0.4)
            p = (bx + nlat, by + noy, bz + along)   # 직선 접선=+z, 좌우=+x
            if p not in straight:
                placed.add(p)
    return sorted(placed)

green_cells = place(gT)
red_cells = place(rT)
purple_cells = sorted(set(green_cells) | set(red_cells))  # 3페 = 합집합(최대 화력) — 유저 위임 디자인
out = {"green": [list(c) for c in green_cells],
       "red": [list(c) for c in red_cells],
       "purple": [list(c) for c in purple_cells]}
json.dump(out, open(os.path.join(HERE, "aura_straight.json"), "w"))
print(f"\n직선 좌표 아우라: green {len(green_cells)} / red {len(red_cells)} / purple {len(purple_cells)}")
print("saved aura_straight.json")
