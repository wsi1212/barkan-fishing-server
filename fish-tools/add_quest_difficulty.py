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
# ★산정 규칙이 없는 목표 verb 수집통 — 아래 검증에서 하드 실패시킨다.
UNKNOWN = collections.Counter()

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


# ══ 최소크기 = «크기 분포의 꼬리» (2026-08-20) ═══════════════════════════════
# v2 는 최소크기를 `×(1 + sz/100)` 선형 배수로 봤다. 160cm 를 2.6배로 계산한다는 뜻이고,
# 실제 값은 **27.4 캐스팅**이다(10배 과소평가). 그래서 「초대형 대물」(주간_초대형,
# fish|아무|아무|1|160)이 난이도 1칸으로 떠 있었다 — 유저가 잡아낸 버그다.
#
# 크기는 `FishingListener` 에서 **균등분포**로 뽑힌다:
#   size = min + random() * (max - min),  구간은 GradeRoller.sizeBand(등급스펙, 뽑힌등급, min, max)
# 범위등급 어종("E~S")만 등급별 하위구간을 쓰고, 나머지는 [minSize, maxSize] 전체다.
# 따라서 P(size >= S | 어종, 등급)은 닫힌 형태로 나온다 — 감으로 배수를 적을 이유가 없다.
RANK = {g: i + 1 for i, g in enumerate(ORDER)}


def size_band(grade_spec, rolled, mn, mx):
    """GradeRoller.sizeBand 이식. 범위등급 어종은 등급별 하위구간을 쓴다."""
    if not grade_spec or "~" not in grade_spec:
        return mn, mx
    parts = grade_spec.split("~")
    gmin, gmax = RANK.get(parts[0], 0), RANK.get(parts[1], 0)
    n = gmax - gmin + 1
    if gmin < 1 or n <= 1:
        return mn, mx
    band = max(0, min(n - 1, RANK.get(rolled, gmin) - gmin))
    step = (mx - mn) / n
    return mn + step * band, mn + step * (band + 1)


def p_size(sp, rolled, minsize):
    """그 어종을 그 등급으로 뽑았을 때 크기가 minsize 이상일 확률."""
    d = FISH.get(sp)
    if not d:
        return 0.0
    mn, mx = size_band(d.get("grade", ""), rolled,
                       float(d["minSize"]), float(d["maxSize"]))
    if mx <= mn:
        return 1.0 if mx >= minsize else 0.0
    return max(0.0, min(1.0, (mx - minsize) / (mx - mn)))


def base_grade(sp):
    g = FISH.get(sp, {}).get("grade", "E")
    return g.split("~")[0] if "~" in g else g


_BY_GRADE = collections.defaultdict(list)
for _sp in FISH:
    _BY_GRADE[base_grade(_sp)].append(_sp)


def _start_grade(gr):
    """목표 등급칸 → 시작 등급. 범위표기는 «쉬운 쪽»(grade_mult 규칙과 동일)."""
    if not gr or gr == "아무":
        return None
    parts = [x for x in gr.split("~") if x in RANK]
    return min(parts, key=lambda x: RANK[x]) if parts else None


def p_cast_any(gr, minsize):
    """어종 지정이 없을 때, 캐스팅 1회가 «그 등급 이상 + minsize 이상»을 낼 확률.
    등급 롤 → 그 등급 풀에서 균등 추첨이므로 등급별 확률에 풀 평균 꼬리확률을 곱해 더한다.
    ★등급 요구와 크기 요구를 따로 곱하지 않는다 — 범위등급 어종은 둘이 상관되어 있다."""
    g0 = _start_grade(gr)
    start = 0 if g0 is None else RANK[g0] - 1
    total = 0.0
    for g in ORDER[start:]:
        pool = _BY_GRADE.get(g, [])
        if pool:
            total += RATE[g] * sum(p_size(s, g, minsize) for s in pool) / len(pool)
    return total


# ★달성 불가 목표 수집통 — 어종의 maxSize 보다 큰 크기를 요구하는 퀘스트는 «영구 미완료»다.
#   2026-08-20 실측으로 본사이드_하겐02(붕어 50cm, 붕어 최대 48cm)를 잡아냈다.
IMPOSSIBLE = []


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


# ── 숨겨진 수집품 — 남은 게 줄면 급격히 비싸진다 (2026-08-19) ─────────────────
#   `collectible|N`은 「이 퀘스트에서 N개를 새로 찾아라」가 아니라 **누적 발견 수**다
#   (`PlayerData.extraFlags["수집품발견"]` 크기 = `CollectibleManager.found()` 권위).
#   그래서 비용은 「풀 P개 중 N개를 찾는 시간」이고, 이 목표의 본질은 **어디를 안 봤는지
#   모른다**는 것이다. 남은 게 r개면 그 한 개를 찾으려고 도시를 처음부터 다시 훑는다.
#
#   ★하모닉(비용 ∝ P/r)으로는 안 맞는다. P=77에서 20개:70개가 1:8밖에 안 되는데 실제
#     체감은 1:100 쪽이다 — 앞쪽 20개는 길 걷다 줍고, 마지막 10개는 전수색이다.
#     그래서 남은 비율의 **세제곱**을 쓴다. 앵커 두 개로 잡은 값이다:
#       20개 ≒ 40분(8칸, 도시 한 바퀴)  ·  70개 ≒ 87시간(20칸, 사실상 전수집)
#   ★P는 collectibles.json 실측이다. 수집품을 더 심으면 같은 목표가 쉬워진다(옳다).
#   ★단순화 — 도시 안 해바라기와 월드 곳곳의 「어드민의 수집품」을 같은 비용으로 본다.
#     후자가 훨씬 멀지만, 목표 카운터가 둘을 구분하지 않으므로 모델도 구분하지 않는다.
COLLECT_POOL = 77          # collectibles.json 이 없을 때의 보수적 기본값
if os.path.exists("collectibles.json"):
    COLLECT_POOL = max(1, len(json.load(open("collectibles.json", encoding="utf-8"))))
COLLECT_UNIT, COLLECT_EXP = 1.3, 3.0


def collect_minutes(n):
    """수집품 누적 n개를 찾는 데 드는 시간(분). n이 풀보다 크면 풀에서 멈춘다."""
    P = COLLECT_POOL
    n = min(int(n), P)
    return sum(COLLECT_UNIT * (P / (P - k + 1)) ** COLLECT_EXP for k in range(1, n + 1))


# ── 카지노 — 기대값이 음수인 게 곧 난이도다 (2026-08-19) ─────────────────────
#   카운터별 (1회 성공 확률, 한 판 소요분). 확률은 자바 실데이터를 그대로 쓴다.
#     `슬롯트리플` — SlotRules.OutcomeType 트리플 티켓 합 340/10,000 = 3.4%
#     `블랙잭승`   — 딜러 우위를 감안한 실플레이 승률 ≒ 43%
CASINO_ODDS = {"슬롯트리플": (0.034, 0.25), "블랙잭승": (0.43, 1.2)}
#   `카지노순익 N` — 슬롯 RTP 93.92%, 즉 **기대 순익이 음수**다. 목표 순익은 변동성으로만
#   얻으므로 잃은 걸 되메우는 시간이 붙는다. 낚시 시급(4,000원/분)의 1/4로 친다 =
#   같은 돈을 카지노로 남기는 데 4배 걸린다.
CASINO_PROFIT_RATE = 1000.0

# ── 확률이 지독한 action (2026-08-19) ────────────────────────────────────────
#   `action|<이름>`은 대개 UI 조작(0.3분)이다. 그런데 확률 이벤트가 섞여 있다 —
#   `슬롯777`은 SEVEN_TRIPLE 10/10,000 = 0.1%, 기대 1,000스핀이다. 평평한 0.3분으로 두면
#   Lv20 퀘스트가 1칸으로 뜬다(실제로 그랬다 — `카지노_슬롯02`).
ACTION_MINUTES = {"슬롯777": 1000 * 0.25}   # 기대 1,000스핀 × 스핀당 0.25분


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
            S = float(sz)
            if sp not in ("아무", ""):
                # 특정 어종 — 그 어종 안에서의 꼬리확률만 곱한다(등급·풀 비용은 위에서 이미 셌다).
                ps = p_size(sp, base_grade(sp), S)
                if ps <= 0:
                    IMPOSSIBLE.append((sp, S, FISH.get(sp, {}).get("maxSize")))
                    ps = 1e-6
                m *= 1.0 / ps
            else:
                # 어종 미지정 — 등급+크기를 «한 번에» 센다. grade_mult 로 이미 센 등급분은 되돌린다.
                pc = p_cast_any(gr, S)
                if pc <= 0:
                    IMPOSSIBLE.append(("아무/" + str(gr), S, None))
                    pc = 1e-6
                m = BASE_CAST * n * (1.0 / pc) * GEAR
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
    if v in ("guilddonate", "guildspend"):
        # 길드 계좌 기부·지출 — 돈을 버는 시간이 곧 비용이다(money 와 같은 시급).
        # ★지출은 「이미 금고에 있는 돈」이라 실제론 더 싸지만, 그 돈도 누군가 벌어 넣은 것이라
        #   같은 값으로 친다.
        return int(p[1]) / 4000.0
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
        return ACTION_MINUTES.get(p[1], 0.3)
    if v == "collectible":
        return collect_minutes(p[1])
    if v == "earn":
        # 누적 수익 — `money`와 같은 시급. money 는 「들고 있어라」, 이쪽은 「벌어라」다.
        return int(p[1]) / 4000.0
    if v == "login":
        # ★달력 제약이라 분으로 옮길 수 없다 — 7일 개근은 아무리 잘해도 7일 걸린다.
        #   하루치 구속을 8분으로 쳐서 「못 서두른다」만 반영한다.
        return 8.0 * int(p[1])
    if v == "casino":
        if p[1] == "카지노순익":
            return int(p[2]) / CASINO_PROFIT_RATE
        odds = CASINO_ODDS.get(p[1])
        if odds is None:
            UNKNOWN["casino|" + p[1]] += 1
            return 3.0 * int(p[2])
        return int(p[2]) / odds[0] * odds[1]
    if v == "level":
        return 0.0                      # ★게이트 — 이미 그 레벨이어야 수락된다
    # ★미지 verb 를 조용히 1.0분으로 넘기면 그 퀘스트는 **1칸**이 된다. 극악 퀘스트가
    #   1칸으로 뜨는 사고가 실제로 났다 — `collectible`·`earn`·`login`·`casino` 12건이
    #   1칸으로 방치돼 있었다(2026-08-19). 아래 검증에서 저장 전에 하드 실패시킨다.
    UNKNOWN[v] += 1
    return 1.0


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

# ★저장 **전에** 막는다 — 규칙 없는 verb 로 계산한 난이도를 quests.json 에 굳히면
#   그때부터 아무도 그게 틀렸다는 걸 모른다.
if UNKNOWN:
    print("\n✗ 산정 규칙이 없는 목표 verb —")
    for _v, _n in UNKNOWN.most_common():
        print(f"    {_v}  {_n}건")
    sys.exit("  goal_minutes() 에 규칙을 넣어라. 안 넣으면 그 퀘스트가 1칸으로 뜬다.")

# ★달성 불가 목표도 저장 전에 막는다 — 난이도만 20칸으로 굳혀 두면 «어렵다»로 위장되고,
#   유저는 평생 못 깨는 퀘스트를 로그에 달고 다닌다(어렵다 ≠ 불가능).
if IMPOSSIBLE:
    print("\n✗ 달성 불가 목표 — 어종의 maxSize 보다 큰 크기를 요구한다:")
    for _sp, _S, _mx in IMPOSSIBLE:
        print(f"    {_sp}  요구 {_S:g}cm  /  최대 {_mx}cm" if _mx else f"    {_sp}  요구 {_S:g}cm  (해당 조건을 만족하는 어종 없음)")
    sys.exit("  quests.json 의 최소크기를 내리거나 어종을 바꿔라.")

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

# 수집품 목표가 풀보다 크면 **완료 불가**다 — 끝까지 찾아도 카운터가 목표에 못 닿는다.
over = [f"{qid} {g}(풀 {COLLECT_POOL})" for qid, e in QUESTS.items() for g in e["목표"]
        if g.split("|")[0] == "collectible" and int(g.split("|")[1]) > COLLECT_POOL]
print("수집품 풀 초과(완료 불가):", over if over else "없음")
if bad or over:
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
