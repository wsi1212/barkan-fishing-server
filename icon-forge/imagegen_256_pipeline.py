#!/usr/bin/env python3
"""ImageGen 고해상도 원본을 256px RGBA 리소스팩 텍스처로 정리한다.

ImageGen이 투명 배경을 요청해도 체크무늬를 실제 RGB 픽셀로 구워 내는 경우가
있다. 이 도구는 테두리에서 연결되는 밝은 무채색 배경만 제거하고, 내부의
흰색 비늘·종이·금속 하이라이트는 외곽선으로 보호된 전경으로 보존한다.

사용:
  python3 imagegen_256_pipeline.py <source.png> <output.png>

최종 PNG는 256x256 RGBA이며, 16x16 축소본을 만들지 않는다.
"""
from __future__ import annotations

import argparse
from collections import deque
from pathlib import Path

from PIL import Image


def is_bright_neutral(rgb: tuple[int, int, int]) -> bool:
    """체크무늬 배경 후보: 거의 무채색이고 밝은 픽셀."""
    r, g, b = rgb
    return max(rgb) - min(rgb) <= 12 and min(rgb) >= 220


def connected_background(im: Image.Image) -> bytearray:
    """가장자리와 연결된 체크무늬 후보만 배경으로 판정한다."""
    rgb = im.convert("RGB")
    w, h = rgb.size
    px = rgb.load()
    seen = bytearray(w * h)
    q: deque[tuple[int, int]] = deque()

    def seed(x: int, y: int) -> None:
        i = y * w + x
        if not seen[i] and is_bright_neutral(px[x, y]):
            seen[i] = 1
            q.append((x, y))

    for x in range(w):
        seed(x, 0)
        seed(x, h - 1)
    for y in range(h):
        seed(0, y)
        seed(w - 1, y)

    # 8방향으로 이어진 체크무늬 셀을 모두 제거한다.
    while q:
        x, y = q.popleft()
        for dx, dy in ((-1, -1), (0, -1), (1, -1), (-1, 0),
                       (1, 0), (-1, 1), (0, 1), (1, 1)):
            nx, ny = x + dx, y + dy
            if not (0 <= nx < w and 0 <= ny < h):
                continue
            i = ny * w + nx
            if not seen[i] and is_bright_neutral(px[nx, ny]):
                seen[i] = 1
                q.append((nx, ny))
    return seen


def prepare(src: Path, size: int = 256) -> Image.Image:
    """고해상도 원본을 정리해 RGBA 캔버스로 반환한다."""
    if size < 256:
        raise ValueError("최종 산출물은 최소 256px이어야 합니다")
    original = Image.open(src).convert("RGBA")
    bg = connected_background(original)
    w, h = original.size
    keyed = original.copy()
    alpha = keyed.getchannel("A")
    ap = alpha.load()
    for i, is_bg in enumerate(bg):
        if is_bg:
            ap[i % w, i // w] = 0
    keyed.putalpha(alpha)

    box = alpha.getbbox()
    if box is None:
        raise SystemExit(f"전경을 찾지 못함: {src}")
    x0, y0, x1, y1 = box
    pad = max(8, round(max(x1 - x0, y1 - y0) * 0.08))
    x0, y0 = max(0, x0 - pad), max(0, y0 - pad)
    x1, y1 = min(w, x1 + pad), min(h, y1 + pad)
    crop = keyed.crop((x0, y0, x1, y1))
    side = max(crop.width, crop.height)
    canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    canvas.alpha_composite(crop, ((side - crop.width) // 2, (side - crop.height) // 2))
    final = canvas.resize((size, size), Image.Resampling.LANCZOS)
    # 완전히 빈 픽셀은 RGB도 비워 둬서 Minecraft의 압출면/halo를 방지한다.
    fp = final.load()
    for y in range(size):
        for x in range(size):
            r, g, b, a = fp[x, y]
            if a == 0:
                fp[x, y] = (0, 0, 0, 0)
    assert final.mode == "RGBA" and final.size == (size, size)
    assert final.getchannel("A").getbbox() is not None
    return final


def process(src: Path, dst: Path, size: int) -> None:
    final = prepare(src, size)
    dst.parent.mkdir(parents=True, exist_ok=True)
    final.save(dst)
    assert final.mode == "RGBA" and final.size == (size, size)
    assert final.getchannel("A").getbbox() is not None
    print(f"{dst}: {final.size}, removed_bg={sum(bg)}, alpha={final.getchannel('A').getextrema()}, bbox={final.getchannel('A').getbbox()}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("source", type=Path)
    ap.add_argument("output", type=Path)
    ap.add_argument("--size", type=int, default=256)
    args = ap.parse_args()
    if args.size < 256:
        ap.error("최종 산출물은 최소 256px이어야 합니다")
    process(args.source, args.output, args.size)


if __name__ == "__main__":
    main()
