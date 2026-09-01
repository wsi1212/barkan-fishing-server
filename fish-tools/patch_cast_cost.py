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
def _unwrap_from_recipes():
    """되돌리기 비율을 recipes.json «권위»에서 읽는다.

    ★2026-09-01: 예전엔 아래 표에 비율을 손으로 적어 뒀고 주석에 「중간재 레시피를 고치면
      여기도 고칠 것」이라 써 뒀는데 — 실제로 갈라져 있었다(표 낡은갈고리 8 vs 라이브 4).
      사본을 갱신하는 대신 권위를 직접 읽는다.
    """
    import json as _j, pathlib as _p
    live = _p.Path("/Users/user/Library/Application Support/feather/player-server/servers/"
                   "07de2d81-991a-47e2-b62d-06c0d1b5150a/plugins/BlockShip/recipes.json")
    want = {"정제된갈고리": "C01", "강철심": "C03"}
    out = {}
    try:
        recs = _j.loads(live.read_text(encoding="utf-8"))["recipes"]
    except Exception:
        return None
    for mat, rid in want.items():
        r = recs.get(rid)
        if not r:
            continue
        ings = [(i.get("typeOrMatId"), i.get("qty", 1)) for i in r.get("ingredients") or []]
        if mat == "정제된갈고리":
            out[mat] = ings                      # 단일 원재료 — 그대로 되돌린다
        else:
            # 강철심은 «강등»이다 — 녹슨부품만 남긴다(아래 주석 참조)
            out[mat] = [(k, q) for k, q in ings if k == "녹슨부품"] or ings
    return out or None


UNWRAP = _unwrap_from_recipes() or {
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
# ★48 → 64 (2026-08-28). 종결 1종(바르칸 낚싯대 Lv70 히든-전설)이 재료 10종을 전부 48 에
#   붙이고도 목표에 −23% 모자랐다. 커스텀 재료는 paper 기반이라 한 스택이 64 다.
#   상한은 «닿을 수 있는 천장»이어야 한다 — 목표는 그대로이므로 다른 종은 영향이 없다
#   (필요할 때만 올라간다).
MAX_QTY = 64
#: 허용 오차 — 이 안에 들면 탐색을 멈춘다.
TOL = 0.02
#: 이 이상 틀어지면 중간재 되돌리기를 시도한다(격자를 잘게 만드는 최후수단).
UNWRAP_AT = 0.08
#: 모양 벌점 — 균등 배율에서 멀어지는 만큼 벌점(로그거리 합 × 이 계수).
#  ★없으면 좌표하강이 «병목 재료 하나만 8→1» 같은 해로 간다. 캐스트는 맞지만 레시피가
#    망가진다(재료 정체성·GUI 가독성). 0.02 면 오차 1%p 를 줄이려고 어떤 재료를 2배
#    비틀지는 않는 정도다. 정확도가 우선이되 동률이면 원본 비율을 지킨다.
SHAPE_W = 0.05
#: 바닥에 걸린 종(relax)에서만 쓰는 모양 벌점 — 훨씬 낮다.
#  ★왜 낮추나: relax 는 «생김새보다 정확도를 택하는 마지막 수단»인데, 원래 수량이 1 인
#    재료를 20 으로 올려야 목표에 닿는 경우 벌점이 log(20/1)=3.0 까지 붙어 정확도 이득
#    (오차 18%→1%)을 이긴다. 그러면 탐색을 아무리 넓혀도 부정확한 해가 남는다
#    (2026-08-28 벼린 작살). 여기서는 목표 적중이 우선이다.
SHAPE_W_RELAX = 0.01


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


def solve(D, cph, ings, target, s, relax=False):
    """정수 수량 벡터를 찾는다. 반환 (수량리스트, 캐스트, 로그오차).

    ★relax — 재료별 상한을 «균등배율의 2배»가 아니라 MAX_QTY 까지 푼다.
      기본 상한은 레시피 «생김새»를 지키려고 좁게 잡혀 있는데, 비싼 중간재가
      1 개 줄면서 생기는 큰 계단을 싼 재료로 메워야 할 때는 그 상한이 해답을
      범위 밖으로 밀어낸다(2026-08-28: 물때·벼린 작살이 이 상태였다 — 단단한자루
      2→1 로 218 캐스트가 빠지는데 물고기비늘 상한이 4 라 못 메웠다).
      바닥에 걸린 종에만 쓴다. SHAPE_W 는 그대로라 여전히 원본 비율을 선호한다."""
    def casts(q):
        h, _, _, _ = D.gate(D.expand([dict(i, qty=x) for i, x in zip(ings, q)]))
        return h * cph

    ideal = [max(1.0, i["qty"] * s) for i in ings]

    w = SHAPE_W_RELAX if relax else SHAPE_W

    def cost(q, c):
        err = abs(math.log(c / target)) if c > 0 else 9e9
        shape = sum(abs(math.log(x / y)) for x, y in zip(q, ideal))
        return err + w * shape, err

    lo = [1] * len(ings)
    hi = [MAX_QTY if relax else max(3, min(MAX_QTY, int(math.ceil(i["qty"] * s * 2)) + 1))
          for i in ings]

    def descend(q0, line=False, sweeps=60, freeze=None):
        """한 출발점에서의 좌표하강.

        line=False → 각 좌표에 ±1 (기본, 빠르다).
        line=True  → 각 좌표를 [lo, hi] 전구간 탐색.
          ★왜 필요한가: 재료는 **결합생산**이라 게이트에 «평지»가 생긴다. 물고기비늘은
            단단한자루를 만드는 동안 부산물로 쌓이므로, 2→3→…→12 까지 올려도 캐스트가
            전혀 늘지 않다가 13 에서야 부산물을 넘겨 오른다. ±1 하강은 그 평지에서
            «개선 없음 + 모양 벌점 증가»로 읽고 멈춘다(2026-08-28 물때·벼린 작살).
            전구간 탐색은 평지를 한 번에 건넌다."""
        b = [max(lo[j], min(hi[j], q0[j])) for j in range(len(ings))]
        bc_ = casts(b)
        bo, be = cost(b, bc_)
        for _ in range(sweeps):
            if be <= math.log(1 + TOL) and bo <= be + 1e-9:
                break
            moved = False
            for j in range(len(ings)):
                if freeze is not None and j == freeze:
                    continue
                vals = range(lo[j], hi[j] + 1) if line else (b[j] - 1, b[j] + 1)
                for v in vals:
                    if v < lo[j] or v > hi[j] or v == b[j]:
                        continue
                    t = b[:]
                    t[j] = v
                    c = casts(t)
                    o, e = cost(t, c)
                    if o < bo - 1e-9:
                        b, bc_, bo, be, moved = t, c, o, e, True
            if not moved:
                break
        return b, bc_, bo, be

    q = [int(round(i["qty"] * s)) for i in ings]
    best, bc, bobj, berr = descend(q)

    # ★다중 출발점 — 좌표하강은 탐욕적이라 «비싼 중간재를 한 칸 내리고 싼 재료를 여러 칸
    #   올리는» 해를 못 찾는다. 첫 걸음만 보면 중간재를 올리는 쪽이 개선이라 그 분지에
    #   갇힌다(2026-08-28: 물때 작살이 「자루 1 + 물고기비늘 13」 대신 「자루 2」로 끝났다).
    #   그래서 재료를 하나씩 «고정»해 두고(freeze) 나머지만 전구간 탐색한다. 고정을 안 하면
    #   첫 스윕에서 그 비싼 재료가 도로 올라가 같은 분지로 돌아온다 — 출발점만 바꾸는
    #   것으로는 부족했다(2026-08-28 실측).
    #   바닥에 걸린 종에만 하므로(relax) 이미 맞는 285종의 결과는 바뀌지 않는다.
    if relax:
        for j in range(len(ings)):
            for v in (1, 2):
                if v > hi[j]:
                    continue
                q0 = q[:]
                q0[j] = v
                b, c, o, e = descend(q0, line=True, sweeps=6, freeze=j)
                if o < bobj - 1e-9:
                    best, bc, bobj, berr = b, c, o, e
    return best, bc, berr


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    src, apply_ = sys.argv[1], "--apply" in sys.argv
    os.environ["BLOCKSHIP_DATA"] = src

    CC = _load("cast_cost")
    D, K, rows, cph = CC.build_rows()
    pool = [r for r in rows if r["craftable"] and r["src"] not in CC.EXCLUDE_SRC
            and (CC.DEFAULT_SRC is None or r["src"] in CC.DEFAULT_SRC)]
    cur, iso = CC.kappa_table(pool)
    tg, clamps, norm = CC.targets(pool, iso)

    R = json.load(open(os.path.join(src, "recipes.json"), encoding="utf-8"))
    byname = {}
    for k, v in R["recipes"].items():
        n = (v.get("rodPartName") if v["resultMode"] == "rod"
             else v.get("resultPartName") if v["resultMode"] == "part" else None)
        if n:
            byname[n] = k

    out, floored, unwrapped, held, relaxed = [], [], [], [], []
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
        # ── 그래도 바닥이면 상한을 풀고 한 번 더 (생김새보다 정확도를 택하는 마지막 수단)
        if math.exp(err) - 1 > UNWRAP_AT:
            q2, c2, e2 = solve(D, cph, ings, v["target"], v["scale"], relax=True)
            if e2 < err - 1e-9:
                q, c, err = q2, c2, e2
                relaxed.append((name, math.exp(e2) - 1))
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
    if relaxed:
        print(f"\n상한 해제 재탐색 {len(relaxed)}건 (비싼 중간재의 계단을 싼 재료로 메움):")
        for n, e in relaxed:
            print(f"   {n:16s} 오차 {e*100:+.1f}%")

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
