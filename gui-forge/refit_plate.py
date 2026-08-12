#!/usr/bin/env python3
"""격자가 통째로 어긋난 판 손질 — 칸을 하나씩 옮기지 않고 **블록째 다시 앉힌다**.

## 어떤 판이 대상인가
칸마다 1~2px 벌어진 정도는 fit_sockets.py 가 메운다(상한 4px). 그보다 크게 틀어진 판,
특히 **피치 자체가 72 가 아닌** 판이 여기 대상이다. 2026-08-12 실측:
  · dextab    가로 피치 69.2 → 열마다 2.8px 씩 누적, 끝 열이 10px 밀림
  · dexisland 세로로 8px 밀림 + 가로 피치 70.6
  · iceshop   칸마다 색이 달라(티어 그라데이션) 액자 복제가 불가 — 개별 이동만 가능

## 하는 일
격자 액자를 **한 덩어리로 잘라** 가로·세로 배율과 위치를 목표 격자에 맞춰 다시 놓는다.
칸을 하나씩 옮기면 경계가 칸 수만큼 생기지만, 블록째 옮기면 경계가 블록 테두리 하나뿐이라
잘린 티가 덜 난다(분해창에서 칸별 이동이 티 났던 이유).

배율은 **첫 칸과 끝 칸의 구멍 중심 실측**에서 뽑는다 — 두 점을 목표 두 점으로 보내는
1차식이라 중간 칸도 따라온다.

사용: python3 refit_plate.py <판이름> [--check]
산출: src/<이름>/bg_source.png 를 덮어쓴다(원본은 .bak-refit 로 남긴다).
"""
import os
import shutil
import sys

from PIL import Image

import make_page_layouts as L

HERE = os.path.dirname(os.path.abspath(__file__))
S, GX, GY, CELL, COLS = L.SCALE, L.GRID_X, L.GRID_Y, L.CELL, L.COLS
ICON, PAD = 16 * S, 4

# 판: [(대상 슬롯들, 블록 상자, 배경을 떠올 이동량)]
#   블록 상자는 액자 바깥 장식까지 넉넉히 문다 — 좁으면 잘려 조각이 남는다(분해창 교훈).
#   배경 이동량은 **같은 결**이 이어지는 방향으로 잡는다(가로결이면 x 이동).
# 블록 상자가 None 이면 **칸마다 따로** 옮긴다 — 액자가 칸마다 다른 판(아이스박스 티어
# 그라데이션, 낱개로 떨어진 버튼)은 한 덩어리로 묶으면 사이의 배경까지 끌고 가 어색해진다.
SOLO_M = 13     # 낱개로 옮길 때 칸 둘레로 함께 물 여유(액자 테두리·장식)
GROUPS = {
    "dexisland": [
        (list(range(10, 17)) + list(range(19, 26)), (96, 136, 616, 300), (0, 170)),
        ([0, 4, 8], None, (0, 150)),
    ],
    # ★한 줄로 붙어 있는 진열대는 블록째 옮긴다. 낱개로 옮겼더니 이웃 액자를 파먹고
    #   메운 자리에 기둥·고드름이 복사돼 판이 망가졌다(2026-08-12).
    #   블록 이동은 액자를 복제하는 게 아니라 통째로 옮기는 것이라 티어별 색도 그대로 간다.
    "iceshop": [
        (list(range(18, 27)), (24, 216, 684, 330), (0, -150)),
        ([0], None, (0, 120)),
    ],
    "dextab": [
        ([s for r in range(4) for s in range(10 + r * 9, 17 + r * 9)],
         (96, 136, 616, 428), (0, 150)),
    ],
}


def cell_center(slot):
    r, c = divmod(slot, COLS)
    return (GX + CELL * c) * S + ICON // 2 + PAD, (GY + CELL * r) * S + ICON // 2 + PAD


def hole_center(px, w, h, cx, cy, th=22):
    """구멍 한가운데에서 사방으로 같은 색이 이어지는 범위 → 실제 중심."""
    ref = px[cx, cy]

    def go(dx, dy, lim=40):
        k = 0
        while k < lim:
            x, y = cx + dx * (k + 1), cy + dy * (k + 1)
            if not (0 <= x < w and 0 <= y < h) or abs(px[x, y] - ref) > th:
                break
            k += 1
        return k
    l, r, t, b = go(-1, 0), go(1, 0), go(0, -1), go(0, 1)
    return cx + (r - l) / 2, cy + (b - t) / 2


MIN_SPAN = 200      # 두 기준점이 이만큼은 떨어져야 배율을 믿는다


def solve(actual, target):
    """두 점을 목표 두 점으로 보내는 (배율, 이동).

    ★기준점이 가까우면(행이 두 줄뿐인 격자 등) 배율 추정이 불안정하다 — 실측 1px 오차가
      배율로 증폭돼 반대쪽 끝을 오히려 밀어낸다. 그럴 땐 배율 1 로 두고 평균만큼 옮긴다."""
    (a0, a1), (t0, t1) = actual, target
    if abs(a1 - a0) < MIN_SPAN:
        return 1.0, ((t0 - a0) + (t1 - a1)) / 2
    k = (t1 - t0) / (a1 - a0)
    return k, t0 - a0 * k


def refit(name, check=False):
    src = os.path.join(HERE, "src", name)
    path = os.path.join(src, "bg_source.png")
    im = Image.open(path).convert("RGB")
    px = im.convert("L").load()
    w, h = im.size

    for slots, box, heal in GROUPS[name]:
        xs = sorted({divmod(s, COLS)[1] for s in slots})
        ys = sorted({divmod(s, COLS)[0] for s in slots})
        first = next(s for s in slots if divmod(s, COLS) == (ys[0], xs[0]))
        last = next(s for s in slots if divmod(s, COLS) == (ys[-1], xs[-1]))
        fa = hole_center(px, w, h, *cell_center(first))
        la = hole_center(px, w, h, *cell_center(last))
        ft, lt = cell_center(first), cell_center(last)
        kx, dx = solve((fa[0], la[0]), (ft[0], lt[0]))
        ky, dy = solve((fa[1], la[1]), (ft[1], lt[1]))
        print(f"  {name} 격자 {len(slots)}칸 · 가로 배율 {kx:.4f} 이동 {dx:+.1f}"
              f" · 세로 배율 {ky:.4f} 이동 {dy:+.1f}")
        if check:
            continue

        if box is None:
            for slot in slots:
                cx, cy = cell_center(slot)
                a = hole_center(px, w, h, cx, cy)
                sx, sy = round(cx - a[0]), round(cy - a[1])
                if not (sx or sy):
                    continue
                bx0, by0 = cx - ICON // 2 - SOLO_M, cy - ICON // 2 - SOLO_M
                bx1, by1 = cx + ICON // 2 + SOLO_M, cy + ICON // 2 + SOLO_M
                piece = im.crop((bx0, by0, bx1, by1))
                hx, hy = heal
                im.paste(im.crop((bx0 + hx, by0 + hy, bx1 + hx, by1 + hy)), (bx0, by0))
                im.paste(piece, (bx0 + sx, by0 + sy))
            print(f"     낱개 {len(slots)}칸 개별 이동")
            continue

        x0, y0, x1, y1 = box
        block = im.crop(box)
        nw, nh = max(1, round((x1 - x0) * kx)), max(1, round((y1 - y0) * ky))
        block = block.resize((nw, nh), Image.LANCZOS)
        # 블록 왼쪽 위 모서리도 같은 1차식으로 옮긴다
        nx, ny = round(x0 * kx + dx), round(y0 * ky + dy)
        # ★옮기기 전에 원래 자리를 배경으로 덮는다 — 새 자리가 옛 자리를 다 가리지 못한다.
        hx, hy = heal
        im.paste(im.crop((x0 + hx, y0 + hy, x1 + hx, y1 + hy)), (x0, y0))
        im.paste(block, (nx, ny))

    if check:
        return
    if not os.path.exists(path + ".bak-refit"):
        shutil.copy2(path, path + ".bak-refit")
    im.save(path)
    print(f"  → {path}")


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    check = "--check" in sys.argv
    for name in (args or GROUPS):
        refit(name, check)


if __name__ == "__main__":
    main()
