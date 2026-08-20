#!/usr/bin/env python3
"""슬롯 GUI용 작은 카지노 컨트롤 아이콘.

정체성 표
  ui_lever_up: 금색 짧은 레버 + 루비 손잡이(위) — 누르기 전
  ui_lever_down: 같은 레버가 아래로 눌린 상태 — 누른 후

아이콘은 프로젝트의 4배 리소스팩 규격(128x128)으로 만들고, 실제 인벤토리에서는
16x16로 읽힌다. 바닐라 레드스톤 토치/염료 대신 같은 카지노 팔레트의 실루엣을 쓴다.
"""

from pathlib import Path

from PIL import Image, ImageDraw


OUT = Path("/Users/user/development/barkan-resourcepack/assets/minecraft/textures/item/slot")
DRAW_SCALE = 32
SIZE = 16 * DRAW_SCALE


def xy(value: float) -> int:
    return round(value * DRAW_SCALE)


def poly(draw: ImageDraw.ImageDraw, points, **kwargs):
    draw.polygon([(xy(x), xy(y)) for x, y in points], **kwargs)


def ellipse(draw: ImageDraw.ImageDraw, box, **kwargs):
    draw.ellipse(tuple(xy(v) for v in box), **kwargs)


def make_pull() -> Image.Image:
    im = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    ellipse(d, (3.1, 11.2, 12.8, 15.0), fill=(28, 18, 12, 255))
    ellipse(d, (3.5, 10.8, 12.4, 14.4), fill=(91, 52, 17, 255), outline=(17, 13, 10, 255), width=xy(0.7))
    ellipse(d, (4.2, 11.0, 11.7, 13.7), fill=(208, 135, 32, 255), outline=(255, 220, 105, 255), width=xy(0.45))
    poly(d, [(7.0, 12.1), (8.7, 12.5), (11.2, 5.0), (9.5, 4.6)], fill=(39, 24, 12, 255))
    poly(d, [(7.6, 11.9), (8.6, 12.0), (10.9, 5.3), (10.0, 5.1)], fill=(188, 111, 20, 255))
    poly(d, [(8.1, 11.6), (8.6, 11.7), (10.5, 5.5), (10.2, 5.4)], fill=(255, 213, 91, 255))
    ellipse(d, (8.8, 2.5, 12.5, 6.2), fill=(35, 12, 12, 255), outline=(236, 167, 44, 255), width=xy(0.55))
    ellipse(d, (9.3, 3.0, 12.0, 5.7), fill=(147, 18, 24, 255), outline=(255, 92, 69, 255), width=xy(0.35))
    ellipse(d, (9.8, 3.3, 10.6, 4.0), fill=(255, 218, 157, 210))
    return im.resize((128, 128), Image.Resampling.LANCZOS)


def make_lever_down() -> Image.Image:
    """같은 받침에서 손잡이가 아래·왼쪽으로 눌린 상태."""
    im = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    ellipse(d, (3.1, 11.2, 12.8, 15.0), fill=(28, 18, 12, 255))
    ellipse(d, (3.5, 10.8, 12.4, 14.4), fill=(91, 52, 17, 255), outline=(17, 13, 10, 255), width=xy(0.7))
    ellipse(d, (4.2, 11.0, 11.7, 13.7), fill=(208, 135, 32, 255), outline=(255, 220, 105, 255), width=xy(0.45))
    poly(d, [(7.0, 12.1), (8.7, 12.5), (5.3, 8.8), (4.1, 9.7)], fill=(39, 24, 12, 255))
    poly(d, [(7.6, 11.9), (8.6, 12.0), (5.5, 8.9), (4.8, 9.6)], fill=(188, 111, 20, 255))
    poly(d, [(8.1, 11.6), (8.6, 11.7), (5.7, 9.1), (5.2, 9.5)], fill=(255, 213, 91, 255))
    ellipse(d, (2.8, 7.0, 6.5, 10.7), fill=(35, 12, 12, 255), outline=(236, 167, 44, 255), width=xy(0.55))
    ellipse(d, (3.3, 7.5, 6.0, 10.2), fill=(147, 18, 24, 255), outline=(255, 92, 69, 255), width=xy(0.35))
    ellipse(d, (3.8, 7.8, 4.6, 8.5), fill=(255, 218, 157, 210))
    return im.resize((128, 128), Image.Resampling.LANCZOS)


def make_stop() -> Image.Image:
    im = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    cx = cy = 8

    def octagon(radius):
        return [
            (cx - radius * 0.45, cy - radius), (cx + radius * 0.45, cy - radius),
            (cx + radius, cy - radius * 0.45), (cx + radius, cy + radius * 0.45),
            (cx + radius * 0.45, cy + radius), (cx - radius * 0.45, cy + radius),
            (cx - radius, cy + radius * 0.45), (cx - radius, cy - radius * 0.45),
        ]

    poly(d, octagon(6.8), fill=(25, 13, 10, 255))
    poly(d, octagon(6.3), fill=(205, 133, 30, 255))
    poly(d, octagon(5.55), fill=(92, 12, 20, 255), outline=(255, 210, 83, 255), width=xy(0.35))
    poly(d, octagon(4.8), fill=(164, 20, 29, 255))
    d.rounded_rectangle((xy(5.1), xy(7.0), xy(10.9), xy(9.0)), radius=xy(0.45), fill=(255, 218, 112, 255))
    d.line((xy(5.5), xy(7.3), xy(10.4), xy(7.3)), fill=(255, 246, 201, 220), width=xy(0.35))
    return im.resize((128, 128), Image.Resampling.LANCZOS)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    make_pull().save(OUT / "ui_pull.png")
    make_pull().save(OUT / "ui_lever_up.png")
    make_lever_down().save(OUT / "ui_lever_down.png")
    make_stop().save(OUT / "ui_stop.png")
    print(f"카지노 레버 상태 아이콘 2종 → {OUT}")


if __name__ == "__main__":
    main()
