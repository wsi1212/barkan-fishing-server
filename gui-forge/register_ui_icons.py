#!/usr/bin/env python3
"""UI 아이콘 등록 — src/icons/<폴더>/*.png → 리소스팩 3종 세트.

1.21.4+ 규약상 **아이템 정의와 모델이 분리**돼 있다. 하나만 쓰면 마젠타 체커보드가 뜬다.
  assets/minecraft/textures/item/barkan_icon/<id>.png   ← 그림
  assets/barkan/models/barkan_icon/<id>.json            ← 모델(텍스처 지정)
  assets/barkan/items/barkan_icon/<id>.json             ← setItemModel 이 찾는 정의

★oversized_in_gui 는 주지 않는다 — 칸 크기에 맞춘 UI 아트라 넘칠 일이 없다.
 (스킬 트리 노드/레일만 켠다. icon-forge/register_icons.py)

폴더 → 아이디 접두어. menu/currency 는 register_menu_icons.py 가 이미 처리한다.
"""
import argparse
import json
import os
import shutil

HERE = os.path.dirname(os.path.abspath(__file__))
RP = os.path.expanduser("~/development/barkan-resourcepack")
TEX = os.path.join(RP, "assets/minecraft/textures/item/barkan_icon")
ITEMS = os.path.join(RP, "assets/barkan/items/barkan_icon")
MODELS = os.path.join(RP, "assets/barkan/models/barkan_icon")

FOLDERS = {
    "enhancement": "ui_scroll_",   # 강화 주문서 10종 (성공률/하락방지/하락감소)
    "tickets": "ui_ticket_",       # 잠수 상점 티켓 (자동심기·비행)
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default=os.path.join(HERE, "src", "icons"))
    args = ap.parse_args()
    for d in (TEX, ITEMS, MODELS):
        os.makedirs(d, exist_ok=True)

    total, added = 0, []
    for folder, prefix in FOLDERS.items():
        path = os.path.join(args.src, folder)
        if not os.path.isdir(path):
            print(f"  ! {folder}/ 없음 — 건너뜀")
            continue
        for f in sorted(os.listdir(path)):
            if not f.endswith(".png"):
                continue
            icon, src = prefix + f[:-4], os.path.join(path, f)
            dst = os.path.join(TEX, icon + ".png")
            if not (os.path.exists(dst) and open(dst, "rb").read() == open(src, "rb").read()):
                shutil.copyfile(src, dst)
                added.append(icon)
            json.dump({"model": {"type": "minecraft:model", "model": f"barkan:barkan_icon/{icon}"}},
                      open(os.path.join(ITEMS, icon + ".json"), "w"), ensure_ascii=False)
            json.dump({"parent": "minecraft:item/generated",
                       "textures": {"layer0": f"minecraft:item/barkan_icon/{icon}"}},
                      open(os.path.join(MODELS, icon + ".json"), "w"), ensure_ascii=False)
            total += 1
    print(f"  등록 {total}개 · 새로 복사 {len(added)}개")
    for a in added:
        print("    +", a)


if __name__ == "__main__":
    main()
