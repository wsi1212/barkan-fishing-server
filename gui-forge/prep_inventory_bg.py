#!/usr/bin/env python3
"""생존 인벤토리 배경 손질 — 받은 그림을 바닐라 칸 좌표에 맞춘다.

## 왜 손질이 필요한가
칸 좌표는 클라이언트 코드에 박혀 있어 1px도 못 옮긴다. 그림 생성은 그 격자를 못 맞춘다
(스킬 허브에서 세 번 연속 어긋났다). 그래서 **재질은 발주, 좌표는 코드**로 나눈다.

## 받은 그림의 어긋남 (실측)
  · 칸 간격이 70.8px (72여야 함) — 9칸 누적으로 양 끝이 5px씩 밀린다
  · 보조손 칸이 29px 오른쪽
  · 결과 칸이 12px 왼쪽
  · 레시피책 버튼 자리에 액자를 하나 그려 놨다 — 거긴 바닐라 버튼이 덮는 자리라 비워야 한다
    (발주서의 빨간 사각형을 '여기 액자'로 읽은 듯)

## 하는 일
1. 창 영역만 잘라 **칸 간격이 정확히 72px 이 되도록** 확대·평행이동한다.
   이걸로 방어구·가방·단축바·조합칸이 한꺼번에 맞는다(테두리가 6px 잘리는 건 감수).
2. 남은 두 칸(보조손·결과)은 액자만 오려서 제자리로 옮기고, 뒤에 남는 자국은
   바로 옆 나뭇결로 덮는다.
3. 레시피책 자리의 액자를 지운다.

산출: assets/minecraft/textures/gui/container/inventory.png (1024x1024)
"""
import os

from PIL import Image

import make_inventory_layout as L

HERE = os.path.dirname(os.path.abspath(__file__))
RP = os.path.expanduser("~/development/barkan-resourcepack")
OUT = os.path.join(RP, "assets/minecraft/textures/gui/container/inventory.png")
RAW = os.path.expanduser(
    "~/.codex/generated_images/019fcffa-2416-7661-aab4-db32e8a6de57/"
    "exec-c990a115-7761-49fb-86d7-12721cadac16.png")

S, CANVAS = L.S, L.CANVAS
WIN_W, WIN_H = L.WIN_W, L.WIN_H

# 실측 칸 간격 70.8 / 70.7 → 72 로 맞추는 배율과 이동량
FIT_W, FIT_H = 716, 676
FIT_DX, FIT_DY = -6, -6

# (자를 상자, 이동 dx·dy, 자국을 메울 나뭇결을 떠올 방향) — 액자만 오려 제자리로.
# 상자는 액자 + 나뭇결 여유를 포함한다. 메울 나뭇결은 반드시 **민무늬인 쪽**에서 뜬다.
MOVES = [
    ((326, 236, 412, 324), -29, +4, (+120, 0)),   # 보조손 — 오른쪽 나뭇결에서 메움
    ((588, 100, 676, 188), +13, +4, (0, +110)),   # 결과   — 아래쪽 나뭇결에서 메움
]
# 레시피책 버튼 자리에 잘못 그려진 액자 — 지운다
ERASE = (414, 216, 522, 330)   # ★액자 위쪽 테두리까지 넉넉히 — 좁게 잡았더니 주황 띠가 남았다
ERASE_SRC_DX = 100                 # 오른쪽 민무늬 나뭇결에서 떠온다


def heal(im, box, dx, dy, src):
    """box 를 (dx, dy) 만큼 옮기고, 원래 자리에 남는 L 자 자국을 나뭇결로 덮는다.

    ★자국을 먼저 덮고 옮기면 옮길 그림까지 지워진다 — 순서는 '떠두기 → 덮기 → 놓기'."""
    x0, y0, x1, y1 = box
    sprite = im.crop(box)
    sdx, sdy = src
    im.paste(im.crop((x0 + sdx, y0 + sdy, x1 + sdx, y1 + sdy)), (x0, y0))
    im.paste(sprite, (x0 + dx, y0 + dy))


# 조합 2x2 는 **넓히는 게 아니라 옮기는 문제**였다(2026-08-11 재측정).
#   처음엔 '구멍이 5~7px 작다'고 보고 손대지 않았는데, 픽셀을 직접 떠 보니 그게 아니었다.
#     왼쪽 테두리 390~394 · 가운데 구분선 463~468 · 오른쪽 테두리 536~541
#     목표(바닐라)                    구분선 456~463
#   구분선이 6px 오른쪽이다 — 액자가 통째로 밀린 것이고, 폭은 거의 맞다.
#   세로는 가운데 가로선이 137~142(목표 136~143)로 이미 정확해서 건드리지 않는다.
#   블록째 -6px 밀면 구분선을 깎지 않고도 네 칸이 한꺼번에 맞는다.
#   ★블록은 **액자 바깥 장식(모서리쇠·못)까지** 넉넉히 물어야 한다. 좁게 잡았더니 오른쪽
#     장식이 잘려 제자리에 조각으로 남았다. 대신 오른쪽 끝은 레시피책 지움 영역(y216~)을
#     건드리지 않게 216 에서 끊는다.
#   ★자국을 따로 덮지 않는다 — 블록에 배경 여유를 함께 물려 옮기면 6px 띠는 원본 배경
#     그대로 남아 이어진다. 덮으려다 옛 테두리를 복제하는 사고를 두 번 냈다.
CRAFT_BLOCK = (376, 44, 560, 216)
CRAFT_DX = -6

# ── 칸 틈 메우기 ────────────────────────────────────────────────────────────
# 판정: **밝은 액자 테두리가 시작하는 지점**을 구멍 경계로 본다. 칸 한가운데보다
#       FIT_RISE 이상 밝아지는 첫 픽셀이 테두리다. 아이템 상자(64px) 바로 바깥,
#       즉 중앙에서 32px 떨어진 자리에서 시작해야 딱 맞는다.
# ★처음엔 '중앙과 비슷한 어두운 색이 몇 px 이어지나'로 셌는데(fit_sockets 방식),
#   구멍 가장자리의 음영 때문에 조기에 끊겨 전 칸이 0px 로 나왔다. 실제로는 왼쪽·위에
#   1px 씩 여백이 남아 있었다(2026-08-12 유저가 확대해서 잡아냄). 액자가 밝은 판에서는
#   '테두리가 어디서 시작하나'로 재야 한다.
# 수법: 바깥 띠를 통째로 **안으로만** 민다. 밖으로 밀면 칸 사이 구분선을 먹는다.
FIT_ICON, FIT_PAD, FIT_RISE = 64, 4, 18


def _edges(px, w, h, ix0, iy0):
    """(왼, 오른, 위, 아래) 여백 — 테두리 시작이 32px 보다 멀리 있으면 그 차이."""
    mx, my = ix0 + FIT_ICON // 2, iy0 + FIT_ICON // 2
    ref = px[mx, my]

    def scan(dx, dy, base):
        for k in range(1, FIT_ICON // 2 + FIT_PAD + 2):
            x, y = mx + dx * k, my + dy * k
            if not (0 <= x < w and 0 <= y < h):
                return None
            if px[x, y] - ref >= FIT_RISE:
                return k - base               # 0 이면 딱 맞음
        return None
    # ★상자는 mx-32 ~ mx+31 로 **좌우가 비대칭**이다(폭 64, 중심이 픽셀 경계가 아니라
    #   픽셀 위에 있다). 그래서 상자 바로 바깥 첫 픽셀이 왼·위는 33칸, 오른·아래는 32칸
    #   떨어져 있다. 양쪽 다 32 로 재면 왼·위가 늘 +1 로 나와 멀쩡한 칸을 1px 씩 밀어버린다
    #   (2026-08-12 그렇게 46칸을 최대 4px 까지 파먹었다).
    return (scan(-1, 0, 33), scan(1, 0, 32), scan(0, -1, 33), scan(0, 1, 32))


def fit_slots(im):
    """모든 칸의 액자 구멍을 아이템 상자에 맞춘다. 조합칸을 옮긴 **뒤에** 부른다."""
    n, w, h = FIT_ICON + 2 * FIT_PAD, *im.size
    fixed = worst = 0
    for gx, gy in L.ARMOR + L.OFFHAND + L.CRAFT + L.RESULT + L.BAG + L.HOTBAR:
        px = im.convert("L").load()          # 앞 칸을 고친 결과를 반영해 다시 잰다
        ix0, iy0 = gx * S, gy * S
        x0, y0 = ix0 - FIT_PAD, iy0 - FIT_PAD
        e = _edges(px, w, h, ix0, iy0)
        if None in e:
            continue                          # 액자가 없는 칸(평평한 판) — 건드리지 않는다
        l, r, t, b = (max(0, min(FIT_PAD, v)) for v in e)
        if l:
            im.paste(im.crop((max(0, x0 - l), y0, ix0 - l, y0 + n)), (max(0, x0 - l) + l, y0))
        if r:
            im.paste(im.crop((ix0 + FIT_ICON + r, y0, min(w, x0 + n + r), y0 + n)), (ix0 + FIT_ICON, y0))
        if t:
            im.paste(im.crop((x0, max(0, y0 - t), x0 + n, iy0 - t)), (x0, max(0, y0 - t) + t))
        if b:
            im.paste(im.crop((x0, iy0 + FIT_ICON + b, x0 + n, min(h, y0 + n + b))), (x0, iy0 + FIT_ICON))
        if max(l, r, t, b):
            fixed += 1
            worst = max(worst, l, r, t, b)
    print(f"  칸 틈 메움 {fixed}칸 · 최대 {worst}px")


def main():
    raw = Image.open(RAW).convert("RGB")
    px = raw.load()
    bg = px[raw.width - 5, raw.height - 5]

    # 창 영역 = 배경색과 다른 픽셀의 바깥 상자
    minx, miny, maxx, maxy = raw.width, raw.height, 0, 0
    for y in range(raw.height):
        for x in range(raw.width):
            c = px[x, y]
            if abs(c[0] - bg[0]) + abs(c[1] - bg[1]) + abs(c[2] - bg[2]) > 18:
                minx = min(minx, x); maxx = max(maxx, x)
                miny = min(miny, y); maxy = max(maxy, y)

    win = raw.crop((minx, miny, maxx + 1, maxy + 1)).resize((FIT_W, FIT_H), Image.LANCZOS)
    im = Image.new("RGB", (CANVAS, CANVAS), bg)
    im.paste(win, (FIT_DX, FIT_DY))

    # ★지우기가 먼저다 — 보조손 자국을 메울 나뭇결을 이 액자 오른쪽에서 떠오기 때문에,
    #   나중에 지우면 지워야 할 액자가 자국 자리에 복사돼 버린다.
    ex0, ey0, ex1, ey1 = ERASE
    im.paste(im.crop((ex0 + ERASE_SRC_DX, ey0, ex1 + ERASE_SRC_DX, ey1)), (ex0, ey0))

    for box, dx, dy, src in MOVES:
        heal(im, box, dx, dy, src)

    # 조합 2x2 액자를 통째로 왼쪽으로 — 옮긴 뒤 오른쪽에 남는 띠만 나뭇결로 덮는다.
    x0, y0, x1, y1 = CRAFT_BLOCK
    im.paste(im.crop(CRAFT_BLOCK), (x0 + CRAFT_DX, y0))

    fit_slots(im)

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    im.convert("RGBA").save(OUT)
    im.save(os.path.join(HERE, "src", "inventory", "_fitted.png"))
    print(f"  inventory {im.size} → {OUT}")


if __name__ == "__main__":
    main()
