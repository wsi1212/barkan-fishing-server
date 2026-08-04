#!/usr/bin/env python3
"""특성 트리 GUI 부품 분해 — Codex 그린스크린 시트 4장 → 개별 조각 PNG.

입력(~/.codex/generated_images/<세션>/): 벽면 플레이트 / 프레임 8조각 / 소켓 3상태 / 레일 2조각
산출: gui-forge/src/skilltree/*.png  (커밋해서 재현 가능하게)

★배경을 통째로 굽지 않고 조각으로 받는 이유: 확산 모델은 픽셀 격자를 못 맞춘다.
  좌표·반복·균일성은 컴포저(build_skilltree_bg.py)가 코드로 처리한다.

그린스크린 제거: 밝은 초록 + Codex가 조각 경계로 그려둔 어두운 초록 둘 다 뺀다.
  프린지는 배경 성분을 역산해 빼서(unmix) 축소할 때 초록 테두리가 안 남게 한다.
"""
import os
import sys

from PIL import Image, ImageFilter

SESS = os.path.expanduser("~/.codex/generated_images/019fc42e-c8f7-7870-b50c-4ad96a0cb315")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "src", "skilltree")

SHEETS = {
    "frame":  "exec-aca79d7d-f491-4e0f-aec3-86afd75f489c.png",
    "socket": "exec-6bcd1a90-5c9b-4c30-ab5c-303e9f27f05b.png",
    "rail":   "exec-a26bd4fc-e9d9-4ee2-8bb9-8e090a03c395.png",
    "wall":   "exec-45e95c5f-c2f2-4712-8d1e-9f0e32d41f38.png",
}

# 측정한 조각 위치 (시트 원본 좌표) — 키잉 후 실제 내용 bbox로 다시 조인다
CROPS = {
    "frame": {
        "frame_tl":     (71, 67, 356, 325),
        "frame_top":    (447, 67, 807, 325),
        "frame_tr":     (900, 67, 1182, 325),
        "frame_left":   (76, 400, 203, 843),
        "frame_right":  (1050, 400, 1177, 843),
        "frame_bl":     (71, 921, 354, 1178),
        "frame_bottom": (446, 921, 807, 1178),
        "frame_br":     (899, 921, 1182, 1178),
    },
    "socket": {
        "socket_locked":   (213, 203, 584, 563),
        "socket_unlocked": (770, 203, 1141, 563),
        "socket_maxed":    (1327, 203, 1698, 563),
    },
    "rail": {
        "rail_straight_lit": (65, 348, 567, 752),
        "rail_elbow_lit":    (684, 348, 1123, 752),
    },
}


def is_green(r, g, b):
    """밝은 초록 배경 + 조각 경계용 어두운 초록 둘 다."""
    return g > r + 45 and g > b + 45 and g > 70


def key_green(im):
    """그린스크린 → RGBA. 프린지는 초록 성분 역산 제거."""
    im = im.convert("RGBA")
    px = im.load()
    w, h = im.size
    for y in range(h):
        for x in range(w):
            r, g, b, _ = px[x, y]
            if not is_green(r, g, b):
                px[x, y] = (r, g, b, 255)
                continue
            # 초록 우세도 = 배경 비중. 클수록 순수 배경
            excess = g - max(r, b)
            if excess > 90:
                px[x, y] = (0, 0, 0, 0)
            else:
                t = 1.0 - excess / 90.0                  # 0=배경 → 1=전경
                gg = max(r, b)                           # 초록 성분을 이웃 채널 수준으로 억제
                px[x, y] = (r, gg, b, int(255 * t))
    return im


def clean(im, erode=3):
    """알파 침식으로 스필 제거 + 내용 bbox 크롭."""
    r, g, b, a = im.split()
    if erode >= 3:
        a = a.filter(ImageFilter.MinFilter(erode))
    im = Image.merge("RGBA", (r, g, b, a))
    bb = im.getbbox()
    return im.crop(bb) if bb else im


def main():
    os.makedirs(OUT, exist_ok=True)
    for sheet, crops in CROPS.items():
        p = os.path.join(SESS, SHEETS[sheet])
        if not os.path.exists(p):
            sys.exit(f"시트 없음: {p}")
        src = Image.open(p)
        print(f"[{sheet}] {SHEETS[sheet]} {src.size}")
        for name, box in crops.items():
            piece = clean(key_green(src.crop(box)))
            piece.save(os.path.join(OUT, f"{name}.png"))
            print(f"  {name}.png {piece.size}")

    # 벽면은 그린스크린이 아니라 통짜 텍스처 — 그대로 복사
    wall = Image.open(os.path.join(SESS, SHEETS["wall"])).convert("RGB")
    wall.save(os.path.join(OUT, "wall_plate.png"))
    print(f"[wall] wall_plate.png {wall.size}")


if __name__ == "__main__":
    main()
