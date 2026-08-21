#!/usr/bin/env python3
"""슬롯 GUI용 작은 카지노 컨트롤 아이콘.

정체성 표
  ui_lever_up: 금색 짧은 레버 + 루비 손잡이(위) — 누르기 전
  ui_lever_down: 같은 레버가 아래로 눌린 상태 — 누른 후
  ui_replay: 금색 순환 화살표 + 루비 칩 — 같은 금액으로 다시
  ui_result: 금색 잭팟 별 배지 + 루비 중심 — 결과/지급 안내
  ui_back: 금색 좌향 화살표 + 버건디 인셋 — 화면 닫기/뒤로가기

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


def make_lever_up() -> Image.Image:
    """중심축에서 머리가 수직 위를 보는 0도 상태."""
    im = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    # 고정축/받침
    ellipse(d, (5.4, 7.0, 10.6, 12.2), fill=(28, 18, 12, 255), outline=(91, 52, 17, 255), width=xy(0.7))
    ellipse(d, (6.1, 7.7, 9.9, 11.5), fill=(208, 135, 32, 255), outline=(255, 220, 105, 255), width=xy(0.45))
    ellipse(d, (7.1, 8.7, 8.9, 10.5), fill=(112, 56, 17, 255), outline=(255, 235, 137, 255), width=xy(0.3))
    # 중심축 위로 올라오는 직선 레버. 축을 먼저 그리고 줄을 나중에 그려
    # 줄이 가운데 동그라미에 묻히지 않고 물리적으로 고정돼 보이게 한다.
    d.rounded_rectangle((xy(7.0), xy(2.5), xy(9.0), xy(9.2)), radius=xy(0.45), fill=(39, 24, 12, 255))
    d.rounded_rectangle((xy(7.5), xy(2.8), xy(8.6), xy(9.0)), radius=xy(0.25), fill=(188, 111, 20, 255))
    d.line((xy(7.8), xy(3.0), xy(7.8), xy(8.8)), fill=(255, 213, 91, 255), width=xy(0.35))
    # 레버 머리 — 위쪽을 향하는 루비 캡
    ellipse(d, (5.4, 0.2, 10.6, 4.8), fill=(35, 12, 12, 255), outline=(236, 167, 44, 255), width=xy(0.55))
    ellipse(d, (6.1, 0.9, 9.9, 4.1), fill=(147, 18, 24, 255), outline=(255, 92, 69, 255), width=xy(0.35))
    ellipse(d, (6.7, 1.4, 7.7, 2.4), fill=(255, 218, 157, 210))
    return im.resize((128, 128), Image.Resampling.LANCZOS)


def make_lever_down() -> Image.Image:
    """같은 픽셀 아이콘을 중심축 기준 정확히 180도 뒤집은 상태."""
    return make_lever_up().transpose(Image.Transpose.ROTATE_180)


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
    make_lever_up().save(OUT / "ui_pull.png")
    make_lever_up().save(OUT / "ui_lever_up.png")
    make_lever_down().save(OUT / "ui_lever_down.png")
    make_stop().save(OUT / "ui_stop.png")
    print(f"카지노 레버 상태 아이콘 → {OUT} (결과/컨트롤 3종은 ImageGen 설치 스크립트 사용)")


if __name__ == "__main__":
    main()
