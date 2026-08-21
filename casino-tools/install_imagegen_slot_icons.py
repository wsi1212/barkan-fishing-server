#!/usr/bin/env python3
"""Install ImageGen casino icons after transparent-edge cleanup.

ImageGen returned the replay icon with real alpha, but rendered a checkerboard
preview into the star and back-arrow files.  This keeps the generated artwork
and removes only the edge-connected neutral checkerboard pixels before fitting
each icon to a square 128x128 item texture.
"""

from collections import deque
from pathlib import Path

from PIL import Image


OUT = Path("/Users/user/development/barkan-resourcepack/assets/minecraft/textures/item/slot")
CASINO_OUT = Path("/Users/user/development/barkan-resourcepack/assets/minecraft/textures/item/casino")
SOURCES = {
    "ui_replay.png": Path("/Users/user/.codex/generated_images/01a01fb0-f9c7-7c03-acf8-ffde8268c0e1/exec-4e56d778-a7f0-44f0-b0a9-e03e340ce6ba.png"),
    "ui_result.png": Path("/Users/user/.codex/generated_images/01a01fb0-f9c7-7c03-acf8-ffde8268c0e1/exec-3998130b-2ea6-49c6-8608-777b8acdabd6.png"),
    "ui_back.png": Path("/Users/user/.codex/generated_images/01a01fb0-f9c7-7c03-acf8-ffde8268c0e1/exec-8b44ce56-9589-44f1-9ede-1fb6522d203e.png"),
}
CASINO_SOURCES = {
    "ui_join.png": Path("/Users/user/.codex/generated_images/01a01fb0-f9c7-7c03-acf8-ffde8268c0e1/exec-20b63984-1ed4-417b-bde0-674b22065579.png"),
    "ui_leave.png": Path("/Users/user/.codex/generated_images/01a01fb0-f9c7-7c03-acf8-ffde8268c0e1/exec-6b5a6ad2-a2b7-4faa-a3bc-5f3d692d8b9a.png"),
    "ui_game_badge.png": Path("/Users/user/.codex/generated_images/01a01fb0-f9c7-7c03-acf8-ffde8268c0e1/exec-d89892e0-1cbc-44d0-b6ad-d00378c63212.png"),
    "ui_rulebook.png": Path("/Users/user/.codex/generated_images/01a01fb0-f9c7-7c03-acf8-ffde8268c0e1/exec-9d430250-496d-484a-9cd5-1ce7cab80ba9.png"),
}


def checkerboard_like(pixel: tuple[int, int, int, int]) -> bool:
    r, g, b, a = pixel
    return a > 0 and max(r, g, b) - min(r, g, b) <= 16 and min(r, g, b) >= 215


def remove_edge_background(im: Image.Image) -> Image.Image:
    rgba = im.convert("RGBA")
    w, h = rgba.size
    removed: set[tuple[int, int]] = set()
    queue: deque[tuple[int, int]] = deque()

    for x in range(w):
        for y in (0, h - 1):
            if checkerboard_like(rgba.getpixel((x, y))):
                queue.append((x, y))
    for y in range(h):
        for x in (0, w - 1):
            if checkerboard_like(rgba.getpixel((x, y))):
                queue.append((x, y))

    while queue:
        x, y = queue.popleft()
        if (x, y) in removed or not checkerboard_like(rgba.getpixel((x, y))):
            continue
        removed.add((x, y))
        for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1),
                       (x - 1, y - 1), (x + 1, y - 1), (x - 1, y + 1), (x + 1, y + 1)):
            if 0 <= nx < w and 0 <= ny < h and (nx, ny) not in removed:
                queue.append((nx, ny))

    pixels = rgba.load()
    for x, y in removed:
        pixels[x, y] = (0, 0, 0, 0)

    bbox = rgba.getbbox()
    if bbox is None:
        raise ValueError("ImageGen icon became empty after background cleanup")
    left, top, right, bottom = bbox
    pad = max(12, int(max(right - left, bottom - top) * 0.045))
    left = max(0, left - pad)
    top = max(0, top - pad)
    right = min(w, right + pad)
    bottom = min(h, bottom + pad)
    crop_w, crop_h = right - left, bottom - top
    side = max(crop_w, crop_h)
    margin = max(18, int(side * 0.04))
    cx, cy = (left + right) // 2, (top + bottom) // 2
    square = Image.new("RGBA", (side + margin * 2, side + margin * 2), (0, 0, 0, 0))
    square.alpha_composite(rgba.crop((left, top, right, bottom)),
                           (margin + (side - crop_w) // 2, margin + (side - crop_h) // 2))
    return square.resize((128, 128), Image.Resampling.LANCZOS)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    CASINO_OUT.mkdir(parents=True, exist_ok=True)
    for target, sources in ((OUT, SOURCES), (CASINO_OUT, CASINO_SOURCES)):
        for filename, source in sources.items():
            if not source.exists():
                raise FileNotFoundError(source)
            cleaned = remove_edge_background(Image.open(source))
            cleaned.save(target / filename)
            print(target.name, filename, cleaned.size, cleaned.mode, cleaned.getbbox())


if __name__ == "__main__":
    main()
