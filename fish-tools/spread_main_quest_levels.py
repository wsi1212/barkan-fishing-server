#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""메인 체인 꼬리(왕도01~끝)의 필요레벨을 «칸당 exp» 기준으로 다시 깐다.

## 왜
2026-09-10 실측: 꼬리 99칸의 칸당 exp 가 Lv.28~38 에서 1,204, Lv.61~70 에서 14,869 —
**12.3 배** 기울어져 있다. 그래서 앞은 한 번에 몰려 열리고(it_s1 Lv.50 기준 논스톱 30칸)
뒤는 순수 그라인드가 된다. 칸당 exp 를 평평하게 밀면 그 둘이 같이 완화된다.

## 범위와 안전장치
- **왕도01 부터 끝까지만** 손댄다(2026-09-10 유저 결정). 스폰·사막 구간은 건드리지 않는다 —
  실유저 41 명이 거기 있고, 그쪽 요구레벨을 올리면 신규가 즉시 막힌다.
- **양 끝을 고정**한다: 왕도01 은 현재 레벨 그대로(사막에서 올라오는 사람이 안 막히게),
  마지막 칸(심해35)은 Lv.70 그대로.
- `--blend` 로 이동 강도를 정한다. 1.0 = 칸당 exp 완전 균등인데, 후반 exp 가 전체의 53% 라
  **스토리 99칸 중 50칸이 Lv.61~70 에 몰린다**(현재 21칸) → 기본값 0.3.
- 전 체인 **단조 보정**을 마지막에 돌린다(왕도03b 32 → 왕도04 31 같은 기존 역전도 같이 펴진다).
- 진행 중인 퀘스트는 안 막힌다 — `QuestManager` 의 레벨 게이트는 «수락 시점»에만 걸린다
  (`QuestManager.java:1753`). 이미 «진행» 인 칸은 요구가 올라가도 그대로 완주한다.

## 권위
`NEED_TABLE` 은 베끼지 않고 `FishingLevelManager.java` 에서 매번 파싱한다 — exp 곡선을
다시 깔면 이 스크립트가 저절로 따라오게 하려는 것이다.

사용:  python3 fish-tools/spread_main_quest_levels.py [--blend 0.3] [--apply]
"""
import argparse, json, re, sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
QUESTS = REPO / "ops/blockship-data/quests.json"
JAVA = Path("/Users/user/development/blockship-plugin/src/main/java/com/blockship"
            "/fishing/FishingLevelManager.java")
RANGE_START = "왕도01"


def need_table() -> list[int]:
    src = JAVA.read_text(encoding="utf-8")
    m = re.search(r"NEED_TABLE\s*=\s*new int\[\]\s*\{(.*?)\}", src, re.S)
    if not m:
        sys.exit("NEED_TABLE 을 못 찾았다 — FishingLevelManager 구조가 바뀌었나 확인할 것")
    return [int(x) for x in re.findall(r"\d+", m.group(1))]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--blend", type=float, default=0.3, help="0=현행 유지, 1=칸당 exp 완전 균등")
    ap.add_argument("--apply", action="store_true", help="실제로 quests.json 에 쓴다")
    a = ap.parse_args()

    NEED = need_table()
    MAX = len(NEED)
    cum = lambda lv: sum(NEED[: max(0, min(lv, MAX) - 1)])

    def lv_at(e: float) -> int:
        for lv in range(1, MAX + 1):
            if cum(lv + 1) > e:
                return lv
        return MAX

    doc = json.loads(QUESTS.read_text(encoding="utf-8"))
    Q = doc["퀘스트"]
    chain, cur, seen = [], "튜토_선원", set()
    while cur and cur not in seen:
        seen.add(cur)
        chain.append(cur)
        cur = (Q.get(cur) or {}).get("다음퀘스트")
    if RANGE_START not in chain:
        sys.exit(f"{RANGE_START} 이 메인 체인에 없다 — 체인이 끊겼는지 확인할 것")

    i0 = chain.index(RANGE_START)
    tail = chain[i0:]
    old = {q: int((Q.get(q) or {}).get("필요레벨", 0)) for q in chain}
    lo, hi = old[tail[0]], old[tail[-1]]
    lo_e, hi_e = cum(lo), cum(hi)
    step = (hi_e - lo_e) / (len(tail) - 1)

    new = dict(old)
    for k, q in enumerate(tail):
        tgt = lv_at(lo_e + step * k)
        new[q] = int(round(old[q] + (tgt - old[q]) * a.blend))
    new[tail[0]], new[tail[-1]] = lo, hi
    prev = 0
    for q in chain:                                  # 전 체인 단조 보정
        if new[q] < prev:
            new[q] = prev
        prev = new[q]

    changed = [q for q in chain if new[q] != old[q]]
    print(f"범위 {RANGE_START}(체인 {i0+1}번째) ~ {tail[-1]} · {len(tail)}칸 · blend={a.blend}")
    print(f"양 끝 고정 Lv.{lo}/{hi} · 균등 목표 칸당 {int(step):,} exp")
    print(f"\n=== 구간별 칸수 (before → after) ===")
    top = max(new[q] for q in tail)          # 표 라벨은 꼬리의 최고 요구레벨까지만
    for a1, b1 in [(28, 38), (39, 50), (51, 60), (61, top)]:
        na = sum(1 for q in tail if a1 <= old[q] <= b1)
        nb = sum(1 for q in tail if a1 <= new[q] <= b1)
        e = cum(min(b1 + 1, MAX + 1)) - cum(a1)
        f = lambda n: f"{int(e/n):,}" if n else "-"
        print(f"   Lv.{a1:<2}~{b1:<3} {na:3}칸 → {nb:3}칸   칸당 {f(na):>9} → {f(nb)}")
    print(f"\n=== 바뀌는 칸 {len(changed)}개 ===")
    for q in changed:
        print(f"   {q:<12} {old[q]:2} → {new[q]:2}   {(Q[q].get('이름') or '')[:30]}")

    if not a.apply:
        print("\n(미적용 — 실제로 쓰려면 --apply)")
        return 0
    for q in changed:
        Q[q]["필요레벨"] = new[q]
    QUESTS.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"\n✅ {QUESTS.relative_to(REPO)} 에 {len(changed)}칸 반영")
    print("   검증:  python3 /Users/user/development/blockship-plugin/tools/quest_audit.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
