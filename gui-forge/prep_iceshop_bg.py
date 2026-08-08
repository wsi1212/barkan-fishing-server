#!/usr/bin/env python3
"""아이스박스 상점 배경 손질 — 받은 아트(bg_source_rebuild.png)에서 어긋난 것만 고친다.

받은 그림은 티어 9칸이 **맨 아랫줄(슬롯 18~26)** 에 72px 피치로 정확히 앉아 있다.
발주는 가운데 줄이었지만 위쪽으로 고드름·기둥·물고기 실루엣이 시원하게 열려 있어
구도가 더 낫다 — 그래서 **그림을 옮기지 않고 코드의 슬롯 번호를 아랫줄로 맞췄다**
(IceboxGui.SHOP_ROW = 18).

여기서 고치는 건 하나뿐: 왼쪽 위 「뒤로가기」 소켓이 셀 중심보다 8px 아래로 처져 있다.
아이템 아이콘은 셀 중심(y 104)에 그려지므로 그대로 두면 액자 위로 삐져나온다.

산출: src/iceshop/bg_source.png  (build_plate.py iceshop 이 먹는 파일)
"""
import os

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "src", "iceshop")

# 소켓 실측 상자와 목표 — 셀0 중심은 y 104, 지금 소켓 중심은 111.5
SOCKET = (26, 75, 102, 148)
SHIFT_Y = -8
# 소켓을 올리면 아래에 8px 구멍이 남는다. 바로 아래 민무늬 얼음벽에서 떠다 메운다.
PATCH_FROM = (26, 160, 102, 176)


def main():
    im = Image.open(os.path.join(SRC, "bg_source_rebuild.png")).convert("RGBA")
    x0, y0, x1, y1 = SOCKET
    socket = im.crop(SOCKET)
    # ① 먼저 소켓 자리를 벽 텍스처로 지운다(위아래로 늘려서 덮는다)
    wall = im.crop(PATCH_FROM)
    wh = PATCH_FROM[3] - PATCH_FROM[1]
    for y in range(y0 + SHIFT_Y, y1, wh):
        im.paste(wall, (x0, y))
    # ② 올린 자리에 소켓을 다시 찍는다
    im.paste(socket, (x0, y0 + SHIFT_Y))
    im.save(os.path.join(SRC, "bg_source.png"))
    print(f"  iceshop  뒤로가기 소켓 {SHIFT_Y}px 이동 · {im.size}")


if __name__ == "__main__":
    main()
