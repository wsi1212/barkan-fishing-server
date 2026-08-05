#!/usr/bin/env python3
"""스킬 노드 아이콘 77종에 균일한 여백을 만든다 — 원본 재작업.

★2026-08-04 발견: 154개 파생본(_locked/_maxed)뿐 아니라 원본 77개 자체가 대부분
  상단 여백 0px로 그려져 있었다(측정: skill_ 154개 중 130개가 캔버스 y=0에 알파가
  닿아 있음). 짙은 남색 트리 배경 위에서 대비가 세져 "위가 살짝 잘린 것처럼" 보였다.
  손으로 그린 자산이라 확인 없이 건드리지 않고 물어봤고, 전체 재작업으로 확정됐다.

방법: 알파 bbox를 구해 콘텐츠를 안쪽으로 축소(프리멀티플 LANCZOS) → 64x64 캔버스
정중앙에 재배치. 목표 여백은 기존 하단 여백(6~8px) 수준으로 통일해 지금까지의
"보기엔 괜찮던" 크기감을 유지한다. 원본은 백업 후 덮어쓴다.

실행 순서: 이 스크립트 → make_skill_states.py(파생본 재생성) → register_icons.py(재등록)
"""
import os

from PIL import Image

RP = os.path.expanduser("~/development/barkan-resourcepack")
TEX = os.path.join(RP, "assets/minecraft/textures/item/barkan_icon")

CANVAS = 64
MARGIN = 6                       # 목표 여백 — 기존 하단 여백(6~8px) 수준에 맞춘다
TARGET = CANVAS - 2 * MARGIN     # 콘텐츠가 들어갈 정사각 영역


def premul_resize(im, size):
    pm = im.copy()
    q = pm.load()
    for y in range(im.height):
        for x in range(im.width):
            r, g, b, a = q[x, y]
            f = a / 255
            q[x, y] = (int(r * f), int(g * f), int(b * f), a)
    sm = pm.resize(size, Image.LANCZOS)
    t = sm.load()
    for y in range(sm.height):
        for x in range(sm.width):
            r, g, b, a = t[x, y]
            t[x, y] = (0, 0, 0, 0) if a == 0 else (min(255, r * 255 // a),
                                                   min(255, g * 255 // a),
                                                   min(255, b * 255 // a), a)
    return sm


def pad_one(path):
    im = Image.open(path).convert("RGBA")
    bbox = im.getbbox()
    if not bbox:
        return None
    content = im.crop(bbox)
    w, h = content.size
    side = max(w, h)
    scale = TARGET / side
    nw, nh = round(w * scale), round(h * scale)
    resized = premul_resize(content, (max(1, nw), max(1, nh)))
    out = Image.new("RGBA", (CANVAS, CANVAS), (0, 0, 0, 0))
    out.alpha_composite(resized, ((CANVAS - nw) // 2, (CANVAS - nh) // 2))
    return out


def main():
    base = sorted(f for f in os.listdir(TEX)
                  if f.startswith("skill_") and f.endswith(".png")
                  and not f.endswith(("_locked.png", "_maxed.png"))
                  and not f.startswith("skill_hub_"))
    n = 0
    for f in base:
        p = os.path.join(TEX, f)
        out = pad_one(p)
        if out is None:
            print(f"  스킵(빈 알파): {f}")
            continue
        out.save(p)
        n += 1
    print(f"원본 {n}개 재작업 완료 — 목표 여백 {MARGIN}px, 콘텐츠 {TARGET}px")


if __name__ == "__main__":
    main()
