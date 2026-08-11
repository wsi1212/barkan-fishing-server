#!/usr/bin/env python3
"""인벤토리 슬롯 목업 합성기 — 아이콘의 '실전 무대'에서 판정한다.

바닐라 GUI 규격 그대로: 패널 #C6C6C6, 슬롯 18×18(내부 #8B8B8B,
베벨 = 위·왼쪽 #373737 / 아래·오른쪽 #FFFFFF), 아이콘은 슬롯 안 (1,1).
offline 판정 중 이게 가장 진실에 가깝다 — 흰 배경 콘택트시트에서 예뻐도
슬롯 회색에서 묻히면 실패. (최종 진실은 물론 RP 배포 후 인게임 스크린샷.)

사용: python3 slot_preview.py <out.png> <icon.png...> [--scale 6] [--cols 7]
"""
import sys
from PIL import Image

PANEL = (198, 198, 198, 255)
SLOT = (139, 139, 139, 255)
DARK = (55, 55, 55, 255)
LITE = (255, 255, 255, 255)


def compose(paths, out, scale=6, cols=None):
    icons = [Image.open(p).convert("RGBA") for p in paths]
    # 애니메이션 스트립이면 첫 프레임만
    icons = [im.crop((0, 0, im.size[0], im.size[0])) if im.size[1] > im.size[0] else im
             for im in icons]
    n = len(icons)
    cols = cols or n
    rows = (n + cols - 1) // cols
    pad = 4
    W = pad * 2 + cols * 18 + (cols - 1) * 2
    H = pad * 2 + rows * 18 + (rows - 1) * 2
    board = Image.new("RGBA", (W, H), PANEL)
    for i, ic in enumerate(icons):
        r, c = divmod(i, cols)
        x0 = pad + c * 20
        y0 = pad + r * 20
        for x in range(18):
            board.putpixel((x0 + x, y0), DARK)
            board.putpixel((x0 + x, y0 + 17), LITE)
        for y in range(18):
            board.putpixel((x0, y0 + y), DARK)
            board.putpixel((x0 + 17, y0 + y), LITE)
        board.putpixel((x0 + 17, y0), SLOT)
        board.putpixel((x0, y0 + 17), SLOT)
        for x in range(1, 17):
            for y in range(1, 17):
                board.putpixel((x0 + x, y0 + y), SLOT)
        if ic.size[0] != 16:
            ic = ic.resize((16, 16), Image.NEAREST)
        board.alpha_composite(ic, (x0 + 1, y0 + 1))
    board = board.resize((W * scale, H * scale), Image.NEAREST)
    board.save(out)
    print(f"슬롯 목업 → {out} ({n}칸)")


if __name__ == "__main__":
    scale, cols = 6, None
    argv = sys.argv[1:]
    if "--scale" in argv:
        i = argv.index("--scale"); scale = int(argv[i + 1]); del argv[i:i + 2]
    if "--cols" in argv:
        i = argv.index("--cols"); cols = int(argv[i + 1]); del argv[i:i + 2]
    compose(argv[1:], argv[0], scale, cols)
