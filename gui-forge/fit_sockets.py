#!/usr/bin/env python3
"""칸 틈 메우기 — 모든 판의 모든 칸에서 액자 구멍을 아이콘 상자(64px)까지 좁힌다.

## 무엇이 문제였나
아이콘은 셀 왼쪽 위 +4px 에서 64x64 로 그려진다. 액자 구멍이 그보다 크면 아이콘과 액자
사이에 **틈**이 남는다. 1~4px(=0.25~1 GUI px)라 겹쳐보기 그림으로는 안 보이고 확대하면
바로 보인다(2026-08-10 유저 제보 → 전 판 전수조사).

## 재는 법 — 이것만 믿는다
칸 한가운데 밝기를 '구멍 기준(ref)'으로 두고, 아이콘 상자 바로 바깥부터 한 픽셀씩
바깥으로 보며 **ref 와 12 이내로 같은** 픽셀이 몇 개 이어지는지 센다. 그 개수가 틈이다.

지표를 다섯 번 갈아엎고 나온 결론이다. 실패한 것들과 이유:
  · '어두운 데가 구멍'    → 판마다 액자가 밝기도 어둡기도 해 절반이 오측
  · '밝은 데가 액자'      → 배경 나뭇결 하이라이트를 액자로 오인(±35px 같은 헛값)
  · 가운데 기준 ±30% 대비 → 칸 안쪽 그라데이션을 액자로 오인, 거의 모든 칸을 상한까지 밀어버림
  · 구멍 폭 자체를 재기   → 입체 그림자·칸 사이 구분선이 경계로 잡힘
'ref 와 거의 같은가'만 보는 이 판정은 열다섯 판의 실제 픽셀 값을 눈으로 대조해 검증했다.

## 메우는 법
바깥 띠를 통째로 안으로 민다. ★한 줄만 복사하면 경계의 중간톤에서 제자리걸음한다.
**안으로만** 민다 — 밖으로 미는 건 칸 사이 구분선을 먹어치워서 안 한다. 그래서 구멍이
아이콘보다 **작은**(아이콘이 테두리를 덮는) 칸은 그냥 둔다. 그건 틈이 아니다.

사용: python3 fit_sockets.py [판이름 ...]      (기본: 전부)
산출: src/<이름>/bg_fitted.png — ★원본은 안 건드린다. build_plate.py 가 있으면 우선 쓴다.
      결과가 마음에 안 들면 이 파일만 지우면 원래대로다.
"""
import os
import sys

from PIL import Image

import build_plate
import make_page_layouts as L

HERE = os.path.dirname(os.path.abspath(__file__))
S, GX, GY, CELL, COLS = L.SCALE, L.GRID_X, L.GRID_Y, L.CELL, L.COLS
N, ICON = CELL * S, 16 * S          # 72, 64
PAD = (N - ICON) // 2               # 4
SAME = 12                           # ref 와 이만큼 이내면 '구멍과 같은 색'
PROBE = 12                          # 이만큼 바깥까지 훑어 액자 안쪽 모서리를 찾는다
NO_SOCKET = 10                      # 이만큼 훑어도 경계가 없으면 그 칸엔 액자가 없다
# ★칸 경계를 넘어 떠오는 것을 허용한다. 아이콘 상자와 셀 경계 사이는 4px 뿐이라
#   4px 로 묶어두면 5~7px 밀린 액자(판 바깥줄 칸들)를 못 고친다. 대신 액자가 아예 없는
#   칸(평평한 목록판)은 건드리지 않는다 — 거기서 밀면 옆 칸을 끌어와 그림이 망가진다.


def gap_depths(px, w, h, x0, y0):
    """(왼, 오른, 위, 아래) 액자 안쪽 모서리가 아이콘 상자 밖으로 나간 거리."""
    ix0, iy0 = x0 + PAD, y0 + PAD
    ix1, iy1 = ix0 + ICON - 1, iy0 + ICON - 1
    mx, my = ix0 + ICON // 2, iy0 + ICON // 2
    ref = px[mx, my]

    def depth(pts):
        d = 0
        for x, y in pts:
            if not (0 <= x < w and 0 <= y < h) or abs(px[x, y] - ref) >= SAME:
                break
            d += 1
        return d

    return (depth([(ix0 - 1 - k, my) for k in range(PROBE)]),
            depth([(ix1 + 1 + k, my) for k in range(PROBE)]),
            depth([(mx, iy0 - 1 - k) for k in range(PROBE)]),
            depth([(mx, iy1 + 1 + k) for k in range(PROBE)]))


def fit_cell(im, slot):
    """액자 안쪽 모서리를 아이콘 상자에 맞춘다. (민 양, 액자없음 여부)"""
    w, h = im.size
    r, c = divmod(slot, COLS)
    x0, y0 = (GX + CELL * c) * S, (GY + CELL * r) * S
    l, rt, t, b = gap_depths(im.convert("L").load(), w, h, x0, y0)
    if max(l, rt, t, b) >= NO_SOCKET:
        return 0, True                    # 평평한 판 — 맞출 액자가 없다
    ix0, iy0 = x0 + PAD, y0 + PAD
    ix1, iy1 = ix0 + ICON - 1, iy0 + ICON - 1
    # 바깥 띠를 통째로 안으로 민다. 떠오는 쪽은 셀을 넘어가도 된다(판 바깥줄·구분선).
    if l:
        im.paste(im.crop((max(0, x0 - l), y0, ix0 - l, y0 + N)), (max(0, x0 - l) + l, y0))
    if rt:
        im.paste(im.crop((ix1 + 1 + rt, y0, min(w, x0 + N + rt), y0 + N)), (ix1 + 1, y0))
    if t:
        im.paste(im.crop((x0, max(0, y0 - t), x0 + N, iy0 - t)), (x0, max(0, y0 - t) + t))
    if b:
        im.paste(im.crop((x0, iy1 + 1 + b, x0 + N, min(h, y0 + N + b))), (x0, iy1 + 1))
    return max(l, rt, t, b), False


def fit(name):
    rows, prefix, code0, *rest = build_plate.PLATES[name]
    fname = rest[0] if rest else "bg_source.png"
    path = os.path.join(HERE, "src", name, fname)
    if not os.path.exists(path):
        print(f"  {name:12} 원본 없음")
        return
    im = Image.open(path).convert("RGBA")
    _, roles, _ = L.PAGES[name]
    slots = [s for s, (role, _) in roles.items() if role != "장식"]
    fixed = worst = flat = 0
    for slot in slots:
        d, no_socket = fit_cell(im, slot)
        if no_socket:
            flat += 1
        elif d:
            fixed += 1
            worst = max(worst, d)
    im.convert("RGB").save(os.path.join(HERE, "src", name, "bg_fitted.png"))
    print(f"  {name:12} 칸 {len(slots):3d} · 틈 메움 {fixed:3d} · 최대 {worst}px"
          + (f" · 액자없는 칸 {flat}" if flat else ""))


def main():
    for n in (sys.argv[1:] or [x for x in build_plate.PLATES if x in L.PAGES]):
        fit(n)


if __name__ == "__main__":
    main()
