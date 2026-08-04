#!/usr/bin/env python3
"""스킬 노드 아이콘의 **상태 변형** 생성 — 잠금 / 최대랭크.

기존 `skill_*.png` 68종은 이미 링 + 심볼이 함께 그려져 있다(링 색이 이미 등급을 나타냄:
주황=근원 / 금색=핵심 / 은색=일반). 그래서 새 소켓 아트를 덧씌우지 않고, **있는 걸 재료로**
상태 변형만 코드로 만든다.

  · 잠금   `<id>_locked`  — 탈채도 + 감광 + 살짝 대비 축소. "아직 못 쓰는 것"이 즉시 읽힌다.
  · 해금   원본 그대로 재사용 (새 파일 0)
  · 최대   `<id>_maxed`   — 밝기·채도 상승 + 시안 림라이트. ★금색으로 하면 안 된다 —
           금색 링은 이미 '핵심 특성'을 뜻하므로 의미가 충돌한다.

★배경에 소켓을 굽지 않는 이유는 build_skilltree_bg.py 주석 참조. 노드 상태는 경우의 수가
  노드수 × 랭크라 배경으로는 표현 불가능하고, 아이템이라야 조합 폭발을 피한다.
"""
import os
import sys

from PIL import Image, ImageEnhance, ImageFilter

RP = os.path.expanduser("~/development/barkan-resourcepack")
TEX = os.path.join(RP, "assets/minecraft/textures/item/barkan_icon")
ITEMS = os.path.join(RP, "assets/barkan/items/barkan_icon")

RIM = (120, 235, 255)          # 최대랭크 림라이트 색 (시안 = 각성 계열)


def locked(im):
    """탈채도 + 감광. 알파는 그대로 둔다(실루엣 유지)."""
    r, g, b, a = im.split()
    gray = Image.merge("RGB", (r, g, b)).convert("L")
    gray = ImageEnhance.Contrast(gray).enhance(0.85)
    # 0.46은 어두운 벽면(패널) 위에서 실루엣이 아예 안 보였다 → 0.64
    gray = ImageEnhance.Brightness(gray).enhance(0.64)
    # 완전 무채색은 죽어 보인다 → 아주 살짝 청색을 남겨 UI 톤과 붙인다
    px = gray.load()
    out = Image.new("RGBA", im.size)
    o = out.load()
    ap = a.load()
    for y in range(im.height):
        for x in range(im.width):
            v = px[x, y]
            o[x, y] = (int(v * 0.92), int(v * 0.97), min(255, int(v * 1.12)), ap[x, y])
    return out


def maxed(im):
    """밝기·채도 상승 + 실루엣 바깥 시안 림라이트."""
    r, g, b, a = im.split()
    body = Image.merge("RGB", (r, g, b))
    # 본체를 세게 올리면 원반 전체가 흐옇게 떠서 안개처럼 보였다 → 살짝만
    body = ImageEnhance.Color(body).enhance(1.14)
    body = ImageEnhance.Brightness(body).enhance(1.05)
    out = Image.merge("RGBA", (*body.split(), a))

    # 림: 알파를 팽창시킨 뒤 원본 알파를 빼면 바깥 테두리만 남는다
    grown = a.filter(ImageFilter.MaxFilter(5))
    ap, gp = a.load(), grown.load()
    rim = Image.new("RGBA", im.size)
    rp = rim.load()
    for y in range(im.height):
        for x in range(im.width):
            edge = gp[x, y] - ap[x, y]
            if edge > 12:
                rp[x, y] = (*RIM, min(255, int(edge * 1.0)))
    # ★블러를 걸면 16px로 줄었을 때 후광이 뭉개져 '안개'가 된다. 팽창 5 + 블러 없음이
    #   실제 게임 크기에서 시안 후광으로 또렷하게 읽힌다(3안 비교로 확정).
    rim.alpha_composite(out)
    return rim


def write_item_json(icon_id):
    """setItemModel(barkan:barkan_icon/<id>) 가 찾는 정의 파일 — 기존 형식 그대로."""
    p = os.path.join(ITEMS, icon_id + ".json")
    with open(p, "w", encoding="utf-8") as f:
        f.write('{"parent":"minecraft:item/generated","textures":'
                '{"layer0":"minecraft:item/barkan_icon/%s"}}' % icon_id)


def main():
    if not os.path.isdir(TEX):
        sys.exit(f"텍스처 폴더 없음: {TEX}")
    os.makedirs(ITEMS, exist_ok=True)
    base = sorted(f[:-4] for f in os.listdir(TEX)
                  if f.startswith("skill_") and f.endswith(".png")
                  and not f.endswith(("_locked.png", "_maxed.png")))
    made = 0
    for name in base:
        src = Image.open(os.path.join(TEX, name + ".png")).convert("RGBA")
        for suf, fn in (("_locked", locked), ("_maxed", maxed)):
            out_id = name + suf
            fn(src).save(os.path.join(TEX, out_id + ".png"))
            write_item_json(out_id)
            made += 1
    print(f"기본 아이콘 {len(base)}종 → 상태 변형 {made}개 생성 (_locked/_maxed)")
    print(f"  텍스처: {TEX}")
    print(f"  정의:   {ITEMS}")


if __name__ == "__main__":
    main()
