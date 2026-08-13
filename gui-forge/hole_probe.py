#!/usr/bin/env python3
"""칸 구멍을 **번짐(flood fill)** 으로 찾는다 — 정렬 판정의 공용 기준.

## 왜 또 만들었나
지금까지 판정을 네 번 갈아엎었고 그때마다 다른 이유로 틀렸다.
  · '어두운 데가 구멍'      → 판마다 액자가 밝기도 어둡기도 해 절반이 오측
  · '중앙과 비슷한 색의 깊이' → 구멍 가장자리 음영에서 조기에 끊겨 전부 0px 로 보임
  · '가장 급격한 경계'       → 구멍 안 질감의 점 하나를 경계로 오인
  · '구멍 통계 + 임계'       → 나아졌지만 분해창(정확한 판)에서 오검출

번짐은 **연결성**을 보므로 질감·음영·액자 밝기에 휘둘리지 않는다. 칸 한가운데에서
비슷한 색으로 이어지는 영역을 채우고 그 상자를 구멍으로 본다 — 사람이 보는 것과 같다.

## 좌우 비대칭
아이콘 상자는 64px 이고 중심이 픽셀 위에 있어 왼·위로 32, 오른·아래로 31 이다.
그래서 상자는 [cx-32, cx+31] — 이 표현을 쓰는 쪽에서 헷갈리지 않게 여기서 상자를 만든다.
"""
from collections import deque

ICON = 64
HALF = ICON // 2


def icon_box(cx, cy):
    """칸 중심 (cx,cy) 의 아이템 상자 (x0,y0,x1,y1) — 끝값 포함."""
    return cx - HALF, cy - HALF, cx + HALF - 1, cy + HALF - 1


def hole_bbox(px, w, h, cx, cy, tol=26, span=HALF + 10):
    """칸 중앙에서 번져 나가 구멍 상자를 찾는다. 못 찾으면 None.

    tol  : 중앙 색과 이만큼 이내면 같은 구멍으로 본다
    span : 중앙에서 이 거리까지만 본다(옆 칸으로 새지 않게)
    """
    ref = px[cx, cy]
    x0 = max(0, cx - span); x1 = min(w - 1, cx + span)
    y0 = max(0, cy - span); y1 = min(h - 1, cy + span)
    seen = {(cx, cy)}
    q = deque([(cx, cy)])
    minx = maxx = cx
    miny = maxy = cy
    while q:
        x, y = q.popleft()
        if x < minx: minx = x
        if x > maxx: maxx = x
        if y < miny: miny = y
        if y > maxy: maxy = y
        for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
            if x0 <= nx <= x1 and y0 <= ny <= y1 and (nx, ny) not in seen:
                if abs(px[nx, ny] - ref) <= tol:
                    seen.add((nx, ny))
                    q.append((nx, ny))
    # 번짐이 칸을 넘어 새어 나갔으면(액자가 끊긴 칸) 믿지 않는다
    if maxx - minx > 2 * span - 4 or maxy - miny > 2 * span - 4:
        return None
    if maxx - minx < 20 or maxy - miny < 20:
        return None
    return minx, miny, maxx, maxy


def delta(px, w, h, cx, cy, **kw):
    """(왼, 오른, 위, 아래) — + 는 구멍이 아이템 상자보다 큼(틈), - 는 액자가 상자를 덮음."""
    hb = hole_bbox(px, w, h, cx, cy, **kw)
    if hb is None:
        return None
    ix0, iy0, ix1, iy1 = icon_box(cx, cy)
    hx0, hy0, hx1, hy1 = hb
    return ix0 - hx0, hx1 - ix1, iy0 - hy0, hy1 - iy1
