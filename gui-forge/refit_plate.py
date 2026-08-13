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

from math import ceil

from PIL import Image

import build_plate
import hole_probe as HP
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
    # 2026-08-12 재발주분. 격자가 판 가운데 떠 있어 좌우 여백이 넉넉하다 — 블록을 옮겨도
    # 경첩·기둥을 안 건드린다(이전 아트가 막혔던 지점).
    "dexisland": [
        (list(range(10, 17)) + list(range(19, 26)), (100, 140, 610, 290), None),
        ([0, 4, 8], None, None),
    ],
    "dextab": [
        (list(range(10, 17)) + list(range(19, 26)) + list(range(28, 35)) + list(range(37, 44)),
         (30, 66, 682, 530), None),
        # ★상단·하단 버튼을 낱개 그룹에 넣지 말 것 — 이 아트는 9x6 전체 격자라 그것들도
        #   위 블록에 이미 들어 있다. 낱개로 또 옮기면 이중 이동이 된다(실측 11.5px).
        #   예외는 48 하나 — 하단 계단이 우리 슬롯과 한 칸 어긋나게 그려졌다.
        ([48], None, None),
    ],
    # 우편함 본문 45칸 — 세로 피치가 촘촘해 행마다 -21~-9px 로 밀린다. 액자를 칸별로
    # 떠서 옮기면 자른 조각에 위 칸 테두리가 딸려와 칸 위에 선이 하나 더 생겼다(실측).
    # 블록째 세로로 늘리면 피치 자체가 72 가 되고 이웃이 섞일 일이 없다.
    "mailbox": [
        (list(range(45)), (24, 92, 680, 452), None),
    ],
    "iceshop": [
        (list(range(18, 27)), (24, 216, 684, 330), None),
        ([0], None, None),
    ],
    # 대장간 결과칸 하나 — 소켓이 아이템 자리보다 4px 왼쪽에 그려져 있다. 칸이 하나뿐이라
    # 자동 블록(4칸 이상)이 안 잡혀 여태 손대지 못했다. 둘레가 균일한 어두운 벽이라
    # 낱개 이동으로 티가 안 난다.
    "smithy": [
        ([8], None, None),
    ],
}


def cell_center(slot):
    r, c = divmod(slot, COLS)
    return (GX + CELL * c) * S + ICON // 2 + PAD, (GY + CELL * r) * S + ICON // 2 + PAD


def hole_center(px, w, h, cx, cy):
    """구멍의 실제 중심. 판정은 hole_probe(번짐) 에 맡긴다 — 질감·음영에 안 휘둘린다.

    ★+1 을 더해야 한다. 픽셀 [a..b] 가 차지하는 실제 구간은 [a, b+1] 이라 중심은 (a+b+1)/2 다.
      (a+b)/2 로 두면 늘 0.5px 위·왼쪽으로 치우친 답이 나오고, 그만큼 격자를 밀어버린다.
      아이템 상자도 [x0+4 .. x0+67] → 중심 x0+36 = cell_center 라 목표는 그대로 맞다."""
    hb = HP.hole_bbox(px, w, h, cx, cy)
    if hb is None:
        return cx, cy          # 액자를 못 찾으면 '이미 맞다'로 두고 건드리지 않는다
    hx0, hy0, hx1, hy1 = hb
    return (hx0 + hx1 + 1) / 2, (hy0 + hy1 + 1) / 2


MIN_SPAN = 200      # 두 기준점이 이만큼은 떨어져야 배율을 믿는다
PASSES = 3          # 되재고 고치는 횟수(보통 2차에서 끝난다)
SETTLED = 0.9       # 남은 오차가 이 아래면 그만둔다 — 4배 판이라 1px = 0.25 GUI px


def solve(actual, target):
    """두 점을 목표 두 점으로 보내는 (배율, 이동).

    ★기준점이 가까우면(행이 두 줄뿐인 격자 등) 배율 추정이 불안정하다 — 실측 1px 오차가
      배율로 증폭돼 반대쪽 끝을 오히려 밀어낸다. 그럴 땐 배율 1 로 두고 평균만큼 옮긴다."""
    (a0, a1), (t0, t1) = actual, target
    if abs(a1 - a0) < MIN_SPAN:
        return 1.0, ((t0 - a0) + (t1 - a1)) / 2
    k = (t1 - t0) / (a1 - a0)
    return k, t0 - a0 * k


AUTO_M = 18      # 자동 블록이 슬롯 격자 밖으로 무는 여유(액자 테두리·장식)


def auto_groups(name):
    """GROUPS 에 없는 판용 — 쓰는 칸 전체를 한 블록으로 잡는다."""
    _, roles, _ = L.PAGES[name]
    slots = sorted(s for s, (r, _) in roles.items() if r != "장식")
    if len(slots) < 4:
        return []
    rc = [divmod(s, COLS) for s in slots]
    r0, r1 = min(r for r, _ in rc), max(r for r, _ in rc)
    c0, c1 = min(c for _, c in rc), max(c for _, c in rc)
    box = ((GX + CELL * c0) * S - AUTO_M, (GY + CELL * r0) * S - AUTO_M,
           (GX + CELL * (c1 + 1)) * S + AUTO_M, (GY + CELL * (r1 + 1)) * S + AUTO_M)
    return [(slots, box, None)]


def refit(name, check=False):
    path = build_plate.source_path(name)     # ★굽는 파일과 같은 걸 고쳐야 반영된다
    im = Image.open(path).convert("RGB")
    px = im.convert("L").load()
    w, h = im.size

    for slots, box, heal in (GROUPS.get(name) or auto_groups(name)):
        if box is None:
            # ★낱개 모드는 칸마다 자기 오차로 옮긴다 — 그룹 공통 배율을 구하지 않는다.
            #   (모서리 버튼처럼 흩어진 칸은 first/last 를 잡을 수 없다)
            moved = 0
            for slot in slots:
                cx, cy = cell_center(slot)
                a = hole_center(px, w, h, cx, cy)
                sx, sy = round(cx - a[0]), round(cy - a[1])
                if not (sx or sy):
                    continue
                bx0 = cx - ICON // 2 - SOLO_M - max(0, sx)
                by0 = cy - ICON // 2 - SOLO_M - max(0, sy)
                bx1 = cx + ICON // 2 + SOLO_M - min(0, sx)
                by1 = cy + ICON // 2 + SOLO_M - min(0, sy)
                im.paste(im.crop((bx0, by0, bx1, by1)), (bx0 + sx, by0 + sy))
                moved += 1
            print(f"  {name} 낱개 {len(slots)}칸 중 {moved}칸 개별 이동")
            if check:
                pass
            continue

        # ★기준점은 '그 자리에 실제로 있는' 칸에서 고른다. (맨위,맨왼쪽) 조합이 슬롯 목록에
        #   없는 판(모서리만 버튼인 판 등)에서 예전엔 StopIteration 으로 죽었다.
        rc = {s: divmod(s, COLS) for s in slots}
        ys = sorted({r for r, _ in rc.values()}); xs = sorted({c for _, c in rc.values()})
        first = min(slots, key=lambda s: (rc[s][0] - ys[0]) ** 2 + (rc[s][1] - xs[0]) ** 2)
        last = min(slots, key=lambda s: (rc[s][0] - ys[-1]) ** 2 + (rc[s][1] - xs[-1]) ** 2)
        ft, lt = cell_center(first), cell_center(last)

        # ★한 번에 안 맞는다 — 되재고 고친다. 계산대로 옮겨도 결과는 2px 쯤 남는다.
        #   줄이고 늘리면(LANCZOS) 액자 가장자리의 번짐 폭이 달라져 구멍 경계가 옮겨 앉기
        #   때문이다. 그래서 옮긴 **결과를 다시 재서** 남은 오차만큼 한 번 더 손본다.
        #   우편함이 그 증거다: 1회 -20.5px 로 크게 맞춘 뒤에도 위 줄이 2.5px 남아 있었다.
        for it in range(PASSES):
            fa = hole_center(px, w, h, *ft)
            la = hole_center(px, w, h, *lt)
            kx, dx = solve((fa[0], la[0]), (ft[0], lt[0]))
            ky, dy = solve((fa[1], la[1]), (ft[1], lt[1]))
            resid = max(abs(fa[0] - ft[0]), abs(fa[1] - ft[1]),
                        abs(la[0] - lt[0]), abs(la[1] - lt[1]))
            tag = f"  {name} 격자 {len(slots)}칸 [{it + 1}차]"
            if resid <= SETTLED:
                print(f"{tag} 남은 오차 {resid:.1f}px — 손대지 않는다")
                break
            print(f"{tag} 가로 배율 {kx:.4f} 이동 {dx:+.1f}"
                  f" · 세로 배율 {ky:.4f} 이동 {dy:+.1f} (남은 오차 {resid:.1f}px)")
            if check:
                break

            # ★메우지 않는다. 옛 자리를 배경으로 덮으려 했더니, 양피지처럼 **세로로 음영이
            #   흐르는 배경**에서 170px 아래를 떠오는 바람에 밝기가 안 맞아 가로 띠가 생겼다
            #   (2026-08-12 유저 지적). 대신 **비는 쪽으로 블록을 더 물어** 옛 자리를 통째로
            #   덮게 한다 — 옮긴 그림이 스스로 자기 자국을 가리므로 이어붙인 경계가 없다.
            x0, y0, x1, y1 = box
            gx0 = x0 - max(0, ceil(x0 - (x0 * kx + dx)))
            gy0 = y0 - max(0, ceil(y0 - (y0 * ky + dy)))
            gx1 = x1 + max(0, ceil(x1 - (x1 * kx + dx)))
            gy1 = y1 + max(0, ceil(y1 - (y1 * ky + dy)))
            block = im.crop((gx0, gy0, gx1, gy1))
            nw, nh = max(1, round((gx1 - gx0) * kx)), max(1, round((gy1 - gy0) * ky))
            block = block.resize((nw, nh), Image.LANCZOS)
            nx, ny = round(gx0 * kx + dx), round(gy0 * ky + dy)
            im.paste(block, (nx, ny))
            if (gx0, gy0, gx1, gy1) != box:
                print(f"     자국을 덮으려 블록을 넓힘: {box} → {(gx0, gy0, gx1, gy1)}")
            # 다음 차수는 **옮겨 놓인 자리**를 대상으로 삼는다(원래 상자는 이미 비었다)
            box = (nx, ny, nx + nw, ny + nh)
            px = im.convert("L").load()

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
