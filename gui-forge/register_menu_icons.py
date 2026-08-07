#!/usr/bin/env python3
"""메뉴 아이콘 등록 — ~/Downloads/barkan-menu-icons/*.png → 리소스팩 ui_menu_* 3종 세트.

1.21.4+ 규약은 **아이템 정의와 모델이 분리**돼 있다. 하나만 쓰면 마젠타 체커보드가 뜬다.
  assets/minecraft/textures/item/barkan_icon/ui_menu_<id>.png   ← 그림
  assets/barkan/models/barkan_icon/ui_menu_<id>.json            ← 모델(텍스처 지정)
  assets/barkan/items/barkan_icon/ui_menu_<id>.json             ← setItemModel 이 찾는 정의

★oversized_in_gui 는 주지 않는다 — 칸 크기에 맞춰 그린 UI 아트라 넘칠 일이 없다.
 (스킬 트리 노드/레일은 옆칸으로 선을 뻗어야 해서 그쪽만 켠다. icon-forge/register_icons.py)

사용: python3 register_menu_icons.py [--src <폴더>]
"""
import argparse
import json
import os
import shutil

RP = os.path.expanduser("~/development/barkan-resourcepack")
TEX = os.path.join(RP, "assets/minecraft/textures/item/barkan_icon")
ITEMS = os.path.join(RP, "assets/barkan/items/barkan_icon")
MODELS = os.path.join(RP, "assets/barkan/models/barkan_icon")
DEFAULT_SRC = os.path.expanduser("~/Downloads/barkan-menu-icons")
PREFIX = "ui_menu_"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default=DEFAULT_SRC)
    args = ap.parse_args()

    for d in (TEX, ITEMS, MODELS):
        os.makedirs(d, exist_ok=True)

    added, same = [], 0
    for f in sorted(os.listdir(args.src)):
        if not f.endswith(".png"):
            continue
        icon = PREFIX + f[:-4]
        dst = os.path.join(TEX, icon + ".png")
        src = os.path.join(args.src, f)
        if os.path.exists(dst) and open(dst, "rb").read() == open(src, "rb").read():
            same += 1
        else:
            shutil.copyfile(src, dst)
            added.append(icon)
        json.dump({"model": {"type": "minecraft:model", "model": f"barkan:barkan_icon/{icon}"}},
                  open(os.path.join(ITEMS, icon + ".json"), "w"), ensure_ascii=False)
        json.dump({"parent": "minecraft:item/generated",
                   "textures": {"layer0": f"minecraft:item/barkan_icon/{icon}"}},
                  open(os.path.join(MODELS, icon + ".json"), "w"), ensure_ascii=False)
    print(f"  갱신 {len(added)}개 {added} · 동일 {same}개")


if __name__ == "__main__":
    main()
