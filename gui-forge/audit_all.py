#!/usr/bin/env python3
"""칸 정렬 전수조사 — 모든 전용 판 + 바닐라 인벤토리를 한 기준으로 잰다.

## 왜 또 만들었나
앞선 두 도구가 각각 다른 이유로 놓쳤다.
  · audit_slots.py  : '첫 급격한 변화'를 경계로 봐서, 구멍 안쪽 음영을 경계로 오인
  · fit_sockets.py  : '중앙과 비슷한 색이 이어지는 깊이'라 그 음영에서 조기에 끊김
                      → 인벤토리 45칸이 전부 0px 로 보였는데 실제로는 1~2px 씩 벌어져 있었다
                      (2026-08-12 유저가 확대해서 잡아냄)

## 판정 — 가장 급격한 경계
칸 한가운데에서 바깥으로 한 픽셀씩 나가며 **이웃 픽셀과의 밝기 차가 가장 큰 자리**를
액자 안쪽 모서리로 본다. 액자는 구멍과 대비가 크고(밝든 어둡든) 음영은 완만해서,
'밝은 데가 액자' 같은 가정 없이 어느 판에서나 통한다.
찾는 범위는 아이템 상자 경계 ±LOOK 으로 좁힌다 — 멀리 있는 장식에 속지 않게.

## 좌우 비대칭 주의
아이콘 상자는 64px 이고 중심이 픽셀 위에 있어 **중심에서 왼·위로 32칸, 오른·아래로
31칸**이다. 바깥 첫 픽셀은 왼·위 33 · 오른·아래 32. 양쪽 다 32 로 재면 왼·위가 늘
+1 로 나와 멀쩡한 칸을 밀어버린다(그 실수로 인벤 46칸을 1px 씩 파먹었다).

사용: python3 audit_all.py [판이름 ...]      (기본: 전부 + inventory)
"""
import os
import sys
from collections import Counter

from PIL import Image

import build_plate
import make_page_layouts as L

HERE = os.path.dirname(os.path.abspath(__file__))
S, GX, GY, CELL, COLS = L.SCALE, L.GRID_X, L.GRID_Y, L.CELL, L.COLS
ICON = 16 * S               # 64
HALF = ICON // 2            # 32
LOOK = 7                    # 상자 경계에서 이만큼 안팎만 훑는다
TOL = 1                     # 이 이하는 안티에일리어싱으로 보고 합격


def edge(px, w, h, mx, my, dx, dy, base, med, thr):
    """중심에서 (dx,dy) 로 나가며 **구멍 색에서 확연히 벗어나는 첫 자리** → base 와의 차.

    구멍 안쪽 질감·음영에 속지 않으려고 임계를 구멍의 산포(표준편차)에서 뽑는다."""
    for k in range(1, HALF + LOOK + 2):
        x, y = mx + dx * k, my + dy * k
        if not (0 <= x < w and 0 <= y < h):
            return None
        if abs(px[x, y] - med) > thr:
            return k - base if abs(k - base) <= LOOK else None
    return None


def hole_stats(px, x0, y0):
    """구멍 대표 밝기와 임계 — 상자 안쪽만 본다(테두리를 섞지 않으려 여백을 크게 둔다)."""
    vals = [px[x0 + 12 + i, y0 + 12 + j] for i in range(0, ICON - 24, 3)
            for j in range(0, ICON - 24, 3)]
    vals.sort()
    med = vals[len(vals) // 2]
    sd = (sum((v - med) ** 2 for v in vals) / len(vals)) ** 0.5
    return med, max(16, 3.2 * sd)


def measure(px, w, h, x0, y0):
    """(왼, 오른, 위, 아래). + 는 구멍이 상자보다 큼(틈), - 는 액자가 상자를 침범."""
    mx, my = x0 + HALF, y0 + HALF
    med, thr = hole_stats(px, x0, y0)
    return (edge(px, w, h, mx, my, -1, 0, 33, med, thr), edge(px, w, h, mx, my, 1, 0, 32, med, thr),
            edge(px, w, h, mx, my, 0, -1, 33, med, thr), edge(px, w, h, mx, my, 0, 1, 32, med, thr))


def plate_slots(name):
    _, roles, _ = L.PAGES[name]
    for slot, (role, _) in sorted(roles.items()):
        if role == "장식":
            continue
        r, c = divmod(slot, COLS)
        yield slot, (GX + CELL * c) * S, (GY + CELL * r) * S


def audit(name, path, slots):
    if not os.path.exists(path):
        print(f"  {name:12} 원본 없음")
        return None
    im = Image.open(path).convert("L")
    px, (w, h) = im.load(), im.size
    bad, flat, tally = [], 0, Counter()
    for key, x0, y0 in slots:
        m = measure(px, w, h, x0, y0)
        if None in m:
            flat += 1
            continue
        worst = max(abs(v) for v in m)
        tally[worst] += 1
        if worst > TOL:
            bad.append((key, m))
    total = len(list(slots)) if isinstance(slots, list) else None
    n = sum(tally.values())
    mark = "✅" if not bad else "⚠️"
    print(f"  {mark} {name:12} 칸 {n + flat:3d} · 일치 {n - len(bad):3d} · 어긋남 {len(bad):3d}"
          f" · 액자없음 {flat:3d}" + (f" · 최대 {max(max(abs(v) for v in m) for _, m in bad)}px" if bad else ""))
    for key, m in bad[:6]:
        print(f"       칸 {key}: 왼{m[0]:+d} 오{m[1]:+d} 위{m[2]:+d} 아{m[3]:+d}")
    if len(bad) > 6:
        print(f"       … 외 {len(bad) - 6}칸")
    return bad


def main():
    names = sys.argv[1:] or [n for n in build_plate.PLATES if n in L.PAGES]
    print("판별 칸 정렬 (허용 ±1px, 4배 기준)")
    for name in names:
        rows, prefix, code0, *rest = build_plate.PLATES[name]
        src = os.path.join(HERE, "src", name)
        path = next((os.path.join(src, f) for f in ("bg_fitted.png", rest[0] if rest else "bg_source.png")
                     if os.path.exists(os.path.join(src, f))), os.path.join(src, "bg_source.png"))
        audit(name, path, list(plate_slots(name)))

    if not sys.argv[1:]:
        import make_inventory_layout as IL
        inv = os.path.expanduser("~/development/barkan-resourcepack/assets/minecraft/textures/gui/container/inventory.png")
        slots = [(f"{n}{i}", x * S, y * S) for n, group in
                 (("방어구", IL.ARMOR), ("보조손", IL.OFFHAND), ("조합", IL.CRAFT),
                  ("결과", IL.RESULT), ("가방", IL.BAG), ("단축바", IL.HOTBAR))
                 for i, (x, y) in enumerate(group)]
        audit("inventory", inv, slots)


if __name__ == "__main__":
    main()
