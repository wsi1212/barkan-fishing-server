#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""전 퀘스트에 `난이도`(1~20) 부여 (2026-08-14).

■ 표시
  퀘스트 아이템 로어에 **`|` 바**로 뜬다. 바의 길이가 곧 난이도다.
  1칸(최저) ~ 20칸(최고극악, 체감 100시간급). 색은 길어질수록
  **초록 → 노랑 → 주황 → 빨강 → 진빨강 → 보라 → 진보라 → 회색 → 검정**.
  렌더링은 자바 `QuestManager.difficultyLore()` 소관 — 이 스크립트는 **숫자만** 넣는다.

■ 산정 방식 — 「그 레벨에 도달한 사람이 이 퀘스트를 깨는 데 걸리는 시간」
  누적 플레이타임이 아니다. `level|66` 같은 게이트는 이미 그 레벨이어야 수락되므로
  비용 0으로 친다. 그래야 "이 퀘스트가 얼마나 빡센가"가 정직하게 나온다.

  목표별 예상 소요(분)를 더한 뒤 **로그 스케일**로 1~20에 사상한다.
    2분  → 1칸        60분 → 9칸
    10분 → 5칸       600분 → 15칸       6000분(100시간) → 20칸

  등급 배수는 PRD 등급 분포의 체감 희소도를 따른다(E~D 1.0 … S 12 · M 30 · L 60).
  작살(`harpoon`)은 같은 조건이라도 ×2 — 접근·명중 난이도가 붙는다.

■ 왜 사람이 손으로 안 매기나
  퀘스트가 282개(메인 138 + 사이드 144)다. 손으로 매기면 **일관성이 무너지고**,
  목표가 바뀔 때마다 갱신을 잊는다. 규칙으로 뽑으면 목표만 고쳐도 난이도가 따라온다.
  ★수동 조정이 필요하면 `MANUAL`에 넣는다(보스처럼 규칙으로 안 잡히는 것).

사용법 — quests.json이 있는 디렉터리에서:
    python3 add_quest_difficulty.py            # 적용
    python3 add_quest_difficulty.py --dry      # 계산만, 저장 안 함
"""
import json, math, os, re, shutil, sys, collections

QP, FP = "quests.json", "fish.json"
DRY = "--dry" in sys.argv
Q = json.load(open(QP, encoding="utf-8"))
QUESTS = Q["퀘스트"]
# 어종 실데이터가 있으면 등급·시간대·날씨 제약을 그대로 쓴다. 없으면 보수적 기본값.
FISH = json.load(open(FP, encoding="utf-8"))["fish"] if os.path.exists(FP) else {}

# ── 등급 체감 희소도 (낚는 데 걸리는 시간 배수) ──────────────────────────────
GRADE = {"아무": 1.0, "E": 1.0, "D": 1.0, "C": 1.5, "B": 2.5, "A": 5.0,
         "S": 12.0, "M": 30.0, "L": 60.0}


def grade_mult(g):
    if not g or g == "아무":
        return 1.0
    if "~" in g:                       # "D~C" 같은 범위는 **쉬운 쪽**이 기준
        parts = [p for p in g.split("~") if p in GRADE]
        return min(GRADE[p] for p in parts) if parts else 1.0
    return GRADE.get(g, 1.0)


BASE_CAST = 0.5        # 아무 물고기 1마리 ≒ 30초


def goal_minutes(g):
    """목표 하나의 예상 소요(분)."""
    p = g.split("|")
    v = p[0]

    def fish(sp, gr, n, sz, fresh=None, harpoon=False):
        n = int(n)
        if sp not in ("아무", ""):
            # ★특정 어종 — 목표의 등급칸(대개 "아무")이 아니라 **어종 실데이터**를 쓴다.
            #   전설어는 등급뿐 아니라 시간대·날씨 제약이 체감 난이도의 대부분이다.
            #   예) 바르칸의심연 = S등급 + 밤 + 비. 셋이 겹쳐야 물린다.
            d = FISH.get(sp, {})
            m = BASE_CAST * n * grade_mult(d.get("grade", gr))
            if d.get("time", "전체") != "전체":
                m *= 2.0
            if d.get("weather", "전체") != "전체":
                m *= 3.0
            m *= 3.0                    # 이름을 콕 집어 기다리는 값
        else:
            m = BASE_CAST * n * grade_mult(gr)
        if sz and sz != "0":
            m *= 1.0 + int(sz) / 100.0  # 최소크기 = 재시도
        if fresh and fresh != "0":
            m *= 1.25                   # 신선도 유지 = 동선 제약
        if harpoon:
            m *= 2.0                    # 접근·명중
        return m

    if v == "fish":
        return fish(p[1], p[2], p[3], p[4])
    if v == "fish_fresh":
        return fish(p[1], p[2], p[3], p[4], p[5] if len(p) > 5 else None)
    if v == "harpoon":
        return fish(p[1], p[2], p[3], p[4], harpoon=True)
    if v == "dogam":
        # 도감은 뒷종이 기하급수적으로 어렵다 — 종수^1.35
        return 2.2 * (int(p[2]) ** 1.35)
    if v == "material":
        return 1.5 * int(p[2]) * (1.0 if p[1] == "아무" else 4.0)
    if v == "forage":
        return 2.5 * int(p[2])
    if v == "mine":
        return 1.2 * int(p[2])
    if v == "craft":
        return 2.0 * int(p[2]) * (1.0 if p[1] == "아무" else 1.5)
    if v == "deliver":
        return 3.0 * int(p[2])
    if v == "sell":
        return 0.6 * int(p[1])
    if v == "money":
        return int(p[1]) / 4000.0       # 체감 시급 ≒ 4,000원/분
    if v == "sail":
        return int(p[1]) / 250.0        # 배 속도 ≒ 250블록/분
    if v == "enhance":
        return 3.0 * int(p[1])
    if v == "skill":
        return 4.0 * int(p[1])
    if v == "trap":
        return 4.0 * int(p[1])
    if v == "usebait":
        return 0.4 * int(p[1])
    if v == "eatdish":
        return 3.0
    if v == "quest_daily":
        return 8.0
    if v in ("iceboxbuy", "iceboxstore"):
        return 2.0
    if v == "equip":
        return 0.5
    if v in ("visit", "area"):
        return 2.0                      # 이동
    if v == "action":
        return 0.3
    if v == "level":
        return 0.0                      # ★게이트 — 이미 그 레벨이어야 수락된다
    return 1.0                          # 미지 verb는 보수적으로 작게


# ── 규칙으로 안 잡히는 것 (보스 등) ─────────────────────────────────────────
MANUAL = {
    "심해33": 20,      # 심해전왕 레비아 — 최종 보스
    "붉은사막04": 14,  # 재의 그릇 (중간보스, 미배선)
    "심해32": 18,      # 앞당겨진 의식 — 보스 직전 대규모 전투
    "심해31": 17,      # 대사제 볼프람
}

LO_MIN, HI_MIN = 2.0, 6000.0           # 1칸 / 20칸 기준선


def to_rank(minutes):
    m = max(minutes, LO_MIN)
    r = 1 + 19 * math.log(m / LO_MIN) / math.log(HI_MIN / LO_MIN)
    return max(1, min(20, int(round(r))))


rows = []
for qid, e in sorted(QUESTS.items()):
    if qid in MANUAL:
        rank, mins = MANUAL[qid], None
    else:
        mins = sum(goal_minutes(g) for g in e["목표"])
        rank = to_rank(mins)
    e["난이도"] = rank
    rows.append((qid, rank, mins, e.get("카테고리", ""), e["필요레벨"],
                 " + ".join(e["목표"])))

if not DRY:
    shutil.copy(QP, QP + ".pre-difficulty")
    with open(QP, "w", encoding="utf-8") as f:
        json.dump(Q, f, ensure_ascii=False, indent=2)

# ── 리포트 ───────────────────────────────────────────────────────────────────
dist = collections.Counter(r[1] for r in rows)
print(f"퀘스트 {len(rows)}개 · 난이도 분포")
for k in range(1, 21):
    n = dist.get(k, 0)
    print(f"  {k:2}칸 {'█' * min(n, 60)}{'' if n <= 60 else '…'} {n}")

print("\n최고 난이도 15개 —")
for qid, rank, mins, cat, lv, goals in sorted(rows, key=lambda r: -r[1])[:15]:
    mm = "수동" if mins is None else f"{mins:.0f}분"
    print(f"  {rank:2}칸 {qid:16} Lv{lv:<3} {mm:>7}  {goals[:70]}")

print("\n최저 난이도 5개 —")
for qid, rank, mins, cat, lv, goals in sorted(rows, key=lambda r: r[1])[:5]:
    mm = "수동" if mins is None else f"{mins:.0f}분"
    print(f"  {rank:2}칸 {qid:16} Lv{lv:<3} {mm:>7}  {goals[:70]}")

# ── 검증 ─────────────────────────────────────────────────────────────────────
bad = [qid for qid, e in QUESTS.items()
       if not isinstance(e.get("난이도"), int) or not 1 <= e["난이도"] <= 20]
print("\n범위 이탈:", bad if bad else "없음")
if bad:
    sys.exit("✗ 검증 실패")

# 메인 체인은 뒤로 갈수록 대체로 어려워져야 한다 — 역행이 심하면 경고
cur, seen, chain = "튜토_길드", set(), []
while cur and cur in QUESTS and cur not in seen:
    seen.add(cur); chain.append(cur); cur = QUESTS[cur].get("다음퀘스트")
drops = [(chain[i - 1], QUESTS[chain[i - 1]]["난이도"], chain[i], QUESTS[chain[i]]["난이도"])
         for i in range(1, len(chain))
         if QUESTS[chain[i]]["난이도"] <= QUESTS[chain[i - 1]]["난이도"] - 6]
print(f"메인 체인 급락(6칸+) {len(drops)}건", drops[:5] if drops else "")
print(f"\n{'(드라이런 — 저장 안 함)' if DRY else '✓ 완료. 반영: /데이터리로드'}")
