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
import json
import os
from collections import Counter

from PIL import Image, ImageFilter

RP = os.path.expanduser("~/development/barkan-resourcepack")
OUT_DIR = os.path.join(RP, "assets/minecraft/textures/item/barkan_icon")
MODEL_DIR = os.path.join(RP, "assets/barkan/models/barkan_icon")
ITEM_DIR = os.path.join(RP, "assets/barkan/items/barkan_icon")

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


def ensure_wiring(icon_id, item_type):
    """신규 ImageGen 아이콘에만 model/items 정의를 보완한다.

    기존 정의는 절대 덮어쓰지 않는다. 낚싯대는 손에 드는 각도를 유지하도록
    handheld_rod 부모를 쓰고, 나머지 장비는 generated 평면 모델을 쓴다.
    """
    if not item_type:
        return
    os.makedirs(MODEL_DIR, exist_ok=True)
    os.makedirs(ITEM_DIR, exist_ok=True)
    model_path = os.path.join(MODEL_DIR, f"{icon_id}.json")
    item_path = os.path.join(ITEM_DIR, f"{icon_id}.json")
    if not os.path.exists(model_path):
        parent = "minecraft:item/handheld_rod" if item_type == "낚싯대" else "minecraft:item/generated"
        model = {"parent": parent, "textures": {"layer0": f"minecraft:item/barkan_icon/{icon_id}"}}
        with open(model_path, "w", encoding="utf-8") as f:
            json.dump(model, f, ensure_ascii=False)
    if not os.path.exists(item_path):
        definition = {"model": {"type": "minecraft:model", "model": f"barkan:barkan_icon/{icon_id}"}}
        with open(item_path, "w", encoding="utf-8") as f:
            json.dump(definition, f, ensure_ascii=False)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("icon_id")
    ap.add_argument("--size", type=int, default=64)
    ap.add_argument("--pixel-grid", type=int,
                    help="원화를 이 논리 픽셀 격자로 축소·32색 양자화한 뒤 nearest로 확대")
    ap.add_argument("--type", choices=["낚싯대", "릴", "줄", "바늘", "미끼", "찌", "작살"],
                    help="신규 아이콘의 model/items 정의를 만들 장비 유형")
    ap.add_argument("--no-key", action="store_true",
                    help="원화에 이미 알파가 있으면 크로마키를 건너뛴다")
    a = ap.parse_args()

    src = Image.open(os.path.expanduser(a.src)).convert("RGBA")
    if a.no_key:
        # ★이미 투명 배경인 원화는 크로마키를 돌리면 안 된다. 모서리가 투명이라 배경색이
        #   검정으로 추정되고, 그림의 어두운 부분이 통째로 지워진다(2026-08-11).
        print(f"소스 {src.size} / 크로마키 생략(알파 사용)")
        keyed = src
    else:
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
    if a.pixel_grid:
        if a.pixel_grid > a.size or a.size % a.pixel_grid:
            ap.error("--pixel-grid는 --size의 약수여야 합니다")
        # ImageGen 원화의 연속 색/반투명 경계를 실제 인벤 픽셀 문법으로 정리한다.
        # 등급별 원본 크기는 유지하되(B 32→128, A 64→256, S 128→512),
        # 논리 격자의 한 픽셀은 nearest 확대 후에도 정확히 같은 색으로 남는다.
        grid = small.resize((a.pixel_grid, a.pixel_grid), Image.Resampling.LANCZOS)
        alpha = grid.getchannel("A").point(lambda v: 255 if v >= 128 else 0)
        rgb = grid.convert("RGB")
        rp = rgb.load()
        for y in range(a.pixel_grid):
            for x in range(a.pixel_grid):
                r0, g0, b0 = rp[x, y]
                # 순수 검정 외곽선은 슬롯에서 뭉개지므로 청흑색으로 밀어 올린다.
                if r0 < 8 and g0 < 8 and b0 < 8:
                    rp[x, y] = (12, 18, 27)
        rgb = rgb.quantize(colors=32, method=Image.Quantize.MEDIANCUT).convert("RGB")
        grid = Image.merge("RGBA", (*rgb.split(), alpha))
        small = grid.resize((a.size, a.size), Image.Resampling.NEAREST)

    out = os.path.join(OUT_DIR, f"{a.icon_id}.png")
    if os.path.exists(out):
        print(f"기존 {a.icon_id} {Image.open(out).size} 교체")
    small.save(out)
    ensure_wiring(a.icon_id, a.type)
    print(f"저장: {out} ({a.size}x{a.size})")


if __name__ == "__main__":
    main()
