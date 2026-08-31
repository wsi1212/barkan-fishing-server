#!/usr/bin/env python3
"""배낭 배경을 서버의 고정 슬롯 좌표에 맞춰 조립한다.

ImageGen은 외곽 가죽 프레임과 캔버스 질감만 담당한다. 반복 슬롯은 생성 결과에서
가져오지 않는다 — 이전 버전은 첫 AI 슬롯 샘플의 오른쪽·아래 경계가 72px 셀 안에
완전히 들어오지 않아 실제 아이템 칸과 어긋났다. 아이스박스에서 검증된 72x72
소켓을 따뜻한 가죽/황동 팔레트로 색변환해 45칸에 동일한 좌표로 찍는다.
"""
import os

from PIL import Image, ImageDraw, ImageOps

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "src", "backpack")
ICEBOX = os.path.join(HERE, "src", "icebox", "bg_source.png")
W, H = 704, 888
GRID_X, GRID_Y, CELL, COLS, ROWS = 28, 140, 72, 9, 5
TOP_Y = 68


def main():
    raw = os.path.join(SRC, "bg_empty_raw.png")
    out = os.path.join(SRC, "bg_source.png")
    im = Image.open(raw).convert("RGB").resize((W, H), Image.Resampling.LANCZOS)

    # 아이스박스에서 이미 실전 검수된 72x72 소켓(1행 5열)을 가져와 가죽 팔레트로
    # 변환한다. 전체 셀을 덮으므로 AI가 중앙 패널에 남긴 가짜 격자는 절대 살아남지 않는다.
    ice = Image.open(ICEBOX).convert("RGB")
    source = ice.crop((GRID_X, GRID_Y + CELL, GRID_X + CELL, GRID_Y + 2 * CELL)).convert("L")
    socket = ImageOps.colorize(
        source,
        black=(19, 12, 9),
        mid=(76, 40, 21),
        white=(201, 148, 67),
    ).convert("RGB")

    # 같은 셀 안의 프레임이 배경 위에 자연스럽게 앉도록 미세한 가죽색 그림자를
    # 먼저 깐다. 소켓 자체는 완전 불투명으로 유지한다.
    shadow = Image.new("RGB", (CELL, CELL), (17, 11, 8))
    sd = ImageDraw.Draw(shadow)
    sd.rectangle((3, 3, CELL - 4, CELL - 4), outline=(43, 24, 14), width=2)

    def stamp(x, y):
        im.paste(shadow, (x, y))
        im.paste(socket, (x, y))

    # 상단 raw 0/8은 휴대용 배낭·상점 버튼이 실제로 올라가는 자리다.
    for col in (0, 8):
        stamp(GRID_X + CELL * col, TOP_Y)

    # 배낭 보관칸 raw 9~53 = 5행×9열. 모든 셀을 동일한 72x72 아트로 고정한다.
    for row in range(ROWS):
        for col in range(COLS):
            stamp(GRID_X + CELL * col, GRID_Y + CELL * row)
    im.save(out)
    print(f"  상단 소켓 2개 + 보관 소켓 {COLS * ROWS}개 고정 · {W}x{H} RGB → {out}")


if __name__ == "__main__":
    main()
