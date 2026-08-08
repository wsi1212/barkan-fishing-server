#!/usr/bin/env python3
"""BetterHud 레이아웃을 배포 전에 오프라인으로 그려보는 미리보기.

배포 -> 접속 -> 스샷 왕복이 한 번에 10분씩 걸려서, 좌표를 눈으로 확인하려면
이게 필요하다. 배치 수식은 추측이 아니라 BetterHud 소스에서 그대로 옮겼다.

  LayoutComponentContainer.kt
    move = align==LEFT ? 0 : align==CENTER ? (max - W)/2 : (max - W)
    build() 앞에 offset==CENTER 이면 -max/2 를 붙인다
  HudParser.kt
    max = 레이아웃 안 "이미지" 중 가장 넓은 것의 폭 (텍스트는 세지 않는다)
  LayoutGroup.kt
    align 기본값 = LEFT, offset 기본값 = CENTER

따라서 요소의 왼쪽 끝 = anchor_x + (-max/2) + x + move.
  align: left   -> 왼쪽끝 = x - max/2      ← max에 종속. 다른 이미지 크기를 바꾸면 같이 움직인다
  align: center -> 왼쪽끝 = x - W/2        ← x가 그 요소 자신의 중심. max와 무관하다 (권장)

★화면 폭은 320으로 잡는다. 마크는 GUI 배율을 아무리 올려도 가상 화면을 최소
  320x240으로 보정하므로, 320에서 안 잘리면 모든 유저에게 보인다.

사용법:
  python3 preview.py [출력.png]
"""
import os, sys, yaml
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, "assets")

SCREEN_W, SCREEN_H = 320, 240   # 마크가 보장하는 최소 가상 화면
HOTBAR_H = 22                   # 참고선용


def load(name):
    return yaml.safe_load(open(os.path.join(HERE, name), encoding="utf-8"))


def main(out_path):
    hud = load("npc-dialogue-hud.yml")["npc_dialogue"]
    layout = load("npc-dialogue-layout.yml")["npc_dialogue_layout"]
    images = load("npc-dialogue-image.yml")

    align = str(layout.get("align", "left")).lower()
    offset = str(layout.get("offset", "center")).lower()

    gui = hud["layouts"][1]["gui"]
    anchor_x = SCREEN_W * gui["x"] / 100.0
    anchor_y = SCREEN_H * gui["y"] / 100.0

    # 이미지 실측 크기 (scale 반영)
    sized = {}
    for key, spec in images.items():
        path = os.path.join(ASSETS, spec["file"])
        im = Image.open(path).convert("RGBA")
        im = im.crop(im.split()[3].getbbox())          # BetterHud는 투명 여백을 잘라낸다
        s = float((spec.get("setting") or {}).get("scale", 1.0))
        w, h = max(1, round(im.width * s)), max(1, round(im.height * s))
        sized[key] = (im.resize((w, h), Image.LANCZOS), w, h)

    used = [e["name"] for e in layout.get("images", {}).values()]
    mx = max((sized[n][1] for n in used if n in sized), default=0)

    def left_edge(x, w):
        base = {"left": 0, "center": -mx / 2, "right": -mx}[offset]
        move = {"left": 0, "center": (mx - w) / 2, "right": mx - w}[align]
        return anchor_x + base + x + move

    canvas = Image.new("RGBA", (SCREEN_W, SCREEN_H), (60, 90, 130, 255))
    d = ImageDraw.Draw(canvas)
    d.rectangle([0, SCREEN_H - HOTBAR_H, SCREEN_W, SCREEN_H], fill=(35, 35, 40, 255))
    d.line([(SCREEN_W // 2, 0), (SCREEN_W // 2, SCREEN_H)], fill=(255, 80, 80, 120))

    print(f"화면 {SCREEN_W}x{SCREEN_H}  앵커 ({anchor_x:.0f},{anchor_y:.0f})  "
          f"align={align} offset={offset}  max={mx}")
    for idx in sorted(layout.get("images", {})):
        e = layout["images"][idx]
        name = e["name"]
        if name not in sized:
            print(f"  ! 이미지 정의 없음: {name}"); continue
        im, w, h = sized[name]
        lx = left_edge(e.get("x", 0), w)
        ty = anchor_y + e.get("y", 0)        # y는 요소의 아래쪽 기준(음수가 위) → 위쪽 = y - h... 아래 주석 참고
        canvas.alpha_composite(im, (round(lx), round(ty)))
        flag = "" if 0 <= lx and lx + w <= SCREEN_W else "   ← ★화면 밖!"
        print(f"  {name:24s} x {lx:6.0f}~{lx+w:<6.0f} (폭 {w:3d})  y {ty:.0f}{flag}")

    for idx in sorted(layout.get("texts", {})):
        t = layout["texts"][idx]
        sw = t.get("split-width", 100)
        lx = left_edge(t.get("x", 0), sw)
        ty = anchor_y + t.get("y", 0)
        lines = t.get("line", 1); lw = t.get("line-width", 10)
        d.rectangle([lx, ty, lx + sw, ty + lines * lw], outline=(255, 0, 0, 200))
        print(f"  [text{idx}]{'':17s} x {lx:6.0f}~{lx+sw:<6.0f} (폭 {sw})  y {ty:.0f}~{ty+lines*lw:.0f}")

    canvas.convert("RGB").resize((SCREEN_W * 3, SCREEN_H * 3), Image.NEAREST).save(out_path)
    print(f"\n미리보기 저장: {out_path}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "/tmp/hud-preview.png")
