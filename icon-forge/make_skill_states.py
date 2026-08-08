#!/usr/bin/env python3
"""스킬 노드 아이콘의 **상태 변형** 생성 — 잠금 / 최대랭크.

기존 `skill_*.png` 68종은 이미 링 + 심볼이 함께 그려져 있다(링 색이 이미 등급을 나타냄:
주황=근원 / 금색=핵심 / 은색=일반). 그래서 새 소켓 아트를 덧씌우지 않고, **있는 걸 재료로**
상태 변형만 코드로 만든다.

  · 잠금   `<id>_locked`  — 탈채도 + 감광 + 살짝 대비 축소. "아직 못 쓰는 것"이 즉시 읽힌다.
  · 투자   원본 그대로 재사용 (새 파일 0). 반짝임(glint)이 따로 붙는다.
  · 가능   `<id>_avail`   — 원본 + 가는 흰 테두리. **지금 찍을 수 있는 칸**.
  · 최대   `<id>_maxed`   — 밝기·채도 상승 + 시안 림라이트. ★금색으로 하면 안 된다 —
           금색 링은 이미 '핵심 특성'을 뜻하므로 의미가 충돌한다.

★가능 상태가 없던 시절엔 0랭크가 전부 `_locked`였다. 그래서 캐릭터를 막 만들면 트리가
  통째로 회색이라 어디부터 찍어야 할지 안 보였다(2026-08-09 제보). 색이 있냐 없냐가
  1차 신호고, 흰 테두리는 그 위의 강조다 — 최대(두꺼운 시안 후광)와 헷갈리지 않게
  얇게(팽창 3) 두른다.

★배경에 소켓을 굽지 않는 이유는 build_skilltree_bg.py 주석 참조. 노드 상태는 경우의 수가
  노드수 × 랭크라 배경으로는 표현 불가능하고, 아이템이라야 조합 폭발을 피한다.
"""
import json
import os
import sys

from PIL import Image, ImageEnhance, ImageFilter

RP = os.path.expanduser("~/development/barkan-resourcepack")
TEX = os.path.join(RP, "assets/minecraft/textures/item/barkan_icon")
MODELS = os.path.join(RP, "assets/barkan/models/barkan_icon")
ITEMS = os.path.join(RP, "assets/barkan/items/barkan_icon")

RIM = (120, 235, 255)          # 최대랭크 림라이트 색 (시안 = 각성 계열)
AVAIL_RIM = (255, 252, 236)    # 투자 가능 테두리 (거의 흰색 — 어느 링 색과도 안 겹친다)


def rim_of(im, color, grow, gain=1.0):
    """실루엣 바깥 테두리만 뽑아 색을 입힌다. 알파를 팽창시킨 뒤 원본 알파를 뺀다."""
    a = im.split()[3]
    grown = a.filter(ImageFilter.MaxFilter(grow))
    ap, gp = a.load(), grown.load()
    out = Image.new("RGBA", im.size)
    op = out.load()
    for y in range(im.height):
        for x in range(im.width):
            edge = gp[x, y] - ap[x, y]
            if edge > 12:
                op[x, y] = (*color, min(255, int(edge * gain)))
    return out


def avail(im):
    """원본 + 가는 흰 테두리. 본체는 아주 살짝만 올린다 — 투자한 칸(원본)과 색이
    달라지면 '이미 찍은 것'처럼 보인다."""
    r, g, b, a = im.split()
    body = Image.merge("RGB", (r, g, b))
    body = ImageEnhance.Brightness(body).enhance(1.04)
    out = Image.merge("RGBA", (*body.split(), a))
    rim = rim_of(im, AVAIL_RIM, 3, 0.92)
    rim.alpha_composite(out)
    return rim


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
    rim = rim_of(im, RIM, 5)
    # ★블러를 걸면 16px로 줄었을 때 후광이 뭉개져 '안개'가 된다. 팽창 5 + 블러 없음이
    #   실제 게임 크기에서 시안 후광으로 또렷하게 읽힌다(3안 비교로 확정).
    rim.alpha_composite(out)
    return rim


def write_defs(icon_id, base_id):
    """아이콘 한 종에 필요한 json 두 장을 쓴다. ★한 장만 쓰면 자주색 체크무늬가 된다.

      · models/barkan_icon/<id>.json — 실제 모델(텍스처 + gui 배율)
      · items/barkan_icon/<id>.json  — setItemModel 이 찾는 **아이템 정의**

    배율·oversized 같은 설정은 손으로 적지 않고 **원본 아이콘의 두 파일을 읽어 텍스처만
    바꾼다** — 원본이 바뀌면 파생도 따라간다.

    ★2026-08-09: 예전 판은 items/ 에 모델 형식(parent+textures)을 썼다. 그건 아이템
      정의가 아니라서 그대로 배포했으면 잠금·최대 아이콘 170종이 통째로 깨질 뻔했다.
      운영 팩에 들어 있는 정상 파일과 대조해서 잡았다."""
    base_model = os.path.join(MODELS, base_id + ".json")
    with open(base_model, encoding="utf-8") as f:
        model = json.load(f)
    model.setdefault("textures", {})["layer0"] = "minecraft:item/barkan_icon/" + icon_id
    with open(os.path.join(MODELS, icon_id + ".json"), "w", encoding="utf-8") as f:
        json.dump(model, f, ensure_ascii=False)

    base_item = os.path.join(ITEMS, base_id + ".json")
    with open(base_item, encoding="utf-8") as f:
        item = json.load(f)
    item["model"]["model"] = "barkan:barkan_icon/" + icon_id
    with open(os.path.join(ITEMS, icon_id + ".json"), "w", encoding="utf-8") as f:
        json.dump(item, f, ensure_ascii=False)


def main():
    if not os.path.isdir(TEX):
        sys.exit(f"텍스처 폴더 없음: {TEX}")
    os.makedirs(ITEMS, exist_ok=True)
    os.makedirs(MODELS, exist_ok=True)
    base = sorted(f[:-4] for f in os.listdir(TEX)
                  if f.startswith("skill_") and f.endswith(".png")
                  and not f.endswith(("_locked.png", "_avail.png", "_maxed.png")))
    made = 0
    for name in base:
        src = Image.open(os.path.join(TEX, name + ".png")).convert("RGBA")
        for suf, fn in (("_locked", locked), ("_avail", avail), ("_maxed", maxed)):
            out_id = name + suf
            fn(src).save(os.path.join(TEX, out_id + ".png"))
            write_defs(out_id, name)
            made += 1
    print(f"기본 아이콘 {len(base)}종 → 상태 변형 {made}개 생성 (_locked/_avail/_maxed)")
    print(f"  텍스처: {TEX}")
    print(f"  모델:   {MODELS}")
    print(f"  정의:   {ITEMS}")


if __name__ == "__main__":
    main()
