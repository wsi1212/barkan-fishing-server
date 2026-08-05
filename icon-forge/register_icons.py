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

# ★icon-forge/pad_skill_icons.py 로 원본 72개에 상단 여백을 만들면서(콘텐츠 폭
#   58/64 → 49/64) 노드가 다시 작아져 레일과 안 붙었다 — 배율은 그대로 뒀는데
#   콘텐츠만 줄어서 생긴 회귀. 캔버스가 아니라 **콘텐츠**가 칸을 채워야 하므로,
#   줄어든 비율(58/49=1.184)만큼 배율을 올려 이전과 같은 유효 크기로 복원한다.
#   1.125 * 58/49 = 1.332. (패딩 전 1.25가 넘쳤던 유효크기 1.133보다 작아 안전.)
GUI_SCALE = 1.332        # 노드
# ★1.125(정확히 18px=칸 크기)로는 실제 게임에서 노드-레일 사이가 살짝 안 붙었다.
#   Python 목업은 아이템이 슬롯 중심 기준으로 확대된다고 가정했는데 실제 엔진 앵커가
#   그와 미세하게 달라 계산상 "완전히 맞음"이 실제로는 1px 안팎의 틈으로 보였다.
#   레일만 살짝(1.2) 더 키워 확실히 겹치게 한다 — 정확히 맞추는 것보다 약간 겹치는 쪽이 안전.
RAIL_SCALE = 1.2
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
