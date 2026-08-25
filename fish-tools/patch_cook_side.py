#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""요리 사이드퀘 정리 (2026-08-26).

① 설명 색코드 누더기·목표 순서 역전 수정 (자동생성 잔재)
   `&7&fB등급 이상&7 &f3마리&7&7를 채우세요.` 처럼 `&7&7` 이 겹치고, 설명 문장 순서가
   목표 배열과 반대였다(요리 먼저 적고 물고기를 나중에 적는데 목표는 물고기가 1번).
② 해금 게이트를 설명에 명시
   잠긴 요리를 요구하는 퀘스트가 그 사실을 한 줄도 안 적어 뒀다. 수락하고 주방에 가서야
   「요리 숙련 Lv.35 부터 배울 수 있습니다」로 막힌다. 튜토 `튜토_요리1` 이 재료를
   `&8특수 밀 2 + 강화 밀 4` 로 적어 두는 것과 같은 관례로 게이트를 적는다.
   ★사이드가 해금 요리를 요구하는 것 자체는 정상이다(2026-08-26 유저 결정) — 대신 사기만 치지 말 것.

quests.json 이 있는 디렉터리에서 실행. 멱등.
"""
import json, shutil, sys

DRY = "--dry" in sys.argv
# DishSpecs.UNLOCK_LEVEL / UNLOCK_COST
LV = {1: 1, 2: 10, 3: 23, 4: 35}
COST = {1: 3_000, 2: 20_000, 3: 80_000, 4: 150_000}
# 잠긴 요리 → 해금 티어 (recipes.json locked + lore 라벨에서 온 값)
GATE = {"피시앤칩스": 4, "초밥플래터": 4, "가시배화채": 1, "트러플스튜": 1}

DESC = {
    # 목표 순서(fish → craft)에 맞춰 다시 씀
    "상사이드_알도02": ["&7귀한 손님이 오네. 상에 올릴 게 필요하오.",
                    "&fB등급 이상 3마리&7를 채우고 &f초밥 플래터&7 하나를 만들어 주게."],
    "사사이드_오마르01": ["&f40cm 이상 물고기 9마리&7를 채우고,",
                     "&f명란 젓갈&7도 하나 담가 주시오."],
    "본사이드_루디03": ["&7루디가 답례로 특별한 소식을 가져왔습니다.",
                    "&f피시 앤 칩스&7를 만들어 나눠 먹으세요."],
    "사사이드_유세프03": ["&f물고기 20마리&7를 판매하고 시원한 것도 좀 드시오.",
                     "&f가시배 화채&7를 하나 먹어보시오."],
    "왕사이드_요리장04": ["&7선왕비가 즐기던 요리를 재현해야 합니다.",
                     "&f트러플 크림스튜&7를 만들어 올리세요.",
                     "&8맛을 보려면 직접 먹어봐야 합니다."],
}


def gate_line(e):
    """이 퀘스트가 요구하는 요리 중 잠긴 것의 해금 조건 한 줄. 없으면 None."""
    tiers = []
    for g in e["목표"]:
        pr = g.split("|")
        if pr[0] not in ("craft", "eatdish") or len(pr) < 2:
            continue
        key = pr[1].replace("_", "")
        if key in GATE:
            tiers.append(GATE[key])
    if not tiers:
        return None
    t = max(tiers)
    lv, cost = LV[t], COST[t]
    head = f"&8요리 숙련 Lv.{lv} · " if lv > 1 else "&8"
    return f"{head}레시피 해금 {cost:,}원"


Q = json.load(open("quests.json", encoding="utf-8"))
changed = []
for qid, e in Q["퀘스트"].items():
    before = list(e.get("설명", []))
    desc = list(DESC.get(qid, before))
    desc = [d for d in desc if not d.startswith("&8요리 숙련") and "레시피 해금" not in d]
    gl = gate_line(e)
    if gl:
        desc.append(gl)
    if desc != before:
        e["설명"] = desc
        changed.append(qid)

print("설명 수정:", changed or "없음")
if changed and not DRY:
    shutil.copy("quests.json", "quests.json.bak-cookside")
    json.dump(Q, open("quests.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print("✓ 저장")
