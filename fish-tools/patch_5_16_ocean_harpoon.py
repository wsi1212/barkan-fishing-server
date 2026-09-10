#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""[5-16] 꺼진 자리의 지도(배상단08b) — 대양 도감을 걷어내고 «대양 작살 사냥»으로 바꾼다.

2026-09-10 유저 결정: `dogam|대양|36` 을 빼고 «작살로 대양에서 200마리(A등급 이상 16마리 포함)».

## 지역 한정이 되는 근거
`harpoon` 목표의 6번째 필드가 지역이다 — `QuestManager.onFish` 가 `fishGoalRegions(o)` 로
`fish`·`fish_cm`·`harpoon` 셋 다 지역을 걸러 준다(`quest_audit.py` 의 GOAL_LENGTHS 도 harpoon 에
선택 지역 필드를 이미 허용한다). 하위 지역에서 잡아도 되게 하려면 그 지역 id 를 쓰면 된다.

## ★같이 고친 버그 (blockship-plugin)
이 목표를 그냥 넣으면 «작살로 대양에서» 가 성립하지 않았다. `onFish` 가 도구를 안 가리고
harpoon 목표를 올리고, `HarpoonListener` 는 `onFish` + `onHarpoon` 을 둘 다 불렀다 →
낚싯대로도 오르고 작살로는 2씩 올랐다(prod 실측: 작살 어획 0회인 유저가 튜토_작살2 완료).
`onFish(.., byHarpoon)` 하나로 통합해 고쳤다. 그 수정이 배포되기 «전»에는 이 목표가
「아무 도구로 대양 100마리」로 동작한다 — 순서를 지킬 것.

## 진행도 인덱스
목표 순서를 바꾸면 questProgress 의 키(1,2,…)가 다른 목표를 가리킨다. 적용 시점에
배상단08b 진행도 보유자가 0명이어서 안전했다 — 나중에 다시 손대려면 먼저 확인할 것.

사용:  python3 fish-tools/patch_5_16_ocean_harpoon.py [--apply]
"""
import argparse, json, sys
from pathlib import Path

QUESTS = Path(__file__).resolve().parents[1] / "ops/blockship-data/quests.json"
QID = "배상단08b"
NEW_GOALS = ["harpoon|아무|아무|200|0|대양", "harpoon|아무|A|16|0|대양"]
OLD_DESC_LINE = "&7&f대양 도감 36종&7 · &f작살로 A등급 이상 16마리&7."
NEW_DESC_LINE = "&7&f작살로 대양에서 200마리&7 — 그중 &fA등급 이상 16마리&7."


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    doc = json.loads(QUESTS.read_text(encoding="utf-8"))
    q = doc["퀘스트"].get(QID)
    if q is None:
        sys.exit(f"{QID} 이 없다")

    print(f"{QID}  {q.get('이름')}")
    print("  목표  before:", q.get("목표"))
    print("        after :", NEW_GOALS)
    desc = list(q.get("설명") or [])
    if OLD_DESC_LINE in desc:
        desc[desc.index(OLD_DESC_LINE)] = NEW_DESC_LINE
        print("  설명  목표 줄 1개 교체")
    elif NEW_DESC_LINE in desc:
        print("  설명  이미 새 문구")
    else:
        print("  ⚠ 설명에서 옛 목표 줄을 못 찾았다 — 손으로 확인할 것")

    if not a.apply:
        print("\n(미적용 — --apply)")
        return 0
    q["목표"] = list(NEW_GOALS)
    q["설명"] = desc
    QUESTS.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"\n✅ 반영. 난이도({q.get('난이도')})는 fish-tools/add_quest_difficulty.py 로 재계산할 것")
    return 0


if __name__ == "__main__":
    sys.exit(main())
