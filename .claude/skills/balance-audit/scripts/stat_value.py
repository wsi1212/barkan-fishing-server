#!/usr/bin/env python3
"""
stat_value.py — 스탯별 실질가치 산정 (공통화폐 = 원/h 환산).

모든 스탯 1포인트가 "시간당 수입(원/h)"으로 얼마인지 라이브 수치에서 계산한다. 이 환산표가
요리 버프·날씨·장비 가치를 평가하는 공통 잣대다. balance 변경 시 스냅샷만 새로 뽑으면 값이 갱신된다.

핵심 원리:
- 수입 앵커: 판매보너스 +1% = income×0.01. 다른 수입계 스탯을 여기 맞춰 환산.
- ★수입가치 ≠ 직관가치: 행운의 수입가치는 '희귀등급'이 아니라 흔한 D/C 등급 확률 상향(E→D
  질량이동)에서 나온다. 희귀등급(M/L/G) 자체는 수입 기여 ≈0 (fish.json 개별가 없음 → 가격=
  grade×quality, G조차 6,700캐스트당 1마리). 행운의 추가 효용(도감/고등급 baseExp)은 별도.
  이런 '어디서 가치가 나오나'를 표의 근거란에 명시한다 — 직관이 틀리기 쉬운 지점.

사용법: python3 stat_value.py [--snapshot audits/snapshots/<date>.raw.json] [--casts 150] [--quality 50]
"""
import argparse, json, os

# 미니게임 1판 ≈ 24초 가정 → 150판/h. balance.md 기준.
DEFAULT_CASTS = 150
DEFAULT_QUALITY = 50  # 평균 품질 (FishItem.quality 기본 50)
DEFAULT_CRIT_RATE = 0.20  # 기준 크리율 (크리확률 스탯 투자 가정). 크리배율 가치는 여기 비례.
DEFAULT_CRIT_DMG = 4      # 기준 크리배율 (base 1, 캡 폐지). 크리확률 가치는 여기 비례.
CRIT_PRICE_COEF = 0.06    # 2026-07-24 신설: 크리 시 판매가 직접 ×(1+critDmg×COEF). FishingListener.java 참조.

GRADE_ORDER = ["E", "D", "C", "B", "A", "S", "M", "L", "G"]

# 실현 가능 최대 매그니튜드 (장비 best-single + 강화 최대). 2026-07-24 데이터.
# ★2026-07-24: 등급업/크리배율/콤보 하드캡 전면 폐지(구식 인위적 상한 — balance-audit이 크리를
# 최약체로 만드는 원인으로 지목해 제거됨). 이제 "상한"은 캡이 아니라 장비+강화 실현가능 최대치.
# "per-1단위 값 × 상한"으로 스탯의 실제 천장 기여를 보여준다 (단위 스케일 왜곡 보정).
MAX_MAGNITUDE = {
    "판매보너스 (1%)": 110, "더블찬스 (1%)": 110, "트리플찬스 (1%)": 13,
    "등급업 (1%)": 56,      # 캡 폐지 후 실현가능 최대(balance.md §9 종결세팅 합계)
    "크기 (1%)": 100, "행운 (1점)": 100, "도주감소 (1%)": 50,
    "크리확률 (1%)": 80, "크리배율 (1점)": 15,  # 캡8 폐지: 장비5+강화10 = 실현가능 15
    "경험치 (1%)": 255,     # gear115 + enhance140
}


def load_snapshot(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def qmult(quality):
    """가격 품질배율 0.5 + q*0.5/100."""
    return 0.5 + quality * 0.5 / 100.0


def grade_distribution(prob, max_rank=9):
    """등급 base 확률(%)로 캐스트당 등급 분포. E는 잔여."""
    dist = {}
    used = 0.0
    for g in GRADE_ORDER[1:max_rank]:
        p = prob.get(g, 0) / 100.0
        dist[g] = p
        used += p
    dist["E"] = max(0.0, 1 - used)
    return dist


def avg_catch_value(dist, price, quality):
    """캐스트당 평균 판매가 (품질배율 적용)."""
    m = qmult(quality)
    return sum(dist[g] * price.get(g, 0) * m for g in dist)


def compute(snapshot, casts, quality, crit_rate=DEFAULT_CRIT_RATE, crit_dmg=DEFAULT_CRIT_DMG):
    raw = snapshot["raw"]
    prob = raw["rng"]["grade_base_prob"]
    price = raw["economy"]["grade_base_price"]
    dist = grade_distribution(prob)
    avg = avg_catch_value(dist, price, quality)
    income = avg * casts  # 원/h (무버프)

    m = qmult(quality)
    V = {}  # stat -> (원/h per unit, 근거)

    # ── 순수 수입계 ──────────────────────────────
    # 판매 +1%: income×0.01
    V["판매보너스 (1%)"] = (income * 0.01, "income×1% (앵커)")
    # 더블 +1%: +0.01 추가물고기/캐스트 (같은 등급) = avg값
    V["더블찬스 (1%)"] = (0.01 * avg * casts, "+1% 확률로 +1마리(평균값)")
    # 트리플 +1%: +0.02 물고기(+2마리)
    V["트리플찬스 (1%)"] = (0.02 * avg * casts, "+1% 확률로 +2마리")

    # 등급업 +1%: 1% 캐스트가 1티어 상승 → 인접티어 가격차 기대값
    # 분포 가중 평균 티어점프 가치
    jump = 0.0
    for i, g in enumerate(GRADE_ORDER[:-1]):
        nxt = GRADE_ORDER[i + 1]
        jump += dist.get(g, 0) * (price.get(nxt, 0) - price.get(g, 0)) * m
    V["등급업 (1%)"] = (0.01 * jump * casts, "1% 캐스트 1티어↑, 분포가중 가격차")

    # 크기 +1%: size×1.01 → quality 상승 → 가격. 어종편차 큼(중간밴드 근사).
    # 중간밴드(q≈50, size≈range) 가정: +1%size ≈ +1 quality; +1 quality → mult +0.005 → 가격 +0.005/m
    price_per_quality = 0.005 / m  # 가격 상대증가율 per +1 quality
    V["크기 (1%)"] = (income * price_per_quality * 1.0, "+1%size≈+1quality (★어종편차 큼)")

    # ── 크리 (★시너지·기준점 의존, 2026-07-24부터 size경로+직접가격보너스 2갈래) ──
    # size경로: income × 크리율 × critDmg×10% × price_per_quality (기존, XP에도 기여)
    # 직접경로: income × 크리율 × critDmg×CRIT_PRICE_COEF (신설, FishingListener 판매가 직접배수)
    # 두 경로 합 = 크리 1회당 가격 상대증가. 크리확률·크리배율은 서로 곱이라 시너지(단독값 무의미).
    crit_gain_per_dmg = crit_dmg * 10 * price_per_quality + crit_dmg * CRIT_PRICE_COEF
    V["크리확률 (1%)"] = (income * 0.01 * crit_gain_per_dmg,
                       f"+1%크리율×(critDmg{crit_dmg}: 크기경로+직접가격+{crit_dmg*6}%). ★critDmg 낮으면 값↓")
    V["크리배율 (1점)"] = (income * crit_rate * (10 * price_per_quality + CRIT_PRICE_COEF),
                       f"크리율{int(crit_rate*100)}%: size+10%/점 + 판매가직접+6%/점 (상한없음)")

    # ── 손실방지 ────────────────────────────────
    # 도주감소 +1%: escapeBase -0.5% (÷2). escape=캐치 전손. 대표 도주율 맥락에서 0.5% 캐치 회수.
    V["도주감소 (1%)"] = (income * 0.005, "escapeBase-0.5%(÷2)=+0.5%캐치 (★도주율 높을때만)")

    # ── 비수입 효용 (income≈0, 별도 평가) ─────────
    # 행운 +1: 등급확률×(1+1/100). 희귀등급 수입기여≈0 → 수입가치 미미. 경험치(고등급 baseExp↑)+도감가치.
    # 수입 델타: 분포를 1% 상향한 income 차이(거의 0)
    dist2 = {g: p * (1.01 if g != "E" else 1) for g, p in dist.items()}
    # 정규화
    s = sum(v for k, v in dist2.items() if k != "E")
    dist2["E"] = max(0, 1 - s)
    income2 = avg_catch_value(dist2, price, quality) * casts
    V["행운 (1점)"] = (income2 - income, "모든등급확률+1%(희귀어 수집엔 실효). 수입기여: 흔함80%/S19%/MLG1.3%")

    # 경험치 +1%: 레벨링은 수입과 나란한 진행 트랙. +1%exp = +1% 레벨링 처리량.
    # 병렬진행 휴리스틱: 레벨링 국면엔 진행 1%를 income 1%와 동가치로 본다 → 판매와 동률(1.0).
    # 만렙 후엔 0. 단일 상수 불가라 '레벨링 값'을 기록하고 국면 태그를 단다.
    V["경험치 (1%)"] = (income * 0.01, "★레벨링 국면: income 1%와 동가치(병렬진행). 만렙 후 0")

    return income, avg, dist, V


def main():
    ap = argparse.ArgumentParser()
    skill = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ap.add_argument("--snapshot", default=None)
    ap.add_argument("--casts", type=int, default=DEFAULT_CASTS)
    ap.add_argument("--quality", type=int, default=DEFAULT_QUALITY)
    ap.add_argument("--crit-rate", type=float, default=DEFAULT_CRIT_RATE, help="기준 크리율(0~1), 크리배율 가치가 비례")
    ap.add_argument("--crit-dmg", type=int, default=DEFAULT_CRIT_DMG, help="기준 크리배율(1~8), 크리확률 가치가 비례")
    args = ap.parse_args()

    snap_dir = os.path.join(skill, "audits", "snapshots")
    if args.snapshot is None:
        snaps = sorted(f for f in os.listdir(snap_dir) if f.endswith(".raw.json") and "pending" not in f)
        args.snapshot = os.path.join(snap_dir, snaps[-1])
    elif not os.path.exists(args.snapshot):
        args.snapshot = os.path.join(snap_dir, args.snapshot)

    snap = load_snapshot(args.snapshot)
    income, avg, dist, V = compute(snap, args.casts, args.quality, args.crit_rate, args.crit_dmg)

    print(f"기준: {args.casts}캐스트/h, 품질{args.quality}, 크리율{int(args.crit_rate*100)}%, 크리배율{args.crit_dmg}")
    print(f"무버프 수입 = {income:,.0f}원/h (평균 캐치 {avg:,.1f}원)\n")
    anchor = V["판매보너스 (1%)"][0]
    print(f"{'스탯':<15}{'원/h/단위':>9}{'정규화':>7}{'상한':>6}{'최대기여원/h':>12}{'최대정규화':>10}   근거")
    print("─" * 110)
    # 정렬: 최대기여(실제 천장 영향) 기준
    def maxcontrib(name, won):
        return won * MAX_MAGNITUDE.get(name, 1)
    rows = sorted(V.items(), key=lambda kv: -maxcontrib(kv[0], kv[1][0]))
    out = {}
    for name, (won, why) in rows:
        norm = won / anchor if anchor else 0
        mag = MAX_MAGNITUDE.get(name, 1)
        mc = won * mag
        mcnorm = mc / (anchor * MAX_MAGNITUDE["판매보너스 (1%)"]) if anchor else 0
        print(f"{name:<15}{won:>9,.0f}{norm:>7.2f}{mag:>6}{mc:>12,.0f}{mcnorm:>10.2f}   {why}")
        out[name] = {"won_per_unit": round(won, 1), "normalized_per_unit": round(norm, 3),
                     "max_magnitude": mag, "max_contribution_won": round(mc), "basis": why}

    # JSON 출력(스냅샷 derived 병합용)
    result = {"income_per_hour": round(income), "avg_catch": round(avg, 1),
              "casts": args.casts, "quality": args.quality,
              "crit_rate": args.crit_rate, "crit_dmg": args.crit_dmg, "anchor_won": round(anchor, 1),
              "stat_values": out}
    print("\n--- JSON ---")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
