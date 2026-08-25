#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""본사이드_루디02 — 세이지 생선구이(T3·요리숙련 Lv.23·80,000원) → 들꽃 꿀차(무해금 T1).

필요레벨 1짜리 사이드 퀘스트가 사실상 서버 중반 요리를 요구하고 있었다.
DishSpecs.FREE_DISHES 주석의 규약("퀘스트가 강제하는 요리는 무해금이어야 한다")도 위반이다.
들꽃 꿀차는 튜토리얼(튜토_식당채집)이 이미 흰들국화 채집을 가르치는 요리라 사슬이 이어진다.

quests.json / dialogue.json 이 있는 디렉터리에서 실행. 멱등이다.
"""
import json, shutil, sys, os

DRY = "--dry" in sys.argv
OLD_GOALS = ["craft|세이지_생선구이|1", "eatdish|세이지생선구이|1"]
NEW_GOALS = ["craft|들꽃_꿀차|1", "eatdish|들꽃꿀차|1"]
NEW_NAME = "&d전령에게 따뜻한 한 잔"
NEW_DESC = ["&7루디는 며칠째 제대로 쉬지도 못했습니다.",
            "&7흰들국화를 우린 &f들꽃 꿀차&7를 끓여 함께 마셔주세요."]
NEW_GREET = "부탁 하나만 할게요. 들꽃 꿀차 1개를 끓여서 같이 마셔주는 일이에요."

Q = json.load(open("quests.json", encoding="utf-8"))
e = Q["퀘스트"]["본사이드_루디02"]
changed = []
if e["목표"] != NEW_GOALS:
    assert e["목표"] == OLD_GOALS, f"예상 밖 목표: {e['목표']}"
    e["목표"] = NEW_GOALS; changed.append("목표")
if e.get("이름") != NEW_NAME:
    e["이름"] = NEW_NAME; changed.append("이름")
if e.get("설명") != NEW_DESC:
    e["설명"] = NEW_DESC; changed.append("설명")

D = json.load(open("dialogue.json", encoding="utf-8"))
node = D["루디"]["인사/본사이드_루디02"]
lines = node["lines"]
for i, ln in enumerate(lines):
    if "세이지 생선구이" in ln:
        lines[i] = NEW_GREET; changed.append("대사")

print("변경:", changed or "없음 (이미 반영됨)")
if changed and not DRY:
    shutil.copy("quests.json", "quests.json.bak-rudi02-tea")
    shutil.copy("dialogue.json", "dialogue.json.bak-rudi02-tea")
    json.dump(Q, open("quests.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    json.dump(D, open("dialogue.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print("✓ 저장")
