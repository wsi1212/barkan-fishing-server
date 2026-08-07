#!/usr/bin/env python3
"""GUI 버튼 아이콘 등록 — src/icons/*.png → barkan:barkan_icon/ui_<이름>

자바에서 `meta.setItemModel(new NamespacedKey("barkan", "barkan_icon/ui_<이름>"))` 로 쓴다.

## 왜 별도 스크립트인가
icon-forge/register_icons.py 는 스킬트리 자산(skill_*/tree_rail_*) 전용이고 노드 배율을
먹인다. UI 버튼 아이콘은 **칸 크기에 맞춰 그린 것**이라 배율을 주면 안 된다
(2026-08-07 스킬 화살표가 노드 배율 1.332를 먹어 과하게 커진 사고와 같은 함정).

## 규약
- items/ 는 **아이템 정의**, models/ 는 **모델** — 둘을 바꿔 쓰면 마젠타 체커보드가 뜬다.
- oversized_in_gui 는 주지 않는다. 버튼은 칸 안에 얌전히 있어야 한다.
"""
import json
import os
import shutil

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "src", "icons")
RP = os.path.expanduser("~/development/barkan-resourcepack")
TEX = os.path.join(RP, "assets/minecraft/textures/item/barkan_icon")
ITEMS = os.path.join(RP, "assets/barkan/items/barkan_icon")
MODELS = os.path.join(RP, "assets/barkan/models/barkan_icon")
PREFIX = "ui_"


def main():
    for d in (TEX, ITEMS, MODELS):
        os.makedirs(d, exist_ok=True)
    n = 0
    for f in sorted(os.listdir(SRC)):
        if not f.endswith(".png"):
            continue
        iid = PREFIX + f[:-4]
        shutil.copy2(os.path.join(SRC, f), os.path.join(TEX, iid + ".png"))
        json.dump({"model": {"type": "minecraft:model", "model": f"barkan:barkan_icon/{iid}"}},
                  open(os.path.join(ITEMS, iid + ".json"), "w", encoding="utf-8"), ensure_ascii=False)
        json.dump({"parent": "minecraft:item/generated",
                   "textures": {"layer0": f"minecraft:item/barkan_icon/{iid}"}},
                  open(os.path.join(MODELS, iid + ".json"), "w", encoding="utf-8"), ensure_ascii=False)
        print(f"  {f} → barkan:barkan_icon/{iid}")
        n += 1
    print(f"UI 아이콘 {n}개 등록 (배율 없음 = 원본 크기)")


if __name__ == "__main__":
    main()
