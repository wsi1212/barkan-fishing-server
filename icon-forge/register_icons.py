#!/usr/bin/env python3
"""아이콘 등록 파일 생성 — items/(아이템 정의) + models/(모델) **두 개** 다 써야 한다.

★2026-08-04 사고: `items/` 에 모델 내용(parent/textures)을 써서 스킬 트리 전체가 마젠타
  체커보드(텍스처 미발견)로 떴다. 기존에 정상 동작하던 72개까지 같이 망가뜨렸다.
  1.21.4+ 규약은 두 파일이 분리돼 있다:

    assets/barkan/items/barkan_icon/<id>.json     ← setItemModel 이 찾는 **아이템 정의**
      {"model":{"type":"minecraft:model","model":"barkan:barkan_icon/<id>"}}

    assets/barkan/models/barkan_icon/<id>.json    ← 실제 **모델** (텍스처·display 변환)
      {"parent":"minecraft:item/generated","textures":{"layer0":"minecraft:item/barkan_icon/<id>"}}

  `display.gui.scale` 은 **모델** 쪽에 들어간다(정의 쪽에 쓰면 무시된다).

사용: python3 register_icons.py            # skill_* / tree_rail_* 전부 재등록
      python3 register_icons.py --check    # 누락·형식오류만 검사
"""
import argparse
import json
import os
import sys

RP = os.path.expanduser("~/development/barkan-resourcepack")
TEX = os.path.join(RP, "assets/minecraft/textures/item/barkan_icon")
ITEMS = os.path.join(RP, "assets/barkan/items/barkan_icon")
MODELS = os.path.join(RP, "assets/barkan/models/barkan_icon")

GUI_SCALE = 1.125        # 16 * 1.125 = 18 = 슬롯 피치 → 인접 레일과 노드가 맞물린다
PREFIXES = ("skill_", "tree_rail_")
NO_SCALE = ("skill_hub_",)   # /레벨 허브 아트에 맞춰진 아이콘 — 키우면 링 밖으로 삐져나온다


def targets():
    return sorted(f[:-4] for f in os.listdir(TEX)
                  if f.endswith(".png") and f.startswith(PREFIXES))


def item_def(icon_id):
    return {"model": {"type": "minecraft:model", "model": f"barkan:barkan_icon/{icon_id}"}}


def model_def(icon_id):
    body = {"parent": "minecraft:item/generated",
            "textures": {"layer0": f"minecraft:item/barkan_icon/{icon_id}"}}
    if not icon_id.startswith(NO_SCALE):
        body["display"] = {"gui": {"scale": [GUI_SCALE] * 3}}
    return body


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    os.makedirs(ITEMS, exist_ok=True)
    os.makedirs(MODELS, exist_ok=True)

    ids = targets()
    bad = []
    for iid in ids:
        ip, mp = os.path.join(ITEMS, iid + ".json"), os.path.join(MODELS, iid + ".json")
        if a.check:
            try:
                got = json.load(open(ip, encoding="utf-8"))
                if "model" not in got:
                    bad.append(f"{iid}: items/ 에 모델 내용이 들어있다(정의 형식 아님)")
            except Exception as e:
                bad.append(f"{iid}: items/ 읽기 실패 {e}")
            if not os.path.exists(mp):
                bad.append(f"{iid}: models/ 없음")
            continue
        json.dump(item_def(iid), open(ip, "w", encoding="utf-8"), ensure_ascii=False)
        json.dump(model_def(iid), open(mp, "w", encoding="utf-8"), ensure_ascii=False)

    if a.check:
        print(f"검사 {len(ids)}개 — 문제 {len(bad)}건")
        for b in bad[:15]:
            print("  ⛔", b)
        sys.exit(1 if bad else 0)
    print(f"등록 완료 {len(ids)}개 (items/ + models/ 각각)")
    print(f"  gui scale {GUI_SCALE} — 단 {', '.join(NO_SCALE)} 제외")


if __name__ == "__main__":
    main()
