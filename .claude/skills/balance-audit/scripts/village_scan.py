#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
village_scan.py — 마을 하나의 «밸런싱 착수 진단»을 한 번에 뽑는다 (2026-08-27 신설).

스폰마을을 손보며 매번 손으로 재던 것들이다. 사막·상단·왕도를 같은 방식으로 채우려면
착수 전에 **이 여섯 가지**를 알아야 한다:

  1. 라인 커버리지 — (카테고리 × 등급) 칸마다 어떤 라인이 있고 **무엇이 비었나**
     ★스폰마을은 작살에 «채집형»이 아예 없었다. 칸이 비면 그 등급에서 그 플레이가 불가능하다.
  2. 동레벨 성능 산포 — 25% 초과는 스탯 사다리 결함(재료로 덮지 말 것)
  3. κ 단조증가 — 상대성능 기준. 역전이면 상위 등급이 «더 싼» 것이다
  4. 죽은 스탯 — 공격속도(항상 0) · 돌진쿨감 < 45(문턱 미달)
  5. 중간재 바닥 — 재료를 전부 1개로 줄여도 목표보다 비싼 종
  6. 모델 커버리지 — 가치 모델이 값을 모르는 스탯을 가진 종

사용:
    python3 village_scan.py 사막마을
    python3 village_scan.py 상단마을 왕도 --cat 작살
"""
import argparse, collections, importlib.util, os, sys
import statistics as st

HERE = os.path.dirname(os.path.abspath(__file__))


def _load(name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, name + ".py"))
    m = importlib.util.module_from_spec(spec)
    sv, sys.argv = sys.argv, [name]
    spec.loader.exec_module(m)
    sys.argv = sv
    return m


CC = _load("cast_cost")

#: 라인 판정 — 그 아이템에서 «가장 두드러진» 스탯으로 라벨을 붙인다.
#  ★정확한 분류기가 아니다. «칸이 비었는지»를 눈으로 보려는 용도다.
#  등급 기반 스탯(공격력·수중호흡·수영속도·난이도)은 라벨 후보에서 뺀다 — 전 종에 깔려 있어
#  라벨이 전부 그걸로 수렴한다(초판이 그래서 «전부 숙련형»으로 나왔다).
#  ★2026-08-27 정정. 초판은 난이도·크기를 «기반»이라고 고정 제외했는데 그게 오진의 원인이었다:
#    난이도는 숙련 라인의 **메인 스탯**이라 빼면 숙련이 구조적으로 라벨링될 수 없다
#    (사막마을 B 에 「숙련 없음」이 나왔지만 모래·사막개척 낚싯대가 도망감소 6 짜리 숙련형이었다).
#  진짜 기반은 마을마다 다르다 — 사막·상단·왕도는 «난이도 2~5 · 등급업 3 · 행운 4»가 거의 전
#  종에 공통이고 스폰마을엔 그런 공통분이 없다. 그래서 **고정 목록이 아니라 그룹에서 실측**한다:
#  (출처, 카테고리, 등급) 안에서 각 스탯의 **p25**(없으면 0)를 기반으로 보고 그만큼 뺀 뒤 라벨한다.
#  ★고정 제외 목록은 **폐기했다**(BASE_STATS·SLOT_MAIN). 기반 차감(p25)이 같은 일을 하는데
#    고정 목록은 라인 메인까지 지워 버린다 — 실제로 두 번 오진했다:
#      · 난이도를 제외 → 사막마을 B 에 「숙련 없음」 (모래·사막개척 낚싯대가 숙련형이었다)
#      · 공격력을 제외 → 「관통 없음」 (사막칼날 작살 공5 가 관통형이었다)
#      · SLOT_MAIN 으로 릴의 경험치를 제외 → 사막 릴(경험치 55, 기반 30)이 «깡스탯» 으로 잡혔다
BASE_STATS = set()
#: 스탯 → 라인. **전 스탯을 매핑한다** — 제외는 기반 차감이 담당한다.
LINE_OF = {
    "난이도": "숙련", "도망감소": "숙련",
    "크리확률": "크리", "크리배율": "크리", "크기": "크리",
    "행운": "행운", "등급업": "행운",
    "판매보너스": "상인", "더블찬스": "상인", "트리플찬스": "상인",
    "경험치": "성장",
    "재료확률": "채집",
    "공격력": "관통",                      # 작살 — 등급 게이트라 초과분이 곧 관통형이다
    "수중호흡": "잠수", "호흡시간": "잠수",
    "수영속도": "기동", "돌진쿨감": "기동",
    "야간투시": "심해",
}
#: 슬롯 «주스탯» — 그 칸의 전 아이템에 깔려 있으므로 라벨 후보에서 뺀다.
#  ★안 빼면 릴이 전부 «성장», 바늘이 전부 «크리»로 나와 라인 구멍이 안 보인다(초판 결함).
SLOT_MAIN = {}
DEAD = {"공격속도": "항상 0원/h", "돌진쿨감": "45 미만은 문턱 미달"}
#: 라벨 가중치 — 초과분을 **가치로** 비교한다. 스탯 단위가 달라서 «크기»로 비교하면 틀린다:
#  사막칼날 작살(공격력 5, 도망감소 17)이 17 > 3 이라 «숙련»으로 잡혔지만 실제로는 관통형이다.
#  값의 출처는 이 스킬의 측정 결과다 — 작살은 harpoon_value(원/h/점, C급 기준), 나머지는
#  stat_value 의 정규화 가치(판매보너스 1% = 1.00). ★정확한 원장이 아니라 **라벨용 대리지표**다.
WEIGHT_ROD = {"난이도": 3.0, "트리플찬스": 2.00, "크리배율": 2.38, "등급업": 2.11,
              "경험치": 1.00, "판매보너스": 1.00, "더블찬스": 1.00, "재료확률": 1.00,
              "크기": 0.59, "크리확률": 0.48, "행운": 0.40, "도망감소": 0.36}
#: 창 전용 스탯은 실측 원/h/점, 공용 스탯은 «판매보너스 1% ≈ 초반 시급의 1%» 로 환산해 붙인다.
#  ★공용 스탯을 빼먹으면 안 된다 — 초판이 그걸 가중 1.0 으로 깔아서 작살 D 6종이 전부
#    «잠수»로 잡혔다(수중호흡 578 vs 판매보너스 1.0). 라벨이 창 전용 스탯으로만 수렴한다.
_SHARED_WON = 840.0     # 초반 시급 84,279 원/h 의 1%
WEIGHT_SPEAR = {"공격력": 1896, "호흡시간": 734, "수중호흡": 578, "수영속도": 195,
                "도망감소": 50, "돌진쿨감": 1, "공격속도": 0, "야간투시": 500,
                **{k: v * _SHARED_WON for k, v in WEIGHT_ROD.items()
                   if k not in ("난이도", "도망감소")}}

#: 카테고리별 «있어야 하는» 라인. 관측된 라벨의 합집합과 비교하면 조합 라벨이 잡음을 만든다
#  (초판이 「관통+크리 없음」 같은 걸 뱉었다) — **고정 목록**과 비교해야 구멍이 읽힌다.
CANON = {
    "낚싯대": ["숙련", "크리", "행운", "상인", "성장", "채집"],
    #  ★기동·깡스탯을 뺐다(2026-08-27). 가치상 성립하지 않는 라인이다:
    #    수영속도 195원/h/점 · 돌진쿨감 ~1 인데 경험치는 840 이라, 수영속도 40점(7,800원)이
    #    경험치 10점(8,400원)에 진다. 그래서 «기동형»을 만들어도 라벨이 성장/잠수로 잡힌다
    #    (왕도 전령 작살 = 수영속도 48·돌진쿨감 50·경험치 18 → 성장으로 잡혔다).
    #    깡스탯도 마찬가지 — 창 전용 스탯만 높이면 수중호흡 초과분이 커서 «잠수»가 된다.
    #    둘은 «빌드»가 아니라 «부수 특성»이다. 살리려면 스탯 가치를 먼저 올려야 한다.
    "작살":   ["잠수", "관통", "크리", "상인", "성장", "채집"],
    "릴": ["숙련", "크리", "행운", "상인", "성장", "채집"],
    "줄": ["숙련", "크리", "행운", "상인", "성장", "채집"],
    "바늘": ["숙련", "크리", "행운", "상인", "성장", "채집"],
    "찌": ["숙련", "크리", "행운", "상인", "성장", "채집"],
    "미끼": ["숙련", "크리", "행운", "상인", "성장", "채집"],
}


def group_base(arr):
    """(출처, 카테고리, 등급) 그룹의 «공통 기반» = 스탯별 p25 (없는 종은 0으로 센다).

    ★마을마다 기반이 다르다. 이걸 안 빼면 공통분이 라인 라벨을 먹는다 — 사막·상단·왕도는
      전 종에 «등급업 3 · 행운 4» 가 깔려 있어서 초판이 「행운×4」로 오진했다.
    """
    base = {}
    keys = {k for r in arr for k, v in r["stats"].items() if isinstance(v, (int, float))}
    for k in keys:
        vals = sorted(float(r["stats"].get(k, 0) or 0) for r in arr)
        base[k] = vals[max(0, int(len(vals) * 0.25) - (1 if len(vals) % 4 == 0 else 0))] \
            if vals else 0.0
    return base


def line_label(stats, cat, base=None):
    skip = SLOT_MAIN.get(cat, set())
    base = base or {}
    cand = {k: v - base.get(k, 0) for k, v in stats.items()
            if k in LINE_OF and k not in skip and isinstance(v, (int, float))
            and v - base.get(k, 0) > 0}
    if not cand:
        return "깡스탯"
    # 같은 라인 스탯끼리 합산 → 최대 라인
    W = WEIGHT_SPEAR if cat == "작살" else WEIGHT_ROD
    agg = collections.Counter()
    for k, v in cand.items():
        agg[LINE_OF[k]] += v * W.get(k, 1.0)
    # ★조합 라벨을 만들지 않는다 — 최상위 하나만. 조합을 만들면 CANON 비교가 잡음이 된다.
    return agg.most_common(1)[0][0]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src", nargs="*", default=[],
                    help="비우면 **전 마을**(등급 전체 커버리지). 마을을 대면 그 마을만.")
    ap.add_argument("--cat", default=None)
    a = ap.parse_args()

    D, K, rows, cph = CC.build_rows()
    srcs = tuple(a.src)
    # ★라인 커버리지는 «마을»이 아니라 «등급»으로 봐야 한다 (2026-08-27 정정).
    #   마을은 «어디서 파나»일 뿐이고 플레이어는 앞 마을 상점을 계속 쓴다. 마을별로 쪼개면
    #   릴 B 가 스폰 3종 + 사막 3종 = 6종인데 «3종뿐이라 라인이 빈다»고 오진한다.
    #   기본은 전 마을 합집합, 마을을 명시하면 그 마을만 본다.
    pool = [r for r in rows if (not srcs or r["src"] in srcs)
            and r["grade"] not in CC.EXEMPT_GRADES
            and r["src"] not in ("캐시", "개발자", "잠수상점")]
    if a.cat:
        pool = [r for r in pool if r["cat"] == a.cat]
    if not pool:
        sys.exit(f"대상 없음 — 출처 {srcs}. parts.json 의 7번째 필드를 확인할 것.")
    print(f"=== {' + '.join(srcs) if srcs else '전 마을(등급 전체 커버리지)'} · {len(pool)}종 ===")

    # ── 1. 라인 커버리지 ───────────────────────────────────────────────
    print(f"\n[1] 라인 커버리지 (칸이 비면 그 등급에서 그 플레이가 불가능하다)")
    grid = collections.defaultdict(lambda: collections.defaultdict(list))
    bases = {}
    for (cat, g), arr in _by(pool, lambda r: (r["cat"], r["grade"])).items():
        b = group_base(arr)
        bases[(cat, g)] = b
        for r in arr:
            grid[cat][g].append((line_label(r["stats"], cat, b), r["name"]))
    for cat in ["낚싯대", "작살", "릴", "줄", "바늘", "찌", "미끼"]:
        if cat not in grid:
            continue
        allines = CANON.get(cat, sorted({l for g in grid[cat].values() for l, _ in g}))
        print(f"  {cat}")
        for g in CC.GRADE_ORDER:
            if g not in grid[cat]:
                continue
            have = collections.Counter(l for l, _ in grid[cat][g])
            miss = [l for l in allines if l not in have]
            b = {k: v for k, v in bases[(cat, g)].items() if v}
            src_mix = collections.Counter(
                r["src"] for r in pool if r["cat"] == cat and r["grade"] == g)
            print(f"    {g} ({len(grid[cat][g])}종 · " +
                  "/".join(f"{k.replace('마을','').replace('히든-','+')} {v}"
                           for k, v in src_mix.most_common()) + ") " + ", ".join(
                f"{l}×{c}" if c > 1 else l for l, c in sorted(have.items()))
                  + (f"   ★없음: {', '.join(miss)}" if miss else ""))
            if b:
                print(f"        기반(p25): " + ", ".join(f"{k}{v:g}" for k, v in sorted(b.items())))

    # ── 2·3. 산포와 κ ──────────────────────────────────────────────────
    print(f"\n[2] 동레벨 성능 산포 (>25% = 스탯 사다리 결함)")
    bad = 0
    for (cat, lv), arr in sorted(collections.defaultdict(list, {
            k: v for k, v in _by(pool, lambda r: (r["cat"], r["lv"])).items()
            if len(v) > 1}).items()):
        p = [r["eff_net"] for r in arr if r["eff_net"] > 0]
        if len(p) < 2:
            continue
        sp = max(p) / min(p) - 1
        if sp > 0.25:
            bad += 1
            print(f"  🔴 {cat} Lv{lv} +{sp*100:.0f}%  " +
                  ", ".join(f"{r['name']} {r['eff_net']:,.0f}" for r in
                            sorted(arr, key=lambda r: -r["eff_net"])))
    print("  🟢 전부 25% 이내" if not bad else f"  → {bad}건")

    print(f"\n[3] κ 등급 사다리 (상대성능 1%p 당 캐스트 · 단조증가여야 한다)")
    cur, des = CC.kappa_table([r for r in pool if r["craftable"]])
    for cat in ["낚싯대", "작살", "릴", "줄", "바늘", "찌", "미끼"]:
        gs = [g for g in CC.GRADE_ORDER if (cat, g) in cur]
        if not gs:
            continue
        vals = [cur[(cat, g)] for g in gs]
        inv = [f"{a_}→{b_}" for a_, b_, x, y in zip(gs, gs[1:], vals, vals[1:]) if y < x * 0.98]
        print(f"  {cat:<5}" + "  ".join(f"{g} {v:>5.1f}" for g, v in zip(gs, vals))
              + (f"   🔴 역전 {', '.join(inv)}" if inv else "   🟢"))

    # ── 4. 죽은 스탯 ───────────────────────────────────────────────────
    print(f"\n[4] 죽은 스탯")
    hits = collections.defaultdict(list)
    for r in pool:
        for k, why in DEAD.items():
            v = r["stats"].get(k)
            if not isinstance(v, (int, float)) or v <= 0:
                continue
            if k == "돌진쿨감" and v >= 45:
                continue
            hits[k].append(f"{r['name']}({v:g})")
    for k, why in DEAD.items():
        if hits[k]:
            print(f"  🔴 {k} — {why} · {len(hits[k])}종: " + ", ".join(hits[k][:8]))
        else:
            print(f"  🟢 {k} 없음")

    # ── 5. 중간재 바닥 ─────────────────────────────────────────────────
    print(f"\n[5] 중간재 바닥 (재료를 전부 1개로 줄여도 목표보다 비싼 종)")
    tg, clamps, _ = CC.targets([r for r in pool if r["craftable"]], des)
    fl = []
    for n, v in tg.items():
        rec = D.recby.get(n)
        if not rec:
            continue
        h, _, _, _ = D.gate(D.expand([dict(i, qty=1) for i in rec["ingredients"]]))
        if h * cph > v["target"] * 1.02:
            fl.append((n, v["target"], h * cph))
    for n, t, f in sorted(fl, key=lambda x: -x[2] / x[1])[:10]:
        print(f"  🔴 {n:<16} 목표 {t:>6,.0f} < 바닥 {f:>6,.0f} (×{f/t:.2f})")
    print("  🟢 없음" if not fl else f"  → {len(fl)}종. 중간재 레시피를 낮춰야 풀린다.")

    # ── 6. 모델 커버리지 ───────────────────────────────────────────────
    print(f"\n[6] 모델 커버리지 (가치 모델이 값을 모르는 스탯)")
    unk = collections.Counter()
    for r in pool:
        for k in r.get("unknown", []):
            unk[k] += 1
    print("  🟢 전부 모델 안" if not unk else "  🔴 " +
          ", ".join(f"{k}×{c}종" for k, c in unk.most_common()))


def _by(rows, key):
    d = collections.defaultdict(list)
    for r in rows:
        d[key(r)].append(r)
    return d


if __name__ == "__main__":
    main()
