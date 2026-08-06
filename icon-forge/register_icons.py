#!/usr/bin/env python3
"""아이콘 등록 파일 생성 — items/(아이템 정의) + models/(모델) **두 개** 다 써야 한다.

★2026-08-04 사고: `items/` 에 모델 내용(parent/textures)을 써서 스킬 트리 전체가 마젠타
  체커보드(텍스처 미발견)로 떴다. 기존에 정상 동작하던 72개까지 같이 망가뜨렸다.
  1.21.4+ 규약은 두 파일이 분리돼 있다:

    assets/barkan/items/barkan_icon/<id>.json     ← setItemModel 이 찾는 **아이템 정의**
      {"model":{"type":"minecraft:model","model":"barkan:barkan_icon/<id>"},
       "oversized_in_gui":true}   ← ★슬롯 밖으로 넘쳐 그려지게 (item_def() 주석 참고)

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

# ★노드 배율은 건드리지 말 것 (유저 지시, 2026-08-06). 1.332가 확정값이다.
#   내가 1.25→1.7로 두 번 바꿨다가 "노드만 커진다"는 재현고를 받았다. 문제는
#   노드 크기가 아니라 **연결선이 슬롯 밖으로 안 나가는 것**이다. 노드를 키워서
#   틈을 메우려는 시도는 전부 오답이니 반복하지 말 것.
GUI_SCALE = 1.332         # 노드 — ★고정. 연결 문제를 이 값으로 풀려 하지 말 것
RAIL_SCALE = 1.7          # 레일
PREFIXES = ("skill_", "tree_rail_")
NO_SCALE = ("skill_hub_",)   # /레벨 허브 아트에 맞춰진 아이콘 — 키우면 링 밖으로 삐져나온다


def targets():
    return sorted(f[:-4] for f in os.listdir(TEX)
                  if f.endswith(".png") and f.startswith(PREFIXES))


def item_def(icon_id):
    # ★oversized_in_gui — 이게 "아이콘이 자기 칸을 못 벗어나는" 문제의 진짜 해답이다.
    #   1.21.8+ 클라는 GUI 아이템을 **슬롯 경계로 클리핑**한다(실측: 클라 jar
    #   ClientItem$Properties 에 oversized_in_gui 필드 존재, 1.21.8/1.21.10/1.21.11/26.2
    #   전부 확인). 그래서 display.gui.scale 을 아무리 올려도 넘치는 부분이 잘려나가
    #   "굵어지기만 하고 옆칸을 침범하지 못하는" 증상이 난다 — 배율 문제가 아니었다.
    #   true 면 별도 렌더 패스(OversizedItemRenderer)로 넘어가 슬롯 밖까지 그려진다.
    #   근거: /도감 물고기가 옆칸을 삐져나가는 이유가 정확히 이것 —
    #   assets/minecraft/items/cod.json 에 "oversized_in_gui": true 가 들어있다.
    #   (팩 전체에서 이 필드를 쓰던 파일이 cod.json 뿐이었다.)
    #   ★이건 **아이템 정의(items/)** 쪽 최상위 필드다. 모델(models/)에 쓰면 무시된다.
    return {"model": {"type": "minecraft:model", "model": f"barkan:barkan_icon/{icon_id}"},
            "oversized_in_gui": True}


def model_def(icon_id):
    body = {"parent": "minecraft:item/generated",
            "textures": {"layer0": f"minecraft:item/barkan_icon/{icon_id}"}}
    if not icon_id.startswith(NO_SCALE):
        sc = RAIL_SCALE if icon_id.startswith("tree_rail_") else GUI_SCALE
        body["display"] = {"gui": {"scale": [sc] * 3}}
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
    print(f"  gui scale 노드 {GUI_SCALE} / 레일 {RAIL_SCALE} — 단 {', '.join(NO_SCALE)} 제외")


if __name__ == "__main__":
    main()
