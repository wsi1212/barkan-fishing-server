#!/usr/bin/env python3
"""ImageGen 산출물을 실제 GUI 합성용 슬롯 텍스처로 정리한다.

ImageGen이 투명 영역을 체커보드로 표시한 경우가 있어, 가장자리에서 연결된
밝은 무채색 배경만 알파로 제거한다. 슬롯 안쪽의 어두운 목재와 금속은 보존한
채 72x72 art px(18 GUI px) 한 칸으로 축소한다.
"""

import os
from collections import deque

from PIL import Image


HERE = os.path.dirname(os.path.abspath(__file__))
SOURCE = os.path.join(HERE, "src", "questpage", "inventory_slot_imagegen_v2.png")
OUTPUT = os.path.join(HERE, "src", "questpage", "inventory_slot.png")
TARGET = 72


def connected_checkerboard(im):
    """가장자리와 연결된 밝은 무채색 픽셀을 True로 반환한다."""
    w, h = im.size
    px = im.load()
    seen = bytearray(w * h)

    def candidate(x, y):
        r, g, b = px[x, y]
        return min(r, g, b) >= 170 and max(r, g, b) - min(r, g, b) <= 20

    q = deque()
    for x in range(w):
        if candidate(x, 0): q.append((0, x)); seen[x] = 1
        idx = (h - 1) * w + x
        if candidate(x, h - 1) and not seen[idx]: q.append((h - 1, x)); seen[idx] = 1
    for y in range(h):
        idx = y * w
        if candidate(0, y) and not seen[idx]: q.append((y, 0)); seen[idx] = 1
        idx = y * w + w - 1
        if candidate(w - 1, y) and not seen[idx]: q.append((y, w - 1)); seen[idx] = 1
    while q:
        y, x = q.popleft()
        for ny, nx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
            if not (0 <= ny < h and 0 <= nx < w):
                continue
            idx = ny * w + nx
            if candidate(nx, ny) and not seen[idx]:
                seen[idx] = 1
                q.append((ny, nx))
    return seen


def main():
    im = Image.open(SOURCE).convert("RGB")
    bg = connected_checkerboard(im)
    alpha = bytes(0 if v else 255 for v in bg)
    alpha_im = Image.frombytes("L", im.size, alpha)
    rgba = im.copy().convert("RGBA")
    rgba.putalpha(alpha_im)
    bbox = alpha_im.getbbox()
    if bbox is None:
        raise SystemExit("슬롯 프레임을 찾지 못했다")
    left, top, right, bottom = bbox
    xs = range(left, right)
    ys = range(top, bottom)
    side = max(right - left, bottom - top)
    cx, cy = (left + right) // 2, (top + bottom) // 2
    sq_left = max(0, cx - side // 2)
    sq_top = max(0, cy - side // 2)
    sq_right = min(im.width, sq_left + side)
    sq_bottom = min(im.height, sq_top + side)
    sq = rgba.crop((sq_left, sq_top, sq_right, sq_bottom))
    sq = sq.resize((TARGET, TARGET), Image.Resampling.LANCZOS)
    sq.save(OUTPUT)
    print(f"{SOURCE} -> {OUTPUT} · bbox={(left, top, right, bottom)} · {sq.size} RGBA")


if __name__ == "__main__":
    main()
