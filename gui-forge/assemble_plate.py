#!/usr/bin/env python3
"""배경 + 액자를 코드로 조립한다 — 격자 정렬 문제의 근본 해결.

## 왜 이 방식인가
그림 생성은 72px 격자를 못 맞춘다. 여덟 번 받아 한 번도 안 맞았고, 받은 판에서 격자를
떼어 옮기면 이번엔 판을 가로지르는 장식(책 접힘선·기둥·걸쇠)이 어긋났다.

그래서 **격자가 없는 빈 배경**과 **액자 한 장**을 따로 받는다. 좌표는 전부 코드가 잡으니
정렬이 어긋날 여지가 없고, 배경에는 손을 대지 않으니 장식도 안 깨진다.

## 액자를 72px 칸에 넣기
칸은 72px, 아이콘은 그 가운데 64px — 테두리에 쓸 수 있는 건 사방 4px 뿐이다.
받은 액자는 테두리가 두꺼우니 9-slice 로 **구멍만 64px 로 늘려** 외곽을 정확히 72px 로
만든다. 그러면 이웃과 겹치지 않고(겹치면 나중 액자가 앞 액자 테두리를 덮어 ㄱ자로
잘린다), 액자끼리 맞닿아 격자선처럼 이어진다 — 기존 판들과 같은 모양이다.

사용: python3 assemble_plate.py <판이름>
산출: src/<이름>/bg_source.png
"""
import os
import sys

from PIL import Image

import build_plate
import make_page_layouts as L

HERE = os.path.dirname(os.path.abspath(__file__))
GEN = os.path.expanduser("~/.codex/generated_images/019fcffa-2416-7661-aab4-db32e8a6de57")
S, GX, GY, CELL, COLS = L.SCALE, L.GRID_X, L.GRID_Y, L.CELL, L.COLS
ICON, PAD = 16 * S, 4
# 액자가 칸 밖으로 나가는 두께. **4 여야 한다** — 외곽이 정확히 셀 크기(72)라 이웃과 안 겹친다.
# 8 로 뒀다가 배포하고 바로 걸렸다(2026-08-12): 겹치면 오른쪽 액자의 왼쪽 코너가 왼쪽 액자의
# 오른쪽 코너를 덮는데, 코너는 좌우 대칭이 아니라 모서리에서 선이 어긋나 보인다.
# '액자가 다 같으니 겹쳐도 티 안 난다'는 판단이 틀렸다. 테두리가 얇아지는 건 감수한다.
PAD_OUT = 4
KEY = (255, 0, 255)        # 액자 그림의 배경 크로마키(마젠타)
KEY_TOL = 60

# 판: (배경 파일, 액자 파일)  — 액자는 칸 역할별로 다르면 {역할: 파일} 로도 준다.
PARTS = {
    "dextab": ("ㅊㅋ.png", "exec-dc0a6566-7b20-401a-8839-0ddb77f6183e.png"),
    "dexisland": ("exec-09f2960c-c325-4a2f-b956-4a0420f0409f.png",
                  "exec-bdbd278c-8043-4791-a354-efbffca48922.png"),
}


def dekey(im):
    """크로마키를 지우고 액자만 남긴다 — 키 색에 가까운 픽셀을 투명으로."""
    im = im.convert("RGBA")
    px = im.load()
    w, h = im.size
    for y in range(h):
        for x in range(w):
            r, g, b, _ = px[x, y]
            if abs(r - KEY[0]) + abs(g - KEY[1]) + abs(b - KEY[2]) < KEY_TOL:
                px[x, y] = (0, 0, 0, 0)
    return im


def tight(im):
    box = im.getbbox()
    return im.crop(box) if box else im


def hole_box(im):
    """액자 안쪽 구멍 — 한가운데 색과 비슷한 픽셀이 이어지는 범위."""
    g = im.convert("L")
    px = g.load()
    w, h = g.size
    cx, cy = w // 2, h // 2
    ref = px[cx, cy]

    def go(dx, dy):
        k = 0
        while 0 <= cx + dx * (k + 1) < w and 0 <= cy + dy * (k + 1) < h:
            if abs(px[cx + dx * (k + 1), cy + dy * (k + 1)] - ref) > 26:
                break
            k += 1
        return k
    return cx - go(-1, 0), cy - go(0, -1), cx + go(1, 0) + 1, cy + go(0, 1) + 1


def nine_slice(sp, w, h, corner):
    sw, sh = sp.size
    out = Image.new("RGBA", (w, h))
    c = max(1, min(corner, sw // 2 - 1, sh // 2 - 1, w // 2, h // 2))
    mw, mh = max(1, w - 2 * c), max(1, h - 2 * c)
    for box, at in (((0, 0, c, c), (0, 0)), ((sw - c, 0, sw, c), (w - c, 0)),
                    ((0, sh - c, c, sh), (0, h - c)), ((sw - c, sh - c, sw, sh), (w - c, h - c))):
        out.paste(sp.crop(box), at)
    out.paste(sp.crop((c, 0, sw - c, c)).resize((mw, c), Image.LANCZOS), (c, 0))
    out.paste(sp.crop((c, sh - c, sw - c, sh)).resize((mw, c), Image.LANCZOS), (c, h - c))
    out.paste(sp.crop((0, c, c, sh - c)).resize((c, mh), Image.LANCZOS), (0, c))
    out.paste(sp.crop((sw - c, c, sw, sh - c)).resize((c, mh), Image.LANCZOS), (w - c, c))
    out.paste(sp.crop((c, c, sw - c, sh - c)).resize((mw, mh), Image.LANCZOS), (c, c))
    return out


def make_frame(path):
    """액자 그림 → 구멍이 정확히 64px 인 액자. 테두리는 사방 PAD_OUT px."""
    sp = tight(dekey(Image.open(os.path.join(GEN, path))))
    hx0, hy0, hx1, hy1 = hole_box(sp)
    # 구멍 밖으로 남길 테두리 = 결과에서 PAD_OUT 이 되도록 원본 비율로 환산
    tw = round(PAD_OUT * (hx1 - hx0) / ICON)
    th = round(PAD_OUT * (hy1 - hy0) / ICON)
    box = (max(0, hx0 - tw), max(0, hy0 - th), min(sp.width, hx1 + tw), min(sp.height, hy1 + th))
    cut = sp.crop(box)
    # ★9-slice 를 쓰지 않는다. 구멍 밖으로 남긴 테두리를 이미 PAD 비율로 계산했으므로
    #   그대로 72px 로 줄이면 구멍이 정확히 64px 가 된다. 9-slice 로 늘리려 했더니 코너가
    #   결과 크기를 넘어 액자가 뭉개졌다(2026-08-12).
    size = ICON + 2 * PAD_OUT
    frame = cut.resize((size, size), Image.LANCZOS)
    hole_px = round((hx1 - hx0) * size / cut.width)
    print(f"  액자 {sp.size} · 구멍 {hx1-hx0}x{hy1-hy0} → 자름 {cut.size} → {size}x{size} (구멍 {hole_px}px)")
    return frame


def assemble(name):
    bg_file, frame_file = PARTS[name]
    rows = build_plate.PLATES[name][0]
    W, H = 176 * S, (114 + rows * CELL) * S
    bg = Image.open(os.path.join(GEN, bg_file)).convert("RGBA")
    if bg.size != (W, H):
        print(f"  배경 {bg.size} → {W}x{H}")
        bg = bg.resize((W, H), Image.LANCZOS)
    frame = make_frame(frame_file)

    def put(gx, gy):
        # 아이콘 상자(칸 안쪽 64px) 기준으로 놓는다 — 액자가 그 둘레로 PAD_OUT 만큼 나간다.
        bg.alpha_composite(frame, (gx * S + PAD - PAD_OUT, gy * S + PAD - PAD_OUT))

    _, roles, _ = L.PAGES[name]
    slots = sorted(s for s, (r, _) in roles.items() if r != "장식")
    for slot in slots:
        r, c = divmod(slot, COLS)
        put(GX + CELL * c, GY + CELL * r)

    # ★플레이어 인벤토리 칸도 같은 액자로 찍는다. 예전엔 build_plate 가 공용 격자(단색 선)를
    #   덧그렸는데, 그러면 위 진열칸과 아래 가방칸의 생김새가 따로 논다.
    # ★바닐라의 139 / 197 은 **아이템이 그려지는 y** 다. 셀 좌상단은 그보다 1 GUI px 위다
    #   (진열칸이 GRID_Y=17, 아이템 18 인 것과 같은 관계). 139 를 셀로 쓰는 바람에 가방칸이
    #   세로로만 4px 밀려 있었다(2026-08-12 유저 지적).
    inv_y0 = 30 + rows * CELL
    inv_rows = [inv_y0, inv_y0 + CELL, inv_y0 + 2 * CELL, inv_y0 + 58]   # 가방 3줄 + 단축바
    for gy in inv_rows:
        for c in range(COLS):
            put(GX + CELL * c, gy)

    out = os.path.join(HERE, "src", name, "bg_source.png")
    bg.convert("RGB").save(out)
    # build_plate 가 공용 인벤 격자를 덧그리지 않게 표시해 둔다.
    open(os.path.join(HERE, "src", name, ".assembled"), "w").write("assemble_plate.py\n")
    print(f"  {name} 진열 {len(slots)}칸 + 인벤 {len(inv_rows) * COLS}칸 배치 → {out}")


def main():
    for n in (sys.argv[1:] or PARTS):
        assemble(n)


if __name__ == "__main__":
    main()
