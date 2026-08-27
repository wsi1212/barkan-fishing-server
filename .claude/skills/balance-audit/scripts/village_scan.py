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
BASE_STATS = {"공격력", "수중호흡", "수영속도", "난이도", "크기"}
LINE_OF = {
    "재료확률": "채집", "판매보너스": "상인",
    "크리확률": "크리", "크리배율": "크리", "경험치": "성장",
    "호흡시간": "잠수", "더블찬스": "잠수", "트리플찬스": "잠수",
    "돌진쿨감": "기동", "수영속도": "기동", "도망감소": "숙련",
    "등급업": "행운", "행운": "행운",
}
#: 슬롯 «주스탯» — 그 칸의 전 아이템에 깔려 있으므로 라벨 후보에서 뺀다.
#  ★안 빼면 릴이 전부 «성장», 바늘이 전부 «크리»로 나와 라인 구멍이 안 보인다(초판 결함).
SLOT_MAIN = {"릴": {"경험치"}, "줄": {"도망감소"}, "바늘": {"크리확률", "크리배율"},
             "찌": {"등급업"}, "미끼": {"행운"}, "낚싯대": set(),
             # 작살은 수영속도가 전 종 기반이라 라벨 후보에서 뺀다(안 빼면 전부 «기동»)
             "작살": {"수영속도"}}
DEAD = {"공격속도": "항상 0원/h", "돌진쿨감": "45 미만은 문턱 미달"}
#: 카테고리별 «있어야 하는» 라인. 관측된 라벨의 합집합과 비교하면 조합 라벨이 잡음을 만든다
#  (초판이 「관통+크리 없음」 같은 걸 뱉었다) — **고정 목록**과 비교해야 구멍이 읽힌다.
CANON = {
    "낚싯대": ["숙련", "크리", "행운", "상인", "성장", "채집"],
    "작살":   ["잠수", "관통", "크리", "상인", "기동", "채집", "깡스탯"],
    "릴": ["숙련", "크리", "행운", "상인", "성장", "채집"],
    "줄": ["숙련", "크리", "행운", "상인", "성장", "채집"],
    "바늘": ["숙련", "크리", "행운", "상인", "성장", "채집"],
    "찌": ["숙련", "크리", "행운", "상인", "성장", "채집"],
    "미끼": ["숙련", "크리", "행운", "상인", "성장", "채집"],
}


def line_label(stats, cat):
    skip = SLOT_MAIN.get(cat, set())
    cand = {k: v for k, v in stats.items()
            if k in LINE_OF and k not in skip and isinstance(v, (int, float)) and v > 0}
    if not cand:
        return "깡스탯"
    # 같은 라인 스탯끼리 합산 → 최대 라인
    agg = collections.Counter()
    for k, v in cand.items():
        agg[LINE_OF[k]] += v
    # ★조합 라벨을 만들지 않는다 — 최상위 하나만. 조합을 만들면 CANON 비교가 잡음이 된다.
    return agg.most_common(1)[0][0]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src", nargs="+")
    ap.add_argument("--cat", default=None)
    a = ap.parse_args()

    D, K, rows, cph = CC.build_rows()
    srcs = tuple(a.src)
    pool = [r for r in rows if r["src"] in srcs and r["grade"] not in CC.EXEMPT_GRADES]
    if a.cat:
        pool = [r for r in pool if r["cat"] == a.cat]
    if not pool:
        sys.exit(f"대상 없음 — 출처 {srcs}. parts.json 의 7번째 필드를 확인할 것.")
    print(f"=== {' + '.join(srcs)} · {len(pool)}종 ===")

    # ── 1. 라인 커버리지 ───────────────────────────────────────────────
    print(f"\n[1] 라인 커버리지 (칸이 비면 그 등급에서 그 플레이가 불가능하다)")
    grid = collections.defaultdict(lambda: collections.defaultdict(list))
    for r in pool:
        grid[r["cat"]][r["grade"]].append((line_label(r["stats"], r["cat"]), r["name"]))
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
            print(f"    {g} ({len(grid[cat][g])}종) " + ", ".join(
                f"{l}×{c}" if c > 1 else l for l, c in sorted(have.items()))
                  + (f"   ★없음: {', '.join(miss)}" if miss else ""))

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
