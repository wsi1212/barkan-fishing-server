#!/usr/bin/env python3
"""칸 정렬 전수조사 — **번짐 판정(hole_probe)** 으로, **배포되는 그림**을 잰다.

## 왜 audit_all.py 를 안 쓰나
그건 '가장 급격한 경계' 판정이라 조립판(코드가 좌표를 잡아 0px 인 판)까지 -4/+4 로 읽고,
우편함은 49칸 전부 '액자없음'으로 넘겼다. 판정을 네 번 갈아엎은 끝에 남은 기준은 번짐이다.

## 두 가지를 따로 센다 — 섞으면 판단이 흐려진다
  · **중심 어긋남** : 구멍 한가운데와 아이템 상자 한가운데의 거리. 이게 유저가 보는 '어긋남'.
  · **구멍 크기**   : 액자 안쪽이 64px 인지. 작은 건 그림의 성질이라(아이템이 테두리에 살짝
                      걸침) 중심만 맞으면 격자는 고르게 보인다. 액자를 키우면 칸이 맞닿는다.

## 재는 대상
`_preview_full.png` — build_plate.py 가 타일로 자르기 **직전** 그림이다. 즉 화면에 나가는 것
그 자체다. 원본(bg_source)을 재면 인벤 격자를 덧그리기 전이라 실제와 다르다.

사용: python3 audit_holes.py [판이름 ...] [--csv]
"""
import os
import sys

from PIL import Image

import build_plate
import hole_probe as HP
import make_page_layouts as L

HERE = os.path.dirname(os.path.abspath(__file__))
S, GX, GY, CELL, COLS = L.SCALE, L.GRID_X, L.GRID_Y, L.CELL, L.COLS
ICON, PAD = 16 * S, 4
TOL = 1          # 중심이 이 이하로 벗어나면 합격(안티에일리어싱·반올림 여지)


def cells(name):
    """(이름, 중심x, 중심y) — 판 자체 칸 + 플레이어 인벤 칸(그것도 화면에 보인다)."""
    rows = build_plate.PLATES[name][0]
    _, roles, _ = L.PAGES[name]
    for slot, (role, _) in sorted(roles.items()):
        if role == "장식":
            continue
        r, c = divmod(slot, COLS)
        yield f"{slot}", (GX + CELL * c) * S + PAD + HP.HALF, (GY + CELL * r) * S + PAD + HP.HALF
    inv_y0 = 30 + rows * CELL
    for tag, gy in (("가방1", inv_y0), ("가방2", inv_y0 + CELL), ("가방3", inv_y0 + 2 * CELL),
                    ("단축바", inv_y0 + 58)):
        for c in range(COLS):
            yield f"{tag}{c}", (GX + CELL * c) * S + PAD + HP.HALF, gy * S + PAD + HP.HALF


def audit(name, rows_out):
    path = os.path.join(HERE, "src", name, "_preview_full.png")
    if not os.path.exists(path):
        print(f"  {name:12} 그림 없음 — build_plate.py 를 돌린 적이 없다")
        return
    im = Image.open(path).convert("L")
    px, (w, h) = im.load(), im.size
    off, small, lost = [], [], 0
    for key, cx, cy in cells(name):
        hb = HP.hole_bbox(px, w, h, cx, cy)
        if hb is None:
            lost += 1
            continue
        hx0, hy0, hx1, hy1 = hb
        # 중심 어긋남 — 구멍 한가운데가 아이템 상자 한가운데에서 얼마나 벗어났나
        dx = (hx0 + hx1 + 1) / 2 - cx
        dy = (hy0 + hy1 + 1) / 2 - cy
        hw, hh = hx1 - hx0 + 1, hy1 - hy0 + 1
        rows_out.append((name, key, round(dx, 1), round(dy, 1), hw, hh))
        if max(abs(dx), abs(dy)) > TOL:
            off.append((key, dx, dy))
        if min(hw, hh) < ICON - 2:
            small.append((key, hw, hh))
    mark = "✅" if not off else "⚠️"
    note = ""
    if small:
        ws = [a for _, a, _ in small] + [b for _, _, b in small]
        note = f" · 구멍이 64보다 작은 칸 {len(small)}(최소 {min(ws)}px)"
    print(f"  {mark} {name:12} 잰 칸 {len(rows_out) and sum(1 for r in rows_out if r[0] == name):3d}"
          f" · 중심 맞음 {sum(1 for r in rows_out if r[0] == name) - len(off):3d}"
          f" · 어긋남 {len(off):3d}"
          + (f" (최대 {max(max(abs(a), abs(b)) for _, a, b in off):.1f}px)" if off else "")
          + (f" · 액자 못 찾음 {lost}" if lost else "") + note)
    for key, dx, dy in off[:8]:
        print(f"       칸 {key}: x{dx:+.1f} y{dy:+.1f}")
    if len(off) > 8:
        print(f"       … 외 {len(off) - 8}칸")


def main():
    names = [a for a in sys.argv[1:] if not a.startswith("--")] or \
        [n for n in build_plate.PLATES if n in L.PAGES]
    print("칸 중심 정렬 (번짐 판정 · 허용 ±1px · 4배 기준)")
    out = []
    for n in names:
        audit(n, out)
    if "--csv" in sys.argv:
        with open(os.path.join(HERE, "audit_holes.csv"), "w") as f:
            f.write("plate,cell,dx,dy,hole_w,hole_h\n")
            for r in out:
                f.write(",".join(str(v) for v in r) + "\n")
        print(f"  → audit_holes.csv ({len(out)}칸)")


if __name__ == "__main__":
    main()
