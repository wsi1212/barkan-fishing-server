#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cast_cost.py — 「이 장비 하나를 만들려면 몇 캐스트를 던져야 하나」의 단일 권위 (2026-08-27).

★왜 «캐스트»인가
  재료 게이트는 여태 **시간(h)** 으로만 나왔다(material_value 의 LP 쌍대해). 시간은 활동을
  섞어 비교할 때는 옳지만 «이 낚싯대 하나 만드는 데 얼마나 던져야 하지?» 라는 플레이어의
  실제 단위가 아니다. 캐스트는 그 단위이고, 드롭이 캐스트(→포획)마다 굴러가므로 재료
  요구 수량과 **선형으로 직결**된다 — 그래서 조정 손잡이로도 캐스트가 맞다.

      캐스트 = LP 게이트 시간(h) × 실측 캐스트/h
  ★광질·바닐라가 섞인 BOM 의 시간도 같은 환율로 환산한다. 그건 «낚시 등가 캐스트»이지
    진짜 던진 횟수가 아니다 — mine_share 컬럼으로 그 비중을 드러낸다.

## 목표 모델 (2026-08-27 유저 결정)
  "지금 평균 장비를 만들기 위해 몇 캐스트가 필요한지 구하고 그거 재료 요구 개수를 수정.
   밸런스 망가지지 않게. 같은 등급이라도 성능차이에 따라 10~25%까지 차이나게 요구캐스트"

      요구캐스트(item) = κ(카테고리, 등급) × 상대성능(item)
                       κ(cat, g) = κ0(cat) × SLOPE^(등급index)   ·   κ0 = 총량정규화 × LIFT

  · **성능은 «그 구간 시급 대비 %»로 잰다(상대성능)** — 절대 원/h 가 아니다.
    ★이게 이 스크립트의 핵심 정정이다(2026-08-27). 구간 시급이 초반 84,279 → 중반 117,511
    → 종결 327,043 원/h 로 **3.9배** 뛰기 때문에, 원/h 로 재면 «같은 값어치의 장비»라도
    상위 등급이 자동으로 3.9배 싸 보인다. 초판이 그 착시를 그대로 사다리로 굳혔다
    (낚싯대 κ 가 D 38 → A 10 으로 «급락»했는데, 상대로 재면 32.0 → 34.1 로 평평했다).
  · **κ 는 «상대성능 1%p 당 캐스트»**. 같은 (카테고리, 등급) 안에서 상수라서 요구캐스트가
    성능에 정확히 비례한다 → 유저가 말한 «성능차이만큼 요구캐스트 차이».
    실측 동레벨 성능 산포가 10~20% 이므로 요구캐스트 산포도 그 범위에 들어온다(검증 출력).
  · **κ 는 등급이 오를수록 «올라간다»** — 등급을 올릴수록 성능 대비 더 많은 캐스트가 든다.
    ★2026-08-27 유저 결정으로 **방향을 뒤집었다**: "서버 플탐을 고려하면 갈수록 효율이
    구려지는게 맞지 않나. 한 등급 올라갈 때마다 성능 올라가는거 대비 더 많은 캐스트, 혹은
    광질이 필요하게. 왜냐면 유저거래로 구매가 얼마든지 될 거기 때문에"
    기존 메모 `feedback_tier_value_must_improve` 는 **여기 해당하지 않는다** — 그 메모는
    「상위 등급이 주는 게 양뿐인가, 성능도 오르나?」로 갈라지고 「성능도 오름 → 단위당 상승
    허용(말 대여, **장비 사다리**)」이라고 장비를 명시적 예외로 적어 뒀다. 초판이 그걸
    거꾸로 적용해 단조**감소**를 걸었다.

## 카테고리를 왜 따로 정규화하나
  작살 성능은 «무료 나무작살 대비 시간당 증분»이라 낚싯대와 스케일이 다르다(C급 작살
  57,803 vs C급 낚싯대 16,548 원/h). 한 κ 로 묶으면 작살 재료비가 3.5배로 뛴다 — 그건
  이 작업의 요청 범위가 아니다. 카테고리 안에서만 정규화하면 카테고리별 총량이 보존된다.

## 미끼는 순성능이 전부 음수다 (모델 결함, 미해결)
  item_ledger 는 미끼 자기유지비를 `캐스트/h × 판매가` 로 센다 — 매 캐스트마다 미끼값을
  치른다는 뜻이고 실제로 그렇다. 그런데 미끼 가격이 그 보너스보다 크게 책정돼 있어서
  전 미끼가 «쓸수록 손해»로 나온다. 그건 **가격 문제**지 재료 문제가 아니므로, 여기서는
  총성능(eff, 유지비 차감 전)으로 순위를 매기고 사실을 명시한다.

사용:
    python3 cast_cost.py                    # 현재 캐스트 + κ + 목표 + 배율
    python3 cast_cost.py --src 스폰마을       # 출처 한정 (기본: 스폰마을 계열 + 튜토)
    python3 cast_cost.py --all              # 전 출처
    python3 cast_cost.py --plan             # patch_*.py 가 먹는 JSON (이름 → 목표배율)
"""
import argparse, collections, importlib.util, json, math, os, sys
import statistics as st

HERE = os.path.dirname(os.path.abspath(__file__))


def _load(name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, name + ".py"))
    m = importlib.util.module_from_spec(spec)
    sv, sys.argv = sys.argv, [name]
    spec.loader.exec_module(m)
    sys.argv = sv
    return m


MV = _load("material_value")
SV = _load("stat_value")
HV = _load("harpoon_value")
IL = _load("item_ledger")
MEAS = _load("measured")

#: 기본 대상 — 「일단 스폰마을부터」(2026-08-27 유저). 히든/튜토도 같은 마을 진행이라 포함.
DEFAULT_SRC = ("스폰마을", "히든-스폰마을", "튜토")
#: 등급 순서 — κ 는 이 순서로 «단조감소»여야 한다.
GRADE_ORDER = ["E", "D", "C", "B", "A", "S"]
#: 카테고리별로 표본이 1~2종뿐인 등급은 등위회귀가 흔들린다 → 최소 표본
MIN_N = 1
#: 성능이 0 이하인 종(나무 작살·녹슨 릴·나무 찌)은 κ 로 목표를 낼 수 없다 — 손대지 않는다.
#  ★이 목록을 «성능 0이니 재료도 0» 으로 처리하면 무료 아이템의 레시피가 사라진다.
MIN_EFF = 1.0
#: E 급은 사다리 밖 — 튜토리얼 구간이다(rod_lines.EXEMPT 와 같은 이유).
#  성능 모델이 여기서는 잡음이다: 초보자 찌 26원/h · 녹슨 릴 −321원/h · 나무 작살 0.
#  그 잡음으로 κ 를 뽑으면 찌 E 가 568(=D 의 32배)이 되어 등위회귀 전체를 왜곡한다.
#  ★E 를 «싸다»고 판정해 재료를 더 물리는 것도 방향이 반대다 — 튜토 장비는 싸야 한다.
EXEMPT_GRADES = {"E"}
#: 등급당 κ 상승률(슬로프). 등급을 한 칸 올릴 때마다 «상대성능 1%p 를 사는 데» 드는
#  캐스트가 이만큼 늘어난다. 유저 의도: 상위 장비는 성능이 오르는 것 이상으로 비싸야 한다.
#  ★1.00 이면 «성능에 정비례»(중립)이고, 1.15 는 등급마다 15% 씩 손해가 커진다는 뜻.
#    D→A 3칸이면 누적 ×1.52 — 성능이 ×3.4 오르는 동안 비용은 ×5.1 오른다.
GRADE_SLOPE = 1.15
#: 전체 배수(리프트). 슬로프만 세우고 총량을 보존하면 **상위가 오르는 게 아니라 하위가
#  내려간다**(×1.70 총량보존이면 D 낚싯대가 1.6h → 0.5h). 「위로 갈수록 빡세게」는 리프트가
#  같이 있어야 성립한다. 1.3 = 스폰마을 전체 재료 수요 +30%.
#  ★★리프트는 **일회성 이주(migration)** 다 — 목표 정의에 남겨 두면 안 된다.
#    κ0 이 «현재 총수요 × LIFT» 로 정규화되므로, 반영한 뒤에도 1.30 이 남아 있으면 다음
#    실행이 **또 30% 를 올린다**(selftest 가 「104종이 ×1.41 로 어긋남」으로 잡아냈다).
#    지금 값이 목표와 같아야 «고정점»이고, 그래야 회귀 검사가 성립한다.
#    2026-08-27 ×1.30 이주 완료 → 1.00 으로 되돌림. 전체 그라인드를 또 올리려면
#    잠깐 값을 올려 patch 를 한 번 돌리고 **반드시 1.00 으로 되돌릴 것.**
GRADE_LIFT = 1.00
#: 동레벨 요구캐스트 산포 상한. 유저: "같은 등급이라도 성능차이에 따라 10~25%까지 차이나게".
#  ★상한을 넘는 쌍은 «재료 문제»가 아니라 **성능 사다리 결함**이다(같은 레벨인데 성능이
#  2~3배). 그래서 목표값을 비틀지 **않고** 그 종을 «손대지 않음(hold)»으로 표시만 한다.
#
#  ★2026-08-27 설계 변경 — 처음엔 기하평균 쪽으로 대칭 수축을 넣었는데 **멀쩡한 종이
#    같이 끌려갔다**. 작살 Lv6 이 실례다: 쇠날 작살이 43,532원/h(같은 레벨 평균의 3배)
#    라는 이유로 벼린 작살(14,682, 정상)의 목표가 303 → 450(+48%)으로 밀렸다.
#    이상치의 죄를 옆 아이템이 뒤집어쓰는 구조라 폐기했다.
#  반대로 이상치를 «성능만큼» 비싸게 매기는 것도 안 된다 — 쇠날 작살이 900 캐스트가 되어
#  모든 C 급 작살(382)보다 비싸진다. D 급 κ 가 C 급의 3배라 성능이 조금만 튀어도 등급
#  간 역전이 난다. **결론: 이상치는 스탯을 먼저 고쳐야 한다. 재료로 덮지 않는다.**
LEVEL_SPREAD_CAP = 0.25


def build_rows():
    D = MV.Data()
    k = D.k
    MEAS.apply(SV, k)
    statvals, incomes = {}, {}
    for stage in SV.STAGES:
        r = SV.compute(stage)
        statvals[stage] = {kk: v[0] for kk, v in r["V"].items()}
        incomes[stage] = r["income"]
    hs = k.get("harpoon") or {}
    harp_ratio = ((hs["catches_per_active_h"] / SV.CATCH_PER_HOUR)
                  * (SV.size_mult(hs["quality_mean"]) / SV.size_mult(k["size_score"])))
    rows = IL.build(D, statvals, incomes, harp_ratio, HV.Model())
    cph = k["casts_per_active_h"]
    for r in rows:
        r["casts"] = r["mat_h"] * cph
        # 미끼는 자기유지비 모델이 깨져 있다(위 docstring) → 총성능으로 순위
        r["perf"] = r["eff"] if r["cat"] == "미끼" else r["eff_net"]
        # ★상대성능 — 그 구간 시급 대비 %. 등급 간 비교는 반드시 이걸로 한다.
        r["rel"] = r["perf"] / incomes[r["stage"]] * 100.0
        # 낚시 외 활동(광질·바닐라) 비중 — 「캐스트」가 얼마나 비유인지 드러낸다
        r["mine_share"] = 0.0
    return D, k, rows, cph


def mine_share(D, name):
    """이 아이템 게이트 시간 중 광질/비낚시 활동이 차지하는 비율."""
    rec = D.recby.get(name)
    if not rec:
        return 0.0
    _, _, hact, _ = D.gate(D.expand(rec["ingredients"]))
    tot = sum(hact.values())
    if tot <= 0:
        return 0.0
    return sum(v for a, v in hact.items() if not a.startswith("낚시:")) / tot


# ══════════════════════════════════════════════════════════════════════════
#  단조감소 등위회귀 (PAVA) — 가중 최소제곱, log 공간
# ══════════════════════════════════════════════════════════════════════════
def isotonic_decreasing(vals, wts):
    """vals 를 단조감소로 만드는 가중 최소제곱 근사 (Pool Adjacent Violators)."""
    blocks = [[v, w] for v, w in zip(vals, wts)]     # [평균, 가중치]
    i = 0
    while i < len(blocks) - 1:
        if blocks[i][0] < blocks[i + 1][0] - 1e-12:  # 위반: 뒤가 더 크다
            v0, w0 = blocks[i]
            v1, w1 = blocks[i + 1]
            blocks[i] = [(v0 * w0 + v1 * w1) / (w0 + w1), w0 + w1]
            del blocks[i + 1]
            i = max(i - 1, 0)
        else:
            i += 1
    out = []
    for v, w in blocks:
        out += [v] * 0
    # 블록을 원래 길이로 펼친다
    res, bi, used = [], 0, 0.0
    counts = []
    # 블록별 원소 수를 다시 세기 위해 두 번째 패스
    blocks2 = [[v, w] for v, w in zip(vals, wts)]
    i, sizes = 0, [1] * len(vals)
    while i < len(blocks2) - 1:
        if blocks2[i][0] < blocks2[i + 1][0] - 1e-12:
            v0, w0 = blocks2[i]
            v1, w1 = blocks2[i + 1]
            blocks2[i] = [(v0 * w0 + v1 * w1) / (w0 + w1), w0 + w1]
            sizes[i] += sizes[i + 1]
            del blocks2[i + 1]
            del sizes[i + 1]
            i = max(i - 1, 0)
        else:
            i += 1
    for (v, _), n in zip(blocks2, sizes):
        res += [v] * n
    return res


def kappa_table(rows):
    """(카테고리, 등급) → κ = 캐스트 / 상대성능(%p). 현재값과 설계 사다리를 함께 낸다.

    설계 사다리:  κ(cat, g) = κ0(cat) × GRADE_SLOPE^(등급index)
    κ0 은 «그 카테고리의 현재 총수요 × GRADE_LIFT» 가 나오도록 정규화해서 정한다 —
    그래서 손으로 정하는 숫자는 SLOPE 와 LIFT **둘뿐**이고, 카테고리별 절대 수준은
    현재 상태에서 이어받는다(설계자가 카테고리마다 값을 찍지 않는다).
    """
    cur, des = {}, {}
    by_cat = collections.defaultdict(dict)
    for r in rows:
        if r["perf"] < MIN_EFF or r["casts"] <= 0 or r["grade"] in EXEMPT_GRADES:
            continue
        by_cat[r["cat"]].setdefault(r["grade"], []).append(r)
    for cat, gs in by_cat.items():
        grades = [g for g in GRADE_ORDER if g in gs and len(gs[g]) >= MIN_N]
        if not grades:
            continue
        for g in grades:
            cur[(cat, g)] = st.median([x["casts"] / x["rel"] for x in gs[g]])
        # κ0 정규화 — Σ(설계 캐스트) == Σ(현재 캐스트) × LIFT
        shape = {g: GRADE_SLOPE ** GRADE_ORDER.index(g) for g in grades}
        tot_cur = sum(x["casts"] for g in grades for x in gs[g])
        tot_raw = sum(shape[g] * x["rel"] for g in grades for x in gs[g])
        k0 = (tot_cur * GRADE_LIFT / tot_raw) if tot_raw > 0 else 1.0
        for g in grades:
            des[(cat, g)] = k0 * shape[g]
    return cur, des


def targets(rows, iso):
    """아이템별 목표 캐스트와 현재 대비 배율.

    3단계다. 순서가 중요하다 — 압축을 먼저 하고 정규화를 나중에 해야 총량이 맞는다.
      ① κ × 성능           (성능 비례 = 유저 요구의 본체)
      ② 동레벨 산포 압축     (LEVEL_SPREAD_CAP — 성능 사다리 결함이 재료로 새는 것을 막는다)
      ③ 카테고리 총량 정규화 (Σ목표 == Σ현재 — «밸런스 망가지지 않게»의 수식적 보증)
    """
    out = {}
    for r in rows:
        k = iso.get((r["cat"], r["grade"]))
        if k is None or r["perf"] < MIN_EFF or r["casts"] <= 0 or r["grade"] in EXEMPT_GRADES:
            continue
        out[r["name"]] = dict(target=k * r["rel"], cur=r["casts"], raw=None,
                              cat=r["cat"], grade=r["grade"], lv=r["lv"], perf=r["perf"],
                              rel=r["rel"], clamped=False)
    for v in out.values():
        v["raw"] = v["target"]

    # ② 동레벨 이상치 표시 (목표값은 건드리지 않는다 — 위 주석 참조)
    by_lv = collections.defaultdict(list)
    for n, v in out.items():
        by_lv[(v["cat"], v["lv"])].append(n)
    clamps = []
    for (cat, lv), names in by_lv.items():
        if len(names) < 2:
            continue
        ts = sorted(out[n]["target"] for n in names)
        med = ts[len(ts) // 2] if len(ts) % 2 else math.sqrt(ts[len(ts)//2 - 1] * ts[len(ts)//2])
        if max(ts) / min(ts) <= 1 + LEVEL_SPREAD_CAP + 1e-9:
            continue
        bad = [n for n in names if out[n]["target"] > med * (1 + LEVEL_SPREAD_CAP)]
        for n in bad:
            out[n]["clamped"] = True      # = «hold»: 이 종은 패치에서 뺀다
        clamps.append((cat, lv, max(ts) / min(ts) - 1,
                       [(n, out[n]["perf"], n in bad) for n in names]))

    # ③ 정규화는 kappa_table 의 κ0 이 이미 했다(총량 × LIFT). 여기서 다시 총량을 맞추면
    #    LIFT 가 상쇄돼 사라진다 — 초판의 «카테고리 총량 보존» 단계를 일부러 뺐다.
    norm = {cat: GRADE_LIFT for cat in {v["cat"] for v in out.values()}}

    for v in out.values():
        v["scale"] = v["target"] / v["cur"]
    return out, clamps, norm


# ══════════════════════════════════════════════════════════════════════════
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", action="append", default=None)
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--plan", action="store_true")
    ap.add_argument("--cat", default=None)
    a = ap.parse_args()

    D, K, rows, cph = build_rows()
    srcs = tuple(a.src) if a.src else DEFAULT_SRC
    pool = [r for r in rows if r["craftable"] and (a.all or r["src"] in srcs)]
    if a.cat:
        pool = [r for r in pool if r["cat"] == a.cat]

    cur, iso = kappa_table(pool)
    tg, clamps, norm = targets(pool, iso)

    if a.plan:
        print(json.dumps({n: round(v["scale"], 6) for n, v in tg.items()},
                         ensure_ascii=False, indent=1))
        return

    print(MEAS.banner(K))
    print(f"  캐스트 환율 {cph:.1f} 캐스트/h  ·  대상 {'전체' if a.all else '/'.join(srcs)} "
          f"제작가능 {len(pool)}종")
    print("  ★캐스트 = LP 재료게이트(h) × 캐스트/h. 광질·바닐라 구간은 «낚시 등가» 환산이다.")

    print(f"\n{'='*104}\nκ 사다리 — 상대성능 1%p(구간 시급 대비) 당 캐스트   [현재 → 설계]\n{'='*104}")
    print(f"{'카테고리':<7}" + "".join(f"{g:>13}" for g in GRADE_ORDER))
    for cat in ["낚싯대", "작살", "릴", "줄", "바늘", "찌", "미끼"]:
        line = f"{cat:<7}"
        any_ = False
        for g in GRADE_ORDER:
            if (cat, g) in cur:
                any_ = True
                c, i = cur[(cat, g)], iso[(cat, g)]
                mark = "" if abs(c - i) / c < 0.005 else "→"
                line += f"{c:>7.1f}{mark}{i:>5.1f}" if mark else f"{c:>13.1f}"
            else:
                line += f"{'-':>13}"
        if any_:
            print(line + ("   ×%.3f 정규화" % norm[cat] if cat in norm else ""))
    print(f"  설계 = κ0 × {GRADE_SLOPE:.2f}^등급  ·  κ0 은 카테고리 총수요 ×{GRADE_LIFT:.2f} 가 "
          f"되도록 정규화. 등급이 오를수록 «성능 대비» 비싸진다(유저 결정 2026-08-27).")
    print(f"  E 급은 사다리 밖(튜토) — 손대지 않는다.")

    for cat in ["낚싯대", "작살", "릴", "줄", "바늘", "찌", "미끼"]:
        arr = [r for r in pool if r["cat"] == cat and r["name"] in tg]
        if not arr:
            continue
        print(f"\n{'='*104}\n{cat}  (n={len(arr)})\n{'='*104}")
        print(f"{'등급':<3}{'Lv':>3} {'이름':<22}{'현재캐스트':>10}{'목표':>9}{'배율':>8}"
              f"{'상대%':>7}{'광질%':>7}  병목")
        for r in sorted(arr, key=lambda r: (GRADE_ORDER.index(r["grade"]), r["lv"], r["name"])):
            t = tg[r["name"]]
            ms = mine_share(D, r["name"]) * 100
            bn = ",".join(m for m, _ in r["bottleneck"][:2]) or "-"
            flag = "  ⚠" if abs(t["scale"] - 1) > 0.5 else ""
            print(f"{r['grade']:<3}{r['lv']:>3} {r['name']:<22}{r['casts']:>10,.0f}"
                  f"{t['target']:>9,.0f}{t['scale']:>8.2f}{r['rel']:>6.1f}%{ms:>7.0f}  {bn}{flag}")

    # ── 동레벨 산포 검증 (유저 목표: 성능차이만큼, 최대 25%) ────────────
    print(f"\n{'='*104}\n동레벨 요구캐스트 산포 — 목표 «성능차이만큼, 상한 "
          f"{LEVEL_SPREAD_CAP*100:.0f}%»\n{'='*104}")
    by_lv = collections.defaultdict(list)
    for r in pool:
        if r["name"] in tg:
            by_lv[(r["cat"], r["lv"])].append(r)
    print(f"{'카테고리':<7}{'Lv':>4}{'n':>3}{'성능산포':>10}{'현재':>8}{'목표':>8}  구성")
    over = 0
    for (cat, lv), arr in sorted(by_lv.items(), key=lambda kv: (kv[0][0], kv[0][1])):
        if len(arr) < 2:
            continue
        c = [r["casts"] for r in arr]
        t = [tg[r["name"]]["target"] for r in arr]
        pf = [r["perf"] for r in arr]
        sp, sc, stt = max(pf)/min(pf)-1, max(c)/min(c)-1, max(t)/min(t)-1
        mark = "  ←hold" if any(tg[r["name"]]["clamped"] for r in arr) else ""
        over += bool(mark)
        print(f"{cat:<7}{lv:>4}{len(arr):>3}{sp*100:>9.1f}%{sc*100:>7.1f}%{stt*100:>7.1f}%  "
              + ", ".join(r["name"] for r in arr) + mark)
    if clamps:
        print(f"\n  ★상한을 넘긴 {len(clamps)}쌍 — 이건 **성능 사다리 결함**이다(같은 레벨인데"
              " 성능이 두 배). 스탯을 먼저 고쳐야 하므로 **재료를 건드리지 않는다**(hold):")
        for cat, lv, ex, items in sorted(clamps, key=lambda x: -x[2]):
            det = ", ".join(f"{n} {p:,.0f}{'  ←hold' if b else ''}"
                            for n, p, b in sorted(items, key=lambda x: -x[1]))
            print(f"    {cat} Lv{lv}: 성능 격차 +{ex*100:.0f}%  ({det})")

    # ── 카테고리 총량 보존 확인 ────────────────────────────────────────
    print(f"\n{'='*104}\n카테고리 총수요 보존 («밸런스 망가지지 않게» 검증)\n{'='*104}")
    print(f"{'카테고리':<7}{'현재합':>11}{'목표합':>11}{'변화':>9}{'최대증':>9}{'최대감':>9}")
    for cat in ["낚싯대", "작살", "릴", "줄", "바늘", "찌", "미끼"]:
        arr = [r for r in pool if r["cat"] == cat and r["name"] in tg]
        if not arr:
            continue
        c = sum(r["casts"] for r in arr)
        t = sum(tg[r["name"]]["target"] for r in arr)
        sc = [tg[r["name"]]["scale"] for r in arr]
        print(f"{cat:<7}{c:>11,.0f}{t:>11,.0f}{(t/c-1)*100:>8.1f}%"
              f"{(max(sc)-1)*100:>8.0f}%{(min(sc)-1)*100:>8.0f}%")


if __name__ == "__main__":
    main()
