#!/usr/bin/env python3
"""납품 원화(bg_raw.png)를 정확한 캔버스에 맞춘다 — 통짜 리사이즈 + 구간별 세로 보정.

## 왜
그림 생성기가 가이드 캔버스를 정확히 못 맞춘다(1117x1409, 1236x1273 처럼 나온다).
비율이 맞으면 통짜 리사이즈로 끝나지만, 안 맞거나 **내부 층 위치가 어긋나면**
(예: 나무 구분 띠가 60px 낮아 인벤 첫 줄이 띠 위에 올라탐) 구간별로 다시 배치해야 한다.

## 방식
`BANDS` 는 (원본 y구간 → 목표 y구간) 목록이다. 프레임처럼 건드리면 안 되는 구간은
1:1로 두고, 판·띠처럼 늘려도 티가 안 나는 구간만 압축/확장한다. 좌우는 손대지 않는다
(가로는 프레임 두께만 문제라 원화 단계에서 잡는 게 맞다).

## 원본 보존
bg_raw.png 는 손대지 않는다. bg_source.png 는 **항상 여기서 재생성**되는 산출물이라
여러 번 돌려도 열화가 누적되지 않는다.

사용: python3 fit_plate.py common6
      python3 fit_plate.py fish_shop
"""
import os
import sys

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))

# gui이름: (목표 캔버스, 세로 보정 구간)
#   구간 없음([]) = 통짜 리사이즈만 (비율이 맞는 경우)
PLATES = {
    # 원화의 나무 구분 띠와 인벤 패널이 약 60px 낮아 인벤 첫 줄(y556~)이 띠 위에 올라탔다.
    # 컨테이너 영역(0~499)은 정확했으므로 그대로 두고 아래만 끌어올린다.
    # ★2026-08-09 재보정: 제목 명판이 GUI y 6~30 을 먹어 **슬롯 0행(y17~35)을 덮었다**.
    #   54칸 화면은 0행에 뒤로가기·닫기·탭을 두므로 그 위에 놋쇠 띠가 가로지르는 꼴이었다.
    #   명판은 제목 글자 한 줄(9px)만 받으면 되므로 GUI y 3~17(art 14~68)로 줄이고
    #   그만큼 판을 위로 넓힌다. 명판은 가로줄 위주라 눌러도 티가 덜 난다.
    "common6": ((704, 888), [((0, 20), (0, 14)),          # 상단 프레임 — 살짝 압축
                             ((20, 125), (14, 68)),       # 제목 명판 — 압축(0행을 비켜준다)
                             ((125, 500), (68, 500)),     # 컨테이너 판 — 위로 확장
                             ((500, 616), (500, 556)),    # 판 아래 테두리 + 나무 띠 — 압축
                             ((616, 859), (556, 860)),    # 인벤 패널 — 확장
                             ((859, 888), (860, 888))]),  # 하단 프레임 — 유지
    "fish_shop": ((704, 744), []),
    "wet_treasure": ((704, 672), []),
}


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    name = sys.argv[1]
    (W, H), bands = PLATES[name]
    d = os.path.join(HERE, "src", name)
    raw = Image.open(os.path.join(d, "bg_raw.png")).convert("RGBA")

    fit = raw.resize((W, H), Image.LANCZOS)
    if bands:
        out = Image.new("RGBA", (W, H))
        for (a0, a1), (b0, b1) in bands:
            out.paste(fit.crop((0, a0, W, a1)).resize((W, b1 - b0), Image.LANCZOS), (0, b0))
        fit = out
    assert fit.getchannel("A").getextrema()[0] == 255, "투명 픽셀이 있다 — 배경판은 불투명이어야 한다"
    fit.save(os.path.join(d, "bg_source.png"))
    print(f"{name}: {raw.size} → {W}x{H}" + (f", 세로 보정 {len(bands)}구간" if bands else ", 통짜 리사이즈"))


if __name__ == "__main__":
    main()
