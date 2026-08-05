#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gear_payback.py — H절: 장비 스탯가치 vs 가격 (회수시간) 재판정.

★2026-08-05 신설. 2026-08-05 리프라이싱(장비 ×20~46)과 stat_value.py 교체(피티 MC + 실측
220 포획/h)가 동시에 일어났으므로, 회수시간을 처음부터 다시 계산해야 한다.

회수시간 = 가격 / 부품의 income 스탯가치(원/h)
  · 스탯가치는 등급이 쓰이는 구간의 앵커로 환산한다(D→초반, C·B→중반, A·S→종결).
    같은 스탯 1점이 구간마다 4배 차이나므로 단일 앵커로 비교하면 고등급이 부당하게 나쁘게 나온다.
  · 경험치는 income이 아니라 성장 트랙이라 **별도 표기**(레벨링 국면 한정 가치).
  · 낚싯대·작살은 **내구도가 없다**(EquipmentManager.SLOTS 제외) — 유지비 0 프리미엄이 있으므로
    부품과 순수 회수시간으로 동률 비교하지 말 것.

경보선(metrics.md H절):
  🟡 등급이 높은데 회수시간이 더 김 = 등급-가치 역전
  🟡 같은 슬롯 내 회수시간 편차 > 3배
"""
import argparse, collections, importlib.util, json, os, statistics as st, sys

HERE = os.path.dirname(os.path.abspath(__file__))
BS = ("/Users/user/Library/Application Support/feather/player-server/servers/"
      "07de2d81-991a-47e2-b62d-06c0d1b5150a/plugins/BlockShip")


def _load(name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, name + ".py"))
    m = importlib.util.module_from_spec(spec)
    saved, sys.argv = sys.argv, [name]
    spec.loader.exec_module(m)
    sys.argv = saved
    return m


SV = _load("stat_value")

GRADE_STAGE = {"E": "초반", "D": "초반", "C": "중반", "B": "중반", "A": "종결", "S": "종결", "G": "종결"}
# 스탯 이름(parts.json) → stat_value 키
STAT_KEY = {
    "판매보너스": "판매보너스 (1%)", "더블찬스": "더블찬스 (1%)", "트리플찬스": "트리플찬스 (1%)",
    "등급업": "등급업 (1%)", "크기": "크기 (1%)", "행운": "행운 (1점)",
    "도망감소": "도주감소 (1%)", "도주감소": "도주감소 (1%)",
    "크리확률": "크리확률 (1%)", "크리배율": "크리배율 (1점)", "난이도": "난이도 (1점)",
}
GROWTH_KEY = {"경험치": "경험치 (1%)"}
# income에도 성장에도 안 들어가는 것들 (별도 효용)
OTHER = {"내구보존", "등급특화", "수중호흡", "수영속도", "공격력", "공격속도", "돌진쿨감", "은신"}


def parse_stats(raw):
    out = {}
    for pair in raw.split(","):
        kv = pair.split(":", 2)
        if len(kv) != 2:
            continue
        k = kv[0].strip()
        try:
            out[k] = float(kv[1].strip())
        except ValueError:
            out[k] = kv[1].strip()
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--parts", default=os.path.join(BS, "parts.json"))
    args = ap.parse_args()

    vals = {}
    for stage in SV.STAGES:
        r = SV.compute(stage)
        vals[stage] = {k: v[0] for k, v in r["V"].items()}
        print(f"[{stage}] 수입 {r['income']:,.0f}원/h")

    parts = json.load(open(args.parts, encoding="utf-8"))["parts"]
    rows = []
    for cat, items in parts.items():
        for name, spec in items.items():
            f = spec.split("|")
            grade, price = f[1], int(f[2])
            stats = parse_stats(f[4]) if len(f) > 4 else {}
            lv = int(f[5]) if len(f) > 5 and f[5].lstrip("-").isdigit() else 1
            stage = GRADE_STAGE.get(grade, "중반")
            inc_val = growth_val = 0.0
            unknown = []
            for k, v in stats.items():
                if not isinstance(v, (int, float)):
                    continue
                if k in STAT_KEY:
                    inc_val += v * vals[stage][STAT_KEY[k]]
                elif k in GROWTH_KEY:
                    growth_val += v * vals[stage][GROWTH_KEY[k]]
                elif k not in OTHER:
                    unknown.append(k)
            # ★2026-08-05 릴 재배정 — 릴의 신규 주스탯은 경험치(성장)다. 순수 income 회수시간으로
            #   재면 경험치는 GROWTH_KEY라 0으로 잡혀 "철제 릴"류가 전부 최악으로 나온다(실측:
            #   숙련 릴 0.52h ↔ 철제 릴 19.83h, 릴C<D 역전까지). 미끼가 행운 자리를 내주고도 이미
            #   inc+growth 결합으로 다루듯, 릴도 같은 원칙 적용 — 경험치가 릴의 실제 설계 가치다.
            eff = (inc_val + growth_val) if cat == "릴" else inc_val
            payback = price / eff if eff > 0 else float("inf")
            rows.append(dict(cat=cat, name=name, grade=grade, price=price, lv=lv, stage=stage,
                             inc=inc_val, growth=growth_val, payback=payback, unknown=unknown))

    unk = collections.Counter(u for r in rows for u in r["unknown"])
    if unk:
        print("\n★미인식 스탯:", dict(unk))

    # ── 축 분리 ───────────────────────────────────────────────────────────
    # ★2026-08-05: 세 카테고리는 회수시간 모델이 서로 다르다. 한 표에 섞으면 오판한다.
    #   ① 장착 부품(릴·줄·바늘·찌) + 낚싯대 → 자본재. 회수시간 = 가격 ÷ 스탯가치.
    #   ② 미끼 → **소모품**. 1개가 내구만큼만 버티므로 판정은 회수시간이 아니라
    #      "유지비/h = (포획/h ÷ 내구) × 가격" 대비 스탯가치/h의 순이득.
    #   ③ 작살 → 스탯(수중호흡·수영속도·공격력·돌진쿨감)이 낚시 income에 직결되지 않는다.
    #      작살의 실제 수익원은 스탯이 아니라 **처리량**(사이클 12.9s vs 16.2s)과
    #      **quality 70~100 고정**이다. 그래서 회수시간 판정 대상이 아니고 별도로 다룬다.
    BAIT_DUR = {"E": 40, "D": 70, "C": 130, "B": 220, "A": 340}
    bait = [r for r in rows if r["cat"] == "미끼"]
    spear = [r for r in rows if r["cat"] == "작살"]
    rows = [r for r in rows if r["cat"] not in ("미끼", "작살")]
    agg_all = collections.defaultdict(list)

    order = {"E": 0, "D": 1, "C": 2, "B": 3, "A": 4, "S": 5, "G": 6}
    print("\n" + "=" * 100)
    print("① 자본재 (낚싯대·릴·줄·바늘·찌) — 회수시간 = 가격 ÷ income 스탯가치")
    print("=" * 100)
    print(f"{'카테고리':<8}{'등급':<4}{'n':>4}{'평균가격':>13}{'평균 income':>13}{'평균 회수h':>12}{'중위 회수h':>12}")
    print("─" * 100)
    agg = collections.defaultdict(list)
    for r in rows:
        agg[(r["cat"], r["grade"])].append(r)
    prev = {}
    warn = []
    for (cat, g), arr in sorted(agg.items(), key=lambda kv: (kv[0][0], order.get(kv[0][1], 9))):
        pb = [x["payback"] for x in arr if x["payback"] < float("inf")]
        if not pb:
            print(f"{cat:<8}{g:<4}{len(arr):>4}{'':>13}{'income 스탯 없음':>13}")
            continue
        mean_pb, med_pb = sum(pb) / len(pb), st.median(pb)
        print(f"{cat:<8}{g:<4}{len(arr):>4}{sum(x['price'] for x in arr)/len(arr):>13,.0f}"
              f"{sum(x['inc'] for x in arr)/len(arr):>13,.0f}{mean_pb:>12.2f}{med_pb:>12.2f}")
        if cat in prev and med_pb < prev[cat][1] * 0.999:
            warn.append(f"🟡 등급-가치 역전: {cat} {g}({med_pb:.2f}h) < {prev[cat][0]}({prev[cat][1]:.2f}h)")
        prev[cat] = (g, med_pb)
        spread = max(pb) / min(pb) if min(pb) > 0 else 0
        if spread > 3:
            worst = max(arr, key=lambda x: x["payback"]); best = min(arr, key=lambda x: x["payback"])
            warn.append(f"🟡 {cat} {g} 슬롯내 편차 {spread:.1f}배 "
                        f"({best['name']} {best['payback']:.2f}h ↔ {worst['name']} {worst['payback']:.2f}h)")

    print("\n" + "=" * 100)
    print("회수시간 최악 12종 (가격 대비 income 가치가 낮은 장비)")
    print("=" * 100)
    finite = [r for r in rows if r["payback"] < float("inf") and r["price"] > 0]
    for r in sorted(finite, key=lambda x: -x["payback"])[:12]:
        print(f"  {r['cat']:<6}{r['grade']:<3}{r['name']:<20}{r['price']:>11,}원 "
              f"income {r['inc']:>9,.0f}원/h → {r['payback']:>7.2f}h  (성장 {r['growth']:,.0f}원/h)")
    print("\n회수시간 최고 8종 (가성비 상위)")
    for r in sorted(finite, key=lambda x: x["payback"])[:8]:
        print(f"  {r['cat']:<6}{r['grade']:<3}{r['name']:<20}{r['price']:>11,}원 "
              f"income {r['inc']:>9,.0f}원/h → {r['payback']:>7.2f}h")

    noinc = [r for r in rows if r["inc"] <= 0 and r["price"] > 0]
    if noinc:
        print(f"\n★income 스탯이 0인 유료 장비 {len(noinc)}종 (성장/기타 효용 전용):")
        for r in noinc[:10]:
            print(f"  {r['cat']:<6}{r['grade']:<3}{r['name']:<20}{r['price']:>11,}원 "
                  f"성장 {r['growth']:,.0f}원/h")

    # ── ② 미끼 (소모품) ───────────────────────────────────────────────────
    print("\n" + "=" * 100)
    print("② 미끼 (소모품) — 유지비/h vs 스탯가치/h 순이득")
    print("=" * 100)
    print(f"{'등급':<4}{'n':>3}{'평균가격':>10}{'내구':>6}{'유지비/h':>11}{'스탯가치/h':>12}"
          f"{'순이득/h':>12}{'가치/유지비':>11}")
    print("─" * 100)
    bagg = collections.defaultdict(list)
    for r in bait:
        bagg[r["grade"]].append(r)
    for g in sorted(bagg, key=lambda x: order.get(x, 9)):
        arr = bagg[g]
        dur = BAIT_DUR.get(g, 100)
        avg_p = sum(x["price"] for x in arr) / len(arr)
        upkeep = (SV.CATCH_PER_HOUR / dur) * avg_p
        # 미끼는 경험치 특화라 income+성장 둘 다 본다
        avg_inc = sum(x["inc"] for x in arr) / len(arr)
        avg_gro = sum(x["growth"] for x in arr) / len(arr)
        total = avg_inc + avg_gro
        print(f"{g:<4}{len(arr):>3}{avg_p:>10,.0f}{dur:>6}{upkeep:>11,.0f}{total:>12,.0f}"
              f"{total-upkeep:>12,.0f}{(total/upkeep if upkeep else 0):>11.1f}x")
    print("  ※미끼 주스탯은 경험치라 income가치는 낮고 성장가치가 대부분 — 둘을 합산해 표기했다.")

    # ── ③ 작살 (스탯이 income에 직결되지 않음) ───────────────────────────
    print("\n" + "=" * 100)
    print("③ 작살 — 회수시간 판정 대상 아님 (수익원이 스탯이 아니라 처리량·quality)")
    print("=" * 100)
    HARP_CATCH, HARP_Q = 270, 84.0     # 실측: 사이클 12.9s / quality 70~100 고정 평균
    rod_m = SV.size_mult(SV.SIZE_SCORE)
    harp_m = SV.size_mult(HARP_Q)
    thr = HARP_CATCH / SV.CATCH_PER_HOUR
    qual = harp_m / rod_m
    print(f"  처리량 우위: {HARP_CATCH}/{SV.CATCH_PER_HOUR} 포획/h = ×{thr:.3f}")
    print(f"  quality 우위: {HARP_Q}(고정 70~100) vs {SV.SIZE_SCORE}(실측) → 가격배율 "
          f"{harp_m:.3f}/{rod_m:.3f} = ×{qual:.3f}")
    print(f"  ⇒ 같은 지역·같은 스탯이라도 작살이 낚싯대보다 income **×{thr*qual:.3f}"
          f" (+{(thr*qual-1)*100:.0f}%)**")
    for stage, inc in [(s, SV.income_of(SV.grade_dist(*SV.STAGES[s]))[0]) for s in SV.STAGES]:
        print(f"    {stage}: 낚싯대 {inc:,.0f}원/h → 작살 {inc*thr*qual:,.0f}원/h "
              f"(초과 {inc*(thr*qual-1):,.0f}원/h)")
    print(f"  · 게다가 작살은 내구·미끼 소모가 없어 **한계비용 0**(EquipmentManager.SLOTS 제외).")
    print(f"  · 즉 작살 {len(spear)}종의 가격이 낚싯대와 같은 밴드인 것은 **작살 저평가**다.")
    print(f"  · 판정: 가격을 올리는 게 아니라 08-03 권고(quality를 실제 크기 백분위로, 유지비 도입)로")
    print(f"    프리미엄 자체를 없애는 쪽이 맞다 — 안 그러면 낚싯대를 쓸 이유가 사라진다.")

    if warn:
        print("\n" + "=" * 100)
        print("경보")
        print("=" * 100)
        for w in warn:
            print("  " + w)
    else:
        print("\n🟢 등급-가치 역전 없음 · 슬롯내 편차 3배 초과 없음")


if __name__ == "__main__":
    main()
