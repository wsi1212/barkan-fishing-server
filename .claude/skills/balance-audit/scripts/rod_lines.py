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
EL = _load("enhance_lines")   # 난이도 3층 예산·숙련 시리즈의 단일 권위

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
#: 등급 → 라인별 기본 난이도. ★복제 금지 — `enhance_lines.ROD_DIFF` 가 단일 권위다
#  (낚싯대 기본 + 강화 총량 + 숙련부품 3층이 «순간이동 문턱»을 함께 만들기 때문에
#   한 곳에서만 정의해야 한다).
DIFF_BY_GRADE = EL.ROD_DIFF
#: 등급별 회수시간 목표(h). 등급이 오르면 완만하게 길어진다(상위 등급은 «오래 쓰는» 물건).
TARGET = {"E": None, "D": 10.5, "C": 11.0, "B": 12.5}

#: 설계 대상 — 이름: (등급, 라인표시, 부스탯, 등급특화, 돈가격 덮어쓰기|None)
#  ★부스탯 수치는 --tune 산출값이다. 손으로 만지지 말고 --tune 을 다시 돌릴 것.
DESIGN = {
    "나뭇가지":           ("E", "입문", {"행운": 1}, None, None),
    "초보자 낚싯대":       ("E", "입문", {"경험치": 3}, None, None),
    "초보 낚싯대":         ("E", "입문", {"크기": 3, "크리확률": 2}, None, None),
    "튼튼한 막대기":       ("D", "숙련", {"도망감소": 3, "경험치": 2}, None, 8700),
    "참나무 낚싯대":       ("C", "숙련", {"도망감소": 4, "경험치": 2}, None, 48200),
    "전문가 낚싯대":       ("B", "숙련", {"도망감소": 8, "경험치": 4}, None, 52300),
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
    "다목적 낚싯대":       ("C", "혼합", {"도망감소": 3, "판매보너스": 5, "더블찬스": 2}, None, 84500),
    "겸업 낚싯대":         ("B", "기타", {"등급업": 5, "크리확률": 8, "크기": 14}, None, None),
    "만능 낚싯대":         ("B", "혼합", {"도망감소": 5, "판매보너스": 9, "더블찬스": 4}, None, 64300),
    "채집용 낚싯대":       ("D", "채집", {"재료확률": 10, "경험치": 3}, None, None),
    "수집가의 낚싯대":     ("C", "채집", {"재료확률": 19, "경험치": 5}, None, None),
    "탐사자의 낚싯대":     ("B", "채집", {"재료확률": 28, "경험치": 7}, None, None),
}
#: 숙련 계열 부품 — 각 슬롯의 «군더더기 없는 기본형» 시리즈에 난이도를 부스탯으로 준다.
#  새 아이템/레시피를 만들지 않는다(상점 목록·제작 UI 를 늘리지 않는 것이 설계 의도).
#  값은 `enhance_lines.PART_DIFF` · 대상은 `enhance_lines.SKILL_SERIES`.
#  ★슬롯별로 목표가 다르다 — 줄은 축 자체가 약하다. 실측(전 부품 원장):
#      릴 회수 중위 6.6h · 바늘 9.5h · 찌 11.8h · **줄 19.7h** (재료원은 4슬롯 동일 213,427원)
#    원인은 도망감소가 **B등급 전용 스탯**이라는 것이다 — 0→80 이 B 를 69%→100% 로 올리지만
#    A 는 +5%p · S 는 +2%p 뿐이고 80 에서 완전 포화한다. 존폭이 1~2칸인 A/S 에서는 도주율을
#    낮춰도 계속 미스해 escapeInc 가 100 까지 밀어올린다. 즉 **도망감소는 난이도의 대체재가
#    아니다** — 난이도는 «맞히게» 해주고 도망감소는 «한 번 더 기회»를 준다. 존이 1칸이면
#    기회를 더 줘도 못 맞힌다. ⇒ 수치를 3배로 올려도 해결 안 되고, 남은 처방은 **줄 레시피
#    원가 인하**뿐이다(별건 — 원가를 건드리면 전 슬롯·낚싯대의 재료 게이트가 다 흔들린다).
#    여기서는 줄에만 완화 목표를 주고 그 사실을 드러낸다.
PART_TARGET = {"E": None, "D": 9.0, "C": 9.5, "B": 10.5, "A": 12.0, "S": 13.0}
PART_TARGET_BY_SLOT = {"줄": {"D": 15.0, "C": 15.0, "B": 15.0, "A": 16.0, "S": 16.0}}

#: 라인 표시 → DIFF_BY_GRADE 키. «겸업»(크리+행운)은 난이도가 정체성이 아니라 기타.
DIFF_KEY = {"숙련": "숙련", "채집": "채집", "혼합": "혼합", "입문": "기타"}

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


_ENH_TABLE = None


def enh_tables():
    """`enhance_lines` 가 생성한 강화표 — 난이도 검증의 권위. 라이브 파일이 아니라
    «지금 설계가 산출하는» 표를 봐야 한다(라이브는 아직 구 표일 수 있다)."""
    global _ENH_TABLE
    if _ENH_TABLE is None:
        _ENH_TABLE, _ = EL.generate()
    return _ENH_TABLE


def enh_diff(rod, level):
    """rod 를 level 까지 강화했을 때 누적 난이도 (생성된 표 기준)."""
    ent = enh_tables().get(rod) or {}
    tot = 0
    for i in range(1, level + 1):
        for t in (ent.get("levels") or {}).get(str(i), "").split(","):
            if t.startswith("난이도:"):
                tot += float(t.split(":", 1)[1])
    return tot


# ── 원장 ────────────────────────────────────────────────────────────────
def ledger(subs_by_name=None, part_prices=None):
    """DESIGN 을 임시 parts.json 에 써서 item_ledger 로 총비용·순성능·회수를 낸다."""
    P = json.load(open(os.path.join(MV.BS, "parts.json"), encoding="utf-8"))
    for n, (g, line, s0, spec, price) in DESIGN.items():
        f = P["parts"]["낚싯대"][n].split("|")
        over = (part_prices or {}).get(n, price)
        if over is not None:
            f[2] = str(over)
        f[4] = stat_str(n, (subs_by_name or {}).get(n))
        P["parts"]["낚싯대"][n] = "|".join(f)
    # 숙련 계열 부품 12종에 난이도 부스탯
    for slot, members in EL.SKILL_SERIES.items():
        for pname, pg in members.items():
            f = P["parts"][slot][pname].split("|")
            st = {k: v for k, v in (x.split(":", 1) for x in f[4].split(",") if ":" in x)}
            st["난이도"] = str(EL.PART_DIFF[pg])
            if part_prices and pname in part_prices:
                f[2] = str(part_prices[pname])
            f[4] = ",".join(f"{k}:{st[k]}" for k in
                            ["난이도", "도망감소", "크리배율", "등급업", "크리확률", "크기",
                             "경험치", "판매보너스", "더블찬스", "트리플찬스", "행운",
                             "재료확률"] if k in st)
            P["parts"][slot][pname] = "|".join(f)
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


_BASE_PRICE = {}
for _slot, _mem in EL.SKILL_SERIES.items():
    _P = json.load(open(os.path.join(MV.BS, "parts.json"), encoding="utf-8"))["parts"]
    for _n in _mem:
        _BASE_PRICE[_n] = int(_P[_slot][_n].split("|")[2])


def tune(rounds=10):
    """부스탯·돈가격을 회수시간 목표에 맞춘다.

    · 부스탯 = 정수 스케일(라인 정체성 유지, 최소 1)
    · 돈가격 = 목표에서 **직접 역산**(price = 순성능 × 목표h − 재료원). 난이도처럼
      «값이 큰데 정수라 못 줄이는» 스탯이 들어오면 부스탯만으로는 절대 목표에 못 닿는다
      — 그때 유일하게 남는 자유도가 가격이다(실측: 참나무 난이도 5 하나가 그 등급 예산
      전부를 먹어 부스탯을 바닥까지 깎아도 8.8h 였다).
    """
    cur = {n: dict(v[2]) for n, v in DESIGN.items()}
    prices = {}
    for _ in range(rounds):
        sel = ledger(cur, prices)
        moved = 0
        for n, (g, line, s0, spec, price) in DESIGN.items():
            tg = TARGET.get(g)
            if tg is None:
                continue
            r = sel[n]
            if r["eff_net"] <= 0 or r["total"] <= 0:
                continue
            if price is not None:                       # 가격 자유도가 있는 행 → 역산
                want = r["eff_net"] * tg - r["mat_won"]
                newp = max(0, int(round(want / 100.0) * 100))
                if prices.get(n) != newp:
                    prices[n] = newp
                    moved += 1
                continue
            if not cur[n]:
                continue
            f = max(0.55, min(1.8, (r["total"] / tg) / r["eff_net"]))
            if abs(f - 1) < 0.03:
                continue
            new = {a: max(MINV[a], int(round(b * f))) for a, b in cur[n].items()}
            if new != cur[n]:
                cur[n] = new
                moved += 1
        # 숙련 계열 부품 — ★«추가한 가치만큼만» 올린다(목표 회수로 역산하지 않는다).
        #   역산을 쓰면 릴 3종 가격이 6.8배로 뛰었다. 그건 난이도 1 을 얹어서가 아니라
        #   **릴 슬롯이 원래 싸다**(회수 중위 6.6h)는 별개 문제 때문이다. 그 문제를 여기서
        #   손대면 같은 시리즈의 나머지 19종과 역전이 생긴다(숙련 릴이 일반 릴보다 나쁨).
        #   ⇒ 인상분 = 난이도 1 점의 원/h × 그 등급 목표 회수시간. 슬롯 리밸런스는 별건.
        for slot, members in EL.SKILL_SERIES.items():
            for pname, pg in members.items():
                r = sel.get(pname)
                tg = PART_TARGET_BY_SLOT.get(slot, PART_TARGET).get(pg)
                if not r or tg is None:
                    continue
                if slot == "줄":
                    # ★줄은 이미 목표의 2배 넘게 어긋나 있다(축 가치 문제, 위 주석 참조).
                    #   여기에 난이도 값만큼 더 받으면 더 나빠진다 — 원가 인하가 선행 조건이다.
                    continue
                stage = IL.STAGE_OF_LEVEL(r["lv"])
                dv = SV.diff_curve(stage)[1] * EL.PART_DIFF[pg]
                newp = int(round((_BASE_PRICE[pname] + dv * tg) / 100.0) * 100)
                if prices.get(pname) != newp:
                    prices[pname] = newp
                    moved += 1
        if not moved:
            break
    return cur, prices


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tune", action="store_true", help="부스탯을 회수시간 목표에 재적합")
    ap.add_argument("--plan", action="store_true", help="ROD_PLAN 형태로 출력")
    a = ap.parse_args()

    print(MEAS.banner(_K))
    subs, prices = tune() if a.tune else (None, None)
    sel = ledger(subs, prices)

    if a.plan:
        print("\nROD_PLAN = {")
        for n, (g, line, s0, spec, price) in DESIGN.items():
            s = stat_str(n, (subs or {}).get(n))
            pr = (prices or {}).get(n, price)
            print(f'    "{n}":{" " * max(1, 20 - len(n))}("{s}", {pr!r}),')
        print("}")
        print("\nPART_PLAN = {   # 숙련 계열 부품: 난이도 부스탯 + 가격")
        for slot, members in EL.SKILL_SERIES.items():
            for pname, pg in members.items():
                print(f'    "{pname}":{" " * max(1, 16 - len(pname))}'
                      f'("{slot}", {EL.PART_DIFF[pg]}, {(prices or {}).get(pname)!r}),')
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

    print(f"\n=== 숙련 계열 부품 (난이도 부스탯 신설) ===")
    print(f"  {'슬롯':<4}{'이름':<16}{'등':<3}{'난이도':>5}{'돈':>10}{'재료원':>10}"
          f"{'총비용':>10}{'순성능':>9}{'회수h':>7}  스탯")
    for slot, members in EL.SKILL_SERIES.items():
        for pname, pg in members.items():
            r = sel.get(pname)
            if not r:
                continue
            pb = r["payback"]
            print(f"  {slot:<4}{pname:<16}{pg:<3}{EL.PART_DIFF[pg]:>5}{r['price']:>10,.0f}"
                  f"{r['mat_won']:>10,.0f}{r['total']:>10,.0f}{r['eff_net']:>9,.0f}"
                  f"{('∞' if pb >= 1e6 else f'{pb:.1f}'):>7}  {','.join(f'{k}:{int(v)}' for k,v in r['stats'].items() if isinstance(v,(int,float)))}")

    print("\n=== 순간이동 검증 (구조 지표 — zoneWidth<1) ===")
    print("  ★부품 = 숙련 계열 릴·줄·바늘·찌 4슬롯 (미끼는 행운 축 유지)")
    print(f"  {'구성':<30}{'낚싯대':>7}{'강화':>5}{'부품':>5}{'합계':>5}"
          f"{'S':>8}{'A':>7}{'M':>7}")
    for rod, lab, lvl, pg in [
            ("튼튼한 막대기", "D 숙련 풀강 + D 숙련부품", 8, "D"),
            ("참나무 낚싯대", "C 숙련 풀강 + C 숙련부품", 10, "C"),
            ("참나무 낚싯대", "C 숙련 풀강 + 일반부품", 10, None),
            ("전문가 낚싯대", "B 숙련 중반강화 + C 숙련부품", 6, "C"),
            ("전문가 낚싯대", "B 숙련 풀강 + B 숙련부품", 13, "B"),
            ("낚시꾼의 낚싯대", "C 일반 풀강 + C 숙련부품", 10, "C"),
            ("낚시꾼의 낚싯대", "C 일반 풀강 + 일반부품", 10, None),
            ("예리한 낚싯대", "B 일반 풀강 + B 숙련부품", 13, "B"),
            ("다목적 낚싯대", "C 혼합 풀강 + C 숙련부품", 10, "C"),
            ("만능 낚싯대", "B 혼합 풀강 + B 숙련부품", 13, "B"),
            ("탐사자의 낚싯대", "B 채집 풀강 + B 숙련부품", 13, "B")]:
        base, e = diff_of(rod), enh_diff(rod, lvl)
        pd = EL.PART_DIFF[pg] * 4 if pg else 0
        rb = base + e + pd
        print(f"  {lab:<30}{base:>7}{e:>5.0f}{pd:>5}{rb:>5.0f}"
              f"{teleport_frac(rb,'S')*100:>7.1f}%{teleport_frac(rb,'A')*100:>6.1f}%"
              f"{teleport_frac(rb,'M')*100:>6.1f}%")

    print("\n=== 강화 사다리 (유저 제약: C풀강 ≥ B중반강화 ≥ A기본) ===")
    for dk in ("숙련", "혼합", "기타", "채집"):
        c = EL.ROD_DIFF[dk]["C"] + EL.ENH_DIFF[dk]["C"]
        b = EL.ROD_DIFF[dk]["B"] + EL.ENH_DIFF[dk]["B"] // 2
        aa = EL.ROD_DIFF[dk]["A"]
        print(f"  {dk:<4} C풀강 {c:>2} · B중반 {b:>2} · A기본 {aa:>2}"
              f"   {'✓' if c >= aa and abs(c - b) <= 1 else '✗'}")


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
