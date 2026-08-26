#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
rod_rebalance.py — 낚싯대 «라인 밸런스» 산출. 같은 등급·같은 비용이면 스탯 총가치가 같아야 한다.

★2026-08-27 신설. 2026-08-27 스폰마을 감사에서 «등급도 레벨제한도 가성비를 예측하지 못하고
라인(주력 스탯)이 결정한다»가 나왔다. 그 원인을 정량화하면 하나다:

    같은 등급 안에서 라인별 «정규화 총합»이 1.9~2.3배 벌어져 있다.
      D: 채집 22.7 · 성장 16.7 · 상인 13.7 · 행운 12.6 · 크리 11.8 · 숙련 9.7   (2.3배)
      C: 채집 33.1 · 성장 22.1 · 상인 22.0 · 숙련 19.0 · 행운 15.5 · 크리 14.4  (2.3배)
      B: 채집 57.5 · 성장 41.4 · 상인 37.9 · 행운 34.6 · 크리 31.5 · 숙련 28.2  (2.0배)
      A: 채집 94.6 · 성장 74.1 · 상인 66.5 · 행운 57.3 · 숙련 50.8 · 크리 49.1  (1.9배)

정규화(`stat_value`, 판매보너스 1% = 1.00)는
    난이도 8.87 · 크리배율 2.38 · 등급업 2.11 · 트리플 2.00 · 판매·더블·경험치·재료확률 1.00
    · 크기 0.59 · 크리확률 0.48 · 도주감소 0.47 · 행운 0.40 · 돌진쿨감 0.23
이고, 라인별 부여량이 이 가중치를 보정하지 않아 격차가 생겼다 — 예: D 등급에서
크리형은 «0.48·0.59 스탯을 2씩»(=2.16) 받는데 채집은 «1.00 스탯을 10»(=10.0) 받는다.

## 목표 정의 — 「재료 대비 성능」이 등급 내에서 균일해야 한다

    목표 총합_i = 등급 중위 총합 × (총비용_i ÷ 등급 중위 총비용)

스탯을 바꿔도 재료·가격은 그대로이므로 총비용은 고정이다. 위 식을 만족하면 **회수시간
(총비용 ÷ 성능)이 등급 안에서 균일**해진다 — 그게 「같은 등급·같은 비용이면 같은 가성비」다.
등급 간에는 손대지 않는다(도매할인은 별건 — item_ledger 의 검사 ③).

## 라인별 조정 규칙

- **채집(재확 ≥10)**: 수입축(행운·등급업·판매보너스) 제거 + 재확을 목표에 맞춤.
  ★난이도·내구보존·경험치는 유지 — 난이도가 0이면 미니게임 존이 최소가 되고(생성기 주석
  「난이도 0이면 미니게임 자체가 안 된다」), 내구보존은 낚싯대 전용 정체성 스탯이다.
  ⇒ 미끼(수입축을 완전히 0으로)와 달리 낚싯대는 income 을 0으로 만들 수 없다. 축 분리는
    «수입 특화 스탯을 뺀다»까지다.
- **그 외 라인**: 주력 쌍의 부여량을 목표 비율로 스케일. 난이도·행운(보편 부스탯)과
  내구보존은 건드리지 않는다.

## 채집 라인 = «재료확률 전문 낚싯대» (★2026-08-27 유저 확정)

초안은 재확을 목표에 맞춰 **내렸다**(10→2 / 18→12 / 28→12). 유저 판단이 그걸 뒤집었다:

> "낚싯대도 재확이 그렇게 사기면 다른 스탯을 거의 죽여버리거나 없애고 그냥 재료확률만 냅둬.
>  그게 유저입장에서는 더 좋을거야"

맞다. 재확을 깎으면 «채집 낚싯대»라는 정체성이 사라지고 그냥 약한 낚싯대가 된다(D 재확 2는
부품 사다리 4보다도 낮다). 대신 **다른 스탯을 없애면** 같은 밸런스를 얻으면서 정체성은 살아
있고, 선택이 진짜 트레이드오프가 된다.

처방: 재확·경험치·내구보존만 남기고 **난이도·행운·등급업·판매보너스·더블·크리·크기 전부 제거**
  · ★난이도까지 뺀다 — 그러면 고등급 미니게임이 사실상 불가해진다(캘리브레이션 기준 난이도 0
    에서 B 68% · A 52% · S 10%). 그게 이 낚싯대의 대가다: 「재료는 쏟아지지만 대물은 못 잡는다」.
    잃는 포획은 B·A·S 가 전체의 8% 뿐이라 재료 수급 자체에는 타격이 작다.
  · 경험치·내구보존은 남긴다 — 둘 다 수입축이 아니고(진행축·유지비 절감) 「오래 낚아 재료를
    모은다」는 이 낚싯대의 용도와 방향이 같다.
⇒ 결과적으로 income 이 거의 0 이 되어 **«돈은 못 벌고 재료만 캐는 낚싯대»** 가 된다.
  미끼 채집 라인(수입축 0 + 재확 ×1.5)과 완전히 같은 철학이다.

## 부수 재확(<10)은 제거 — 축을 채집 라인에 독점시킨다
유목민4 · 오아시스5 · 고고학자의6 · 사막탐사6 · 감별사의6 · 왕립서고6 · 감정왕의8 ·
유적탐사자의8 은 재확이 **장식**이다(그 라인의 정체성이 아니다). 빼면 축이 깨끗해지고,
게다가 **생성기 산출과 일치**한다(gen_rod_builds 는 재확을 만들지 않는다) — 드리프트가 줄고
그 아이템들이 다시 생성기 관리로 돌아온다.
★단 그 순간 `is_external()` 보호를 잃으므로, 이후 그 아이템의 수치는 생성기 표가 권위가 된다.

사용:
    python3 rod_rebalance.py                # 현황 + 제안
    python3 rod_rebalance.py --village 스폰마을
    python3 rod_rebalance.py --plan          # 패치 스크립트용 (이름 TAB 새스탯)
"""
import argparse, collections, importlib.util, json, os, statistics as st, sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
BS = os.environ.get("BLOCKSHIP_DATA",
                    "/Users/user/Library/Application Support/feather/player-server/servers/"
                    "07de2d81-991a-47e2-b62d-06c0d1b5150a/plugins/BlockShip")


def _load(name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, name + ".py"))
    m = importlib.util.module_from_spec(spec)
    sv, sys.argv = sys.argv, [name]
    spec.loader.exec_module(m)
    sys.argv = sv
    return m


MV = _load("material_value")
SV = _load("stat_value")
IL = _load("item_ledger")
MEAS = _load("measured")

# ── 라인별 «조정 대상» 스탯 (2026-08-27 2차 — 초안의 두 오류를 고쳤다) ─────────
#  초안은 «FIXED 아닌 전부»를 스케일했고 그 결과:
#   ① 숙련형(난이도+내구보존)은 둘 다 고정이라 스케일러가 **행운에 전부 쏟아부었다**
#      (튼튼한 막대기 행운 2→8) — 숙련형이 행운 로드로 변질된다.
#   ② 내구보존을 정규화에서 뺐는데 item_ledger 의 순성능에는 dur_val 로 들어 있어
#      목표와 실제가 어긋났다 → 상인형이 과잉 너프(다목적 판매 5→2)됐다.
#  ⇒ 라인마다 «그 라인의 정체성 스탯»만 조정하고, 목표는 정규화가 아니라
#    **item_ledger 의 순성능(원/h)** 을 직접 쓴다(단일 출처).
# 채집 라인에 남길 스탯 — 이 밖의 스탯은 전부 제거한다
FORAGE_KEEP = {"재료확률", "경험치", "내구보존"}
# 부수 재확 판정 — 이 값 미만이면 «장식»으로 보고 제거한다
FORAGE_DECOR_MAX = 9

LINE_ADJ = {
    "숙련형":     ["내구보존"],
    "행운형":     ["등급업", "행운"],
    "크리형":     ["크리확률", "크기", "크리배율"],
    "상인형":     ["판매보너스", "더블찬스", "트리플찬스"],
    "성장형":     ["경험치", "트리플찬스"],
    "채집(재확)": ["재료확률", "경험치"],
    "기타":       ["행운"],
}
# 난이도는 어떤 라인에서도 손대지 않는다 — 미니게임 존 폭이라 0 이면 게임이 성립하지 않고,
# 등급별 하한이 이미 설계돼 있다(생성기 §8.1).
NEVER = {"난이도", "등급특화"}
# 채집 라인에서 제거할 «수입 특화» 스탯
STRIP_ON_FORAGE = {"행운", "등급업", "판매보너스", "더블찬스", "트리플찬스",
                   "크리확률", "크리배율", "크기", "도망감소"}
FORAGE_MIN = 10          # 재료확률 이 값 이상이면 «채집 라인»으로 본다
# ★E 등급은 재조정 대상이 아니다 — 유료 항목이 2종뿐이라 «등급 중위»가 성립하지 않고
#   (초보자 낚싯대는 튜토리얼 지급물), 초보 낚싯대의 문제는 스탯이 아니라 재료 소요량이다.
SKIP_GRADES = {"E"}
# 부여량 최소 단위 — parts.json 은 정수만 담는다
STAT_ORDER = ["난이도", "도망감소", "크리배율", "등급업", "크리확률", "크기", "경험치",
              "판매보너스", "더블찬스", "트리플찬스", "행운", "재료확률", "내구보존"]


def norm_table():
    """정규화 가중치 — 판매보너스 1% = 1.00 (stat_value 중반)."""
    V = SV.compute("중반")["V"]
    a = V["판매보너스 (1%)"][0]
    return {k.split(" (")[0]: v[0] / a for k, v in V.items()}


def stat_str(st_):
    """스탯 문자열. ★등급특화 처럼 값이 문자열인 스탯이 있어 숫자만 라운딩한다."""
    num = {k: v for k, v in st_.items() if isinstance(v, (int, float)) and v}
    other = {k: v for k, v in st_.items() if not isinstance(v, (int, float))}
    keys = [k for k in STAT_ORDER if k in num] + [k for k in num if k not in STAT_ORDER]
    out = [f"{k}:{int(round(num[k]))}" for k in keys]
    out += [f"{k}:{v}" for k, v in other.items()]
    return ",".join(out)


def line_of(s):
    if s.get("재료확률", 0) >= FORAGE_MIN:
        return "채집(재확)"
    if s.get("판매보너스", 0) > 0:
        return "상인형"
    if s.get("크리확률", 0) > 0 and s.get("크기", 0) > 0:
        return "크리형"
    if s.get("경험치", 0) > 0:
        return "성장형"
    if s.get("등급업", 0) > 0:
        return "행운형"
    if s.get("내구보존", 0) > 0:
        return "숙련형"
    return "기타"


def build_rows():
    k = MEAS.apply(SV)
    sv_, inc_ = {}, {}
    for s_ in SV.STAGES:
        r = SV.compute(s_)
        sv_[s_] = {a: b[0] for a, b in r["V"].items()}
        inc_[s_] = r["income"]
    HV = _load("harpoon_value")
    HM = HV.Model()
    hs = k["harpoon"]
    ratio = ((hs["catches_per_active_h"] / SV.CATCH_PER_HOUR)
             * (SV.size_mult(hs["quality_mean"]) / SV.size_mult(k["size_score"])))
    D = MV.Data()
    rows = IL.build(D, sv_, inc_, ratio, HM)
    return k, [r for r in rows if r["cat"] == "낚싯대"], sv_


def unit_value(stage, statvals, name, grade="C"):
    """스탯 1단위의 원/h — item_ledger 와 같은 축 배정을 쓴다."""
    V = statvals[stage]
    if name in IL.STAT_KEY:
        return V[IL.STAT_KEY[name]]
    if name in IL.GROWTH_KEY:
        return V[IL.GROWTH_KEY[name]]
    if name in IL.GATE_KEY:
        return V[IL.GATE_KEY[name]]
    if name == "내구보존":
        # ★item_ledger 와 같은 식: 내구보존 v% = v/100 × 세트 유지비.
        #   이걸 0 으로 두면 숙련형(조정 대상이 내구보존 하나)이 영구히 조정 불가가 된다.
        A = SV.CASTS_PER_HOUR
        return A * (4 * IL.REPAIR_RATE.get(grade, 5) + IL.CHEAPEST_BAIT) / 100.0
    return 0.0


# ── 사다리 상한 — 조정이 «다음 등급»을 넘지 못하게 (2026-08-27) ────────────────
#  라인 밸런싱은 부여량을 자유롭게 키울 수 있어 C 등급 행운이 A 등급(14)을 넘는 해가 나왔다
#  (잉어꾼의 행운 6→16). 등급 사다리가 뒤집히면 라인 균형을 맞춰도 소용이 없다.
#  ⇒ 생성기(gen_rod_builds.PRIMARY)의 «다음 등급 값»을 상한으로 쓴다 — 설계 권위 그대로.
GEN_ROD = os.path.expanduser(
    "~/Library/Application Support/feather/player-server/servers/"
    "07de2d81-991a-47e2-b62d-06c0d1b5150a/plugins/Skript/scripts/fish-tools/gen_rod_builds.py")
GRADE_SEQ = "EDCBAS"


def primary_table(path=GEN_ROD):
    """gen_rod_builds.PRIMARY 파싱. 없으면 빈 dict(상한 미적용)."""
    import re, ast
    if not os.path.exists(path):
        return {}
    src = open(path, encoding="utf-8").read()
    m = re.search(r"PRIMARY = \{(.*?)\n\}", src, re.S)
    if not m:
        return {}
    out = {}
    for line in m.group(1).split("\n"):
        mm = re.match(r'\s*"([^"]+)":\s*(\{[^}]*\})', line)
        if mm:
            try:
                out[mm.group(1)] = ast.literal_eval(mm.group(2))
            except Exception:
                pass
    return out


# ── 가드레일 (★2026-08-27 2차 — 초안이 극단값을 뱉었다) ────────────────────
#  초안은 상한을 «다음 등급의 설계값»으로 뒀는데 A 등급 판매보너스가 S 값 24 까지 올라
#  8→24(3배) 같은 해가 나왔다. 그리고 하한이 없어 «판매보너스 16→1»(왕도 상회) ·
#  «경험치 35→6»(유적탐사자의) 처럼 스탯이 사실상 사라지는 해도 나왔다.
#  ⇒ 상한 = 같은 등급 설계값 ×1.5 · 하한 = 현재값 ×0.5. 라인 정체성을 유지하는 폭 안에서만
#    조정하고, 그 폭으로 목표에 못 닿으면 «그만큼만» 맞춘다(완벽한 균등보다 정체성 우선).
CAP_MULT = 1.5
FLOOR_MULT = 0.5
#  ★현재값 대비 증감 상한 — 사다리 상한만으로는 «판매보너스 8→27»(감별사의) 같은 3.4배 급증이
#    남는다. 한 번의 조정으로 스탯이 2배를 넘게 뛰면 그건 밸런싱이 아니라 재설계다.
MAX_GROWTH = 2.0


def stat_cap(PRI, stat, grade):
    """그 등급에서 이 스탯이 넘지 못할 값 = 같은 등급 설계값 × CAP_MULT."""
    tbl = PRI.get(stat)
    if not tbl:
        return None
    if grade in tbl:
        return max(1, int(round(tbl[grade] * CAP_MULT)))
    i = GRADE_SEQ.find(grade)
    for g in reversed(GRADE_SEQ[:i]):
        if g in tbl:
            return max(1, int(round(tbl[g] * CAP_MULT)))
    return max(1, int(round(max(tbl.values()) * CAP_MULT)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--village", default=None, help="출처 필터 (예: 스폰마을)")
    ap.add_argument("--plan", action="store_true")
    ap.add_argument("--include-hidden", action="store_true")
    a = ap.parse_args()

    N = norm_table()
    PRI = primary_table()
    k, rods, statvals = build_rows()
    rods = [r for r in rods if r["currency"] == "원" and r["total"] > 0]
    if a.village:
        rods = [r for r in rods if a.village in r["src"]]
    if not a.include_hidden:
        rods = [r for r in rods if "히든" not in r["src"]]

    for r in rods:
        # 내구보존은 income 이 아니라 유지비 절감 → 총합에서 제외(별도 축)
        r["norm"] = sum(N.get(x, 0) * v for x, v in r["stats"].items()
                        if isinstance(v, (int, float)) and x != "내구보존")
        r["line"] = line_of(r["stats"])

    if not a.plan:
        print(MEAS.banner(k))
        print("\n정규화(판매보너스 1% = 1.00): "
              + " · ".join(f"{x} {N[x]:.2f}" for x in
                           sorted(N, key=lambda x: -N[x]) if x in STAT_ORDER))

    plan = {}
    by_grade = collections.defaultdict(list)
    for r in rods:
        by_grade[r["grade"]].append(r)

    for grade in "EDCBAS":
        arr = by_grade.get(grade)
        if not arr or len(arr) < 2:
            continue
        if grade in SKIP_GRADES:
            continue
        med_norm = st.median([r["norm"] for r in arr])
        med_cost = st.median([r["total"] for r in arr])
        if not a.plan:
            print(f"\n{'='*112}\n[{grade}]  등급 중위 회수 "
                  f"{st.median([r['payback'] for r in arr if r['payback']<1e6]):.1f}h"
                  f"  → 목표 성능 = 총비용 ÷ 중위회수\n{'='*112}")
            print(f"{'Lv':>3} {'이름':<20}{'라인':<11}{'총비용':>11}{'현성능':>10}{'목표성능':>10}"
                  f"{'회수 변화':>13}  현 스탯 → 새 스탯")
        med_pb = st.median([r["payback"] for r in arr if r["payback"] < 1e6])
        for r in sorted(arr, key=lambda r: r["lv"]):
            # ★목표 = 회수시간을 등급 중위로 맞추는 순성능
            target_eff = r["total"] / med_pb
            new = dict(r["stats"])
            mc = new.get("재료확률", 0)
            if isinstance(mc, (int, float)) and mc >= FORAGE_MIN:
                # ★채집 전문화 — 재확·경험치·내구보존만 남기고 전부 제거(난이도 포함)
                new = {x: v for x, v in new.items() if x in FORAGE_KEEP}
                plan[r["name"]] = (new, None, None)
                if not a.plan:
                    print(f"{r['lv']:>3} {r['name']:<20}{'채집전문':<11}{r['total']:>11,.0f}"
                          f"{r['eff_net']:>10,.0f}{'—':>10}{'—':>13}"
                          f"  {stat_str(r['stats'])}\n{'':>66}→ {stat_str(new)}")
                continue
            if isinstance(mc, (int, float)) and 0 < mc <= FORAGE_DECOR_MAX:
                new.pop("재료확률")      # 장식 재확 제거 → 생성기 산출과 일치
            adj = [x for x in LINE_ADJ.get(r["line"], []) if x in new and x not in NEVER]
            stage = IL.STAGE_OF_LEVEL(r["lv"])
            uv = {x: unit_value(stage, statvals, x, grade) for x in adj}
            adj_eff = sum(uv[x] * new[x] for x in adj)
            # 고정분 = 현재 순성능에서 조정 대상 기여를 뺀 것 (유지비·내구보존 포함)
            fixed_eff = r["eff_net"] - adj_eff
            room = target_eff - fixed_eff
            if adj_eff > 0 and room > 0:
                scale = room / adj_eff
                for x in adj:
                    v = max(1, round(new[x] * scale))
                    cap = stat_cap(PRI, x, grade)
                    if cap:
                        v = min(v, cap)                      # ★사다리 상한
                    v = min(v, max(1, int(round(new[x] * MAX_GROWTH))))  # ★증감 상한
                    v = max(v, max(1, int(round(new[x] * FLOOR_MULT))))   # ★정체성 하한
                    new[x] = v
            elif adj_eff > 0:
                for x in adj:
                    new[x] = max(1, int(round(new[x] * FLOOR_MULT)))  # 고정분만으로 목표 초과
            new_eff = fixed_eff + sum(uv[x] * new[x] for x in adj)
            plan[r["name"]] = (new, new_eff, target_eff)
            if not a.plan:
                ch = "동일" if stat_str(new) == stat_str(r["stats"]) else stat_str(new)
                print(f"{r['lv']:>3} {r['name']:<20}{r['line']:<11}{r['total']:>11,.0f}"
                      f"{r['eff_net']:>10,.0f}{target_eff:>10,.0f}"
                      f"{r['payback']:>7.1f}→{r['total']/max(new_eff,1):>5.1f}h"
                      f"  {stat_str(r['stats'])}\n{'':>66}→ {ch}")

    if a.plan:
        for n, (new, nn, tg) in plan.items():
            print(f"{n}\t{stat_str(new)}")
        return

    # ── 조정 후 밴드 편차 검산 ────────────────────────────────────────
    print(f"\n{'='*104}\n조정 후 라인 밸런스 검산 (같은 등급이면 «비용당 총합»이 같아야 한다)\n{'='*104}")
    for grade in "EDCBAS":
        arr = by_grade.get(grade)
        if not arr or len(arr) < 2 or grade in SKIP_GRADES:
            continue
        before, after = [], []
        for r in arr:
            if plan[r["name"]][1] is None:
                continue          # 채집전문 — 축이 달라 같은 잣대로 비교하지 않는다
            before.append(r["eff_net"] / r["total"])
            after.append(plan[r["name"]][1] / r["total"])
        bd = max(before) / max(min(before), 1e-9)
        ad = max(after) / max(min(after), 1e-9)
        print(f"  {grade}: 비용당 총합 편차  {bd:.2f}배 → {ad:.2f}배"
              f"   (라인 {len({r['line'] for r in arr})}종 · n={len(arr)})")


if __name__ == "__main__":
    main()
