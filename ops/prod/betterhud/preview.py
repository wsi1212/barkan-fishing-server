#!/usr/bin/env python3
"""BetterHud 대화창을 배포 전에 오프라인으로 그려보는 미리보기.

배포 -> 접속 -> 스샷 왕복이 한 번에 10분씩 걸려서, 좌표를 눈으로 확인하려면 이게 필요하다.
배치 수식은 추측이 아니라 BetterHud 소스에서 그대로 옮겼다.

  LayoutComponentContainer.kt
    move = align==LEFT ? 0 : align==CENTER ? (max - W)/2 : (max - W)
    build() 앞에 offset==CENTER 이면 -max/2 를 붙인다
  HudParser.kt
    max = 레이아웃 안 "이미지" 중 가장 넓은 것의 폭 (텍스트는 세지 않는다)
  LayoutGroup.kt
    align 기본값 = LEFT, offset 기본값 = CENTER

따라서 요소의 왼쪽 끝 = anchor_x + (-max/2) + x + move.
  align: left   -> 왼쪽끝 = x - max/2   ← max 종속. 다른 이미지 크기만 바꿔도 전부 움직인다
  align: center -> 왼쪽끝 = x - W/2     ← x가 그 요소 자신의 중심. max와 무관 (권장)

★화면은 320x240으로 잡는다. 마크는 GUI 배율을 아무리 올려도 가상 화면을 최소
  320x240으로 보정하므로, 여기서 안 잘리면 모든 유저에게 보인다.
★이미지 폭은 160을 넘기지 말 것. 폰트 글리프 아틀라스에 못 들어가면 에러 없이 조용히
  사라진다(실측: 52·110·144는 나오고 217·300은 안 나옴). 넓은 판은 조각내서 붙인다.

사용법:  python3 preview.py [출력.png]
"""
import os, sys, yaml
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, "assets")

SCREEN_W, SCREEN_H = 426, 240   # 16:9에서 보장되는 최소 가상 화면(세로 240 제약이 먼저 걸림)
HOTBAR_H = 22

# 서버 폰트. 대사를 실제로 그려서 양피지 밖으로 넘치는지 잡는다.
# 16px은 인게임 스샷 실측으로 보정한 값. 13px일 때 141px로 나왔는데 실제는 167px이라
# 18% 과소평가였고, 그래서 글자 넘침을 못 잡았다.
FONT_TTF = os.path.expanduser("~/development/barkan-resourcepack/assets/barkan/font/aggro_medium.ttf")
FONT_PX = 16

# 패널 그림에서 실측한 영역. 패널 왼쪽 위를 (0,0)으로 본 좌표.
PARCHMENT = (112, 8, 387, 90)    # 대사가 들어가야 하는 자리 (400판 기준)
PORTRAIT_SLOT = (16, 14, 91, 95)  # 초상화가 들어가야 하는 액자 홈

SAMPLE_TEXT = "바르칸의 물은 정직하단다 — 던진 만큼 돌려주지."
SAMPLE_NAME = "[길잡이] 할아버지"


def load(name):
    return yaml.safe_load(open(os.path.join(HERE, name), encoding="utf-8"))


def main(out_path):
    hud = load("npc-dialogue-hud.yml")["npc_dialogue"]
    layout = load("npc-dialogue-layout.yml")["npc_dialogue_layout"]
    images = load("npc-dialogue-image.yml")

    align = str(layout.get("align", "left")).lower()
    offset = str(layout.get("offset", "center")).lower()
    gui = hud["layouts"][1]["gui"]
    ax, ay = SCREEN_W * gui["x"] / 100.0, SCREEN_H * gui["y"] / 100.0

    sized = {}
    for key, spec in images.items():
        im = Image.open(os.path.join(ASSETS, spec["file"])).convert("RGBA")
        im = im.crop(im.split()[3].getbbox())        # BetterHud는 투명 여백을 잘라낸다
        s = float((spec.get("setting") or {}).get("scale", 1.0))
        w, h = max(1, round(im.width * s)), max(1, round(im.height * s))
        sized[key] = (im.resize((w, h), Image.LANCZOS), w, h)

    used = [e["name"] for e in layout.get("images", {}).values()]
    mx = max((sized[n][1] for n in used if n in sized), default=0)

    def left_edge(x, w):
        base = {"left": 0, "center": -mx / 2, "right": -mx}[offset]
        move = {"left": 0, "center": (mx - w) / 2, "right": mx - w}[align]
        return ax + base + x + move

    canvas = Image.new("RGBA", (SCREEN_W, SCREEN_H), (60, 90, 130, 255))
    d = ImageDraw.Draw(canvas)
    d.rectangle([0, SCREEN_H - HOTBAR_H, SCREEN_W, SCREEN_H], fill=(35, 35, 40, 255))
    d.line([(SCREEN_W // 2, 0), (SCREEN_W // 2, SCREEN_H)], fill=(255, 80, 80, 120))

    print(f"화면 {SCREEN_W}x{SCREEN_H}  앵커 ({ax:.0f},{ay:.0f})  "
          f"align={align} offset={offset}  max={mx}")

    panel_l, panel_t = None, None
    for idx in sorted(layout.get("images", {})):
        e = layout["images"][idx]; name = e["name"]
        if name not in sized:
            print(f"  ! 이미지 정의 없음: {name}"); continue
        im, w, h = sized[name]
        lx, ty = left_edge(e.get("x", 0), w), ay + e.get("y", 0)
        canvas.alpha_composite(im, (round(lx), round(ty)))
        warn = ""
        if lx < 0 or lx + w > SCREEN_W:
            warn = "   ← ★화면 밖!"
        if w > 160:
            warn += "   ← ★폭 160 초과: 렌더 안 될 수 있음"
        if lx < (SCREEN_W-320)/2 or lx + w > (SCREEN_W+320)/2:
            warn += "   (4:3 좁은 창에서는 잘림)"
        if name.startswith("dialogue_panel"):
            panel_l = lx if panel_l is None else min(panel_l, lx)
            panel_t = ty if panel_t is None else min(panel_t, ty)
        print(f"  {name:24s} x {lx:6.0f}~{lx+w:<6.0f} (폭 {w:3d})  y {ty:.0f}~{ty+h:.0f}{warn}")

    parch = None
    if panel_l is not None:
        parch = (panel_l + PARCHMENT[0], panel_t + PARCHMENT[1],
                 panel_l + PARCHMENT[2], panel_t + PARCHMENT[3])
        d.rectangle(list(parch), outline=(0, 220, 0, 200))

    def wrap(text, limit, font):
        out, cur = [], ""
        for ch in text:
            if d.textlength(cur + ch, font=font) > limit and cur:
                out.append(cur); cur = ch
            else:
                cur += ch
        if cur: out.append(cur)
        return out

    for idx in sorted(layout.get("texts", {})):
        t = layout["texts"][idx]
        sample = SAMPLE_TEXT if idx == 1 else SAMPLE_NAME
        fs = max(6, round(FONT_PX * float(t.get("scale", 1.0))))
        font = ImageFont.truetype(FONT_TTF, fs)
        sw = t.get("split-width")
        lines = (wrap(sample, sw, font) if sw else [sample])[: t.get("line", 99)]
        lw = t.get("line-width", 10)
        widest = max((d.textlength(l, font=font) for l in lines), default=0)
        lx = left_edge(t.get("x", 0), sw if sw else widest)
        ty = ay + t.get("y", 0)
        warn = ""
        for i, line in enumerate(lines):
            y = ty + i * lw
            d.text((lx, y), line, font=font, fill=(61, 40, 64, 255))
            if parch and idx == 1:
                if lx < parch[0] or lx + d.textlength(line, font=font) > parch[2]:
                    warn = "   ← ★양피지 좌우로 넘침!"
                elif y < parch[1] or y + FONT_PX > parch[3]:
                    warn = "   ← ★양피지 위아래로 넘침!"
        print(f"  [text{idx}] {len(lines)}줄  x {lx:6.0f}~{lx+widest:<6.0f} "
              f"(가장 긴 줄 {widest:.0f})  y {ty:.0f}~{ty+len(lines)*lw:.0f}{warn}")
    if parch:
        print(f"  (양피지 x {parch[0]:.0f}~{parch[2]:.0f}  y {parch[1]:.0f}~{parch[3]:.0f})")

    canvas.convert("RGB").resize((SCREEN_W * 3, SCREEN_H * 3), Image.NEAREST).save(out_path)
    print(f"\n미리보기 저장: {out_path}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "/tmp/hud-preview.png")
