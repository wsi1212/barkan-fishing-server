#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""요리 사이드퀘 보상 재조정 (2026-08-26).

사이드 보상 곡선은 1~11칸이 8,000~12,000원으로 평평하다가 12칸부터 뛴다
(12칸 중앙 94,000 · 14칸 260,000 · 16칸 1,000,000). 그런데 요리 퀘스트 보상은
전부 「제작 = 쉬움」 가정으로 매겨져 있어서 17칸 두 개가 평평한 구간 값을 받고 있었다.

  루디03  17칸 1,552분  22,000원 =    14원/분
  알도02  17칸 1,508분   8,000원 =     5원/분   ← 같은 라인 알도03(17칸)은 340,000원
  요리장04 5칸    13분  30,000원 = 2,353원/분  ← 5칸 구간 최고액
  루디02   5칸    11분  14,000원 = 1,271원/분

★상향폭을 알도03(340,000)보다 낮게 잡은 이유: 루디03·알도02는 **같은 Lv.35 해금 게이트를
  공유**한다. 비용은 한 번 내는데 보상은 두 번 받으므로 각각에 만액을 주면 이중 지급이 된다.
"""
import json, shutil, sys

DRY = "--dry" in sys.argv
NEW = {
    # qid: (보상돈, 보상경험치)
    "본사이드_루디03": (150_000, 900),   # 17칸 — 해금 게이트 공유분 감안
    "상사이드_알도02": (120_000, 800),   # 17칸 — 위와 같은 게이트, 선행이 더 얕다
    "왕사이드_요리장04": (12_000, 90),   # 5칸 — 구간 중앙(8,500원/85exp)+별빛진주 2 감안
    "본사이드_루디02": (8_000, 80),      # 5칸 — 들꽃 꿀차로 내려온 만큼 보상도
}

Q = json.load(open("quests.json", encoding="utf-8"))
changed = []
for qid, (money, xp) in NEW.items():
    e = Q["퀘스트"][qid]
    if e.get("보상돈") != money or e.get("보상경험치") != xp:
        changed.append(f"{qid} {e.get('보상돈'):,}→{money:,}원 · {e.get('보상경험치')}→{xp}exp")
        e["보상돈"], e["보상경험치"] = money, xp

print("보상 수정:")
for c in changed or ["  없음 (이미 반영됨)"]:
    print("  " + c)
if changed and not DRY:
    shutil.copy("quests.json", "quests.json.bak-cookreward")
    json.dump(Q, open("quests.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print("✓ 저장")
