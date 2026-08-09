#!/usr/bin/env python3
"""NPC 대화창 뼈대판 — BetterHud 하단 오버레이라 상자 창과 규칙이 다르다.

## 상자 창과 다른 점
상자 창 배경은 제목에 심는 글리프라 176 GUI px 안에서 논다. 대화창은 **BetterHud 가
화면에 직접 얹는 이미지**다. 그래서:

  · 최종 크기가 곧 화면 픽셀이다. 440x80 으로 그리면 화면에 440x80 으로 뜬다.
  · 판은 **110px 짜리 네 조각**으로 잘라 쓴다. 글리프 아틀라스가 한 조각 160px 까지라,
    가장 큰 단계(1.40배)에서 110x1.4=154 로 아슬아슬하게 들어간다. 440 이 상한이다.
  · 초상화·이름표·대사는 판 위에 따로 얹힌다. 판에는 **그 자리만 파 두고 내용은 비운다.**

## 좌표 (판 왼쪽 위 = 0,0)
ops/prod/betterhud/gen_hud_sizes.py 의 DIALOGUE 에서 그대로 가져온다 — 거기가 권위다.
이 파일은 그 숫자를 그림으로 보여줄 뿐이다.

산출: src/dialogue/_template.png (4배 확대본 — 발주는 여기에 덧칠하고 우리가 줄인다)
"""
import os

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
RP = os.path.expanduser("~/development/barkan-resourcepack")
FONT_TTF = os.path.join(RP, "assets/barkan/font/aggro_bold.ttf")

PANEL_W, PANEL_H = 440, 80
SLICE_W = 110
Z = 4                                   # 뼈대판만 4배로 크게 — 최종 납품은 440x80 으로 줄인다

# gen_hud_sizes.py DIALOGUE 와 같은 값
PORTRAIT = (35, 10, 128 * 0.40, 154 * 0.40)     # x, y, w, h
NAMEPLATE = (9, 62, 110 * 0.8, 32 * 0.8)
LINE = (122, 10, 230, 3 * 15)                    # x, y, 최대폭, 3줄 높이
NAME = (26, 68)

BG = (30, 30, 36, 255)
PLATE = (52, 54, 62, 255)
EDGE = (188, 190, 200, 255)
CUT = (255, 150, 130, 210)
INK = (235, 236, 244, 255)
DIM = (168, 170, 180, 255)


def font(px):
    try:
        return ImageFont.truetype(FONT_TTF, px)
    except Exception:
        return ImageFont.load_default()


def region(d, box, color, label, fs, dash=False):
    x, y, w, h = [v * Z for v in box]
    d.rectangle([x, y, x + w - 1, y + h - 1], outline=color, width=3)
    d.text((x + 6, y + 6), label, font=fs, fill=color)


def main():
    W, H = PANEL_W * Z, PANEL_H * Z
    im = Image.new("RGBA", (W, H + 60), BG)
    d = ImageDraw.Draw(im, "RGBA")
    fs, fm = font(18), font(22)

    d.rectangle([0, 0, W - 1, H - 1], fill=PLATE, outline=EDGE, width=4)

    # 조각 경계 — 여기서 잘린다. 경계에 딱 걸치는 장식은 티가 난다.
    for i in range(1, 4):
        x = SLICE_W * i * Z
        for y in range(0, H, 24):
            d.line([x, y, x, y + 12], fill=CUT, width=3)
    d.text((SLICE_W * Z + 8, H - 30), "↑ 110px 마다 잘린다 (조각 4장)", font=fs, fill=CUT)

    region(d, PORTRAIT, (120, 200, 255, 255), "초상화가 얹힌다", fs)
    region(d, NAMEPLATE, (255, 210, 120, 255), "이름표가 얹힌다 (판 아래로 8px 삐져나옴)", fs)
    region(d, LINE, (140, 235, 160, 255), "대사 3줄", fs)
    d.ellipse([NAME[0] * Z - 5, NAME[1] * Z - 5, NAME[0] * Z + 5, NAME[1] * Z + 5],
              fill=(255, 210, 120, 255))

    d.text((8, H + 8), f"최종 {PANEL_W} x {PANEL_H} (이 판은 {Z}배 확대본)", font=fm, fill=INK)
    d.text((8, H + 34), "초상화·이름표·글자는 코드가 얹는다. 자리만 파고 내용은 비울 것",
           font=fs, fill=DIM)

    out = os.path.join(HERE, "src", "dialogue")
    os.makedirs(out, exist_ok=True)
    im.save(os.path.join(out, "_template.png"))
    print(f"  dialogue {W}x{H + 60} (최종 {PANEL_W}x{PANEL_H}) · 조각 {PANEL_W // SLICE_W}장")


if __name__ == "__main__":
    main()
