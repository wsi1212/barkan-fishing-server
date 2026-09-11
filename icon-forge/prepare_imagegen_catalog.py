#!/usr/bin/env python3
"""ImageGen 장비 원화를 카탈로그 PNG로 안전하게 가져온다.

ImageGen이 실제 알파 대신 흰색/회색 체크무늬를 그려 반환하는 경우가 있어,
일반적인 모서리 크로마키만으로는 장비의 흰색 하이라이트까지 지워질 수 있다.
이 도구는 테두리에서 시작한 중성 고휘도 영역만 flood-fill로 제거한 뒤
프리멀티플 축소하여 기존 ImageGen 장비 아이콘과 같은 투명 PNG를 만든다.
모델과 item 정의는 건드리지 않고 텍스처만 교체한다.
"""
from __future__ import annotations

import argparse
from collections import deque
from pathlib import Path

from PIL import Image, ImageChops, ImageFilter

from catalog_build import RP


def has_real_alpha(im: Image.Image) -> bool:
    """ImageGen 결과가 실제 투명 배경인지 판정한다."""
    alpha = im.getchannel("A")
    w, h = im.size
    points = [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1),
              (w // 2, 0), (w // 2, h - 1), (0, h // 2), (w - 1, h // 2)]
    return sum(alpha.getpixel(p) == 0 for p in points) >= 4


def strip_checkerboard(im: Image.Image) -> Image.Image:
    """테두리와 연결된 체크무늬만 투명화한다."""
    im = im.convert("RGBA")
    w, h = im.size
    rgb = im.convert("RGB")
    px = rgb.load()

    def background_like(x: int, y: int) -> bool:
        r, g, b = px[x, y]
        # 체크무늬는 거의 무채색이며, 장비의 밝은 금속/실은 어두운 외곽선에
        # 둘러싸여 있으므로 테두리 flood-fill에 들어오지 않는다.
        # ImageGen checkerboards are not consistently near-white. Some runs use
        # alternating ~#d2d2d2/#fdfdfd tiles, so accepting only >=220 leaves the
        # darker half baked into the icon. Flood-fill starts at the canvas edge,
        # therefore this wider neutral-gray threshold does not erase enclosed
        # silver highlights on the item itself.
        return max(r, g, b) - min(r, g, b) <= 18 and min(r, g, b) >= 190

    seen = bytearray(w * h)
    queue: deque[tuple[int, int]] = deque()

    def push(x: int, y: int) -> None:
        if 0 <= x < w and 0 <= y < h:
            i = y * w + x
            if not seen[i] and background_like(x, y):
                seen[i] = 1
                queue.append((x, y))

    for x in range(w):
        push(x, 0)
        push(x, h - 1)
    for y in range(h):
        push(0, y)
        push(w - 1, y)

    while queue:
        x, y = queue.popleft()
        push(x - 1, y)
        push(x + 1, y)
        push(x, y - 1)
        push(x, y + 1)

    out = im.copy()
    out_px = out.load()
    for i, marked in enumerate(seen):
        if marked:
            x = i % w
            y = i // w
            out_px[x, y] = (0, 0, 0, 0)
    return out


def normalize(source: Path, target: Path, size: int, pixel_grid: int | None = None) -> None:
    src = Image.open(source).convert("RGBA")
    if not has_real_alpha(src):
        # 가짜 체크무늬가 아닌 불투명 결과를 실수로 설치하지 않도록 강제한다.
        src = strip_checkerboard(src)
    # ImageGen can encode the solid interior of a cutout as alpha 250~254.
    # Treat that as opaque so the 16px inventory icon does not become a faint,
    # mostly-semi-transparent silhouette; keep only the actual edge antialiasing.
    r, g, b, alpha = src.split()
    alpha = alpha.point(lambda value: 255 if value >= 248 else value)
    src = Image.merge("RGBA", (r, g, b, alpha))
    bbox = src.getchannel("A").getbbox()
    if bbox is None:
        raise SystemExit(f"배경 제거 후 내용이 없습니다: {source}")
    cropped = src.crop(bbox)
    # Exact-bbox crops touch the 16px slot edge after downscaling. Keep a small
    # clear rim while letting narrow props retain enough width to read in-slot.
    pad = max(1, round(max(cropped.size) * 0.05))
    side = max(cropped.size) + pad * 2
    square = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    square.alpha_composite(cropped, ((side - cropped.width) // 2, (side - cropped.height) // 2))

    # 투명 가장자리의 흰색/회색 헤일로를 줄이고, 축소 시 색 번짐을 방지한다.
    r, g, b, alpha = square.split()
    premultiplied = Image.merge("RGBA", (
        ImageChops.multiply(r, alpha),
        ImageChops.multiply(g, alpha),
        ImageChops.multiply(b, alpha),
        alpha,
    ))
    small = premultiplied.resize((size, size), Image.Resampling.LANCZOS)
    sp = small.load()
    for y in range(size):
        for x in range(size):
            rr, gg, bb, aa = sp[x, y]
            if aa == 0:
                sp[x, y] = (0, 0, 0, 0)
            else:
                factor = 255 / aa
                sp[x, y] = (min(255, round(rr * factor)), min(255, round(gg * factor)),
                            min(255, round(bb * factor)), aa)
    small = small.filter(ImageFilter.UnsharpMask(radius=1, percent=55, threshold=2))
    if pixel_grid:
        if pixel_grid > size or size % pixel_grid:
            raise SystemExit("--pixel-grid는 --size의 약수여야 합니다")
        grid = small.resize((pixel_grid, pixel_grid), Image.Resampling.LANCZOS)
        alpha = grid.getchannel("A").point(lambda value: 255 if value >= 128 else 0)
        rgb = grid.convert("RGB")
        pixels = rgb.load()
        for y in range(pixel_grid):
            for x in range(pixel_grid):
                red, green, blue = pixels[x, y]
                if red < 8 and green < 8 and blue < 8:
                    pixels[x, y] = (12, 18, 27)
        rgb = rgb.quantize(colors=14, method=Image.Quantize.MEDIANCUT).convert("RGB")
        grid = Image.merge("RGBA", (*rgb.split(), alpha))
        small = grid.resize((size, size), Image.Resampling.NEAREST)
    target.parent.mkdir(parents=True, exist_ok=True)
    small.save(target)
    if small.getchannel("A").getbbox() is None or target.stat().st_size <= 100:
        raise SystemExit(f"생성 결과가 비어 있습니다: {target}")
    print(f"저장: {target} ({size}x{size}), source={src.size}, bbox={bbox}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("source", type=Path)
    ap.add_argument("icon_id")
    ap.add_argument("--size", type=int, required=True)
    ap.add_argument("--pixel-grid", type=int,
                    help="논리 픽셀 격자로 축소·14색 양자화한 뒤 nearest로 확대")
    args = ap.parse_args()
    target = RP / "assets/minecraft/textures/item/barkan_icon" / f"{args.icon_id}.png"
    normalize(args.source.expanduser(), target, args.size, args.pixel_grid)


if __name__ == "__main__":
    main()
