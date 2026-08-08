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

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    im.convert("RGBA").save(OUT)
    im.save(os.path.join(HERE, "src", "inventory", "_fitted.png"))
    print(f"  inventory {im.size} → {OUT}")


if __name__ == "__main__":
    main()
