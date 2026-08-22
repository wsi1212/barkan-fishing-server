#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
stat_value.py — 스탯별 실질가치 산정 (공통화폐 = 원/h 환산).

★2026-08-05 전면 교체. 구 버전의 두 가지 근본 오류를 제거했다:
  1) **등급 base 확률을 flat rate로 썼다** — 피티(PRD)를 무시해 수입을 실제의 1/3~1/16로
     과소집계했다. 이제 `price_ladder.mc`와 같은 GradeRoller 충실복제 몬테카를로를 쓴다.
  2) **캐스트/h를 150으로 하드코딩했다** — 근거 없는 값이었다. 이제 prod 텔레메트리 실측
     확정치(포획 220/h, 활성 사이클 16.2초, 완주율 85% → 캐스트 259/h)를 쓴다.

또 하나 구조적 변경: **스탯가치는 단일 숫자가 아니다.** 구간마다 낚시 시급이 4배 차이나므로
같은 스탯 1점의 원/h 값도 4배 차이난다. 그래서 초반/중반/종결 3구간을 병기한다.

산출 방식 (항목별로 가장 정확한 방법을 골라 씀):
  · 완전 선형(판매보너스·더블·트리플·경험치) → 해석해
  · 가격 공식 경유(크기·크리) → 해석해 (price = grade × (0.5 + sizeScore/200))
  · 롤 확률 경유(행운·등급업) → 몬테카를로 유한차분(공통난수 CRN)
  · 미니게임 경유(난이도·도주감소) → minigame_sim 성공률 델타 × 등급분포 × 가격

사용법: python3 stat_value.py [--stage 초반|중반|종결] [--all-stages]
"""
import argparse, importlib.util, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)


def _load(name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, name + ".py"))
    m = importlib.util.module_from_spec(spec)
    saved, sys.argv = sys.argv, [name]
    spec.loader.exec_module(m)
    sys.argv = saved
    return m


PL = _load("price_ladder")
MG = _load("minigame_sim")

PRICE = PL.PRICE
GRADE_ORDER = ["E", "D", "C", "B", "A", "S", "M", "L", "G"]

# ── 실측 파라미터 (2026-08-05 prod 텔레메트리) ─────────────────────────────
CATCH_PER_HOUR = 220          # 포획/h — 활성 사이클 16.2초
COMPLETION = 0.85             # 캐스트→포획 완주율 실측(82~85%)
CASTS_PER_HOUR = CATCH_PER_HOUR / COMPLETION   # ≈ 259 시도/h
SIZE_SCORE = 65.6             # 실측 평균 크기점수
REACT_TICKS = MG.ms_to_ticks(250 + 40)         # 반응 250ms + 핑 40ms = 6틱

DEFAULT_CRIT_RATE = 0.20      # 기준 크리율(크리배율 가치가 여기 비례)
DEFAULT_CRIT_DMG = 4          # 기준 크리배율(크리확률 가치가 여기 비례)
CRIT_PRICE_COEF = 0.06        # FishingListener: 크리 시 판매가 ×(1+critDmg×0.06)

STAGES = {  # 구간 → (풀, 레벨)
    "초반": (set("EDCBA"), 7),
    "중반": (set("EDCBAS"), 30),
    "종결": (set("EDCBASMLG"), 65),
}

# 실현 가능 최대 매그니튜드 (장비 best-single + 강화 최대).
# ★2026-08-05 4차 갱신 — 난이도를 부품에서 도로 철회(유저 판단: 난이도감소는 요리로 충분,
#   부품/낚싯대는 가격 재조정만으로 이미 밸런스가 맞음 — "숙련형" 빌드 삭제). 난이도는 다시
#   로드 전용: 실측 최대 5(아이템) + 1(강화, enhance.json 전수스캔 — 8/4는 이론상한일 뿐 실제
#   아이템 없음) = 6. 나머지 스탯(트리플찬스9·더블찬스85·크기69 등)은 3차 갱신 때 라이브
#   parts.json+enhance.json을 전수 스캔해 확정한 값 그대로(숙련형 제거는 난이도 외 스탯에는
#   영향 없음 — 숙련형은 난이도만 부여했었다).
MAX_MAGNITUDE = {
    "판매보너스 (1%)": 108, "더블찬스 (1%)": 85, "트리플찬스 (1%)": 9,
    "등급업 (1%)": 65, "크기 (1%)": 69, "행운 (1점)": 103, "도주감소 (1%)": 30,
    "크리확률 (1%)": 95, "크리배율 (1점)": 8, "경험치 (1%)": 255, "난이도 (1점)": 6,
    # ★2026-08-23 신설 2종.
    #   재료확률 = 낚싯대 채집형 히든 A 50 + 부품 5슬롯 × 20(상단 A 채집형) = 150. 강화엔 없다.
    #   돌진쿨감 = 작살 속도형 S 52 (gen_spear_builds.py PRIMARY). 부품/강화엔 없다(창 전용).
    "재료확률 (1%)": 150, "돌진쿨감 (1%)": 52,
}


# ── 재료확률 (2026-08-23 신설 공용 스탯) ──────────────────────────────────
# 재료확률은 «수입»이 아니라 **장비 획득 속도**를 올린다. 그래서 income 곱셈이 아니라
# cross-economy-values.md §6의 «게이트» 렌즈로 값을 낸다:
#   장비 1티어를 갖추는 시간 = max(재료 게이트, 가격 게이트)  (낚시 한 번이 둘을 동시에 준다)
#   재료확률 v%  →  재료 게이트 / (1 + v/100)
# 즉 **재료가 관문인 티어에서만** 값이 나고, 돈이 관문인 티어에서는 0이다.
# ★출처 = 2026-08-05 리프라이싱 감사(레시피 196건 대조). 수치를 갱신할 땐 저 표와 같이 고칠 것.
MAT_GATE_H = {"D": 0.35, "C": 0.80, "B": 1.35, "A": 2.01, "S": 3.75}   # 포획 시간(h)
GOLD_GATE_H = {"D": 0.08, "C": 0.21, "B": 0.76, "A": 8.50, "S": 26.39}  # 노동 시간(h)
STAGE_TIERS = {"초반": ["D", "C"], "중반": ["B"], "종결": ["A", "S"]}
# 진행은 «레벨 축»과 «장비 축» 둘이다. 재료확률은 장비 축의 관문만 당기므로 절반만 인정한다.
#  (경험치가 레벨 축 전체를 당겨 1.00을 받는 것과 대칭 — 경험치도 «국면 한정»으로 깎여 있다.)
GEAR_AXIS_SHARE = 0.5

# ★★비장비 싱크 (2026-08-23 1차 모델 정정)
# 처음엔 «장비 레시피 게이트»만 봤다 → A/S는 돈이 관문이므로 종결 = 0.00 이 나왔다. 그런데
# 라이브 레시피를 세어 보면 낚시 드롭 재료를 쓰는 레시피가 낚싯대 73 · 부품 105 · 작살 51 ·
# 재료 7 · **요리 3**이고, 그 요리가 종결 싱크의 본체다 — `DishSpecs` 상위 요리 하나가
# 별빛진주 60(2% 드롭 → 3,000 포획 ≈ 13.6h) · 진주코어 18을 먹는다. 이건 **돈으로 못 산다**.
# 즉 종결에서도 재료는 여전히 관문이고, 다만 그 관문이 «진행»이 아니라 «버프 유지»로 성격이
# 바뀐다. 그래서 종결은 0 이 아니라 절반이다.
#   ★검증 실패의 흔적: 종결 0 으로 두면 gear_payback 이 A급 채집형 장비를 회수 13.7h(전 등급
#     최악)로 뱉었다. «A 채집형을 팔면서 그 스탯값을 0으로 셈»하는 자기모순이라 모델을 고쳤다.
NON_GEAR_SINK_SHARE = {"초반": 1.0, "중반": 1.0, "종결": 0.5}

# ── 돌진쿨감 (작살 전용) ──────────────────────────────────────────────────
# 낚시 income 공식이 아예 안 통하는 스탯이라 **작살 사냥 사이클**을 직접 모델링한다.
#   사이클 = 접근 + 교전.  접근은 돌진(≈1s, 12블록을 20틱에 주파)이거나 수영(≈4s).
#   돌진 쿨타임 T = 10s / (1 + v/100)  (HarpoonManager.DASH_COOLDOWN + 돌진쿨감)
# 시간당 사이클 수 C 는 쿨타임 제한 구간과 사이클 제한 구간이 갈린다(아래 harpoon_cycles).
# 처리량 1% ↑ = 포획 1% ↑ = income 1% ↑ 로 환산한다(작살도 같은 물고기를 잡아 판다).
DASH_CD_SEC = 10.0        # HarpoonManager.DASH_COOLDOWN (200틱)
DASH_APPROACH_SEC = 1.0   # DASH_TICKS(20) × DASH_SPEED — 12블록 주파
SWIM_APPROACH_SEC = 4.0   # 같은 12블록을 수영으로 (가정치 — 수영속도 스탯 0 기준)
ENGAGE_SEC = 6.0          # 찌르기~포획 (가정치)


def harpoon_cycles(dash_cut_pct):
    """돌진쿨감 v% 일 때 시간당 작살 사냥 사이클 수.

    쿨타임이 사이클보다 길면(초반) 일부 사이클만 돌진을 쓴다 → 쿨타임 제한.
    쿨타임이 짧아지면 모든 사이클이 돌진을 쓴다 → 사이클 제한(포화).
    ★포화 뒤로는 돌진쿨감이 **정확히 0**이 된다 — 확률의 자연 포화와 같은 성질이라
      인위적 캡을 둘 필요가 없다("스탯 캡 금지" 원칙).
    """
    T = DASH_CD_SEC / (1.0 + dash_cut_pct / 100.0)
    cycle_all_dash = ENGAGE_SEC + DASH_APPROACH_SEC
    if T <= cycle_all_dash:                       # 사이클 제한(포화)
        return 3600.0 / cycle_all_dash
    # 쿨타임 제한: 6C + (3600/T)×1 + (C - 3600/T)×4 = 3600
    return (3600.0 + (SWIM_APPROACH_SEC - DASH_APPROACH_SEC) * 3600.0 / T) / \
           (ENGAGE_SEC + SWIM_APPROACH_SEC)


def dash_saturation():
    """돌진쿨감이 포화하는 지점(%) — 쿨타임이 «교전+돌진» 사이클과 같아지는 값."""
    return (DASH_CD_SEC / (ENGAGE_SEC + DASH_APPROACH_SEC) - 1.0) * 100.0


def size_mult(size_score):
    """가격 크기점수 배율 = 0.5 + sizeScore/200 (FishItem)."""
    return 0.5 + size_score / 200.0


def grade_dist(pool, level, luck=0, n=400_000, seed=20260805):
    """피티 반영 등급 분포 (GradeRoller 충실복제)."""
    import random
    rnd = random.Random(seed)
    mg = 6
    if level >= 30: mg = 7
    if level >= 45: mg = 8
    if level >= 60: mg = 9
    lm = (100.0 + luck) / 100.0
    pity = {k: 0 for k in "GLMSABCD"}
    cnt = {}
    for _ in range(n):
        g = "E"
        for gr, base, gate in PL.ROLL:
            if g != "E": break
            if gate > 0 and mg < gate: continue
            if gr not in pool: continue
            if rnd.random() < base * lm * (1 + pity[gr]) / 100.0:
                g = gr; pity[gr] = 0
        for k in pity:
            if k != g: pity[k] += 1
        cnt[g] = cnt.get(g, 0) + 1
    return {g: cnt.get(g, 0) / n for g in GRADE_ORDER}


def success_rates(rod_bonus, escape_reduction, trials=4000):
    """등급별 미니게임 성공률 (minigame_sim, 반응 250ms+핑 40ms)."""
    return {g: MG.simulate_catch(g, rod_bonus, escape_reduction, REACT_TICKS, trials, seed=7)
            for g in GRADE_ORDER}


def income_of(dist, size_score=SIZE_SCORE, sell_bonus=0.0):
    """시간당 수입 = 포획/h × Σ P(g)×가격(g).

    ★성공률을 여기 곱하면 **이중계상**이다. 실측 220 포획/h는 미니게임 실패·도주를 이미 포함한
    값(캐스트 259회 중 220회 성공)이고, 실측 등급분포도 '잡힌 물고기'의 분포다. 운영자 실측
    3세션의 원/마리(605~679원)와 이 식이 정합한다. 성공률은 난이도·도주감소의 **상대 델타**를
    구할 때만 쓴다(아래 success_gain).
    """
    m = size_mult(size_score) * (1 + sell_bonus / 100.0)
    per_catch = sum(dist[g] * PRICE[g] * m for g in GRADE_ORDER)
    return per_catch * CATCH_PER_HOUR, per_catch


def success_gain(dist, base_succ, new_succ):
    """미니게임 성공률 개선이 '성공 매출'을 몇 % 늘리는지 (비율만 씀).

    minigame_sim의 절대 성공률은 반응 250ms 가정이라 실측보다 비관적이다(A 11% 등).
    절대값을 income에 곱하면 실측과 안 맞으므로, **개선 비율**만 취해 절대 편향을 상쇄한다.
    """
    b = sum(dist[g] * PRICE[g] * base_succ[g] for g in GRADE_ORDER)
    n = sum(dist[g] * PRICE[g] * new_succ[g] for g in GRADE_ORDER)
    return (n / b - 1.0) if b else 0.0


def compute(stage, crit_rate=DEFAULT_CRIT_RATE, crit_dmg=DEFAULT_CRIT_DMG):
    pool, level = STAGES[stage]
    dist = grade_dist(pool, level)
    succ = success_rates(0, 0)                 # 기준 = 스탯 0 (나뭇가지) — 델타 산출 전용
    income, per_catch = income_of(dist)
    m = size_mult(SIZE_SCORE)
    avg_catch = per_catch
    caught_per_h = CATCH_PER_HOUR

    V = {}

    # ── 선형 (해석해) ────────────────────────────────────────────────
    V["판매보너스 (1%)"] = (income * 0.01, "income×1% (앵커)")
    V["더블찬스 (1%)"] = (0.01 * avg_catch * caught_per_h, "+1% 확률로 +1마리(같은 등급·크기)")
    V["트리플찬스 (1%)"] = (0.02 * avg_catch * caught_per_h, "+1% 확률로 +2마리")
    V["경험치 (1%)"] = (income * 0.01, "★레벨링 국면: income 1%와 동가치(병렬진행). 만렙 후 0")

    # ── 가격 공식 경유 (해석해) ──────────────────────────────────────
    # +1% 크기 ≈ +1 크기점수 → 가격 상대증가 = 0.005/m
    price_per_score = 0.005 / m
    V["크기 (1%)"] = (income * price_per_score, "+1%size≈+1크기점수 (★어종편차 큼)")

    # 크리: size경로(+critDmg×10 점) + 직접경로(판매가 ×(1+critDmg×0.06))
    crit_gain = crit_dmg * 10 * price_per_score + crit_dmg * CRIT_PRICE_COEF
    V["크리확률 (1%)"] = (income * 0.01 * crit_gain,
                       f"+1%크리율×(critDmg{crit_dmg}: 크기경로+판매가직접+{crit_dmg*6}%)")
    V["크리배율 (1점)"] = (income * crit_rate * (10 * price_per_score + CRIT_PRICE_COEF),
                       f"크리율{int(crit_rate*100)}% 가정: 1점당 size+10 & 판매가+6%")

    # ── 롤 확률 경유 (MC 유한차분, CRN) ──────────────────────────────
    # 행운: luckMult=(100+luck)/100 → 피티와 곱이라 실효는 √로 압축된다. delta=10으로 재고 ÷10.
    d_luck = grade_dist(pool, level, luck=10)
    inc_luck, _ = income_of(d_luck)
    V["행운 (1점)"] = ((inc_luck - income) / 10.0,
                     "MC 유한차분(+10 ÷10). ★피티가 base를 √로 압축해 실효가 낮다")

    # 등급업: 1% 캐스트가 1티어 상승 → 분포가중 인접티어 가격차
    jump = 0.0
    for i, g in enumerate(GRADE_ORDER[:-1]):
        nxt = GRADE_ORDER[i + 1]
        jump += dist.get(g, 0) * (PRICE[nxt] - PRICE[g]) * m
    V["등급업 (1%)"] = (0.01 * jump * CATCH_PER_HOUR, "1% 포획이 1티어↑, 분포가중 인접티어 가격차")

    # ── 미니게임 경유 (성공률 개선 '비율' × income) ──────────────────
    # 난이도: rodBonus가 zoneWidth를 넓혀 성공률을 올린다. 등급별 S자라 구간 평균으로 근사.
    g_diff = success_gain(dist, succ, success_rates(6, 0))
    V["난이도 (1점)"] = (income * g_diff / 6.0,
                      "존폭 확장 → 성공매출 +%(rodBonus 0→6 ÷6). 등급문턱에서 몰리는 계단식")
    # 도주감소: 미스 '다음'에만 escapeBase를 floor(÷2) 낮추는 2차 방어선
    g_esc = success_gain(dist, succ, success_rates(0, 20))
    V["도주감소 (1%)"] = (income * g_esc / 20.0,
                       "미스 후에만 발동+floor(÷2) 감쇠 → 성공매출 +%(0→20 ÷20)")

    # ── 게이트 경유 (재료확률) ───────────────────────────────────────
    # 이 구간 티어들 중 «재료가 관문»인 비율만큼만 값이 난다. 관문이 돈이면 0.
    tiers = STAGE_TIERS[stage]
    binding = [t for t in tiers if MAT_GATE_H[t] > GOLD_GATE_H[t]]
    gear_share = len(binding) / len(tiers)
    # 장비 게이트가 돈으로 넘어간 구간에서도 요리·작살·중간재 싱크가 재료를 관문으로 남긴다.
    sink_share = max(gear_share, NON_GEAR_SINK_SHARE[stage])
    V["재료확률 (1%)"] = (
        income * 0.01 * sink_share * GEAR_AXIS_SHARE,
        f"재료 게이트 ÷(1+v/100). 장비 재료관문 {len(binding)}/{len(tiers)}({','.join(tiers)})"
        f", 비장비싱크 {NON_GEAR_SINK_SHARE[stage]:g} → 유효 {sink_share:g} × 장비축 {GEAR_AXIS_SHARE:g}")

    # ── 작살 사이클 경유 (돌진쿨감) ─────────────────────────────────
    base_c = harpoon_cycles(0)
    d_c = harpoon_cycles(1)
    sat = dash_saturation()
    sat_gain = harpoon_cycles(sat) / base_c - 1.0
    V["돌진쿨감 (1%)"] = (income * (d_c / base_c - 1.0),
                       f"작살 사이클 {base_c:.0f}→{d_c:.1f}/h. {sat:.0f}%에서 포화 → 그 뒤 0. "
                       f"★실제 총이득 +{sat_gain*100:.1f}% (오른쪽 «최대기여»는 선형외삽이라 과대)")

    return dict(income=income, per_catch=per_catch, avg_catch=avg_catch,
                caught_per_h=caught_per_h, dist=dist, succ=succ, V=V)


def print_stage(stage, r, anchor_name="판매보너스 (1%)"):
    V = r["V"]
    anchor = V[anchor_name][0]
    print(f"\n{'='*112}")
    print(f"[{stage}]  수입 {r['income']:,.0f}원/h  ·  포획 {CATCH_PER_HOUR}/h (실측) "
          f"·  포획당 평균 {r['avg_catch']:,.0f}원")
    print(f"  등급분포: " + " ".join(f"{g}{r['dist'][g]*100:.2f}%" for g in GRADE_ORDER if r['dist'][g] > 0.0001))
    print(f"  미니게임 성공률(스탯0, 델타산출용): " + " ".join(f"{g}{r['succ'][g]*100:.0f}%" for g in GRADE_ORDER))
    print("=" * 112)
    print(f"{'스탯':<15}{'원/h/단위':>11}{'정규화':>8}{'상한':>6}{'최대기여':>13}{'최대정규화':>11}   근거")
    print("─" * 112)
    rows = sorted(V.items(), key=lambda kv: -(kv[1][0] * MAX_MAGNITUDE.get(kv[0], 1)))
    out = {}
    for name, (won, why) in rows:
        mag = MAX_MAGNITUDE.get(name, 1)
        mc = won * mag
        norm = won / anchor if anchor else 0
        mcn = mc / (anchor * MAX_MAGNITUDE[anchor_name]) if anchor else 0
        print(f"{name:<15}{won:>11,.0f}{norm:>8.2f}{mag:>6}{mc:>13,.0f}{mcn:>11.2f}   {why}")
        out[name] = {"won_per_unit": round(won, 1), "normalized": round(norm, 3),
                     "max_magnitude": mag, "max_contribution_won": round(mc), "basis": why}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", default=None, choices=list(STAGES))
    ap.add_argument("--all-stages", action="store_true")
    ap.add_argument("--crit-rate", type=float, default=DEFAULT_CRIT_RATE)
    ap.add_argument("--crit-dmg", type=int, default=DEFAULT_CRIT_DMG)
    ap.add_argument("--json", action="store_true", help="스냅샷 derived 병합용 JSON 출력")
    args = ap.parse_args()

    stages = list(STAGES) if (args.all_stages or args.stage is None) else [args.stage]
    print(f"기준: 포획 {CATCH_PER_HOUR}/h · 완주율 {COMPLETION:.0%} → 시도 {CASTS_PER_HOUR:.0f}/h · "
          f"크기점수 {SIZE_SCORE} · 크리율 {args.crit_rate:.0%} · 크리배율 {args.crit_dmg}")
    print("★구 버전(flat 확률 + 150캐스트)과 비교 불가 — 2026-08-05 전면 교체")
    result = {}
    for s in stages:
        r = compute(s, args.crit_rate, args.crit_dmg)
        result[s] = {"income_per_hour": round(r["income"]), "avg_catch": round(r["avg_catch"], 1),
                     "stat_values": print_stage(s, r)}
    if args.json:
        print("\n--- JSON ---")
        print(json.dumps({"casts_per_hour": round(CASTS_PER_HOUR, 1),
                          "catch_per_hour": CATCH_PER_HOUR, "size_score": SIZE_SCORE,
                          "stages": result}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
