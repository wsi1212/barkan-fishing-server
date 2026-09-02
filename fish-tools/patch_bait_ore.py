#!/usr/bin/env python3
"""미끼를 «광질 전용 소모품» 으로 다시 깐다 — 재료를 압축 광물로만 채운다.

★유저 결정 (2026-08-28): 「미끼는 광질 기반으로만. 그것도 압축 흑정석 같은 게 대부분이어야 함.」

━━ 왜 ━━
미끼는 서버에서 유일한 **소모품**이다(내구가 아니라 «개수»라 다 쓰면 사라지고 다시 조달해야
한다). 그래서 광질에 «유량 수요»를 만들 수 있는 단 하나의 자리인데, 실제로는 반대였다:

  · 요구 캐스트가 «영구 장비» κ 사다리에 얹혀 있었다 → 반딧불이 미끼가 내구 220캐스트(0.88h)를
    주는데 재료 모으기가 1.33h. 쓸 수 있는 시간보다 만드는 시간이 길었다.
  · 병목이 광물이 아니라 «녹슨 부품 16개» 였다(LP 분해: 1.33h 중 1.25h 가 「강에서 녹슨 부품
    낚기」, 광물 9개는 12초). 부품 계열 고유 재료를 미끼에까지 물린 탓이다.

━━ 어떻게 ━━
미끼 재료 = 압축 광물만. 수량은 «그 미끼가 버티는 낚시 시간 × UPKEEP_SHARE» 를 채굴 시간으로
환산해 역산한다. 즉 «미끼를 계속 대려면 플레이 시간의 몇 %를 채굴에 써야 하는가» 가 설계 손잡이다.

  등급  광물 구성                         (드릴 티어 사다리와 동일)
  E·D·C·B  압축 흑정석                      T1
  A        압축 흑정석 + 압축 적철석            T2
  S        압축 흑정석 + 압축 적철석 + 압축 자수정  T3

★수량 근거는 LP 쌍대해(material_value)에서 «압축 광물 1개당 채굴 시간» 을 그때그때 읽는다.
  드릴 산출이 바뀌면 수량도 따라 바뀐다 — 상수를 여기 복제하지 않는다.
"""
import importlib.util, json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = os.path.join(ROOT, "ops", "blockship-data")
SKILL = os.path.join(ROOT, ".claude", "skills", "balance-audit", "scripts")

#: 미끼 한 개가 버티는 낚시 시간 중 «채굴에 쓰는» 비율. 이 값 하나가 광질 강도를 정한다.
UPKEEP_SHARE = 0.15
#: 상점 구매가 = 채굴 원가 × 이 값. 1 보다 커야 «만드는 쪽이 싸다» 가 성립한다.
#: ★상점을 막지 않는 게 설계다 — 소모품이라 매번 조합대에 가는 건 번거롭다.
#:  급하면 30% 웃돈을 주고 사고, 평소엔 캐서 만든다.
#: ★가격을 parts.json 기준가에서 뽑으면 안 된다 — 그 값은 채굴 예산과 무관해서
#:  같은 B급 안에서도 「제작/구매」가 4배~12배로 튄다(2026-08-28 실측). 원가에서 직접 뽑는다.
BUY_PREMIUM = 1.30

#: 미끼 1개 상점가의 절대 상한(원). ★유저 결정 2026-09-02: 「아무리 비싸도 한 개에
#: 만원을 넘으면 어카냐」. 종전 최고가는 성좌 미끼 147,775원이었다 — 후반 시급이
#: 커서 «시간 15%» 라는 설계가 돈으로 환산되면 터무니없는 숫자가 됐다.
#: 상한에 걸리면 채굴 예산 자체를 상한이 허용하는 만큼으로 되깎는다(광물 수량도 같이
#: 내려간다). 가격만 깎고 광물을 두면 「사는 게 만드는 것보다 싸다」가 되어
#: BUY_PREMIUM 의 전제가 깨진다.
MAX_PRICE = 10000

#: 등급별 «상점가 띠» — MAX_PRICE 대비 (하한, 상한). 등급 안에서는 레벨로 보간한다.
#: ★상한 하나만 걸면 후반이 전부 상한에 붙어 **레시피가 글자까지 같아진다**
#:   (2026-09-02 실측: S 10종이 전부 흑정석2·적철석1·자수정1). 그래서 띠로 깐다.
#: E·D 는 자연값이 이미 띠보다 낮아 손대지 않는다(min 을 취하므로).
PRICE_BAND = {
    "C": (0.45, 0.60),
    "B": (0.60, 0.75),
    "A": (0.75, 0.90),
    "S": (0.90, 1.00),
}

#: 같은 등급 안에서 «성능 좋은 미끼가 더 비싸야» 한다. 성능/등급평균 비를 이 범위로 조인다.
#: (영구 장비의 κ 사다리와 같은 취지 — 다만 여기선 채굴 시간 예산에 곱한다.)
SPREAD = (0.75, 1.30)
#: 등급별 광물 구성 — (matId, 시간 배분 비중). 비중 합은 1.
#: ★유저 지시 2026-09-02: 「미끼도 티어링 좀 하자」. 종전엔 E~B 가 전부 흑정석 하나였고
#:   (그래서 같은 등급 미끼끼리 레시피가 글자까지 겹쳤다) 철광석이 A, 자수정이 S 에서야
#:   등장했다. 장비 쪽 사다리(patch_ore_ladder: 철광석 B상위·자수정 A중상위)와 같은
#:   방향으로 한 등급씩 앞당긴다. 비중은 «채굴 시간 배분»이라 총 부담은 안 바뀐다.
MIX = {
    "E": [("압축흑정석", 1.00)],
    "D": [("압축흑정석", 1.00)],
    "C": [("압축흑정석", 0.80), ("압축철광석", 0.20)],
    "B": [("압축흑정석", 0.60), ("압축철광석", 0.40)],
    "A": [("압축흑정석", 0.40), ("압축철광석", 0.40), ("압축자수정", 0.20)],
    "S": [("압축흑정석", 0.30), ("압축철광석", 0.40), ("압축자수정", 0.30)],
}
#: 캐스트/h 는 «복제하지 않고» cast_cost.build_rows() 에서 받아 쓴다.
#  ★예전엔 CATCH_PER_HOUR = 249.1 을 여기 적고 실제값과 다르면 죽는 가드를 뒀다.
#    그런데 이 값은 stat_value 가 recipes.json 을 읽어 산출하는 파생값이라, 레시피를
#    고칠 때마다 움직인다(2026-09-02: 249.1 → 271.7). 그래서 가드는 「사고 감지」가
#    아니라 「레시피를 고칠 때마다 상수를 손으로 따라 적어라」는 숙제가 됐다.
#    사본을 없애는 게 감시보다 낫다 — 값은 한 곳(cast_cost)에서만 나온다.


def load(name, d):
    sp = importlib.util.spec_from_file_location(name, os.path.join(d, name + ".py"))
    m = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(m)
    return m


def main():
    dry = "--dry" in sys.argv
    os.environ.setdefault("BLOCKSHIP_DATA", os.path.abspath(os.path.join(ROOT, "..", "..", "BlockShip")))
    CC = load("cast_cost", SKILL)
    MV = load("material_value", SKILL)
    D = MV.Data()
    _, _, rows, cph = CC.build_rows()
    print(f"캐스트/h = {cph:.1f} (cast_cost 산출값)")

    # 압축 광물 1개당 채굴 시간(h) — LP 쌍대해. 상수 복제 금지.
    ORE_BASE = {"압축흑정석": "흑정석", "압축철광석": "철광석", "압축자수정": "자수정"}
    unit_h = {}
    for mid, base in ORE_BASE.items():
        h, _, _, _ = D.gate({("ore", base): 9.0})
        if h <= 0:
            print(f"🔴 {mid} 의 채굴 시간을 못 구했다 — LP 에 공급원이 없다")
            sys.exit(1)
        unit_h[mid] = h

    # 구간 시급 — 채굴 시간을 «원» 으로 바꾸는 환산율. cast_cost 의 rows 가 이미 들고 있다.
    wage = {r["name"]: r["wage"] for r in rows if r["cat"] == "미끼"}

    R = json.load(open(os.path.join(BASE, "recipes.json"), encoding="utf-8"))
    P = json.load(open(os.path.join(BASE, "parts.json"), encoding="utf-8"))["parts"]
    mats = json.load(open(os.path.join(BASE, "materials.json"), encoding="utf-8"))["materials"]
    recs = R["recipes"]

    def ing(mid, qty):
        m = mats[mid]
        return {"kind": "custom", "typeOrMatId": mid, "displayName": m["name"],
                "mcItem": m["mcItem"], "qty": int(qty)}

    # 등급별 평균 성능 — 같은 등급 안 상대비교의 기준. 미끼의 perf 는 eff(순수 수입 기여)다.
    perf = {r["name"]: r["perf"] for r in rows if r["cat"] == "미끼" and r["perf"] > 0}
    gsum, gcnt = {}, {}
    for n, v in perf.items():
        g = P["미끼"][n].split("|")[1] if n in P["미끼"] else None
        if g:
            gsum[g] = gsum.get(g, 0.0) + v
            gcnt[g] = gcnt.get(g, 0) + 1
    gmean = {g: gsum[g] / gcnt[g] for g in gsum}

    # 등급별 레벨 구간 — 띠 안에서 보간할 기준. 손으로 적지 않는다.
    grade_lv = {}
    for n2, v2 in P["미끼"].items():
        f2 = v2.split("|")
        if len(f2) < 6 or not f2[5].isdigit():
            continue
        g2, lv2 = f2[1], int(f2[5])
        lo, hi = grade_lv.get(g2, (lv2, lv2))
        grade_lv[g2] = (min(lo, lv2), max(hi, lv2))

    changed, report = 0, []
    for rid, r in recs.items():
        if r.get("resultPartType") != "미끼":
            continue
        n = r["resultPartName"]
        if n not in P["미끼"]:
            continue
        f = P["미끼"][n].split("|")
        grade, dur = f[1], int(f[3])
        mix = MIX.get(grade)
        if mix is None:
            print(f"🔴 {n}: 등급 {grade} 의 광물 구성이 없다")
            sys.exit(1)
        budget_h = dur / cph * UPKEEP_SHARE          # 채굴에 쓸 시간
        # 같은 등급 안 성능 편차 반영 — 좋은 미끼일수록 더 캐야 한다.
        if n in perf and gmean.get(grade):
            k = perf[n] / gmean[grade]
            budget_h *= min(SPREAD[1], max(SPREAD[0], k))
        # ── 상점가 띠 → 채굴 예산 되깎기 ──
        #   가격이 채굴원가에서 파생되므로, 목표 가격을 정하면 예산이 정해진다.
        w = wage.get(n)
        if w:
            band = PRICE_BAND.get(grade)
            if band:
                lv = int(f[5]) if f[5].isdigit() else 0
                lo_lv, hi_lv = grade_lv.get(grade, (lv, lv))
                t = (lv - lo_lv) / max(1, hi_lv - lo_lv)
                want_price = MAX_PRICE * (band[0] + (band[1] - band[0]) * t)
            else:
                want_price = MAX_PRICE
            cap_h = min(want_price, MAX_PRICE) / (w * BUY_PREMIUM)
            if budget_h > cap_h:
                budget_h = cap_h
        items = []
        for mid, share in mix:
            q = max(1, round(budget_h * share / unit_h[mid]))
            items.append(ing(mid, q))
        r["ingredients"] = items
        changed += 1
        got = sum(i["qty"] * unit_h[i["typeOrMatId"]] for i in items)
        # ── 상점가 재산출 ── 채굴 원가 × BUY_PREMIUM. parts.json 3번째 필드(가격)를 덮어쓴다.
        #   되깎기 후에도 반올림으로 상한을 살짝 넘을 수 있어 여기서 한 번 더 조인다.
        if w:
            f[2] = str(max(1, min(MAX_PRICE, round(got * w * BUY_PREMIUM))))
            P["미끼"][n] = "|".join(f)
        report.append((grade, int(f[5]), n, dur, budget_h, got,
                       " · ".join(f"{i['displayName']}×{i['qty']}" for i in items)))

    # ── 상한을 «전» 미끼에 건다 ──
    #   위 루프는 레시피가 있는 미끼만 돈다. 잠수상점 전용 2종(잠수부·심해 잠수부 미끼)은
    #   레시피가 없어 가격이 손대지 않은 채 남는다 — 실측으로 심해 잠수부 미끼가
    #   12,000원으로 상한을 넘고 있었다. 상한은 상점 진열가의 «불변식»이므로 여기서
    #   한 번 더 훑는다(레시피 유무와 무관).
    over = []
    for n2, v2 in P["미끼"].items():
        f2 = v2.split("|")
        if len(f2) < 3 or not f2[2].lstrip("-").isdigit():
            continue
        if int(f2[2]) > MAX_PRICE:
            over.append((n2, int(f2[2])))
            f2[2] = str(MAX_PRICE)
            P["미끼"][n2] = "|".join(f2)
    if over:
        print("상한 초과 미끼 되깎기(레시피 없는 상점 전용 포함): "
              + " · ".join(f"{n2} {c:,}→{MAX_PRICE:,}원" for n2, c in over))

    if not dry:
        json.dump(R, open(os.path.join(BASE, "recipes.json"), "w", encoding="utf-8"),
                  ensure_ascii=False, indent=2)
        _P = json.load(open(os.path.join(BASE, "parts.json"), encoding="utf-8"))
        _P["parts"]["미끼"] = P["미끼"]
        json.dump(_P, open(os.path.join(BASE, "parts.json"), "w", encoding="utf-8"),
                  ensure_ascii=False, indent=2)

    print(f"미끼 {changed}종을 광물 전용으로 재작성  (유지비율 {UPKEEP_SHARE:.0%})")
    print(f"압축 광물 1개당 채굴: " + " · ".join(f"{k} {v*3600:.0f}초" for k, v in unit_h.items()))
    print()
    print(f"{'급':<2}{'렙':>4} {'미끼':<14}{'채굴분':>7}{'상점가':>10}{'유지비중':>8}  재료")
    for g, lv, n, dur, want, got, txt in sorted(report, key=lambda x: (x[1])):
        w = wage.get(n, 0)
        price = min(MAX_PRICE, round(got * w * BUY_PREMIUM))
        share = price / (dur / cph) / w * 100 if w else 0
        print(f"{g:<2}{lv:>4} {n:<14}{got*60:>7.1f}{price:>10,}{share:>7.0f}%  {txt}")
    print("\n※ 유지비중 = 상점에서 사 쓸 때 미끼값이 낚시 수입에서 차지하는 비율")
    if dry:
        print("★ --dry: 아무것도 쓰지 않았다. 빼면 실제로 쓴다.")


if __name__ == "__main__":
    main()
