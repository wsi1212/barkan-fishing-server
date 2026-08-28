#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
patch_weekly_families.py — 주간 퀘스트를 «공통 + 레벨 자동전환» 구조로 (2026-08-28).

유저: "주퀘에 접속 n일, 물고기 n마리처럼 누구나 다 할 수 있는 공통적인건 공통으로 하고
       나머지 일부는 유저 레벨에 따라 자동으로 난이도가 달라지게 하자. 뉴비는 B급 n마리 이상,
       뭐 한 20렙부터는 A급 40부터는 S급 이런식으로"

## 무엇이 문제였나
주간은 «필요레벨 이상이면 배정» 이라 **누적**됐다. 그래서
   Lv1 6개 · Lv10 22개 · Lv20 36개  ← 올클리어 보상은 «1.5 레벨분» 고정
Lv20 은 36개를 다 깨야 Lv5 가 6개로 받는 것과 같은 보상을 받는다 — **레벨을 올리면 벌칙**이다.
게다가 고레벨 목록에 «접속 3일»·«크기 35» 같은 1분 잡무가 30개 남아 체크리스트가 된다.

## 구조
  · **공통** — 접속·일퀘·기초 조업. 레벨 무관, 모두 같은 것을 받는다.
  · **가족(family)** — 같은 계열의 여러 판본이 레벨 구간을 나눠 갖고 **한 칸만 활성**된다.
    구간은 유저 지시대로 뉴비 / Lv20+ / Lv40+ 3단이 기본이다.
  ⇒ 활성 개수가 레벨과 무관하게 일정해지고, 올클리어 부담이 고정된다.

동작은 QuestManager.checkWeekly 의 «최대레벨» 게이트가 담당한다(2026-08-28 신설).
구간을 벗어난 판본은 목록에서 빼 준다 — 안 그러면 미완료로 남아 올클리어가 영구 불가가 된다.

사용:
    python3 patch_weekly_families.py <BlockShip경로> [--apply]
"""
import json, os, shutil, sys

#: (필요레벨, 최대레벨). 최대레벨 0 = 상한 없음.
NEWBIE, MID, END = (1, 19), (20, 39), (40, 0)

#: 공통 — 레벨 무관, 전원 동일
COMMON = ["주간_접속꾸준", "주간_개근왕", "주간_성실모험가", "주간_헌신", "주간_일퀘마스터",
          "주간_대물손맛"]

#: 가족 — 같은 계열이 레벨 구간을 나눠 갖는다. 한 구간에 한 칸만 활성.
FAMILIES = {
    "등급소량": [("주간_B급헌터", NEWBIE), ("주간_A급어획", MID), ("주간_전설낚시", END)],
    "등급대량": [("주간_C급대량", NEWBIE), ("주간_B급대량", MID), ("주간_A급대량", END)],
    "조업":     [("주간_조업", NEWBIE), ("주간_조업II", MID), ("주간_불타는조업", END)],
    "판매":     [("주간_어시장", NEWBIE), ("주간_대량출하", MID), ("주간_대형출하", END)],
    "재료":     [("주간_재료낚시1", NEWBIE), ("주간_재료낚시2", MID), ("주간_재료낚시3", END)],
    "골드":     [("주간_골드획득1", NEWBIE), ("주간_골드획득2", MID), ("주간_골드획득3", END)],
    "크기":     [("주간_월척", NEWBIE), ("주간_거물", MID), ("주간_초대형", END)],
    "어종월척": [("주간_붕어월척", (1, 9)), ("주간_누치월척", (10, 19)),
                 ("주간_가물치월척", MID), ("주간_잉어월척", END)],
    "특수재료": [("주간_거대비늘수집", NEWBIE), ("주간_토기복원", MID), ("주간_고대유물제출", END)],
    # C급 소량은 «등급소량» 뉴비 칸이 B급으로 올라가면서 남는다 → 더 낮은 입문 칸으로 둔다.
    "등급입문": [("주간_C급사냥", (1, 9)), ("주간_전설쌍", END)],
}


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    src, apply_ = sys.argv[1], "--apply" in sys.argv
    path = os.path.join(src, "quests.json")
    J = json.load(open(path, encoding="utf-8"))
    Q = J["퀘스트"]
    weekly = J["주간"]

    plan = {}
    for q in COMMON:
        plan[q] = (1, 0)
    for fam, rows in FAMILIES.items():
        for q, (lo, hi) in rows:
            plan[q] = (lo, hi)

    missing = [q for q in weekly if q not in plan]
    extra = [q for q in plan if q not in weekly]
    if missing or extra:
        print(f"★분류 누락 {len(missing)}건: {missing}")
        print(f"★주간 풀에 없는 항목 {len(extra)}건: {extra}")
        if missing:
            raise SystemExit("주간 36종 전부를 분류해야 한다 — 빠진 건 영원히 배정되지 않는다")

    print(f"{'퀘스트':<20}{'가족':<10}{'현재Lv':>7}{'→ 필요':>7}{'최대':>6}  목표")
    for fam, rows in [("공통", [(q, (1, 0)) for q in COMMON])] + list(FAMILIES.items()):
        for q, (lo, hi) in rows:
            v = Q[q]
            g = (v.get("목표") or [""])[0]
            print(f"  {q:<18}{fam:<10}{v.get('필요레벨',1):>7}{lo:>7}{hi if hi else '-':>6}  {g[:26]}")

    # 레벨별 활성 개수
    print("\n레벨별 활성 주간 개수:")
    for lv in (1, 5, 10, 15, 20, 30, 40, 60):
        n = sum(1 for q, (lo, hi) in plan.items() if lv >= lo and (hi == 0 or lv <= hi))
        print(f"   Lv{lv:>2}: {n:>2}개")

    if not apply_:
        print("\n[dry-run] --apply 로 실제 반영")
        return
    shutil.copy(path, path + ".bak-weeklyfam")
    for q, (lo, hi) in plan.items():
        Q[q]["필요레벨"] = lo
        if hi:
            Q[q]["최대레벨"] = hi
        else:
            Q[q].pop("최대레벨", None)
    json.dump(J, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print("\n✅ quests.json 반영 (백업 quests.json.bak-weeklyfam)")


if __name__ == "__main__":
    main()
