#!/usr/bin/env python3
"""ImageGen 특수작물 아이콘을 리소스팩용 64×64 PNG로 정리한다.

ImageGen이 일부 결과에서 실제 투명 알파 대신 검정/흰색/체커보드를 그릴 수 있어,
가장자리에서 연결된 중립색 배경만 제거한다. 작물 본체의 색 있는 픽셀과 내부
그림자는 유지하고, 최종 아이콘은 64×64로 저장한다(16×16 원본으로 축소하지 않음).
"""
from __future__ import annotations

from collections import deque
from pathlib import Path

from PIL import Image


GEN = Path("/Users/user/.codex/generated_images/01a02b35-2a57-7e81-83e8-c19a65ea699d")
OUT = Path("/Users/user/development/barkan-resourcepack/assets/minecraft/textures/item/barkan_icon")

FILES = {
    "wheat_harvest": "exec-0aee685f-f686-4000-85c8-f1aae39b8805.png",
    "carrot_harvest": "exec-3d4485e7-f832-4ca6-b370-098a8c5985ee.png",
    "potato_harvest": "exec-02aaa052-efe0-4105-a259-42549cf5d717.png",
    "tomato_harvest": "exec-b11a879d-f808-4c50-9c73-bba5b06ac682.png",
    "cabbage_harvest": "exec-d6c16752-0a79-4ae6-9dbe-9eac6190c0a4.png",
    "mushroom_harvest": "exec-3e3804c4-5250-456b-9bbe-b932ee4e46c8.png",
    "melon_harvest": "exec-56f3be7a-b406-43f9-8a04-99c897439ffe.png",
    "wheat_seed": "exec-334ddd3d-1288-4406-95ab-941f9f953229.png",
    "carrot_seed": "exec-202c73e2-f47f-44cd-8f38-90849dcf61ed.png",
    "potato_seed": "exec-ca103850-df46-488e-bd42-fbbcfbe25a9a.png",
    "tomato_seed": "exec-b88dc7ef-c811-4eeb-8e2f-7fc69626ab79.png",
    "cabbage_seed": "exec-ea2374a8-8cf2-4362-9029-0a1a690f9d16.png",
    "mushroom_seed": "exec-ef90473a-7a69-4fa1-8b21-b85bd6c5455b.png",
    "melon_seed": "exec-50d2b7de-3456-437c-a49e-2fed7d3d068d.png",
}


def remove_edge_background(im: Image.Image) -> Image.Image:
    """연결된 무채색 배경을 알파 0으로 만든다. 본체 내부 색은 건드리지 않는다."""
    im = im.convert("RGBA")
    px = im.load()
    w, h = im.size
    candidate = bytearray(w * h)
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if a == 0:
                continue
            spread = max(r, g, b) - min(r, g, b)
            lum = (r + g + b) / 3
            # 검정/흰색/회색/체커보드 계열만 후보. 색 있는 본체는 제외.
            if spread <= 32 and (lum < 95 or lum > 158):
                candidate[y * w + x] = 1

    seen = bytearray(w * h)
    q = deque()
    for x in range(w):
        q.extend(((x, 0), (x, h - 1)))
    for y in range(h):
        q.extend(((0, y), (w - 1, y)))
    while q:
        x, y = q.popleft()
        if x < 0 or y < 0 or x >= w or y >= h:
            continue
        i = y * w + x
        if seen[i] or not candidate[i]:
            continue
        seen[i] = 1
        q.extend(((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)))

    out = im.copy()
    alpha = out.getchannel("A")
    for y in range(h):
        for x in range(w):
            if seen[y * w + x]:
                alpha.putpixel((x, y), 0)
    out.putalpha(alpha)
    return out


def fit_icon(im: Image.Image) -> Image.Image:
    im = remove_edge_background(im)
    bbox = im.getchannel("A").getbbox()
    if not bbox:
        raise ValueError("투명 제거 후 본체가 남지 않음")
    im = im.crop(bbox)
    im.thumbnail((52, 52), Image.Resampling.LANCZOS)
    out = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    out.alpha_composite(im, ((64 - im.width) // 2, (64 - im.height) // 2))
    return out


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for name, file_name in FILES.items():
        final = fit_icon(Image.open(GEN / file_name))
        final.save(OUT / f"crop_{name}.png")
        assert final.getchannel("A").getpixel((0, 0)) == 0
    print(f"OK — ImageGen 아이콘 {len(FILES)}개를 64×64 투명 PNG로 저장")


if __name__ == "__main__":
    main()
