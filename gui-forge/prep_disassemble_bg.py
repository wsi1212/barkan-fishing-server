#!/usr/bin/env python3
"""분해창 납품 손질 — 액자를 72px 격자에 다시 앉힌다.

## 왜 옮기는 정도로 안 되나
2026-08-11 납품(대장간 놋쇠 액자)을 재보니 격자가 통째로 어긋나 있었다.
    가로 구멍 시작 111·182·251·321·391·461·530   (목표 104·176·248·320·392·464·536)
    세로 구멍 시작 253·316·380                    (목표 216·288·360)
    구멍 49x46px, 피치 70/63                      (목표 64x64, 피치 72)
세로는 시작이 37px 아래고 피치가 63이라 아래 행일수록 벌어진다. 한두 픽셀 미는 걸로는
못 맞춘다 — 아이콘이 액자 밖 배경 위에 뜬다.

## 그래서 하는 일 (재질은 발주, 좌표는 코드 — skillhub 와 같은 방식)
액자 한 장을 떠서 9-slice 로 늘려 **구멍이 정확히 아이콘 상자(64px)가 되게** 만든 뒤,
격자 자리를 판 질감으로 지우고 21칸 좌표에 다시 찍는다. 액자 테두리는 셀 경계를 넘어
이웃과 겹치는데, 원본에서도 액자들이 거의 맞닿아 있어 두꺼운 격자선처럼 보인다.

사용: python3 prep_disassemble_bg.py [납품파일]
산출: src/disassemble/bg_source.png (704x888) — build_plate.py 가 이걸 굽는다.
"""
import os
import sys

from PIL import Image

import make_page_layouts as L

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "src", "disassemble")
S, GX, GY, CELL, COLS = L.SCALE, L.GRID_X, L.GRID_Y, L.CELL, L.COLS
ICON, PAD = 16 * S, (CELL * S - 16 * S) // 2      # 64, 4

DEFAULT = os.path.expanduser(
    "~/Downloads/barkan-new-imagegen-20260811/"
    "disassemble_forge_imagegen_guided_usable_socket_button_fixed_704x888.png")

# 704x888 로 줄인 뒤의 좌표다. 액자 한 장의 바깥 테두리와 그 안 구멍.
# 2026-08-11 세 번째 납품(guided_usable_socket_button_fixed): 704x888 정타에 피치도 72 정확,
# 구멍 중심까지 목표와 일치했다. 남은 건 구멍이 54px(아이콘 64)로 작다는 것뿐 —
# audit_slots 가 21칸 전부 네 변 -5px 로 균일하게 뱉었다. 그래서 자리는 그대로 두고
# 구멍만 64px 로 늘린다.
SPRITE = (101, 213, 171, 283)     # 외곽(넉넉히. TRIM 이 실제 크롭을 정한다)
HOLE = (109, 221, 163, 275)       # 구멍 54x54
CORNER = 14                       # 9-slice 모서리(리벳이 온전히 들어가는 크기)
# 액자를 지우고 메울 바닥 질감 — 격자 아래 빈 곳에서 떠온다.
PLATE_FILL = (150, 452, 300, 504)
# 지울 격자 영역(액자만. 판 테두리는 건드리지 않는다)
GRID_AREA = (98, 208, 606, 428)
# ★테두리는 4px 여야 한다 — 외곽이 정확히 셀 크기(72)가 되어 **이웃과 안 겹친다.**
#   6·8px 로 두면 외곽이 76·80 이라 다음 액자가 앞 액자의 오른쪽·아래 테두리를 덮어먹어
#   'ㄱ자'로 잘린 액자가 된다(2026-08-11 실측, 유저가 바로 잡아냄).
#   겹치는 자리를 밝은 쪽으로 합성해 살리는 것도 해 봤지만, 구멍이 배경보다 어두워서
#   배경 잡동사니가 구멍 안으로 뚫고 들어온다 — 못 쓴다.
#   ★셀 72 에 아이콘 64 가 들어가면 여백이 각 변 4px 뿐이다. 원본 그림처럼 액자 사이를
#   떼어 놓는 건 이 격자에서 불가능하다(그러려면 구멍을 아이콘보다 작게 그려야 하는데,
#   그게 바로 이 납품의 원래 문제였다 — 아이콘이 테두리를 덮는다).
TRIM = 4
# 갈기 버튼 — 아트에서 셀49 보다 아래·오른쪽에 그려져 있어 통째로 옮긴다.
BUTTON = (300, 432, 404, 500)
BUTTON_FILL = (160, 452, 290, 520)
# 버튼 그림의 세로 중심은 바깥 프레임이 아니라 **안쪽 톱니 패널** 기준이다(468~520).
BUTTON_CENTER_Y = 466


def nine_slice(sp, w, h, corner=CORNER):
    """모서리는 그대로 두고 변·중앙만 늘린다 — 테두리 두께와 리벳 크기가 유지된다."""
    sw, sh = sp.size
    out = Image.new("RGBA", (w, h))
    c = min(corner, sw // 2, sh // 2)
    mid_w, mid_h = max(1, w - 2 * c), max(1, h - 2 * c)
    boxes = [((0, 0, c, c), (0, 0)), ((sw - c, 0, sw, c), (w - c, 0)),
             ((0, sh - c, c, sh), (0, h - c)), ((sw - c, sh - c, sw, sh), (w - c, h - c))]
    for box, at in boxes:
        out.paste(sp.crop(box), at)
    out.paste(sp.crop((c, 0, sw - c, c)).resize((mid_w, c), Image.LANCZOS), (c, 0))
    out.paste(sp.crop((c, sh - c, sw - c, sh)).resize((mid_w, c), Image.LANCZOS), (c, h - c))
    out.paste(sp.crop((0, c, c, sh - c)).resize((c, mid_h), Image.LANCZOS), (0, c))
    out.paste(sp.crop((sw - c, c, sw, sh - c)).resize((c, mid_h), Image.LANCZOS), (w - c, c))
    out.paste(sp.crop((c, c, sw - c, sh - c)).resize((mid_w, mid_h), Image.LANCZOS), (c, c))
    return out


def fill_area(im, area, src):
    """판 질감을 타일로 깔아 액자를 지운다."""
    tile = im.crop(src)
    tw, th = tile.size
    x0, y0, x1, y1 = area
    for y in range(y0, y1, th):
        for x in range(x0, x1, tw):
            im.paste(tile.crop((0, 0, min(tw, x1 - x), min(th, y1 - y))), (x, y))


def move_button(im):
    """갈기 버튼을 슬롯 49 한가운데로 옮긴다. 아트에선 아래·오른쪽으로 밀려 그려져 있다."""
    bx, by = cell_box(49)
    btn = im.crop(BUTTON)
    cx, cy = (BUTTON[0] + BUTTON[2]) / 2, BUTTON_CENTER_Y
    dx, dy = round(bx + ICON / 2 - cx), round(by + ICON / 2 - cy)
    fill_area(im, BUTTON, BUTTON_FILL)
    im.alpha_composite(btn, (BUTTON[0] + dx, BUTTON[1] + dy))
    print(f"  갈기 버튼 {dx:+d},{dy:+d} 이동")


def cell_box(slot):
    r, c = divmod(slot, COLS)
    x0, y0 = (GX + CELL * c) * S, (GY + CELL * r) * S
    return x0 + PAD, y0 + PAD                      # 아이콘 상자 좌상단


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else DEFAULT
    im = Image.open(os.path.expanduser(src)).convert("RGBA")
    W, H = 176 * S, (114 + 6 * CELL) * S
    if im.size != (W, H):
        print(f"  납품 {im.size} → {W}x{H} 로 축소")
        im = im.resize((W, H), Image.LANCZOS)

    # 구멍 바깥 TRIM 만큼만 남겨 잘라낸다 — 이게 액자 테두리가 된다.
    box = (max(SPRITE[0], HOLE[0] - TRIM), max(SPRITE[1], HOLE[1] - TRIM),
           min(SPRITE[2], HOLE[2] + TRIM), min(SPRITE[3], HOLE[3] + TRIM))
    sprite = im.crop(box)
    fl, ft = HOLE[0] - box[0], HOLE[1] - box[1]
    fr, fb = box[2] - HOLE[2], box[3] - HOLE[3]
    frame = nine_slice(sprite, fl + ICON + fr, ft + ICON + fb)
    print(f"  액자 {sprite.size} → {frame.size} (테두리 좌{fl} 위{ft} 우{fr} 아{fb} · 구멍 {ICON}px)")

    fill_area(im, GRID_AREA, PLATE_FILL)
    move_button(im)

    _, roles, _ = L.PAGES["disassemble"]
    slots = sorted(s for s, (role, _) in roles.items() if role == "입력")
    for slot in slots:
        bx, by = cell_box(slot)
        im.alpha_composite(frame, (bx - fl, by - ft))
    print(f"  액자 {len(slots)}칸 재배치")

    im.convert("RGB").save(os.path.join(SRC, "bg_source.png"))
    print(f"  → {os.path.join(SRC, 'bg_source.png')}")


if __name__ == "__main__":
    main()
