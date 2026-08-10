#!/usr/bin/env python3
"""칸 정렬 전수조사 — 액자 구멍이 아이콘 상자(64px)와 정확히 맞는지 모든 판·모든 칸에서 잰다.

## 무엇을 재나
아이콘은 셀 왼쪽 위 +4px 에서 64x64 로 그려진다(바닐라가 칸 테두리 1px 를 두므로).
액자 구멍(어두운 안쪽)이 그보다 **크면 틈**, **작으면 아이콘이 테두리를 덮는다.**
네 변 각각의 차이를 px(4배 기준)로 낸다 — +는 구멍이 더 큼(틈), -는 더 작음(겹침).

## 왜 눈으로 안 되나
2px(=0.5 GUI px) 는 겹쳐보기 그림으로 안 보인다. 실제로 NPC 대화창에서 놓쳤고
유저가 확대해서 잡아냈다(2026-08-10). 그래서 숫자로 만든다.

## 재는 법
칸 안쪽만 본다(셀 경계 밖은 옆 칸이다). 셀 중앙을 지나는 가로·세로 한 줄에서
**셀 중심을 포함하는 가장 긴 어두운 구간**을 구멍으로 본다. 칸 밖 배경의 어두움이나
입체 그림자에 속지 않으려면 이 '중심을 포함하는 연속 구간' 조건이 필요하다.

사용: python3 audit_slots.py [판이름 ...]      (기본: 전부)
"""
import os
import sys

from PIL import Image

import build_plate
import make_page_layouts as L

HERE = os.path.dirname(os.path.abspath(__file__))
S, GX, GY, CELL, COLS = L.SCALE, L.GRID_X, L.GRID_Y, L.CELL, L.COLS
ICON = 16 * S            # 64
PAD = (CELL * S - ICON) // 2      # 4 — 칸 테두리
TOL = 1                  # 이 이하 차이는 합격으로 본다(안티에일리어싱 경계)


def inner_edge(vals, center, step, thr):
    """가운데에서 바깥으로 훑어 **액자 안쪽 모서리**(첫 급격한 밝기 변화)를 찾는다.

    ★어두운 구멍/밝은 구멍을 가리지 않는다. 판마다 액자가 밝은 것도(놋쇠) 어두운 것도
      있어서, '어두운 데가 구멍' 같은 가정을 두면 절반이 오측된다(2026-08-10 첫 판정 실패).
    """
    i = center
    while 0 < i < len(vals) - 1:
        j = i + step
        if j < 0 or j >= len(vals):
            return None
        if abs(vals[j] - vals[i]) > thr:
            return i                     # i 까지가 구멍, j 부터 액자
        i = j
    return None


def measure(im, slot):
    """(왼, 오른, 위, 아래) 차이. + 는 구멍이 아이콘보다 큼(틈), - 는 겹침."""
    px = im.load()
    r, c = divmod(slot, COLS)
    x0, y0 = (GX + CELL * c) * S, (GY + CELL * r) * S
    n = CELL * S
    row = [px[x0 + i, y0 + n // 2] for i in range(n)]
    col = [px[x0 + n // 2, y0 + j] for j in range(n)]
    out = []
    for vals, lo_first in ((row, True), (col, True)):
        thr = max(18, (max(vals) - min(vals)) * 0.30)
        a = inner_edge(vals, n // 2, -1, thr)
        b = inner_edge(vals, n // 2, +1, thr)
        if a is None or b is None:
            return None
        out += [PAD - a, b - (PAD + ICON - 1)]
    return out[0], out[1], out[2], out[3]


def audit(name):
    rows, prefix, code0, *rest = build_plate.PLATES[name]
    fname = rest[0] if rest else "bg_source.png"
    path = os.path.join(HERE, "src", name, fname)
    if not os.path.exists(path):
        print(f"  {name:12} 원본 없음 ({fname})")
        return None
    im = Image.open(path).convert("L")
    _, roles, _ = L.PAGES[name]
    gaps, overs, skipped, worst = [], [], 0, 0
    for slot, (role, _) in roles.items():
        if role == "장식":
            continue
        m = measure(im, slot)
        if m is None:
            skipped += 1
            continue
        for d in m:
            if d > TOL:
                gaps.append((slot, d))
            elif d < -TOL:
                overs.append((slot, d))
            worst = max(worst, abs(d))
    total = sum(1 for r, _ in roles.values() if r != "장식")
    ok = total - skipped - len({s for s, _ in gaps} | {s for s, _ in overs})
    print(f"  {name:12} 칸 {total:3d}  일치 {ok:3d}  틈 {len({s for s, _ in gaps}):3d}"
          f"  겹침 {len({s for s, _ in overs}):3d}  못잼 {skipped:3d}  최대 {worst:.0f}px")
    return {"name": name, "gaps": gaps, "overs": overs, "skipped": skipped, "worst": worst}


def main():
    names = sys.argv[1:] or [n for n in build_plate.PLATES if n in L.PAGES]
    print("판           칸수  일치   틈  겹침 못잼  최대   (+틈 / -겹침, 4배 px · 허용 ±1)")
    for n in names:
        audit(n)


if __name__ == "__main__":
    main()
