#!/usr/bin/env python3
"""판에 이미 그려진 액자를 **떠서 격자에 다시 찍는다** — 배경은 그대로 두고 칸만 바로잡는다.

## 왜 이게 필요한가
정렬이 정확한 판은 셋뿐이었고(분해창·수집품섬·도감목록) 전부 **코드가 좌표를 잡은** 판이다.
나머지는 그림에 그려진 격자를 쓰는데, 피치가 72 가 아니라 열·행마다 오차가 쌓인다.
블록째 배율을 먹여 옮겨 봐도(refit_plate) 8px → 6px 정도까지만 줄어든다.

그래서 assemble_plate 와 같은 원리를 **이미 받은 판**에 적용한다: 판에서 액자 한 칸을 떠서
구멍이 정확히 64px 이 되게 맞춘 뒤 모든 칸에 다시 찍는다. 좌표를 코드가 잡으므로 0px 다.

## 쓸 수 있는 판 / 없는 판
칸 액자가 **전부 같은 판**만 대상이다. 아이스박스(티어별 색)·우편함(상태별 색)처럼 칸마다
그림이 다른 판은 하나로 덮으면 그 다양성이 사라진다 — 그런 판은 refit_plate 로 옮긴다.

사용: python3 resnap_plate.py <판이름> [--src <슬롯>] [--check]
산출: src/<이름>/bg_source.png (원본은 .bak-resnap)
"""
import os
import shutil
import sys

from PIL import Image, ImageChops

import hole_probe as HP
import make_page_layouts as L

HERE = os.path.dirname(os.path.abspath(__file__))
S, GX, GY, CELL, COLS = L.SCALE, L.GRID_X, L.GRID_Y, L.CELL, L.COLS
ICON, PAD = 16 * S, 4

# 판: 액자를 떠올 칸(없으면 오차가 가장 작은 칸을 자동으로 고른다)
SOURCE = {}


def cell_origin(slot):
    r, c = divmod(slot, COLS)
    return (GX + CELL * c) * S, (GY + CELL * r) * S


# 칸마다 그림이 다른 판 — 하나로 덮으면 그 다양성이 사라진다(아이스박스 티어색, 우편 상태색).
# ★강화창은 칸마다 안내 그림(낚싯대·상승권·방지권·감소권)이 달라 통일하면 지워진다.
SKIP = {"iceshop", "mailbox", "enhance"}


def groups_of(name):
    """역할(홈/입력/목록)별로 묶는다 — 역할이 다르면 액자 생김새도 다르다."""
    _, roles, _ = L.PAGES[name]
    out = {}
    for s, (r, _) in sorted(roles.items()):
        if r == "장식":
            continue
        out.setdefault(r, []).append(s)
    return out


DIFF_MAX = 45      # 칸 안쪽이 이보다 다르면 '같은 액자'가 아니다
                   # ★60 으로 뒀다가 강화창 입력칸(차이 59)이 통과해 그림이 덮였다


def cells_differ(im, slots):
    """칸 **안쪽**이 서로 다른가 — 강화창처럼 칸마다 안내 그림이 그려진 판을 지키는 가드.

    ★2026-08-13: 이 가드 없이 돌렸다가 강화창의 낚싯대·상승권·방지권 안내 그림이 한 칸
      그림으로 전부 덮였다. 조합대 탭 아이콘도 같은 사고를 낼 뻔했다."""
    if len(slots) < 2:
        return False
    crops = []
    for s in slots:
        x0, y0 = cell_origin(s)
        x0 += PAD + 8
        y0 += PAD + 8
        crops.append(im.crop((x0, y0, x0 + ICON - 16, y0 + ICON - 16)))
    base = crops[0]
    return any(max(ImageChops.difference(base, c).convert("L").getextrema()) > DIFF_MAX
               for c in crops[1:])


def pick_source(px, w, h, slots):
    """구멍이 64px 에 가장 가까운 칸 — 그 칸이 액자를 가장 온전히 담고 있다."""
    best, score = None, None
    for slot in slots:
        x0, y0 = cell_origin(slot)
        hb = HP.hole_bbox(px, w, h, x0 + PAD + HP.HALF, y0 + PAD + HP.HALF)
        if hb is None:
            continue
        sc = abs((hb[2] - hb[0] + 1) - ICON) + abs((hb[3] - hb[1] + 1) - ICON)
        if score is None or sc < score:
            best, score = slot, sc
    return best


def make_frame(im, px, w, h, slot):
    """그 칸에서 액자를 떠서 구멍이 정확히 64px 인 72x72 액자로 만든다."""
    x0, y0 = cell_origin(slot)
    hb = HP.hole_bbox(px, w, h, x0 + PAD + HP.HALF, y0 + PAD + HP.HALF)
    if hb is None:
        raise SystemExit(f"  {slot}번 칸에서 구멍을 못 찾았다 — --src 로 다른 칸을 지정할 것")
    hx0, hy0, hx1, hy1 = hb
    hw, hh = hx1 - hx0 + 1, hy1 - hy0 + 1
    # 구멍 밖으로 남길 테두리 = 결과에서 PAD(4px) 가 되도록 원본 비율로 환산
    tw, th = round(PAD * hw / ICON), round(PAD * hh / ICON)
    box = (hx0 - tw, hy0 - th, hx1 + 1 + tw, hy1 + 1 + th)
    cut = im.crop(box)
    frame = cut.resize((CELL * S, CELL * S), Image.LANCZOS)
    print(f"  액자 원본 칸 #{slot} · 구멍 {hw}x{hh} → 테두리 {tw}/{th} 물어 {cut.size} → 72x72")
    return frame


def resnap(name, src_slot=None, check=False):
    if name in SKIP:
        print(f"  {name}: 칸마다 그림이 달라 건너뛴다(refit_plate 로 옮길 것)")
        return
    path = os.path.join(HERE, "src", name, "bg_source.png")
    im = Image.open(path).convert("RGB")
    px = im.convert("L").load()
    w, h = im.size
    done = 0
    for role, slots in groups_of(name).items():
        if src_slot is None and cells_differ(im, slots):
            print(f"    {role} {len(slots)}칸 — ★칸마다 그림이 다르다(안내 아이콘 등). 통일하면 지워지므로 건너뛴다")
            continue
        slot = src_slot if src_slot is not None else pick_source(px, w, h, slots)
        if slot is None:
            print(f"  {name}/{role}: 쓸 만한 액자를 못 찾아 건너뜀 ({len(slots)}칸)")
            continue
        frame = make_frame(im, px, w, h, slot)
        if check:
            continue
        for s in slots:
            im.paste(frame, cell_origin(s))
        done += len(slots)
        print(f"    {role} {len(slots)}칸")
    if check or not done:
        return
    if not os.path.exists(path + ".bak-resnap"):
        shutil.copy2(path, path + ".bak-resnap")
    im.save(path)
    print(f"  {name} 총 {done}칸 다시 찍음")


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    check = "--check" in sys.argv
    src = None
    if "--src" in sys.argv:
        src = int(sys.argv[sys.argv.index("--src") + 1])
    for n in args:
        resnap(n, src, check)


if __name__ == "__main__":
    main()
