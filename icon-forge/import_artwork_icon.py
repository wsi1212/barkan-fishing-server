#!/usr/bin/env python3
"""단색 배경(크로마키) 컨셉 아트 → 인벤 아이콘 PNG 변환.

사용법:
  python3 import_artwork_icon.py <소스이미지> <아이콘id> [--size 64] [--keep-bg-sample]

예)
  python3 import_artwork_icon.py ~/Desktop/wheat.png skill_hub_farming

산출: barkan-resourcepack/assets/minecraft/textures/item/barkan_icon/<아이콘id>.png
      (모델·items JSON이 이미 있으면 그대로 재사용 — 텍스처만 교체)

크로마키 처리:
  - 배경색은 네 모서리 픽셀의 최빈값으로 자동 추정 (마젠타 등 어떤 단색이든)
  - 코어(거리 <= CORE)는 완전 투명, 프린지(<= EDGE)는 부분 투명 + 배경색 성분 제거
    (그냥 임계값만 쓰면 축소할 때 마젠타 테두리가 남는다)
  - 알파 프리멀티플 상태로 축소 → 반투명 경계에 배경색 헤일로가 안 낀다
"""
import argparse
import os
from collections import Counter

from PIL import Image, ImageFilter

RP = os.path.expanduser("~/development/barkan-resourcepack")
OUT_DIR = os.path.join(RP, "assets/minecraft/textures/item/barkan_icon")

CORE = 60      # 이 거리 이내 = 순수 배경 → 알파 0
EDGE = 150     # 이 거리 이내 = 프린지 → 부분 알파 + 색 보정


def guess_key(im):
    """네 모서리에서 배경색 추정."""
    w, h = im.size
    pts = [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1),
           (w // 2, 0), (w // 2, h - 1), (0, h // 2), (w - 1, h // 2)]
    return Counter(im.getpixel(p)[:3] for p in pts).most_common(1)[0][0]


def dist(c, k):
    return sum((c[i] - k[i]) ** 2 for i in range(3)) ** 0.5


def key_out(im, k):
    """크로마키 → RGBA. 프린지는 배경 성분을 빼서 색번짐(마젠타 테두리)을 없앤다."""
    im = im.convert("RGBA")
    px = im.load()
    w, h = im.size
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            d = dist((r, g, b), k)
            if d <= CORE:
                px[x, y] = (0, 0, 0, 0)
            elif d <= EDGE:
                t = (d - CORE) / (EDGE - CORE)          # 0=배경 → 1=전경
                # 관측색 = t*전경 + (1-t)*배경  →  전경 = (관측 - (1-t)*배경) / t
                fg = tuple(max(0, min(255, int((c - (1 - t) * kc) / t)))
                           for c, kc in zip((r, g, b), k))
                px[x, y] = fg + (int(255 * t),)
    return im


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("icon_id")
    ap.add_argument("--size", type=int, default=64)
    a = ap.parse_args()

    src = Image.open(os.path.expanduser(a.src)).convert("RGBA")
    k = guess_key(src)
    print(f"소스 {src.size} / 추정 배경색 #{k[0]:02x}{k[1]:02x}{k[2]:02x}")

    keyed = key_out(src, k)
    # 스필 제거: 프린지 보정만으로는 반투명 경계에 배경색 성분이 조금 남는다.
    # 고해상도 단계에서 알파를 2px 침식하면 스필 픽셀이 통째로 날아간다
    # (1254px 기준 0.16%라 실루엣 변화는 안 보인다).
    r_, g_, b_, a_ = keyed.split()
    keyed = Image.merge("RGBA", (r_, g_, b_, a_.filter(ImageFilter.MinFilter(5))))
    bbox = keyed.getbbox()
    if bbox:
        keyed = keyed.crop(bbox)                        # 투명 여백 제거 → 아이콘이 칸을 꽉 채움
        print(f"내용 bbox {bbox} → {keyed.size}")

    # 정사각 캔버스에 중앙 배치 (비율 유지)
    side = max(keyed.size)
    sq = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    sq.alpha_composite(keyed, ((side - keyed.width) // 2, (side - keyed.height) // 2))

    # 프리멀티플 상태로 축소 (경계 헤일로 방지)
    r, g, b, al = sq.split()
    pm = Image.merge("RGBA", (
        Image.eval(Image.merge("L", (r,)), lambda v: v),  # 아래에서 곱셈 처리
        g, b, al))
    pmp = pm.load()
    for y in range(side):
        for x in range(side):
            rr, gg, bb, aa = pmp[x, y]
            f = aa / 255
            pmp[x, y] = (int(rr * f), int(gg * f), int(bb * f), aa)
    small = pm.resize((a.size, a.size), Image.LANCZOS)
    sp = small.load()
    for y in range(a.size):                             # 언프리멀티플
        for x in range(a.size):
            rr, gg, bb, aa = sp[x, y]
            if aa == 0:
                sp[x, y] = (0, 0, 0, 0)
            else:
                f = 255 / aa
                sp[x, y] = (min(255, int(rr * f)), min(255, int(gg * f)),
                            min(255, int(bb * f)), aa)
    small = small.filter(ImageFilter.UnsharpMask(radius=1, percent=70, threshold=2))

    out = os.path.join(OUT_DIR, f"{a.icon_id}.png")
    if os.path.exists(out):
        print(f"기존 {a.icon_id} {Image.open(out).size} 교체")
    small.save(out)
    print(f"저장: {out} ({a.size}x{a.size})")


if __name__ == "__main__":
    main()
