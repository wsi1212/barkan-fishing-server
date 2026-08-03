#!/usr/bin/env python3
"""섬상점 GUI 글리프(barkan:gui ) — 하단 플레이어 인벤 영역까지 프레임 확장.

기존 176x133(상단 컨테이너 6행만 덮음)을 176x222(6행 상자 창 전체)로 늘린다.
상단 헤더+컨테이너창(y0~126)은 원본 그대로 보존하고, y127~221을 원본과 같은
어휘(2px 베벨 / 금색 레일 / 남색 채움 / 다이아 장식)로 다시 그린다.

★gui.json은 height도 222로 같이 올려야 한다 — 비트맵 글리프의 렌더 폭은
  텍스처폭 x (height / 텍스처높이) 라서, height를 133으로 두면 105px로 쭈그러든다.
  ascent는 13 유지(=창 y0에 상단 정렬: top = titleLabelY(6) + 7 - ascent).

6행 상자(176x222) 바닐라 좌표 — 슬롯 (sx,sy)의 텍스처 구멍은 (sx-1,sy-1) 18x18:
  컨테이너 6행 y17~124 / 인벤 3행 y138~191 / 핫바 y196~213 / 하단여백 y214~221
  슬롯 가로는 x7~169 (컨테이너와 동일) / "인벤토리" 라벨 y128~135

라벨 처리: 바닐라가 y128에 dark-gray(0x404040)로 "인벤토리"를 글리프 위에 덮어 찍는다.
원본의 금색 헤어라인이 그 자리에 있으면 글자가 레일을 갉아먹은 것처럼 보이므로,
이음매는 y128~136을 통짜 어두운 띠로 만들어 글자를 삼킨다(어두운 색 위 = 거의 안 보임).
원본 하단띠(금선+다이아 장식)는 y214~221로 그대로 이주 — 창 진짜 맨아래로 내려간다.
"""
import os

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
# 원본 상단부(176x133) = 커밋된 소스 자산. 리소스팩 쪽은 산출물이라 몇 번 돌려도 같은 결과.
SRC = os.path.join(HERE, "src", "island_shop_container.png")
OUT = os.path.expanduser(
    "~/development/barkan-resourcepack/assets/barkan/textures/gui/island_shop.png"
)
W, H_OLD, H_NEW = 176, 133, 222

# 원본에서 추출한 팔레트
L = (64, 110, 126, 255)   # 406e7e 밝은 베벨(좌·상)
G = (204, 164, 60, 255)   # cca43c 금색 레일
HI = (236, 200, 98, 255)  # ecc862 밝은 금색 하이라이트
D = (22, 38, 45, 255)     # 16262d 어두운 채움 / 베벨(우·하)
N = (40, 66, 78, 255)     # 28424e 측면 레일 안쪽 남색
CLEAR = (0, 0, 0, 0)


def row_fill(px, y, inner):
    """수평 띠: 좌베벨 LL / 금 / inner 채움 / 금 / 우베벨 DD (원본 y127·y3과 동일 구조)."""
    px[0, y] = L
    px[1, y] = L
    px[2, y] = G
    for x in range(3, 173):
        px[x, y] = inner
    px[173, y] = G
    px[174, y] = D
    px[175, y] = D


def row_gold(px, y):
    """금색 가로선 한 줄 (원본 y126과 동일)."""
    px[0, y] = L
    px[1, y] = L
    for x in range(2, 174):
        px[x, y] = G
    px[174, y] = D
    px[175, y] = D


def row_window_edge(px, y):
    """슬롯창이 열리거나 닫히는 전환 줄 — 측면은 레일(N), 내부는 금색 (원본 y16·y125)."""
    px[0, y] = L
    px[1, y] = L
    px[2, y] = G
    for x in range(3, 6):
        px[x, y] = N
    for x in range(6, 170):
        px[x, y] = G
    for x in range(170, 173):
        px[x, y] = N
    px[173, y] = G
    px[174, y] = D
    px[175, y] = D


def row_rails(px, y):
    """슬롯창 본문 줄 — 양쪽 레일만 그리고 내부는 투명(바닐라 슬롯 노출, 원본 y17~124)."""
    px[0, y] = L
    px[1, y] = L
    px[2, y] = G
    for x in range(3, 6):
        px[x, y] = N
    px[6, y] = G
    for x in range(7, 169):
        px[x, y] = CLEAR
    px[169, y] = G
    for x in range(170, 173):
        px[x, y] = N
    px[173, y] = G
    px[174, y] = D
    px[175, y] = D


def main():
    src = Image.open(SRC).convert("RGBA")
    if src.size != (W, H_OLD):
        raise SystemExit(f"소스 자산이 176x133이 아님: {SRC} {src.size}")

    out = Image.new("RGBA", (W, H_NEW), CLEAR)
    out.paste(src, (0, 0))
    px = out.load()

    # y127: 이음매 상단 하이라이트 (헤더 y3과 같은 역할 — 위에서 빛 받는 면)
    row_fill(px, 127, HI)

    # y128~136: 통짜 어두운 이음매 9px — 원본의 금선/다이아를 지우고 라벨을 삼킨다
    for y in range(128, 137):
        row_fill(px, y, D)

    # 인벤 3행 창 (y138~191)
    row_window_edge(px, 137)
    for y in range(138, 192):
        row_rails(px, y)
    row_window_edge(px, 192)

    # 인벤 3행 ↔ 핫바 사이 4px 홈 (금 - 어둠 2px - 금)
    row_fill(px, 193, D)
    row_fill(px, 194, D)
    row_window_edge(px, 195)

    # 핫바 창 (y196~213)
    for y in range(196, 214):
        row_rails(px, y)

    # y214~221: 원본 하단띠(y125~132, 금선+다이아 장식 포함)를 창 맨아래로 이주
    out.paste(src.crop((0, 125, W, 133)), (0, 214))

    out.save(OUT)
    print(f"저장: {OUT} ({W}x{H_NEW})")
    print("★gui.json의 island_shop height도 222여야 함 (ascent 13 유지)")


if __name__ == "__main__":
    main()
