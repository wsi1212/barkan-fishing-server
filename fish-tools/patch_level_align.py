#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
patch_level_align.py — **동레벨 성능 산포**를 목표 밴드 안으로 정렬한다 (2026-08-27).

`village_scan [2]` 가 22 건을 잡았다. 같은 레벨에 여러 마을 아이템이 겹치는데 성능이
최대 2.1배 벌어진다(낚싯대 Lv52: 중개인 198,265 vs 근위 94,096). 유저 기준은 **≤25%** 다.

## 어떻게 맞추나 — «라인 초과분»만 스케일한다

    가치(item) = Σ (스탯 − 등급기반) × 가중치        가중치 = village_scan.WEIGHT_*
    목표 = 그 (카테고리, 레벨) 그룹의 **기하중위** 가치
    각 아이템의 초과분에 clamp(목표/자기, [1/MAX_S, MAX_S]) 를 곱한다

★왜 «가치 가중»인가: 스탯 크기로 맞추면 단위가 달라 엉뚱한 걸 깎는다(공격력 1점 =
  도망감소 38점). 라벨러와 같은 가중표를 쓰므로 판정과 조정이 같은 자를 쓴다.
★왜 «초과분»만인가: 기반(난이도·등급업·행운 등 전 종 공통분)을 건드리면 등급 정체성이
  깨진다. 라인 스탯만 움직이면 «어떤 빌드인가»는 그대로 두고 «얼마나 센가»만 맞춰진다.
★**게이트 스탯은 안 건드린다**(GATE_KEEP) — 공격력은 1점이 어종 등급을 가르고 난이도는
  순간이동 문턱을 가른다. 스케일하면 빌드가 아니라 «해금»이 바뀐다.

사용:
    python3 patch_level_align.py <BlockShip경로> [--apply] [--cap 0.25]
"""
import importlib.util, json, os, shutil, sys
import statistics as st

SKILL = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                     ".claude", "skills", "balance-audit", "scripts")


def _load(name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(SKILL, name + ".py"))
    m = importlib.util.module_from_spec(spec)
    sv, sys.argv = sys.argv, [name]
    spec.loader.exec_module(m)
    sys.argv = sv
    return m


#: 스케일에서 제외 — 게이트 스탯(1점이 «해금»을 바꾼다) + 야간투시(심해 월드 필수, 단계값).
#  ★돌진쿨감도 게이트다 — 45 미만이면 돌진 2회 조건을 못 넘어 **가치가 0** 이 된다.
#    초판이 이걸 스케일해서 중개인의 작살을 50 → 38(문턱 미달)로 죽였다.
GATE_KEEP = {"공격력", "난이도", "야간투시", "돌진쿨감"}
#: 정렬 자체를 면제하는 출처 — «사다리»가 아닌 특수 층이다.
#  ★심해 3종은 유저가 수중호흡·호흡시간 2000 을 명시 지정했고, 히든-전설은 사다리 밖이다.
#    초판이 이걸 안 빼서 심해 작살을 1175/1156 으로 깎고 야간투시 2→1 로 죽였다.
EXEMPT_SRC = {"심해", "히든-전설"}
#: ★«가치 가중 합 ÷ 순성능» 을 비중으로 쓰면 안 된다 — 단위가 다르다(가중표는 «판매보너스
#  1% = 1.00» 정규화 단위, 순성능은 원/h). 초판이 그렇게 해서 share 가 0.001 로 나오고
#  50종이 전부 «못 고침» 으로 막혔다. 대신 **반복 수렴**으로 푼다:
#    필요배율을 순성능에서 내고, 비게이트 초과분에 곱한 뒤, 원장을 다시 돌려 재측정한다.
#  게이트가 성능의 근원인 종(쇠날 작살의 공격력 2)은 수렴하지 않고 남는다 → 마지막에 보고.
PASSES = 6
#: 한 아이템에 걸 수 있는 최대 배율. 이보다 더 필요하면 라인 설계 문제라 보고만 한다.
MAX_S = 1.50
SKIPSRC = {"캐시", "개발자", "잠수상점"}


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    src = sys.argv[1]
    apply_ = "--apply" in sys.argv
    cap = 0.25
    if "--cap" in sys.argv:
        cap = float(sys.argv[sys.argv.index("--cap") + 1])
    os.environ["BLOCKSHIP_DATA"] = src
    VS = _load("village_scan")
    CC = VS.CC
    ppath = os.path.join(src, "parts.json")
    # ★백업은 **항상** 뜬다 — 반복 수렴이 파일을 읽고 쓰므로 dry-run 도 파일을 건드린다.
    #   dry-run 이면 마지막에 백업에서 되돌린다.
    shutil.copy(ppath, ppath + ".bak-align")
    allchanged, over = [], []
    for it in range(PASSES):
        n = _pass(src, ppath, VS, CC, cap, apply_, allchanged, over)
        print(f"  패스 {it+1}: {n}종 조정")
        if n == 0:
            break
    print(f"\n동레벨 정렬 — 상한 {cap*100:.0f}% · 누적 조정 {len(allchanged)}종")
    seen = set()
    for cat, lv, name, sc in allchanged:
        if (cat, lv, name) in seen:
            continue
        seen.add((cat, lv, name))
    for cat, lv, name, sc in allchanged[-40:]:
        print(f"    {cat} Lv{lv} {name:<18}×{sc:.2f}")
    if over:
        uniq = {(a, b, c) for a, b, c in over}
        print(f"\n★수렴하지 않은 {len(uniq)}종 — 성능이 게이트 스탯(공격력·난이도)에서 나온다."
              " 스탯 스케일로는 못 고치고 라인/등급 배치를 봐야 한다:")
        for a, b, c in sorted(uniq)[:14]:
            print(f"    {a} Lv{b} {c}")
    if not apply_:
        shutil.copy(ppath + ".bak-align", ppath)
        print("\n[dry-run] 파일을 되돌렸다. --apply 로 실제 반영")
    else:
        print("\n✅ parts.json 반영 → 다음: patch_cast_cost.py")
    return


def _pass(src, ppath, VS, CC, cap, apply_, allchanged, over):
    import math
    D, K, rows, cph = CC.build_rows()
    P = json.load(open(ppath, encoding="utf-8"))

    base_of = {}
    for cat in {r["cat"] for r in rows}:
        for g in ("D", "C", "B", "A", "S"):
            arr = [r for r in rows if r["cat"] == cat and r["grade"] == g
                   and r["src"] not in SKIPSRC]
            if arr:
                base_of[(cat, g)] = {a: b for a, b in VS.group_base(arr).items() if b}

    def wval(r):
        """라인 초과분의 가치 합."""
        W = VS.WEIGHT_SPEAR if r["cat"] == "작살" else VS.WEIGHT_ROD
        b = base_of.get((r["cat"], r["grade"]), {})
        tot = 0.0
        for k, v in r["stats"].items():
            if not isinstance(v, (int, float)) or k in GATE_KEEP:
                continue
            exc = v - b.get(k, 0)
            if exc > 0:
                tot += exc * W.get(k, 1.0)
        return tot

    groups = {}
    for r in rows:
        if r["src"] in SKIPSRC or r["src"] in EXEMPT_SRC or r["grade"] == "E":
            continue
        groups.setdefault((r["cat"], r["lv"]), []).append(r)

    changed = []
    for (cat, lv), arr in sorted(groups.items()):
        if len(arr) < 2:
            continue
        # ★판정과 목표는 **실제 순성능**으로 낸다. wval(가치 가중 초과분)은 «무엇을 얼마나
        #   깎을까»를 정하는 데만 쓴다 — 게이트 스탯을 제외하니 wval 자체는 성능의 대리가
        #   못 된다(쇠날 작살이 그래서 ×6.38 을 요구했다).
        import math
        vals = [(r["eff_net"], r) for r in arr]
        pos = [v for v, _ in vals if v > 0]
        if len(pos) < 2 or max(pos) / min(pos) - 1 <= cap:
            continue
        med = math.exp(sum(math.log(v) for v in pos) / len(pos))
        for v, r in vals:
            if v <= 0:
                continue
            want = min(med * (1 + cap / 2), max(med / (1 + cap / 2), v))
            s = want / v
            if abs(s - 1) < 0.03:
                continue
            s_c = max(1 / MAX_S, min(MAX_S, s))
            if abs(s_c - s) > 1e-9:
                over.append((cat, lv, r["name"]))
            b = base_of.get((cat, r["grade"]), {})
            new = {}
            for k, val in r["stats"].items():
                if not isinstance(val, (int, float)) or k in GATE_KEEP:
                    new[k] = val
                    continue
                exc = val - b.get(k, 0)
                new[k] = (b.get(k, 0) + max(1, round(exc * s_c))) if exc > 0 else val
            f = P["parts"][cat][r["name"]].split("|")
            f[4] = ",".join(f"{a}:{x:g}" if isinstance(x, (int, float)) else f"{a}:{x}"
                            for a, x in new.items())
            P["parts"][cat][r["name"]] = "|".join(f)
            changed.append((cat, lv, r["name"], s_c))

    allchanged.extend(changed)
    # ★dry-run 이라도 다음 패스의 재측정을 위해 **파일에 써야** 한다. 그래서 dry-run 은
    #   임시 사본에 쓰고 끝에 되돌린다 — 여기서는 apply_ 여부와 무관하게 쓰고, apply_ 가
    #   아니면 호출부가 백업에서 복원한다.
    json.dump(P, open(ppath, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    return len(changed)


if __name__ == "__main__":
    main()
