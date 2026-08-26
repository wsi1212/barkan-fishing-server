#!/usr/bin/env python3
"""재료 게이트 실측 — 라이브 recipes.json + materials.json + parts.json 에서
«장비 1티어(풀세팅)를 갖추기까지의 낚시 시간»과 미끼 유지비를 뽑는다.

★2026-08-26 신설. 구 cross-economy-values.md §6 표가 ①아이템 1점 평균을 «1티어»라 부르고
②별빛진주를 8%(실제 2%)로 적고 ③재료가 6개 지역에 흩어진 것을 무시해 재료확률 가치를
절반~1/4로 깎고 있었다. 그 표를 손으로 다시 적지 않도록 이 스크립트가 권위가 된다.

사용:
    python3 material_gate.py            # 등급별 풀세팅 게이트 + 미끼 유지비
    python3 material_gate.py --items    # 아이템 1점 게이트 전체 목록
"""

# ══════════════════════════════════════════════════════════════════════════
#  ★★ DEPRECATED (2026-08-26) — material_value.py 가 이 스크립트를 대체했다.
#
#  놓치는 것 셋: ①같은 재료가 여러 지역에서 나는 것(진주·별빛진주는 16개 지역 전부)을
#  무시하고 «전역 최댓값 하나»만 쓴다 ②광질·바닐라 재료를 비용 0으로 버린다(장비 레시피
#  사용빈도 2·3위 중간재가 광질 산출이다) ③결합생산(한 포획이 드롭테이블 전체를 굴린다)을
#  반영하지 않아 같은 시간을 여러 번 센다. 실측 대조: 구 휴리스틱이 LP 대비 D +48% · C +27%
#  · B +18% 과대계상.
#
#  이 파일은 **과거 감사와의 델타 비교** 전용으로만 남겼다. 새 리포트에 이 출력의 숫자를
#  옮기지 말 것 — 새 스크립트와 단위·전제가 달라 한 리포트에 섞으면 또 3중 오류가 난다
#  (2026-08-26 이전이 정확히 그 상태였다).
# ══════════════════════════════════════════════════════════════════════════
import sys as _dep_sys
print("\033[33m★DEPRECATED — material_value.py 를 쓸 것. 이 출력은 과거 델타 비교 전용이다.\033[0m",
      file=_dep_sys.stderr)
import json, collections, statistics, sys, os

BS = os.environ.get("BLOCKSHIP_DATA",
    "/Users/user/Library/Application Support/feather/player-server/servers/"
    "07de2d81-991a-47e2-b62d-06c0d1b5150a/plugins/BlockShip")

REC = json.load(open(BS + "/recipes.json"))["recipes"]
MATJ = json.load(open(BS + "/materials.json"))
PARTS = json.load(open(BS + "/parts.json"))["parts"]

CATCH_H = 220.0                 # 실측 포획/h (price_ladder.py 와 동일)
ATTEMPT_H = 259.0               # 시도/h = 포획 ÷ 완주율 85% — 미끼는 «시도»마다 1개 소모
# 티어 실측 수입 (price_ladder.py 산출)
TIER_INCOME = {"E": 95403, "D": 95403, "C": 133022, "B": 133022, "A": 345778, "S": 370210}

DROP = {a: {d["matId"]: d["chance"] for d in t} for a, t in MATJ["dropTables"].items()}
WDROP = {w: {d["matId"]: d["chance"] for d in t} for w, t in MATJ["weatherDrops"].items()}
BASE_FISH = set()
for t in list(DROP.values()) + list(WDROP.values()):
    BASE_FISH |= set(t)

# 재료별 최고확률 지역 — 게이트의 «어디서 모으나»
BEST = {}
for mid in BASE_FISH:
    cand = [(t.get(mid, 0), a) for a, t in DROP.items() if t.get(mid, 0) > 0]
    if cand:
        c, a = max(cand); BEST[mid] = (a, c)
    else:
        for w, t in WDROP.items():
            if mid in t: BEST[mid] = ("날씨:" + w, t[mid])


def _result_mat(v):
    for l in (v.get("result", {}) or {}).get("lore", []) or []:
        if l.startswith("&8mat:"): return l[6:]
    return None

MATREC = {}
for k, v in REC.items():
    if v["resultMode"] == "direct":
        rid = _result_mat(v)
        if rid: MATREC[rid] = v


def _expand(matid, qty, out, depth=0):
    """중간재를 base(낚시 드롭 / 타 경제 / 바닐라)까지 전개."""
    if depth > 8: out[("?", matid)] += qty; return
    if matid in BASE_FISH: out[("fish", matid)] += qty; return
    r = MATREC.get(matid)
    if r is None: out[("other", matid)] += qty; return
    for i in r["ingredients"]:
        q = i["qty"] * qty
        if i["kind"] == "custom": _expand(i["typeOrMatId"], q, out, depth + 1)
        else: out[("item", i["typeOrMatId"])] += q


def recipe_base(v):
    out = collections.Counter()
    for i in v["ingredients"]:
        if i["kind"] == "custom": _expand(i["typeOrMatId"], i["qty"], out)
        elif i["kind"] == "item": out[("item", i["typeOrMatId"])] += i["qty"]
        else: out[(i["kind"], i["typeOrMatId"])] += i["qty"]
    return out


def gate(base, mult=1.0, mode="seq", catch_h=CATCH_H):
    """낚시 드롭 재료 게이트(h).
    mode='seq'  지역 안에서는 동시(max), 지역 간에는 순차(sum) — 현실 모델
    mode='par'  전 재료 동시(max) — 낙관 하한
    """
    byarea = collections.defaultdict(float); det = []
    for (kind, mid), q in base.items():
        if kind != "fish": continue
        a, c = BEST.get(mid, (None, 0))
        if c <= 0: continue
        h = q / (catch_h * (c / 100.0 * mult))
        byarea[a] = max(byarea[a], h); det.append((mid, q, c, a, h))
    det.sort(key=lambda x: -x[4])
    if not byarea: return 0.0, det
    return (sum(byarea.values()) if mode == "seq" else max(byarea.values())), det


META = {}
for cat, items in PARTS.items():
    for name, line in items.items():
        f = line.split("|")
        META[name] = dict(cat=cat, grade=f[1], price=int(f[2]), dur=int(f[3]),
                          stats=f[4], lvl=int(f[5]), src=f[6] if len(f) > 6 else "")

RECBY = {}
for k, v in REC.items():
    if v["resultMode"] == "rod": n = v.get("rodPartName") or v["displayName"]
    elif v["resultMode"] == "part": n = v.get("resultPartName") or v["displayName"]
    else: continue
    RECBY[n] = v


def stat_of(name, key):
    for tok in META.get(name, {}).get("stats", "").split(","):
        p = tok.split(":")
        if len(p) >= 2 and p[0] == key:
            try: return float(p[1])
            except ValueError: return 0.0
    return 0.0


def pick(cat, grade, allow_hidden=False):
    """그 등급/카테고리의 «가격 중앙값» 아이템 = 대표 (히든/캐시/잠수상점 제외).
    ★S 낚싯대는 전부 히든-전설이라 allow_hidden 폴백이 필요하다."""
    c = [(n, m) for n, m in META.items()
         if m["cat"] == cat and m["grade"] == grade and m["price"] > 0 and n in RECBY
         and (allow_hidden or "히든" not in m["src"])
         and m["src"] not in ("캐시", "개발자", "잠수상점")]
    if not c:
        return None if allow_hidden else pick(cat, grade, True)
    med = statistics.median([m["price"] for _, m in c])
    return min(c, key=lambda x: abs(x[1]["price"] - med))[0]


SET_GRADES = ["D", "C", "B", "A", "S"]
SLOTS = ["릴", "줄", "바늘", "찌"]


def full_set(grade):
    rod = pick("낚싯대", grade)
    pg = "A" if grade == "S" else grade      # 부품엔 S 등급이 없다
    names = [rod] + [pick(c, pg) for c in SLOTS]
    if any(n is None for n in names): return None
    tot = collections.Counter(); price = 0
    for n in names:
        for k, v in recipe_base(RECBY[n]).items(): tot[k] += v
        price += META[n]["price"]
    return names, tot, price


def main():
    if "--items" in sys.argv:
        rows = []
        for n, m in META.items():
            if n not in RECBY: continue
            g, det = gate(recipe_base(RECBY[n]))
            if g > 0: rows.append((m["grade"], m["lvl"], n, m, g, det))
        order = {"E": 0, "D": 1, "C": 2, "B": 3, "A": 4, "S": 5}
        rows.sort(key=lambda r: (order.get(r[0], 9), r[1]))
        print(f"{'등급':<3}{'Lv':>4} {'분류':<5}{'이름':<22}{'가격':>10}{'게이트h':>9}  병목")
        for g_, lv, n, m, h, det in rows:
            t = det[0]
            print(f"{g_:<3}{lv:>4} {m['cat']:<5}{n:<22}{m['price']:>10,}{h:>9.2f}  "
                  f"{t[0]}×{t[1]}@{t[2]}%({t[3]})")
        return

    print(f"기준: {CATCH_H:.0f} 포획/h · 시도 {ATTEMPT_H:.0f}/h")
    print("\n=== 등급별 풀세팅(낚싯대+릴+줄+바늘+찌) 게이트 ===")
    print(f"{'등급':<4}{'가격합':>12}{'돈게이트h':>10}{'재료h(동시)':>12}{'재료h(순차)':>12}  관문  포화v*")
    for g in SET_GRADES:
        fs = full_set(g)
        if not fs: continue
        names, tot, price = fs
        gp, _ = gate(tot, mode="par"); gs, det = gate(tot, mode="seq")
        money = price / TIER_INCOME[g]
        verdict = "재료" if gs > money else "돈"
        sat = (gs / money - 1) * 100 if money > 0 and gs > money else 0
        print(f"{g:<4}{price:>12,}{money:>10.2f}{gp:>12.2f}{gs:>12.2f}  {verdict}  {sat:>5.0f}%")
        print(f"      {' + '.join(names)}")
        print(f"      병목: " + ", ".join(f"{d[0]}×{d[1]}@{d[2]}%({d[3]})={d[4]:.1f}h" for d in det[:3]))

    print("\n=== 돈으로 살 수 없는 재료 싱크 (작살·요리) 상위 ===")
    sink = []
    for k, v in REC.items():
        if v["category"] not in ("요리", "작살"): continue
        h, det = gate(recipe_base(v))
        if h > 0: sink.append((h, v["category"], v["displayName"], det[:2]))
    sink.sort(reverse=True)
    for h, c, n, det in sink[:8]:
        print(f"{h:>8.2f}h  {c:<5}{n:<20} " + ", ".join(f"{d[0]}×{d[1]}@{d[2]}%={d[4]:.1f}h" for d in det))

    print("\n=== 미끼 유지비 — ★라이브는 «시도 1회 = 미끼 1개» (parts.json 내구 필드는 사문화) ===")
    print(f"{'등급':<3}{'Lv':>4} {'이름':<18}{'원/개':>8}{'라이브 비용/h':>13}{'수입대비':>8}"
          f"{'설계의도 비용/h':>15}{'대비':>7}  재료확률")
    order = {"E": 0, "D": 1, "C": 2, "B": 3, "A": 4}
    for n in sorted(PARTS["미끼"], key=lambda x: (order.get(META[x]["grade"], 9), META[x]["lvl"])):
        m = META[n]; inc = TIER_INCOME.get(m["grade"], 95403)
        live = m["price"] * ATTEMPT_H
        intended = m["price"] * ATTEMPT_H / max(1, m["dur"])
        print(f"{m['grade']:<3}{m['lvl']:>4} {n:<18}{m['price']:>8,}{live:>13,.0f}{live/inc*100:>7.0f}%"
              f"{intended:>15,.0f}{intended/inc*100:>6.1f}%  {stat_of(n,'재료확률'):g}")


if __name__ == "__main__":
    main()
