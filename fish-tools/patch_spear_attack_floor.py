#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
patch_spear_attack_floor.py — 작살 공격력을 «등급 하한»까지 올리고, 올린 만큼 다른 스탯을
또래 작살 수준으로 되돌린다 (2026-09-19).

## 왜

작살 공격력의 설계 권위는 `.claude/skills/balance-audit/scripts/spear_lines.py` 의 `BASE` 다
— «공격력은 등급별 최소치이고 라인 손잡이로 쓰면 안 된다»(1점이 등급 게이트를 넘겨 수입
4.5배를 만든다). 그런데 그 스크립트의 `ASSIGN` 이 스폰마을+대장간 20종만 덮어서, 사막·상단·
왕도·전설 47종은 옛 `gen_spear_builds.py` 규약(주력 {B4,A5,S7} / 부 {B2,A3,S4}, 복합형 ×0.8)
그대로 남았다. 결과가 27종 하한 미달이고, 그 중 S 6종은 공3~4다.

prod 2026-09 실측이 그 영향을 보여준다 — S어종 도주율이 공4에서 0~6%(다이아 70/0, 강철 75/5),
공3에서 20~24%(잠수부 51/16, 대상단 31/8)다. Lv61·194만원짜리 왕실 작살(공3)이 Lv40·78만원짜리
다이아 작살(공4)보다 S어종을 못 잡는다.

## 무엇을 하나

① 공격력 < BASE[등급] 인 작살의 공격력을 BASE 까지 올린다. **공격력만 건드린다.**
② 그 상향분만큼 **다른 스탯을 비례 축소**한다. 등급 중앙값을 기본으로 하되 같은 등급 안에서도
   해금 레벨이 높을수록 최대 +12%, 히든 출처는 추가 +6%의 목표 성능을 허용한다. 총원가(가격+재료)는
   안 건드리므로 회수시간 = 총원가 / eff 다. 이미 목표보다 낮으면 **아무것도 깎지 않는다**(순상향).

원/h 판정은 `item_ledger.build` 와 **같은 식**을 쓴다(작살 67종 재현 오차 0.0000원/h 검산).
창 전용 스탯은 `harpoon_value` 모델(사이클+등급천장), 보상 스탯은 `stat_value` 단가다.

## 안 깎는 것

  · 공격력 — 이 패치가 올리는 축
  · 야간투시 — 가치 모델이 없는 심해 3종 정체성(SPEAR_UNMODELED)
  · 수중호흡은 `HarpoonManager.breathFloor` 등급 하한 아래로 안 내린다(코드가 어차피 올려
    잡으므로 그 아래 숫자는 «표시만 되는 거짓말»이다)
  · 돌진쿨감은 45 아래로 안 내린다 — 돌진 2회 문턱이라 그 아래는 아무 일도 안 한다
    (spear_lines.DASH_MIN 과 같은 근거)
  · 원래 1 이상이던 스탯은 0 으로 지우지 않는다(빌드 정체성이 통째로 사라진다)

사용:
    python3 patch_spear_attack_floor.py <BlockShip경로>            # dry-run
    python3 patch_spear_attack_floor.py <BlockShip경로> --apply
"""
import importlib.util, json, os, shutil, statistics, sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.join(os.path.dirname(HERE), ".claude", "skills", "balance-audit", "scripts")


def _load(name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(SKILL, name + ".py"))
    m = importlib.util.module_from_spec(spec)
    sv, sys.argv = sys.argv, [name]
    spec.loader.exec_module(m)
    sys.argv = sv
    return m


#: 깎지 않는 스탯.
KEEP = {"공격력", "야간투시"}
#: 돌진 2회 문턱 — 이 아래로는 내리지 않는다(내리면 «아무 일도 안 하는 스탯»이 된다).
DASH_MIN = 45
#: ★스탯 레버의 바닥. 기타 스탯을 이 배율보다 더 깎아야 또래에 닿는다면 **건드리지 않고
#  보류**한다. 주력 스탯이 반 넘게 날아가면 그 작살은 더 이상 그 빌드가 아니다(크리형의
#  크리확률 38→1). 그런 종은 스탯이 아니라 **원가가 등급에 안 맞는 것**이다 — 왕도 S 5종은
#  총원가 267만~329만인데 하한을 지키는 S 4종은 641만~840만이다(2~3배). 레시피 쪽
#  (`patch_cast_cost.py`)에서 올릴 일이지 여기서 스탯을 깎아 덮을 일이 아니다.
IDENTITY_FLOOR = 0.40
#: 같은 등급 안의 레벨 진행으로 허용할 최대 성능 차이. 등급은 사냥터, 레벨은 미세 성장이다.
LEVEL_PERF_SPREAD = 0.12
#: 히든은 발견·재료 관문을 더 통과한 보상으로, 같은 레벨 일반품보다 조금 강하게 남긴다.
HIDDEN_PERF_BONUS = 0.06


def stat_str(st, order):
    return ",".join(f"{k}:{st[k]:g}" for k in order if st.get(k))


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    src, apply_ = sys.argv[1], "--apply" in sys.argv
    os.environ["BLOCKSHIP_DATA"] = os.path.abspath(src)

    SL = _load("spear_lines")
    IL = _load("item_ledger")
    BASE = {g: v["공격력"] for g, v in SL.BASE.items()}
    BASE.setdefault("E", 1)

    D = IL.MV.Data()
    k = D.k
    IL.MEAS.apply(IL.SV, k)
    statvals, incomes = {}, {}
    for stage in IL.SV.STAGES:
        r = IL.SV.compute(stage)
        statvals[stage] = {kk: v[0] for kk, v in r["V"].items()}
        incomes[stage] = r["income"]
    hs = k.get("harpoon") or {}
    hr = ((hs.get("catches_per_active_h") or 174.8) / IL.SV.CATCH_PER_HOUR
          * (IL.SV.size_mult(hs.get("quality_mean") or IL.HARPOON_QUALITY)
             / IL.SV.size_mult(k["size_score"])))
    HM = IL.HV.Model()
    P = json.load(open(os.path.join(src, "parts.json"), encoding="utf-8"))
    origins = {name: raw.split("|")[6] for name, raw in P["parts"]["작살"].items()}
    rows = {r["name"]: r for r in IL.build(D, statvals, incomes, hr, HM) if r["cat"] == "작살"}

    _bc = {}

    def spear_base(lv):
        key = 10 if lv < 20 else (30 if lv < 50 else 60)
        if key not in _bc:
            dist = HM.dist_for(key)
            _bc[key] = (HM.income(HM.effective("나무 작살"), dist), dist)
        return _bc[key]

    def eff_of(name, stats):
        """item_ledger.build 의 작살 eff 를 임의 스탯으로 재현(검산 오차 0원/h)."""
        m = rows[name]
        V = statvals[IL.STAGE_OF_LEVEL(m["lv"])]
        inc = growth = gate = 0.0
        for kk, v in stats.items():
            if not isinstance(v, (int, float)):
                continue
            if kk in IL.STAT_KEY:
                inc += v * V[IL.STAT_KEY[kk]] * hr
            elif kk in IL.GROWTH_KEY:
                growth += v * V[IL.GROWTH_KEY[kk]] * hr
            elif kk in IL.GATE_KEY:
                gate += v * V[IL.GATE_KEY[kk]]
        b, dist = spear_base(m["lv"])
        st = dict(stats)
        st["수중호흡"] = max(st.get("수중호흡", 0), IL.HV.BREATH_FLOOR.get(m["grade"], 5))
        st["공격력"] = max(1, st.get("공격력", 0))
        st["_harpoon_grade"] = m["grade"]
        return inc + gate + growth + (HM.income(st, dist) - b)

    # ── 등급별 «하한을 지키는 또래»의 회수시간 중앙값 = 목표 ──────────────
    target_h = {}
    for g in ("D", "C", "B", "A", "S", "G"):
        ok = [r["payback"] for r in rows.values()
              if r["grade"] == g and r["stats"].get("공격력", 0) >= BASE.get(g, 0)
              and r["payback"] == r["payback"] and r["payback"] != float("inf")]
        if ok:
            target_h[g] = statistics.median(ok)
    grade_levels = {
        g: (min(r["lv"] for r in rows.values() if r["grade"] == g),
            max(r["lv"] for r in rows.values() if r["grade"] == g))
        for g in target_h
    }

    def target_eff(m, grade_payback):
        lo, hi = grade_levels[m["grade"]]
        level_progress = 0.0 if hi <= lo else (m["lv"] - lo) / (hi - lo)
        bonus = LEVEL_PERF_SPREAD * level_progress
        if origins.get(m["name"], "").startswith("히든"):
            bonus += HIDDEN_PERF_BONUS
        return m["total"] / grade_payback * (1.0 + bonus)

    viol = [n for n, r in rows.items() if r["stats"].get("공격력", 0) < BASE.get(r["grade"], 0)]
    viol.sort(key=lambda n: (list("EDCBASMLG").index(rows[n]["grade"]), rows[n]["lv"]))

    def scaled(name, s):
        """cuttable 스탯을 s 배 — 보호 규칙 적용, 정수화."""
        m = rows[name]
        out = {}
        for kk, v in m["stats"].items():
            if kk in KEEP or not isinstance(v, (int, float)):
                out[kk] = v
                continue
            nv = v * s
            if kk == "수중호흡":
                nv = max(nv, IL.HV.BREATH_FLOOR.get(m["grade"], 5))
            elif kk == "돌진쿨감" and v > 0:
                nv = max(nv, DASH_MIN)
            nv = int(round(nv))
            if v >= 1 and nv < 1:
                nv = 1
            out[kk] = nv
        out["공격력"] = BASE[m["grade"]]
        return out

    plan, held = {}, []
    print(f"{'등':>2} {'Lv':>4} {'작살':<16}{'공':>7} {'eff원/h 전→후':>26} {'회수h 전→후':>18}  비고")
    for g in ("B", "A", "S"):
        th = target_h.get(g)
        if th:
            print(f"── {g}등급 · 또래(하한 충족) 회수 중앙값 {th:.1f}h ──")
        for n in [x for x in viol if rows[x]["grade"] == g]:
            m = rows[n]
            total, e0, h0 = m["total"], m["eff"], m["payback"]
            raised = scaled(n, 1.0)                      # 공격력만 올린 상태
            e_raise = eff_of(n, raised)
            tgt = target_eff(m, th) if th and total == total else None
            note = ""
            if tgt is None or e_raise <= tgt:
                final, s = raised, 1.0
                note = "보정 없음(또래 이하)"
            else:
                lo, hi = 0.0, 1.0
                for _ in range(60):                       # 이분법
                    mid = (lo + hi) / 2
                    if eff_of(n, scaled(n, mid)) > tgt:
                        hi = mid
                    else:
                        lo = mid
                s = lo
                if s < IDENTITY_FLOOR:
                    held.append((n, m, e_raise, total / e_raise, tgt))
                    print(f"{g:>2} {m['lv']:>4} {n:<16}{m['stats'].get('공격력',0):>3g}→{BASE[g]:<3}"
                          f"{'':>12}  {'':>12} {h0:>8.1f} → {'':>7}  "
                          f"🚫 보류 — 스탯 ×{s:.2f} 까지 깎아야 함(빌드 소멸). 원가 레버 필요")
                    continue
                final = scaled(n, s)
                note = f"기타 스탯 ×{s:.2f}"
            e1 = eff_of(n, final)
            h1 = total / e1 if (total == total and e1 > 0) else float("inf")
            plan[n] = final
            print(f"{g:>2} {m['lv']:>4} {n:<16}{m['stats'].get('공격력',0):>3g}→{BASE[g]:<3}"
                  f"{e0:>12,.0f} →{e1:>12,.0f} {h0:>8.1f} →{h1:>8.1f}  {note}")
            ch = [f"{kk} {m['stats'].get(kk,0):g}→{final[kk]:g}"
                  for kk in final if final[kk] != m["stats"].get(kk, 0) and kk != "공격력"]
            if ch:
                print(f"{'':>7}   {' · '.join(ch)}")

    order = SL.STAT_ORDER + [x for x in ("야간투시",) if True]
    for n, st in plan.items():
        f = P["parts"]["작살"][n].split("|")
        f[4] = stat_str(st, order + [kk for kk in st if kk not in order])
        P["parts"]["작살"][n] = "|".join(f)

    if held:
        print("\n🚫 보류 — 스탯으로는 못 맞춘다(원가가 등급에 안 맞음). 이 종은 건드리지 않았다:")
        print(f"{'':>4}{'작살':<16}{'현재총원가':>12}{'공하한시 eff':>14}{'그때 회수h':>10}"
              f"{'또래맞춤 필요총원가':>20}{'배수':>7}")
        for n, m, e, h, tgt in held:
            need = e * (m["total"] / tgt)
            print(f"{'':>4}{n:<15}{m['total']:>12,.0f}{e:>14,.0f}{h:>10.1f}"
                  f"{need:>20,.0f}{need / m['total']:>6.1f}배")
    if not apply_:
        print(f"\n[dry-run] {len(plan)}종 변경 예정 · {len(held)}종 보류. 반영하려면 --apply")
        return
    dst = os.path.join(src, "parts.json")
    shutil.copy2(dst, dst + ".bak")
    with open(dst, "w", encoding="utf-8") as fh:      # 끝 개행 유지(diff 노이즈 방지)
        json.dump(P, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    print(f"\n[apply] {len(plan)}종 반영 → {dst} (백업 {dst}.bak)")


if __name__ == "__main__":
    main()
