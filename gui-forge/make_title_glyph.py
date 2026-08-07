#!/usr/bin/env python3
"""GUI 제목을 **아트로 렌더**해 글리프로 등록한다 — 구워넣은 것처럼 보이면서 화면별로 다르게.

## 왜
배경에 제목을 구우면 그 화면 전용이 된다. 공용 6행 판은 54칸 GUI 44개가 공유하므로
구울 수 없다. 그렇다고 게임 폰트 흰 글씨를 얹으면 배경 아트와 따로 놀아 싸구려로 보인다.
→ 제목을 **금박 글자 이미지**로 렌더해 글리프로 만든다. 화면마다 다른 이미지를 쓰면서도
  프레임과 같은 재질로 읽힌다.

## 렌더
리소스팩의 어그로체(aggro_bold)로 4배 크기에 그린 뒤,
 · 어두운 외곽선(배경 나무결 위에서 글자를 띄운다)
 · 세로 금색 그라데이션(위 밝은 금 → 아래 구리)
 · 1px 아래쪽 그림자(음각처럼)
을 얹는다. 폭은 렌더 결과에서 실측하므로 **가운데 정렬이 정확**하다
(추정 폭으로 맞추던 GuiTitle.textWidth 는 한글/영문 혼용에서 어긋났다).

산출: <RP>/assets/barkan/textures/gui/title_<id>.png + gui.json provider
      src/titles/_glyphs.json  (자바가 id로 글리프 문자열을 가져다 쓴다)
"""
import json
import os

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "src", "titles")
RP = os.path.expanduser("~/development/barkan-resourcepack")
TEXDIR = os.path.join(RP, "assets/barkan/textures/gui")
FONT_JSON = os.path.join(RP, "assets/barkan/font/gui.json")
FONT_TTF = os.path.join(RP, "assets/barkan/font/aggro_bold.ttf")

SCALE = 4
TITLE_H_GUI = 16          # 글리프 높이(GUI px) — 제목 줄 한 칸
ASCENT = 13               # 글리프 top = 6 (바닐라 제목 줄 위치)
CODE0 = 0xE700
PREFIX = "title_"

# 위(밝은 금) → 아래(구리). 프레임 금속과 같은 계열.
GRAD_TOP = (255, 226, 150)
GRAD_BOT = (176, 116, 52)
OUTLINE = (18, 12, 8, 255)
SHADOW = (0, 0, 0, 120)

TITLES = {
    "menu": "MENU",
}


def render(text):
    f = ImageFont.truetype(FONT_TTF, TITLE_H_GUI * SCALE - 12)
    tmp = Image.new("L", (2000, TITLE_H_GUI * SCALE * 2), 0)
    d = ImageDraw.Draw(tmp)
    d.text((40, 8), text, font=f, fill=255)
    bb = tmp.getbbox()
    if not bb:
        raise SystemExit("빈 텍스트")
    mask = tmp.crop(bb)
    w, h = mask.size

    pad = 3 * SCALE // 2                      # 외곽선 여유
    W, H = w + pad * 2, TITLE_H_GUI * SCALE
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ox, oy = pad, (H - h) // 2

    # ① 어두운 외곽선 — 마스크를 8방향으로 밀어 찍는다
    ol = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    t = max(1, SCALE // 2)
    solid = Image.new("RGBA", (w, h), OUTLINE)
    for dx in range(-t, t + 1):
        for dy in range(-t, t + 1):
            if dx * dx + dy * dy > t * t:
                continue
            ol.paste(solid, (ox + dx, oy + dy), mask)
    img.alpha_composite(ol)

    # ② 금색 세로 그라데이션 본체
    grad = Image.new("RGBA", (w, h))
    gp = grad.load()
    for y in range(h):
        k = y / max(1, h - 1)
        gp_row = tuple(round(GRAD_TOP[i] + (GRAD_BOT[i] - GRAD_TOP[i]) * k) for i in range(3))
        for x in range(w):
            gp[x, y] = gp_row + (255,)
    img.paste(grad, (ox, oy), mask)

    # ③ 아래쪽 그림자 한 줄 — 음각 느낌
    sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sh.paste(Image.new("RGBA", (w, h), SHADOW), (ox, oy + t), mask)
    base = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    base.alpha_composite(sh)
    base.alpha_composite(img)
    return base


def main():
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(TEXDIR, exist_ok=True)
    provs, glyphs, code = [], {}, CODE0
    for tid, text in TITLES.items():
        im = render(text)
        fn = f"{PREFIX}{tid}"
        im.save(os.path.join(TEXDIR, fn + ".png"))
        ch = chr(code)
        provs.append({"type": "bitmap", "file": f"barkan:gui/{fn}.png",
                      "ascent": ASCENT, "height": TITLE_H_GUI, "chars": [ch]})
        # 글리프 폭(GUI px) = 이미지 폭 / SCALE. advance 는 +1.
        w_gui = round(im.width / SCALE)
        glyphs[tid] = {"text": text, "width": w_gui, "glyph": f"\\u{ord(ch):04x}"}
        print(f"  {tid:12} '{text}'  {im.size} → 폭 {w_gui}gui  U+{ord(ch):04X}")
        code += 1

    d = json.load(open(FONT_JSON, encoding="utf-8"))
    kept = [p for p in d["providers"] if PREFIX not in str(p.get("file", ""))]
    d["providers"] = kept + provs
    json.dump(d, open(FONT_JSON, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    json.dump(glyphs, open(os.path.join(OUT, "_glyphs.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print(f"제목 글리프 {len(provs)}개 (기존 provider {len(kept)}개 보존)")


if __name__ == "__main__":
    main()
