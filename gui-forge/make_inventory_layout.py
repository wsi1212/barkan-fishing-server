#!/usr/bin/env python3
"""바닐라 생존 인벤토리(E 키) 뼈대판 — `gui/container/inventory.png` 를 갈아 끼우기 위한 것.

## 지금까지의 화면들과 다른 점
우리 GUI 는 지금까지 **상자 창 제목에 비트맵 글리프**를 심는 방식이었다. 그건 우리가
띄우는 창에만 통한다. 플레이어 인벤토리는 클라이언트가 직접 그리므로 **바닐라 텍스처를
덮어쓰는 수밖에** 없다.

## 좌표는 바닐라가 정한다 — 옮길 수 없다
칸 위치는 클라이언트 코드에 박혀 있어서 그림으로 못 바꾼다. 아래 좌표는 1.21.10
클라이언트 jar 의 실제 텍스처에서 픽셀 단위로 읽어낸 것이다(추측 아님).

  방어구 4   (8, 8·26·44·62)      · 보조손 1  (77, 62)
  조합 2x2   (98·116, 18·36)      · 결과   1  (154, 28)
  가방 3x9   (8+18c, 84·102·120)  · 단축바 9  (8+18c, 142)
  플레이어 모델 뷰포트  x 26~75, y 8~78   (3D 모델이 이 위에 그려진다)
  레시피책 버튼          x 104~124, y 61~79 (바닐라 스프라이트가 이 위에 뜬다)

## 해상도
바닐라는 256x256 캔버스에 176x166 만 쓴다. 텍스처를 **4배(1024x1024)** 로 올려도
클라이언트가 같은 비율로 샘플링해서 그대로 그려진다 — 우리 글리프 판과 같은 4배다.
그래서 이 뼈대판도 1024x1024 이고, 창은 왼쪽 위 704x664 다.

산출: src/inventory/_template.png
"""
import os

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
RP = os.path.expanduser("~/development/barkan-resourcepack")
FONT_TTF = os.path.join(RP, "assets/barkan/font/aggro_bold.ttf")

S = 4                      # 배율
CANVAS = 256 * S           # 1024 — 바닐라 캔버스와 같은 비율
WIN_W, WIN_H = 176 * S, 166 * S

BG = (30, 30, 36, 255)
OUTSIDE = (18, 18, 21, 255)
LINE = (208, 208, 216, 255)
SOCKET = (72, 72, 80, 255)
SOCKET_EDGE = (168, 168, 178, 255)
NOTE = (150, 150, 160, 255)
WARN = (255, 150, 130, 255)

# (x, y) — 바닐라 텍스처에서 실측한 칸 왼쪽 위 (16x16 안쪽 기준)
ARMOR = [(8, 8), (8, 26), (8, 44), (8, 62)]
OFFHAND = [(77, 62)]
CRAFT = [(98, 18), (116, 18), (98, 36), (116, 36)]
RESULT = [(154, 28)]
BAG = [(8 + 18 * c, y) for y in (84, 102, 120) for c in range(9)]
HOTBAR = [(8 + 18 * c, 142) for c in range(9)]
VIEWPORT = (26, 8, 75, 78)          # 3D 플레이어 모델이 그려지는 사각형
RECIPE_BTN = (104, 61, 124, 79)     # 레시피책 토글 버튼이 뜨는 자리


def font(px):
    try:
        return ImageFont.truetype(FONT_TTF, px)
    except Exception:
        return ImageFont.load_default()


def socket(d, x, y, label=None, fs=None):
    """칸 하나. 바닐라 칸은 안쪽 16px + 테두리 1px = 18px 이다."""
    x0, y0 = (x - 1) * S, (y - 1) * S
    d.rounded_rectangle([x0, y0, x0 + 18 * S - 1, y0 + 18 * S - 1], radius=8,
                        fill=SOCKET, outline=SOCKET_EDGE, width=3)
    if label:
        d.text((x0 + 6, y0 + 6), label, font=fs, fill=(230, 230, 240, 255))


def main():
    im = Image.new("RGBA", (CANVAS, CANVAS), OUTSIDE)
    d = ImageDraw.Draw(im, "RGBA")
    fs, fm = font(15), font(20)

    d.rectangle([0, 0, WIN_W - 1, WIN_H - 1], fill=BG, outline=LINE, width=4)

    for x, y in ARMOR:
        socket(d, x, y, "방어", fs)
    for x, y in OFFHAND:
        socket(d, x, y, "보조", fs)
    for x, y in CRAFT:
        socket(d, x, y)
    for x, y in RESULT:
        socket(d, x, y, "결과", fs)
    for x, y in BAG + HOTBAR:
        socket(d, x, y)

    vx0, vy0, vx1, vy1 = [v * S for v in VIEWPORT]
    d.rectangle([vx0, vy0, vx1 + S - 1, vy1 + S - 1], outline=(120, 200, 255, 255), width=4)
    d.text((vx0 + 8, vy0 + 8), "플레이어 모델이\n여기 그려진다\n(뒤에 깔 배경만)",
           font=fs, fill=(150, 210, 255, 255))

    rx0, ry0, rx1, ry1 = [v * S for v in RECIPE_BTN]
    d.rectangle([rx0, ry0, rx1 + S - 1, ry1 + S - 1], outline=WARN, width=4)
    d.text((rx0, ry0 - 26), "레시피책 버튼 자리", font=fs, fill=WARN)

    d.text((8, WIN_H + 12), f"창 = 왼쪽 위 {WIN_W} x {WIN_H} · 캔버스 {CANVAS} x {CANVAS}",
           font=fm, fill=NOTE)
    d.text((8, WIN_H + 42), "이 바깥 어두운 영역은 게임이 안 쓴다. 그냥 두거나 채워도 무방",
           font=fs, fill=NOTE)

    out = os.path.join(HERE, "src", "inventory")
    os.makedirs(out, exist_ok=True)
    im.save(os.path.join(out, "_template.png"))
    print(f"  inventory {CANVAS}x{CANVAS} · 창 {WIN_W}x{WIN_H} · 칸 "
          f"{len(ARMOR + OFFHAND + CRAFT + RESULT + BAG + HOTBAR)}개")


if __name__ == "__main__":
    main()
