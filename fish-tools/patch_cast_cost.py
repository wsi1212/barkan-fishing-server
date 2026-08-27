#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
patch_cast_cost.py — 장비 레시피의 «요구 캐스트»를 성능 비례로 재조정한다 (2026-08-27).

유저 요청:
    "지금 평균 장비를 만들기 위해 몇 캐스트가 필요한지 구하고 그거 재료 요구 개수를
     수정하는 작업 해줘. 밸런스 망가지지 않게. 같은 등급이라도 성능차이에 따라
     10~25%까지 차이나게 요구캐스트. 일단 스폰마을부터"

목표값의 산출은 **`.claude/skills/balance-audit/scripts/cast_cost.py` 가 단일 권위**다.
여기서는 그 목표 캐스트에 «정수 재료 수량»을 맞추는 일만 한다. 목표 모델(κ 등위회귀·
동레벨 압축·카테고리 총량 보존)을 바꾸려면 저쪽을 고칠 것 — 이 파일에 복제하지 말 것.

## 왜 「균등 배율 + 국소 탐색」인가
  LP 게이트는 수요벡터에 **1차 동차**다 — 모든 재료를 s 배 하면 게이트도 정확히 s 배다.
  그래서 «균등 배율»이 수학적으로 정확한 해이고, 오차는 오직 **정수 반올림**에서만 온다.
  그런데 수량이 1~8 로 작아서 반올림 오차가 크다(균등 반올림만 하면 중앙 +6.7%, 최악 +84%).
  → 균등 반올림을 출발점으로 두고 ±1 좌표하강으로 목표에 맞춘다. 출발점이 균등이라
    레시피 «생김새»가 원본을 유지한다(병목 재료만 폭증하는 해를 피한다).

## 바닥(floor) 문제 — 중간재가 최저 원가를 만든다
  모든 재료를 1 개로 줄여도 남는 비용이 바닥이다. 정제된갈고리 1 개 = 낡은갈고리 8 개
  = **146 캐스트** 라서, 이걸 쓰는 D 급 저가 아이템은 목표(87~142)로 내려갈 수가 없다.
  해당 종에 한해 **중간재를 그 원재료로 되돌린다**(정제된갈고리1 → 낡은갈고리 N, N<8).
  ★단일 원재료 중간재만 되돌린다 — 단단한자루·강철심은 원재료가 여럿이라 되돌리면
    레시피가 커지고 정체성이 깨진다. 그 종은 바닥을 받아들이고 보고한다.

사용:
    python3 patch_cast_cost.py <BlockShip경로>            # dry-run
    python3 patch_cast_cost.py <BlockShip경로> --apply
"""
import collections, importlib.util, json, math, os, shutil, sys

SKILL = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                     ".claude", "skills", "balance-audit", "scripts")


def _load(name, d=SKILL):
    spec = importlib.util.spec_from_file_location(name, os.path.join(d, name + ".py"))
    m = importlib.util.module_from_spec(spec)
    sv, sys.argv = sys.argv, [name]
    spec.loader.exec_module(m)
    sys.argv = sv
    return m


#: 되돌리기 가능한 중간재 — {중간재: [(원재료, 1개당 수량), …]}. recipes.json 의 direct
#  레시피 그대로다(복제가 아니라 «되돌리기 허용 목록»이다 — 비율은 코드가 읽지 않고
#  여기 적힌 값을 쓰므로, 중간재 레시피를 고치면 여기도 고칠 것).
#  ★왜 되돌리나: 중간재 1 개가 큰 덩어리라 **정수 격자가 성글다**.
#    정제된갈고리 1 개 = 146 캐스트 → 1↔2 사이에 목표가 떨어지면 ±25% 를 피할 수 없다.
#    되돌리면 낡은갈고리 1 개 = 18 캐스트라 격자가 8 배 잘아진다. 요구 총량은 동일하다.
#  ★단단한자루(강화실12+물고기비늘16)는 **일부러 뺐다**. 되돌리면 오차는 잡히지만
#    「자루 없는 작살」이 되고 물고기비늘이 33 개까지 불어난다 — 정체성이 정확도보다 앞선다.
UNWRAP = {
    "정제된갈고리": [("낡은갈고리", 8)],
    # ★강철심 → 녹슨부품 «강등»(되돌리기가 아니다 — 강화철괴2·강화석탄4 를 버린다).
    #   D 작살 4종(갯벌·물때·벼린·여울)이 목표 117~165 인데 바닥이 277 이라 못 내려갔다.
    #   바닥의 정체가 강철심 1 개다. 그런데 이 넷은 전부 **공격력 1** — harpoon 모델에서
    #   공격력이 잡을 수 있는 어종 등급을 가르고, 1→2 에서 성능이 3.4배 뛴다(C 작살 = 공격력 2).
    #   즉 「공격력 1짜리 원시 작살」이 강철심(C~B 급 중간재)을 요구하고 있던 것이고,
    #   빼는 게 수치상으로도 테마상으로도 맞다. 강철심 레시피의 녹슨부품 8 만 남긴다.
    "강철심": [("녹슨부품", 8)],
}
#: 되돌리기를 허용하는 등급. C 이상에서 «정제된» 부품을 «낡은» 원재료로 바꾸면 등급이
#  내려간 느낌이 든다 — 저티어에서만 푼다(D 는 원래 조악한 장비가 컨셉이다).
UNWRAP_GRADES = {"E", "D"}
#: 강등은 더 좁게 — 되돌리기와 달리 재료 구성이 실제로 바뀐다. 근거가 있는 곳만.
UNWRAP_ONLY = {"강철심": {"작살"}}
#: 수량 상한 — 이보다 크면 GUI 에서 읽기 힘들고 «재료 요구»가 아니라 «노가다»가 된다.
MAX_QTY = 48
#: 허용 오차 — 이 안에 들면 탐색을 멈춘다.
TOL = 0.02
#: 이 이상 틀어지면 중간재 되돌리기를 시도한다(격자를 잘게 만드는 최후수단).
UNWRAP_AT = 0.08
#: 모양 벌점 — 균등 배율에서 멀어지는 만큼 벌점(로그거리 합 × 이 계수).
#  ★없으면 좌표하강이 «병목 재료 하나만 8→1» 같은 해로 간다. 캐스트는 맞지만 레시피가
#    망가진다(재료 정체성·GUI 가독성). 0.02 면 오차 1%p 를 줄이려고 어떤 재료를 2배
#    비틀지는 않는 정도다. 정확도가 우선이되 동률이면 원본 비율을 지킨다.
SHAPE_W = 0.05


def unwrap_display(R, mid):
    """다른 레시피에서 그 재료의 displayName/mcItem 을 빌려온다(표시 일관성)."""
    for v in R["recipes"].values():
        for i in v.get("ingredients", []):
            if i.get("typeOrMatId") == mid:
                return i.get("displayName"), i.get("mcItem")
    return mid, "stick"


def unwrap_at(R, ings, j):
    """ings[j] 의 중간재를 원재료로 되돌린 새 재료목록. 같은 재료가 이미 있으면 합친다."""
    mid, n = ings[j]["typeOrMatId"], ings[j]["qty"]
    out = [dict(i) for i in ings[:j]] + [dict(i) for i in ings[j + 1:]]
    for base, ratio in UNWRAP[mid]:
        hit = next((i for i in out if i.get("typeOrMatId") == base), None)
        if hit:
            hit["qty"] += n * ratio
        else:
            dn, mc = unwrap_display(R, base)
            out.insert(j, {"kind": "custom", "typeOrMatId": base, "displayName": dn,
                           "mcItem": mc, "qty": n * ratio})
    return out


def solve(D, cph, ings, target, s):
    """정수 수량 벡터를 찾는다. 반환 (수량리스트, 캐스트, 로그오차)."""
    def casts(q):
        h, _, _, _ = D.gate(D.expand([dict(i, qty=x) for i, x in zip(ings, q)]))
        return h * cph

    ideal = [max(1.0, i["qty"] * s) for i in ings]

    def cost(q, c):
        err = abs(math.log(c / target)) if c > 0 else 9e9
        shape = sum(abs(math.log(x / y)) for x, y in zip(q, ideal))
        return err + SHAPE_W * shape, err

    lo = [1] * len(ings)
    hi = [max(3, min(MAX_QTY, int(math.ceil(i["qty"] * s * 2)) + 1)) for i in ings]
    q = [max(lo[j], min(hi[j], int(round(i["qty"] * s)))) for j, i in enumerate(ings)]
    best, bc = q[:], casts(q)
    bobj, berr = cost(best, bc)
    # 좌표하강 — 개선이 없을 때까지 각 좌표에 ±1
    for _ in range(60):
        if berr <= math.log(1 + TOL) and bobj <= berr + 1e-9:
            break
        moved = False
        for j in range(len(ings)):
            for d in (-1, 1):
                v = best[j] + d
                if v < lo[j] or v > hi[j]:
                    continue
                t = best[:]
                t[j] = v
                c = casts(t)
                o, e = cost(t, c)
                if o < bobj - 1e-9:
                    best, bc, bobj, berr, moved = t, c, o, e, True
        if not moved:
            break
    return best, bc, berr


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    src, apply_ = sys.argv[1], "--apply" in sys.argv
    os.environ["BLOCKSHIP_DATA"] = src

    CC = _load("cast_cost")
    D, K, rows, cph = CC.build_rows()
    pool = [r for r in rows if r["craftable"] and r["src"] in CC.DEFAULT_SRC]
    cur, iso = CC.kappa_table(pool)
    tg, clamps, norm = CC.targets(pool, iso)

    R = json.load(open(os.path.join(src, "recipes.json"), encoding="utf-8"))
    byname = {}
    for k, v in R["recipes"].items():
        n = (v.get("rodPartName") if v["resultMode"] == "rod"
             else v.get("resultPartName") if v["resultMode"] == "part" else None)
        if n:
            byname[n] = k

    out, floored, unwrapped, held = [], [], [], []
    for name, v in sorted(tg.items(), key=lambda kv: (kv[1]["cat"], kv[1]["lv"], kv[0])):
        rid = byname.get(name)
        if not rid:
            continue
        if v["clamped"]:
            # 동레벨 성능 이상치 — 스탯 결함이라 재료로 덮지 않는다(cast_cost 주석 참조)
            held.append((name, v))
            continue
        ings = [dict(i) for i in R["recipes"][rid]["ingredients"]]
        orig = [i["qty"] for i in ings]

        # ── 원본으로 풀어 보고, 못 맞추면 중간재를 되돌려 격자를 잘게 만든다 ──
        q, c, err = solve(D, cph, ings, v["target"], v["scale"])
        if math.exp(err) - 1 > UNWRAP_AT:
            for j, i in enumerate(ings):
                mid = i.get("typeOrMatId")
                if mid not in UNWRAP or v["grade"] not in UNWRAP_GRADES:
                    continue
                if mid in UNWRAP_ONLY and v["cat"] not in UNWRAP_ONLY[mid]:
                    continue
                alt = unwrap_at(R, ings, j)
                q2, c2, e2 = solve(D, cph, alt, v["target"], v["scale"])
                if e2 < err - 1e-9:
                    ings, q, c, err = alt, q2, c2, e2
                    unwrapped.append((name, i["typeOrMatId"],
                                      "+".join(b for b, _ in UNWRAP[i["typeOrMatId"]])))
                    break
        if math.exp(err) - 1 > UNWRAP_AT:
            floored.append((name, v["target"], c))
        for i, x in zip(ings, q):
            i["qty"] = x
        out.append(dict(name=name, rid=rid, cat=v["cat"], grade=v["grade"], lv=v["lv"],
                        cur=v["cur"], target=v["target"], got=c, err=math.exp(err) - 1,
                        ings=ings, orig=orig,
                        origids=[i["typeOrMatId"] for i in R["recipes"][rid]["ingredients"]]))

    # ── 보고 ───────────────────────────────────────────────────────────
    print(f"대상 {len(out)}종  ·  캐스트 환율 {cph:.1f}/h")
    for cat in ["낚싯대", "작살", "릴", "줄", "바늘", "찌", "미끼"]:
        arr = [r for r in out if r["cat"] == cat]
        if not arr:
            continue
        print(f"\n{'='*112}\n{cat} (n={len(arr)})\n{'='*112}")
        print(f"{'등':<2}{'Lv':>3} {'이름':<20}{'현재':>7}{'목표':>7}{'결과':>7}{'오차':>7}  재료 변화")
        for r in arr:
            was = dict(zip(r["origids"], r["orig"]))
            ch = ", ".join(
                (f"{i['typeOrMatId']} {was[i['typeOrMatId']]}→{i['qty']}"
                 if i["typeOrMatId"] in was and was[i["typeOrMatId"]] != i["qty"]
                 else f"{i['typeOrMatId']} {i['qty']}"
                 + ("★" if i["typeOrMatId"] not in was else ""))
                for i in r["ings"])
            gone = [m for m in was if m not in {i["typeOrMatId"] for i in r["ings"]}]
            if gone:
                ch += "  (−" + ",".join(gone) + ")"
            print(f"{r['grade']:<2}{r['lv']:>3} {r['name']:<20}{r['cur']:>7,.0f}"
                  f"{r['target']:>7,.0f}{r['got']:>7,.0f}{r['err']*100:>6.1f}%  {ch}")

    e = sorted(abs(r["err"]) for r in out)
    print(f"\n오차: 중앙 {e[len(e)//2]*100:.1f}% · 90분위 {e[int(len(e)*0.9)]*100:.1f}% · "
          f"최악 {e[-1]*100:.1f}%  (허용 {TOL*100:.0f}%)")
    if held:
        print(f"\n★hold {len(held)}종 — 같은 레벨 안에서 성능이 이상치라 **재료를 건드리지 않았다**."
              " 스탯 사다리를 먼저 고쳐야 한다:")
        for n, v in held:
            print(f"   {v['cat']} {v['grade']} Lv{v['lv']} {n}: 성능 {v['perf']:,.0f}원/h · "
                  f"현재 {v['cur']:,.0f} 캐스트 (성능비례라면 {v['target']:,.0f})")
    if unwrapped:
        print(f"\n중간재 되돌림 {len(unwrapped)}건 (바닥이 목표보다 높아서):")
        for n, a, b in unwrapped:
            print(f"   {n}: {a} → {b}")
    if floored:
        print(f"\n★정수 격자로 목표에 못 닿은 {len(floored)}종 — 되돌릴 수 없는 중간재"
              "(강철심·압축흑정석)가 큰 덩어리라 그 배수 사이에 목표가 떨어진다:")
        for n, t, f in floored:
            print(f"   {n}: 목표 {t:,.0f} → 실제 {f:,.0f} ({f/t-1:+.0%})")

    # ── 총량 검증 ──────────────────────────────────────────────────────
    print(f"\n{'='*112}\n총수요 검증\n{'='*112}")
    print(f"{'카테고리':<7}{'현재합':>10}{'목표합':>10}{'결과합':>10}{'변화':>9}")
    for cat in ["낚싯대", "작살", "릴", "줄", "바늘", "찌", "미끼"]:
        arr = [r for r in out if r["cat"] == cat]
        if not arr:
            continue
        a = sum(r["cur"] for r in arr)
        b = sum(r["target"] for r in arr)
        c = sum(r["got"] for r in arr)
        print(f"{cat:<7}{a:>10,.0f}{b:>10,.0f}{c:>10,.0f}{(c/a-1)*100:>8.1f}%")

    if not apply_:
        print("\n[dry-run] --apply 로 실제 반영")
        return
    for r in out:
        R["recipes"][r["rid"]]["ingredients"] = r["ings"]
    p = os.path.join(src, "recipes.json")
    shutil.copy(p, p + ".bak-castcost")
    json.dump(R, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"\n✅ recipes.json 반영 {len(out)}종 (백업 {os.path.basename(p)}.bak-castcost)")
    print("   → /데이터리로드 또는 서버 재시작 후 확인")


if __name__ == "__main__":
    main()
