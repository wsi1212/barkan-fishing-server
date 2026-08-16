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

# ══ 산정 모델 v2 (2026-08-15) — 손으로 지어낸 배수를 버리고 실측치를 쓴다 ══════
#
# v1은 등급 배수를 감으로 적었고(S=12) 도감을 `종수^1.35`로 쳤다. 둘 다 틀렸다.
#   ① 등급 — `GradeRoller.ROLL_ORDER` 주석에 **몬테카를로 80만 캐스트 실측**이 박혀 있다
#      (스탯 0 기준). S는 12배가 아니라 **45배**다. v1은 S를 4배 헐값으로 매겼다.
#   ② 도감 — 절대 종수만 봤다. 그런데 도감의 난이도는 **풀 대비 깊이**다.
#      76종 풀에서 18종은 퀘스트하다 저절로 차고, 58종 풀에서 58종은 지옥이다.
#      v1은 전자를 4~6배 부풀리고 후자를 깎았다(`본섬08`이 Lv8에 11칸으로 뜬 원인).
#
# ── 등급별 실제 출현율 (스탯 0, GradeRoller 2026-08-04 실측 주석) ─────────────
#   E 34.6 · D 33.2 · C 21.5 · B 6.0 · A 2.5 · S 1.0 · M 0.82 · L 0.36 · G 0.033 (%)
RATE = {"E": .346, "D": .332, "C": .215, "B": .060, "A": .025,
        "S": .010, "M": .0082, "L": .0036, "G": .00033}
ORDER = ["E", "D", "C", "B", "A", "S", "M", "L", "G"]

# 목표의 등급칸은 「그 등급 **이상**」을 뜻한다 → 누적 확률의 역수 = 기대 캐스트 수.
CASTS_GE, CASTS_EQ = {}, {}
for i, _g in enumerate(ORDER):
    CASTS_GE[_g] = 1.0 / sum(RATE[x] for x in ORDER[i:])
    CASTS_EQ[_g] = 1.0 / RATE[_g]
CASTS_GE["아무"] = 1.0

# ★스탯 0은 최악값이다. 실플레이는 등급업(캡 30%)·미끼·요리·날씨가 붙어 희귀 등급이
#   더 자주 뜬다. 전 구간에 같은 할인을 먹여 **상대 서열은 유지하고 절대값만** 낮춘다.
GEAR = 0.55            # 실전 장비 보정 — 스탯 0 대비 체감 소요
BASE_CAST = 0.5        # 캐스팅 1회 ≒ 30초 (입질 대기 + 미니게임)


def grade_mult(g):
    """그 등급 **이상** 1마리를 올리는 데 드는 캐스트 수(장비 보정 포함)."""
    if not g or g == "아무":
        return 1.0
    if "~" in g:                       # "D~C" 같은 범위는 **쉬운 쪽**이 기준
        parts = [p for p in g.split("~") if p in CASTS_GE]
        return min(CASTS_GE[p] for p in parts) * GEAR if parts else 1.0
    return CASTS_GE.get(g, 1.0) * GEAR


REGIONS = json.load(open(FP, encoding="utf-8"))["regions"] if os.path.exists(FP) else {}


def _pool(region):
    """지역의 전 버킷 어종 집합."""
    sp = set()
    for bucket in REGIONS.get(region, {}).values():
        sp.update(bucket)
    return sp


def same_grade_pool(sp, grade):
    """그 어종이 사는 지역 중 **동급 경쟁자가 가장 적은 곳**의 동급 종수.
    등급을 뽑은 뒤 균등 추첨이므로, 이 수가 곧 「몇 번 더 뽑아야 하나」다."""
    best = None
    for r in REGIONS:
        if sp not in _pool(r):
            continue
        n = sum(1 for x in _pool(r) if FISH.get(x, {}).get("grade") == grade)
        best = n if best is None else min(best, n)
    return max(1, best or 1)


def dex_minutes(regionspec, k):
    """도감 k종 — **풀 대비 깊이**로 잰다.
    지역 풀의 어종을 흔한 순으로 세우고 k번째 놈이 걸릴 확률의 역수를 쓴다.
    (그 놈을 볼 때쯤이면 더 흔한 것들은 이미 다 봤다.)
    ★퀘스트 전용 어종은 뺀다 — 특정 퀘스트가 켜져 있을 때만 풀에 들어오므로
      상시 수집 대상이 아니다."""
    sp = set()
    for r in regionspec.split(","):
        sp |= _pool(r.strip())
    w = []
    for s in sp:
        d = FISH.get(s, {})
        if d.get("quest"):
            continue
        m = CASTS_EQ.get(d.get("grade", "E"), 1.0)
        if d.get("time", "전체") != "전체":
            m *= 2.5
        if d.get("weather", "전체") != "전체":
            m *= 3.0
        w.append(1.0 / m)
    if not w:
        return 2.2 * k ** 1.35          # 지역 데이터가 없으면 옛 근사로 후퇴
    w.sort(reverse=True)
    tot = sum(w)
    k = min(int(k), len(w))
    return BASE_CAST * GEAR * tot / w[k - 1]


# ── 특수작물 — 실시간 성장이 곧 난이도다 (2026-08-16, 마인팜 라인) ────────────
#   `CropSpecs.ALL`의 (수확 산출 개수, 성장 분). 낚시와 달리 **기다리는 시간**이 비용이라
#   따로 센다. 밭을 여러 칸 굴리면 병렬이 되므로 「섬 작물 한도 중간값」으로 나눈다.
CROP = {"밀": (3, 20), "당근": (2, 30), "감자": (2, 45), "토마토": (2, 60),
        "양배추": (2, 25), "버섯": (3, 40), "수박": (4, 1440)}
PLOTS = 8              # 섬 작물 한도 중간값 (CROP_LIMIT = 4/8/12/20/32)
WAIT_WEIGHT = 0.25     # 기다리는 동안 낚시를 하므로 대기시간은 4분의 1만 친다


def crop_minutes(crop_id, items):
    """특수작물 `items`개를 손에 넣는 데 드는 시간(분)."""
    outq, grow = CROP.get(crop_id, (2, 30))
    harvests = -(-int(items) // outq)                 # 올림
    batches = -(-harvests // PLOTS)
    return harvests * 2.0 + batches * grow * WAIT_WEIGHT


def goal_minutes(g):
    """목표 하나의 예상 소요(분)."""
    p = g.split("|")
    v = p[0]

    def fish(sp, gr, n, sz, fresh=None, harpoon=False):
        n = int(n)
        if sp not in ("아무", ""):
            # ★특정 어종 — 목표의 등급칸(대개 "아무")이 아니라 **어종 실데이터**를 쓴다.
            #   롤은 ①등급을 뽑고 ②그 등급 풀에서 균등 추첨이다. 그래서 비용은
            #   「그 등급이 뜰 때까지」 × 「그 등급 풀에서 이놈이 걸릴 확률의 역수」다.
            #   전설어는 여기에 시간대·날씨가 붙는다 — 그게 체감의 대부분이다.
            d = FISH.get(sp, {})
            g2 = d.get("grade", gr if gr != "아무" else "E")
            m = BASE_CAST * n * CASTS_EQ.get(g2, 1.0) * GEAR * same_grade_pool(sp, g2)
            if d.get("time", "전체") != "전체":
                m *= 2.5                # 밤/새벽만 = 실시간의 일부만 유효
            if d.get("weather", "전체") != "전체":
                m *= 3.0                # 특정 날씨 대기
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
        return dex_minutes(p[1], p[2])
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
    if v == "harvest":
        return crop_minutes(p[1], int(p[2]) * CROP.get(p[1], (2, 30))[0])
    if v == "submitmat":
        # 특수작물 산출물이면 재배 시간을, 그 외 조합 재료면 material과 같은 값을 쓴다.
        if p[1].startswith("작물_"):
            return crop_minutes(p[1][len("작물_"):], int(p[2]))
        return 1.5 * int(p[2]) * 4.0
    if v == "farmland":
        # 괭이질 자체는 빠르지만 흙·물·평탄화가 붙는다. 3,000칸 ≒ 2시간.
        return 0.04 * int(p[1])
    if v == "islandvisit":
        # ★남이 올려 주는 수치다 — 혼자 어떻게 할 수 없는 유일한 목표라 비싸게 친다.
        return 4.0 * int(p[1])
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
