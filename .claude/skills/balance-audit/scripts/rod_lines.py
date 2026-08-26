#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
rod_lines.py — 스폰마을 낚싯대 «라인 설계»의 단일 권위 (2026-08-27).

`rod_rebalance.py` 를 대체한다. 구 스크립트는 «회수시간을 등급 중위에 맞추도록
부스탯을 스케일»하는 것만 했는데, 그 접근은 두 번 실패했다:
  ① 내구보존이 숙련형의 유일한 조정축이라 스케일러가 행운에 전부 쏟아부었다.
  ② 난이도를 «단가 × 점수»로 세는 바람에 고난이도(6~10)를 통째로 과대평가했다.
둘 다 원인이 같다 — **난이도는 선형이 아니고, 라인 정체성은 스칼라가 아니다.**

이 스크립트는 순서를 뒤집는다:
    1. 라인마다 «메인 + 부스탯 1~2» 를 사람이 고정한다(LINES).
    2. 난이도는 «구조 목표»에서 역산한다(순간이동 문턱, teleport_table()).
    3. 남은 자유도(부스탯 크기 · 돈가격)만 회수시간에 맞춘다.

★난이도가 왜 특별한가
    net = rodBonus − fishDifficulty(등급) − sizeDifficulty(cm)
    zoneWidth = 8 + floor(net/2)  → 1 미만이면 존이 «순간이동»(overflowDiff>0)
고등급 매출 비중이 초반 A 29% · 중반 S 28.6% 라 난이도는 «매출 절반의 문지기»다.
그래서 모든 라인에 깔면 전 라인이 «난이도 낚싯대 + 장식»으로 수렴한다(실측: C
상인형 판매보너스가 6 → 2 로 밀렸다). 숙련형에 몰아주고 나머지는 얕게 깐다.

사용:
    python3 rod_lines.py                # 설계표 + 회수시간 + 순간이동 검증
    python3 rod_lines.py --tune         # 부스탯을 회수시간 목표에 맞춰 재탐색
    python3 rod_lines.py --plan         # patch_*.py 에 붙일 ROD_PLAN 형태로 출력
"""
import argparse, collections, importlib.util, json, os, shutil
import statistics as st
import sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))


def _load(name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    saved, sys.argv = sys.argv, [name]
    spec.loader.exec_module(mod)
    sys.argv = saved
    return mod


MV = _load("material_value")
SV = _load("stat_value")
HV = _load("harpoon_value")
IL = _load("item_ledger")
MEAS = _load("measured")

STAT_ORDER = ["난이도", "도망감소", "크리배율", "등급업", "크리확률", "크기", "경험치",
              "판매보너스", "더블찬스", "트리플찬스", "행운", "재료확률", "등급특화"]

#: 라인 → (메인, 부스탯…). 부스탯은 «1~2개» 가 원칙 — 3개를 넘으면 정체성이 안 읽힌다.
LINES = {
    "숙련":  ("난이도", ["도망감소", "경험치"]),
    "크리":  ("크기", ["크리확률", "크리배율"]),
    "행운":  ("행운", ["등급업"]),
    "상인":  ("판매보너스", ["더블찬스"]),
    "성장":  ("경험치", ["트리플찬스"]),
    "채집":  ("재료확률", ["경험치"]),
}
#: 등급 → 라인별 기본 난이도. 숙련형만 깊고, 채집형은 0(유저 확정), 나머지는 얕게.
DIFF_BY_GRADE = {
    "숙련": {"E": 0, "D": 3, "C": 5, "B": 7},
    "혼합": {"E": 0, "D": 2, "C": 3, "B": 4},
    "기타": {"E": 0, "D": 1, "C": 2, "B": 2},
    "채집": {"E": 0, "D": 0, "C": 0, "B": 0},
}
#: 등급별 회수시간 목표(h). 등급이 오르면 완만하게 길어진다(상위 등급은 «오래 쓰는» 물건).
TARGET = {"E": None, "D": 10.5, "C": 11.0, "B": 12.5}

#: 설계 대상 — 이름: (등급, 라인표시, 부스탯, 등급특화, 돈가격 덮어쓰기|None)
#  ★부스탯 수치는 --tune 산출값이다. 손으로 만지지 말고 --tune 을 다시 돌릴 것.
DESIGN = {
    "나뭇가지":           ("E", "입문", {"행운": 1}, None, None),
    "초보자 낚싯대":       ("E", "입문", {"경험치": 3}, None, None),
    "초보 낚싯대":         ("E", "입문", {"크기": 3, "크리확률": 2}, None, None),
    "튼튼한 막대기":       ("D", "숙련", {"도망감소": 3, "경험치": 2}, None, 35000),
    "참나무 낚싯대":       ("C", "숙련", {"도망감소": 4, "경험치": 2}, None, 112000),
    "전문가 낚싯대":       ("B", "숙련", {"도망감소": 8, "경험치": 4}, None, 130000),
    "낚시견습생의 낚싯대":  ("D", "크리", {"크기": 11, "크리확률": 7}, None, None),
    "낚시꾼의 낚싯대":     ("C", "크리", {"크기": 11, "크리확률": 8}, None, None),
    "예리한 낚싯대":       ("B", "크리", {"크기": 15, "크리확률": 11, "크리배율": 2}, None, None),
    "대나무 막대기":       ("D", "행운", {"행운": 11, "등급업": 3}, None, None),
    "잉어꾼의 낚싯대":     ("C", "행운", {"행운": 13, "등급업": 5}, "C:50", None),
    "숙련자의 낚싯대":     ("B", "행운", {"행운": 17, "등급업": 8}, None, None),
    "장터 낚싯대":         ("D", "상인", {"판매보너스": 8, "더블찬스": 3}, None, None),
    "장사꾼의 낚싯대":     ("C", "상인", {"판매보너스": 6, "더블찬스": 2}, None, None),
    "거래상의 낚싯대":     ("B", "상인", {"판매보너스": 17, "더블찬스": 7}, None, None),
    "수련생 낚싯대":       ("D", "성장", {"경험치": 8, "트리플찬스": 1}, None, None),
    "경험의 낚싯대":       ("C", "성장", {"경험치": 6, "트리플찬스": 1}, None, None),
    "학도의 낚싯대":       ("B", "성장", {"경험치": 17, "트리플찬스": 2}, None, None),
    "다목적 낚싯대":       ("C", "혼합", {"도망감소": 3, "판매보너스": 5, "더블찬스": 2}, None, 84000),
    "겸업 낚싯대":         ("B", "기타", {"등급업": 5, "크리확률": 8, "크기": 14}, None, None),
    "만능 낚싯대":         ("B", "혼합", {"도망감소": 5, "판매보너스": 9, "더블찬스": 4}, None, 145000),
    "채집용 낚싯대":       ("D", "채집", {"재료확률": 10, "경험치": 3}, None, None),
    "수집가의 낚싯대":     ("C", "채집", {"재료확률": 18, "경험치": 5}, None, None),
    "탐사자의 낚싯대":     ("B", "채집", {"재료확률": 28, "경험치": 7}, None, None),
}
#: 라인 표시 → DIFF_BY_GRADE 키. «겸업»(크리+행운)은 난이도가 정체성이 아니라 기타.
DIFF_KEY = {"숙련": "숙련", "채집": "채집", "혼합": "혼합", "입문": "기타"}

#: 숙련형 강화표 난이도 증설 — patch 스크립트의 ENH_DIFF 와 짝. 여기 값이 권위다.
ENH_DIFF = {
    "튼튼한 막대기": {2: 1, 4: 1, 6: 1, 8: 1},
    "참나무 낚싯대": {2: 1, 4: 1, 5: 1, 7: 1, 8: 1, 10: 1},
    "전문가 낚싯대": {3: 1, 5: 1, 7: 1, 9: 1, 11: 1, 13: 1},
}
#: 부스탯 최소값 — 0 이 되면 라인의 부스탯이 사라져 정체성이 깨진다.
MINV = collections.defaultdict(lambda: 1)


def diff_of(name):
    g, line, *_ = DESIGN[name]
    return DIFF_BY_GRADE[DIFF_KEY.get(line, "기타")][g]


def stat_str(name, subs=None):
    g, line, s0, spec, _ = DESIGN[name]
    subs = s0 if subs is None else subs
    d = {}
    dv = diff_of(name)
    if dv:
        d["난이도"] = dv
    for a, b in subs.items():
        if b > 0:
            d[a] = int(b)
    if spec:
        d["등급특화"] = spec
    return ",".join(f"{a}:{d[a]}" for a in STAT_ORDER if a in d)


# ── 순간이동 문턱 (구조 지표 — 모델 캘리브레이션과 무관하게 참) ─────────────
def teleport_frac(rod_bonus, grade="S"):
    """그 등급 어종 중 «존 순간이동»이 걸리는 크기 비율. zoneWidth<1 ⇔ net ≤ −15."""
    fd = {"E": 0, "D": 2, "C": 4, "B": 8, "A": 12, "S": 16, "M": 24, "L": 28, "G": 32}[grade]
    dist = SV.size_difficulty_dist()[grade]
    return sum(w for sd, w in dist.items() if (rod_bonus - fd - sd) <= -15)


def enh_diff(rod, level, enh_table):
    """rod 를 level 까지 강화했을 때 누적 난이도. ENH_DIFF 가 있으면 그 표가 권위."""
    if rod in ENH_DIFF:
        return sum(v for lv, v in ENH_DIFF[rod].items() if lv <= level)
    ent = enh_table.get(rod) or {}
    tot = 0
    for i in range(1, level + 1):
        raw = (ent.get("levels") or {}).get(str(i))
        if raw is None:
            raw = "난이도:1"                       # EnhanceLoader 폴백
        for t in raw.split(","):
            if t.startswith("난이도:"):
                tot += float(t.split(":", 1)[1])
    return tot


# ── 원장 ────────────────────────────────────────────────────────────────
def ledger(subs_by_name=None):
    """DESIGN 을 임시 parts.json 에 써서 item_ledger 로 총비용·순성능·회수를 낸다."""
    P = json.load(open(os.path.join(MV.BS, "parts.json"), encoding="utf-8"))
    for n, (g, line, s0, spec, price) in DESIGN.items():
        f = P["parts"]["낚싯대"][n].split("|")
        if price is not None:
            f[2] = str(price)
        f[4] = stat_str(n, (subs_by_name or {}).get(n))
        P["parts"]["낚싯대"][n] = "|".join(f)
    tmp = tempfile.mkdtemp()
    try:
        for fn in ("materials.json", "recipes.json"):
            shutil.copy(os.path.join(MV.BS, fn), tmp)
        json.dump(P, open(os.path.join(tmp, "parts.json"), "w", encoding="utf-8"),
                  ensure_ascii=False)
        rows = IL.build(MV.Data(bs=tmp), _SV, _INC, _RATIO, _HM)
    finally:
        shutil.rmtree(tmp)
    return {r["name"]: r for r in rows}


def tune(rounds=8):
    """부스탯을 등급별 회수시간 목표에 맞춰 정수 스케일. 난이도·가격은 고정."""
    cur = {n: dict(v[2]) for n, v in DESIGN.items()}
    for _ in range(rounds):
        sel = ledger(cur)
        moved = 0
        for n, (g, line, s0, spec, price) in DESIGN.items():
            tg = TARGET.get(g)
            if tg is None or not cur[n]:
                continue
            r = sel[n]
            if r["eff_net"] <= 0 or r["total"] <= 0:
                continue
            f = (r["total"] / tg) / r["eff_net"]
            f = max(0.55, min(1.8, f))
            if abs(f - 1) < 0.03:
                continue
            new = {a: max(MINV[a], int(round(b * f))) for a, b in cur[n].items()}
            if new != cur[n]:
                cur[n] = new
                moved += 1
        if not moved:
            break
    return cur


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tune", action="store_true", help="부스탯을 회수시간 목표에 재적합")
    ap.add_argument("--plan", action="store_true", help="ROD_PLAN 형태로 출력")
    a = ap.parse_args()

    print(MEAS.banner(_K))
    subs = tune() if a.tune else None
    sel = ledger(subs)

    if a.plan:
        print("\nROD_PLAN = {")
        for n, (g, line, s0, spec, price) in DESIGN.items():
            s = stat_str(n, (subs or {}).get(n))
            print(f'    "{n}":{" " * max(1, 20 - len(n))}("{s}", {price!r}),')
        print("}")
        return

    print(f"\n{'등':<3}{'라인':<7}{'이름':<20}{'돈':>9}{'재료원':>10}{'총비용':>10}"
          f"{'순성능':>9}{'회수h':>7}  스탯")
    byg = collections.defaultdict(list)
    for n, (g, line, s0, spec, price) in DESIGN.items():
        r = sel[n]
        pb = r["payback"]
        if TARGET.get(g) and r["total"] > 0 and pb < 1e6:
            byg[g].append(pb)
        print(f"{g:<3}{line:<7}{n:<20}{r['price']:>9,.0f}{r['mat_won']:>10,.0f}"
              f"{r['total']:>10,.0f}{r['eff_net']:>9,.0f}"
              f"{('∞' if pb >= 1e6 else f'{pb:.1f}'):>7}  {stat_str(n, (subs or {}).get(n))}")
    print()
    for g in "DCB":
        if g in byg:
            print(f"  {g}: 중위 {st.median(byg[g]):.1f}h · {min(byg[g]):.1f}~{max(byg[g]):.1f}h"
                  f" · 편차 {max(byg[g]) / min(byg[g]):.2f}배")

    enh = json.load(open(os.path.join(MV.BS, "enhance.json"), encoding="utf-8"))["table"]
    print("\n=== S급 순간이동 검증 (구조 지표 — zoneWidth<1) ===")
    for rod, lab, lvl in [("튼튼한 막대기", "D 숙련 풀강", 8),
                          ("참나무 낚싯대", "C 숙련 풀강", 10),
                          ("참나무 낚싯대", "C 숙련 +5", 5),
                          ("전문가 낚싯대", "B 숙련 +5 (하위강)", 5),
                          ("전문가 낚싯대", "B 숙련 풀강", 13),
                          ("낚시꾼의 낚싯대", "C 일반 풀강", 10),
                          ("예리한 낚싯대", "B 일반 풀강", 13),
                          ("다목적 낚싯대", "C 혼합 풀강", 10),
                          ("만능 낚싯대", "B 혼합 풀강", 13)]:
        base, e = diff_of(rod), enh_diff(rod, lvl, enh)
        rb = base + e
        print(f"  {lab:<20} 기본{base:>2} +강화{e:>2.0f}(+{lvl:<2}) = rodBonus {rb:>4.0f}"
              f" → 순간이동 S {teleport_frac(rb)*100:5.1f}% · A {teleport_frac(rb,'A')*100:4.1f}%")


_K = MEAS.apply(SV)
_SV, _INC = {}, {}
for _s in SV.STAGES:
    _r = SV.compute(_s)
    _SV[_s] = {k: v[0] for k, v in _r["V"].items()}
    _INC[_s] = _r["income"]
_HM = HV.Model()
_HS = _K["harpoon"]
_RATIO = ((_HS["catches_per_active_h"] / SV.CATCH_PER_HOUR)
          * (SV.size_mult(_HS["quality_mean"]) / SV.size_mult(_K["size_score"])))

if __name__ == "__main__":
    main()
