#!/usr/bin/env python3
"""ImageGen 원화를 BPS의 실제 54칸 좌표에 맞춘 전용 제출 판으로 정리한다."""
from pathlib import Path

from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
RAW = HERE / "src" / "bps" / "bg_imagegen-v2.png"
OUT = HERE / "src" / "bps" / "bg_source.png"
W, H, TOP_H, SLOT, X0, Y0 = 704, 888, 552, 72, 28, 68


def slot_xy(slot: int) -> tuple[int, int]:
    return X0 + SLOT * (slot % 9), Y0 + SLOT * (slot // 9)


def frame(draw: ImageDraw.ImageDraw, slot: int, edge, fill, inset: int = 4) -> None:
    x, y = slot_xy(slot)
    draw.rounded_rectangle((x + inset, y + inset, x + SLOT - inset, y + SLOT - inset),
                           radius=10, fill=fill, outline=edge, width=4)


def submission_socket(draw: ImageDraw.ImageDraw, slot: int, number: int) -> None:
    x, y = slot_xy(slot)
    draw.rounded_rectangle((x - 5, y - 5, x + SLOT + 5, y + SLOT + 5), radius=15,
                           fill=(21, 67, 72, 255), outline=(57, 219, 211, 255), width=5)
    draw.ellipse((x + 2, y + 2, x + SLOT - 2, y + SLOT - 2), fill=(35, 50, 48, 255),
                 outline=(242, 193, 78, 255), width=6)
    draw.ellipse((x + 10, y + 10, x + SLOT - 10, y + SLOT - 10), fill=(20, 35, 36, 255),
                 outline=(123, 83, 32, 255), width=2)
    # 숫자는 슬롯 위쪽 배지라 실제 물고기 아이콘을 가리지 않는다.
    draw.ellipse((x + 23, y - 16, x + 49, y + 10), fill=(242, 193, 78, 255),
                 outline=(76, 45, 14, 255), width=3)
    draw.text((x + 36, y - 13), str(number), anchor="ma", fill=(45, 29, 11, 255), stroke_width=1)


def main() -> None:
    if not RAW.is_file():
        raise SystemExit(f"BPS 원화가 없습니다: {RAW}")
    raw = Image.open(RAW).convert("RGBA")
    out = Image.new("RGBA", (W, H), (30, 22, 14, 255))
    out.alpha_composite(raw.resize((W, TOP_H), Image.Resampling.LANCZOS), (0, 0))
    draw = ImageDraw.Draw(out)

    # 선택 버튼은 상단의 작은 금속 패널, 실제 물고기는 가운데 세 개의 원형 소켓.
    frame(draw, 11, (112, 210, 151, 255), (24, 71, 55, 255))
    frame(draw, 15, (112, 210, 151, 255), (24, 71, 55, 255))
    for number, slot in enumerate((19, 22, 25), 1):
        submission_socket(draw, slot, number)

    # 하단 액션은 물고기 소켓과 색·형태를 달리해 한눈에 구별된다.
    frame(draw, 38, (249, 199, 72, 255), (118, 76, 20, 255), inset=0)
    frame(draw, 40, (76, 235, 130, 255), (19, 99, 54, 255), inset=0)
    frame(draw, 42, (240, 83, 69, 255), (104, 29, 22, 255), inset=0)

    # 플레이어 가방은 build_plate.py가 공통 규격의 칸을 정확한 좌표에 합성한다.
    draw.rectangle((0, TOP_H, W, H), fill=(25, 18, 12, 255))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    out.convert("RGB").save(OUT)
    print(f"BPS 전용 판 → {OUT} (원화 {raw.size} → {W}x{H})")


if __name__ == "__main__":
    main()
