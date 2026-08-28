#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
patch_quest_levelreq.py — 퀘스트 «필요레벨» 중복 잠금 해제 (2026-08-28).

유저 지시: "랩제 다 없애고 싶은데 어케생각해" → "남겨야하는건 남기고 나머지는 없애자".

## 왜 없애나 — 악순환
사이드 퀘스트에 필요레벨이 걸려 있으면 **레벨이 없어 퀘스트를 못 받고, 퀘스트를 못 받아
레벨이 안 오른다.** 유저가 이미 이 문제 때문에 사이드 필요레벨을 손으로 1~4 까지 낮춰 뒀고,
그래서 E 구간(Lv1~4) 퀘스트 경험치 분담률이 **1136%** 라는 기형이 생겼다.

## 무엇을 남기나 — 목표가 스스로 관문인가
실측(2026-08-28): 필요레벨 ≥10 퀘스트 133개 중
  · **93개가 «자연관문»** — 목표가 dogam(도감 N종)·fish(특정 어종)·fish_cm(크기)·submit·
    harpoon·sail·skill 등이라 **레벨제를 지워도 저렙은 못 깬다.** 필요레벨은 중복 잠금이다.
  · **31개가 «이동/대화»** — 목표가 visit/area/talk 뿐이라 레벨제를 지우면 Lv1 이 바로 먹는다.
    그중 큰 것들이 메인 7장(심해 편)이고 보상이 최대 20만원이다. **이건 남긴다.**

★지역 레벨제는 별개로 살아 있다(원양 50·심해_협곡 62·심해_교단_본부 67·무명의_성소 68).
  심해 계열 이동 퀘스트는 그 지역이 대신 막으므로 이중으로 안전하다.

사용:
    python3 patch_quest_levelreq.py <BlockShip경로> [--apply]
"""
import collections, json, os, shutil, sys

#: 이 목표만으로 이뤄진 퀘스트는 «레벨제가 유일한 관문» 이라 남긴다.
OPEN_GOALS = {"visit", "area", "talk"}


def kinds(goals):
    return {g.split("|")[0] for g in (goals or []) if isinstance(g, str)}


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    src, apply_ = sys.argv[1], "--apply" in sys.argv
    path = os.path.join(src, "quests.json")
    Q = json.load(open(path, encoding="utf-8"))
    qs = Q["퀘스트"]

    freed, kept = [], []
    for qid, v in qs.items():
        lv = v.get("필요레벨", 0) or 0
        if lv <= 1:
            continue
        k = kinds(v.get("목표"))
        if k and k <= OPEN_GOALS:
            kept.append((qid, lv, v.get("보상돈", 0) or 0, v.get("이름", "")))
        else:
            freed.append((qid, lv, v.get("보상돈", 0) or 0, v.get("이름", "")))

    print(f"레벨제 해제 {len(freed)}건 · 유지 {len(kept)}건\n")
    bd = collections.Counter(lv for _, lv, _, _ in freed)
    print("해제 대상 레벨 분포:", dict(sorted(bd.items())))
    print(f"해제분 보상돈 합 {sum(m for _, _, m, _ in freed):,}원\n")
    print("★유지 (목표가 이동/대화뿐이라 레벨제가 유일한 관문):")
    for qid, lv, m, nm in sorted(kept, key=lambda x: -x[2])[:12]:
        print(f"   Lv{lv:>2} {m:>8,}원  {qid:<16}{nm[:34]}")
    if len(kept) > 12:
        print(f"   … 외 {len(kept)-12}건")

    if not apply_:
        print("\n[dry-run] --apply 로 실제 반영")
        return
    shutil.copy(path, path + ".bak-levelreq")
    for qid, *_ in freed:
        qs[qid]["필요레벨"] = 1
    json.dump(Q, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"\n✅ quests.json 반영 {len(freed)}건 (백업 quests.json.bak-levelreq)")


if __name__ == "__main__":
    main()
