#!/usr/bin/env python3
"""길드 임무 ImageGen 원화를 54칸 GUI 좌표에 맞는 전용 판으로 손질한다."""
from pathlib import Path

from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
RAW = HERE / "src" / "guild_quest_bg_imagegen.png"
OUT = HERE / "src" / "guild_quest" / "bg_source.png"
W, H = 704, 888
SLOT = 72
X0 = 28


def outline_slot(draw: ImageDraw.ImageDraw, slot: int, row: int, color) -> None:
    col = slot % 9
    x, y = X0 + SLOT * col, 68 + SLOT * row
    box = (x + 4, y + 4, x + SLOT - 5, y + SLOT - 5)
    draw.rounded_rectangle(box, radius=8, outline=(*color, 255), width=3)
    draw.rounded_rectangle((box[0] + 5, box[1] + 5, box[2] - 5, box[3] - 5),
                           radius=5, outline=(57, 43, 28, 210), width=2)


def medal_slot(draw: ImageDraw.ImageDraw, slot: int) -> None:
    col = slot % 9
    x, y = X0 + SLOT * col, 68 + SLOT * 4
    cx, cy = x + SLOT // 2, y + SLOT // 2
    draw.ellipse((cx - 29, cy - 29, cx + 29, cy + 29),
                 fill=(43, 31, 22, 255), outline=(199, 151, 67, 255), width=4)
    draw.ellipse((cx - 20, cy - 20, cx + 20, cy + 20),
                 outline=(90, 174, 163, 255), width=3)


def button(draw: ImageDraw.ImageDraw, slot: int, accent) -> None:
    col = slot % 9
    row = slot // 9
    x, y = X0 + SLOT * col, 68 + SLOT * row
    box = (x + 5, y + 7, x + SLOT - 6, y + SLOT - 7)
    draw.rounded_rectangle(box, radius=9, fill=(52, 39, 25, 255), outline=(*accent, 255), width=3)


def main() -> None:
    if not RAW.exists():
        raise SystemExit(f"원화가 없습니다: {RAW}")
    raw = Image.open(RAW).convert("RGBA")
    out = Image.new("RGBA", (W, H), (29, 22, 15, 255))

    # 원화의 제목판·임무 게시판·기여자 메달·하단 목재를 GUI 높이에 맞춘다.
    # 각 밴드를 따로 리샘플링해 세로형 원화의 핵심 장식이 아래 인벤 영역으로
    # 밀려 내려가지 않게 한다.
    bands = [
        ((0, 800), (0, 330)),
        # 원화의 하단 5개 링을 실제 기여자 슬롯(4행) 중심에 맞춘다.
        ((800, 1090), (300, 496)),
        ((1090, raw.height), (496, H)),
    ]
    for (y0, y1), (t0, t1) in bands:
        crop = raw.crop((0, y0, raw.width, y1))
        out.paste(crop.resize((W, t1 - t0), Image.Resampling.LANCZOS), (0, t0))

    draw = ImageDraw.Draw(out)

    # 원화의 하단 대형 링은 간격이 1칸보다 넓다. 실제 머리 아이템 5개가
    # 38~42번에 붙으므로 그 구간만 목재·청록 로프로 정리하고 슬롯 폭의 메달을 다시 그린다.
    draw.rectangle((24, 310, 680, 498), fill=(48, 34, 22, 255))
    draw.rectangle((24, 314, 680, 321), fill=(11, 66, 62, 255))
    draw.rectangle((24, 482, 680, 489), fill=(11, 66, 62, 255))
    for y in range(354, 474, 24):
        draw.line((32, y, 672, y), fill=(72, 49, 29, 255), width=2)

    # 요약 4번과 기본 임무 카드 20·22·24의 실제 슬롯 외곽.
    outline_slot(draw, 4, 0, (221, 172, 83))
    for slot in (20, 22, 24):
        outline_slot(draw, slot, 2, (201, 158, 77))

    # 상위 기여자 38~42는 게시판 원화의 원형 메달과 같은 톤으로 맞춘다.
    for slot in (38, 39, 40, 41, 42):
        medal_slot(draw, slot)

    # 49번 뒤로 버튼은 하단 중앙의 황동 명판을 살려 둔다.
    button(draw, 49, (71, 151, 138))

    # 마지막 3행은 플레이어 인벤토리 영역. build_plate.py가 정확한 격자를 추가한다.
    draw.rectangle((24, 548, 680, 887), fill=(27, 21, 15, 255))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    out.convert("RGB").save(OUT)
    print(f"길드 임무 전용 판 → {OUT} (원화 {raw.size} → {W}x{H})")


if __name__ == "__main__":
    main()
