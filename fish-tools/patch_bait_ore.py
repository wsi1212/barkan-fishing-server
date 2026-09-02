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

#: 압축 광물 «세 종 사이의 가치비» — 압축흑정석을 1 로 둔 설계값.
#: ★유저 결정 2026-09-02: 「흑정석·적철석·자수정 사이 가치 차이가 크게 없음.
#:   1 : 1.1 : 1.2 정도로 생각해. 압축적철석·압축자수정 기준.」
#: 왜 LP 값을 안 쓰나 — LP 는 드릴 산출량에서 단가를 뽑는데 그 입력이
#:   drill_per_hour = {흑정석 2715, 철광석 340} (measured.py, is_fallback=True) 이고
#:   **자수정 340 은 표본 0 의 대리값**이다(DRILL_UNOBSERVED, 「반드시 «추정» 표기」).
#:   그래서 LP 는 1 : 7.9 : 7.9 를 내놓는다 — 압축자수정 1개가 압축흑정석 8개 값이 된다.
#:   실측이 아닌 추정 위에 세운 8배 격차보다, 광산을 만든 사람의 설계 의도가 권위다.
#: ★실제 드릴 산출이 측정되면 이 비율과 대조할 것 — 어긋나면 광산 쪽을 고치는 게 맞다.
ORE_VALUE_RATIO = {"압축흑정석": 1.00, "압축철광석": 1.10, "압축자수정": 1.20}

#: 등급별 «상점가 띠» — 절대 금액(원). 등급 안에서는 레벨로 보간한다.
#: ★유저 결정 2026-09-02: 「상한 유지하는 선에서 앞의 것 가격을 낮춰. B 38렙인데
#:   하나에 7,000원은 너무 과도함. B등급은 하나 2,000원 수준.」
#: MAX_PRICE 대비 «비율»로 깔았더니 C·B 가 7,000~8,400원까지 올라갔다 — 상한에서
#: 거꾸로 내려오는 방식이라 앞 등급이 비싸졌다. 그래서 앞부터 쌓는 절대 금액으로 바꿨다.
#: ★이 띠가 «재료 요구량»도 정한다 — 가격 = 채굴원가 × BUY_PREMIUM 이므로.
#:   앞 등급을 낮춘 덕에 후반이 상대적으로 올라가 요구량 역전도 같이 줄어든다.
PRICE_BAND = {
    "E": (400, 600),
    "D": (700, 1400),
    "C": (1500, 1900),
    "B": (2000, 2800),
    "A": (3500, 7000),
    "S": (8000, MAX_PRICE),
}

#: 같은 등급 안에서 «성능 좋은 미끼가 더 비싸야» 한다. 성능/등급평균 비를 이 범위로 조인다.
#: (영구 장비의 κ 사다리와 같은 취지 — 다만 여기선 채굴 시간 예산에 곱한다.)
#: ★0.75~1.30 이던 것을 좁혔다. 편차가 등급 띠 폭보다 넓으면 **등급 경계가 뒤집힌다** —
#:   실측으로 C 살아있는 미끼(perf 상위, ×1.30)가 흑정석 11 개, B 반딧불이(perf 하위,
#:   ×0.75)가 7 개였다. 등급이 성능보다 상위 서열이므로 등급 단조가 먼저다.
#:   TIME_LADDER 의 등급 간 간격도 이 폭을 견디게 잡아야 한다(다음 등급 하한 > 이전
#:   등급 상한 × 1.15/0.90 ≈ ×1.28).
SPREAD = (0.90, 1.15)
#: 1회 제작으로 나오는 미끼 개수. ★유저 지시 2026-09-02: 「하나 만드는데 하나씩 필요한 거
#: 아니지? 재료로 만들면 한 10개씩 주게 해줘. 대신 재료도 더 비싸게 하고.」
#: jar 쪽 `Recipe.resultAmount` + `EquipmentManager.grantPart(.., count)` 와 짝이다 —
#: **둘이 같이 나가야 한다.** 데이터만 먼저 나가면 10배 재료로 1개가 나온다.
RESULT_AMOUNT = 10

#: 등급별 «1회 제작(=RESULT_AMOUNT개) 채굴 예산» — 분. 등급 안은 레벨로 보간.
#: ★예전엔 예산을 «상점가 상한에서 역산»했다. 그래서 Lv50 에서 구간 시급이 2.6배로
#:   뛰는 순간 같은 돈이 사는 채굴시간이 줄어 **재료 요구량이 거꾸로 떨어졌다**
#:   (A Lv49 흑정석5·적철석4·자수정2 → Lv50 2·1·1). 시급은 설계가 아니라 관측값이라
#:   그걸 재료량의 분모로 쓰면 이런 역전이 구조적으로 생긴다.
#:   ⇒ 재료는 «시간 사다리»가 직접 정하고, 가격은 PRICE_BAND 가 따로 정한다.
TIME_LADDER = {
    "E": (0.5, 0.5),
    "D": (0.7, 1.4),
    "C": (1.8, 2.4),
    "B": (3.1, 3.8),
    "A": (4.9, 6.2),
    "S": (8.0, 10.0),
}

#: 등급별 광물 구성 — (matId, 시간 배분 비중). 비중 합은 1.
#: ★유저 지시: 「A부터 압축흑정석도 늘고 적철석도 늘고 압축자수정도 늘어야지. S도 그래.
#:   압축자수정 한 7개는 필요할 거 같아.」 → 세 종이 **모두** 단조 증가해야 한다.
#:   비중을 급하게 옮기면(예 B 흑정석 0.60 → A 0.40) 예산이 늘어도 흑정석 개수가 줄어
#:   그 자체로 역전이 된다. 그래서 비중은 완만하게 옮기고 예산으로 끌어올린다.
MIX = {
    "E": [("압축흑정석", 1.00)],
    "D": [("압축흑정석", 1.00)],
    "C": [("압축흑정석", 0.85), ("압축철광석", 0.15)],
    "B": [("압축흑정석", 0.70), ("압축철광석", 0.30)],
    "A": [("압축흑정석", 0.55), ("압축철광석", 0.27), ("압축자수정", 0.18)],
    "S": [("압축흑정석", 0.45), ("압축철광석", 0.30), ("압축자수정", 0.25)],
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
    # ── 세 종 사이 비율은 설계값으로 덮는다(위 ORE_VALUE_RATIO 주석 참조) ──
    #   절대 수준은 LP 가 정한다 — 압축흑정석의 실측 단가를 앵커로 쓰고 비율만 적용한다.
    anchor = unit_h.get("압축흑정석")
    if anchor:
        lp = {k: v / anchor for k, v in unit_h.items()}
        print("압축광물 단가비  LP(추정 포함) "
              + " : ".join(f"{lp[k]:.1f}" for k in ORE_VALUE_RATIO)
              + "  →  설계 "
              + " : ".join(f"{ORE_VALUE_RATIO[k]:.1f}" for k in ORE_VALUE_RATIO))
        for mid, ratio in ORE_VALUE_RATIO.items():
            if mid in unit_h:
                unit_h[mid] = anchor * ratio

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
        lv = int(f[5]) if f[5].isdigit() else 0
        lo_lv, hi_lv = grade_lv.get(grade, (lv, lv))
        t = (lv - lo_lv) / max(1, hi_lv - lo_lv)
        band_t = TIME_LADDER.get(grade)
        if band_t is None:
            print(f"🔴 {n}: 등급 {grade} 의 시간 사다리가 없다")
            sys.exit(1)
        budget_h = (band_t[0] + (band_t[1] - band_t[0]) * t) / 60.0
        # 같은 등급 안 성능 편차 반영 — 좋은 미끼일수록 더 캐야 한다.
        if n in perf and gmean.get(grade):
            k = perf[n] / gmean[grade]
            budget_h *= min(SPREAD[1], max(SPREAD[0], k))
        w = wage.get(n)
        # ── 개수 배분: 내림 + 큰 소수부 우선 보충 ──
        #   ★올림(round)으로 하면 종마다 최대 반 개씩 넘쳐 «가격이 목표 띠를 초과»한다
        #     (실측: B급 목표 2,000원 → 2,536원, 27% 초과). 가격이 채굴원가에서
        #     나오므로 개수 반올림이 곧 가격 오차다. 그래서 예산을 넘지 않는 쪽으로
        #     내림한 뒤, 남은 예산이 허용하는 만큼만 소수부가 큰 순서로 +1 한다.
        raw = {mid: budget_h * share / unit_h[mid] for mid, share in mix}
        qty = {mid: max(1, int(v)) for mid, v in raw.items()}
        used = sum(qty[m] * unit_h[m] for m in qty)
        for mid in sorted(raw, key=lambda m: -(raw[m] - int(raw[m]))):
            if used + unit_h[mid] <= budget_h:
                qty[mid] += 1
                used += unit_h[mid]
        items = [ing(mid, qty[mid]) for mid, _ in mix]
        r["ingredients"] = items
        r["resultAmount"] = RESULT_AMOUNT
        changed += 1
        got = sum(i["qty"] * unit_h[i["typeOrMatId"]] for i in items)
        # ── 상점가는 «띠»가 정한다(개당) ──
        #   ★예전엔 채굴원가 × BUY_PREMIUM 이었다. 그 결합을 끊은 이유는 위 TIME_LADDER
        #     주석 참조 — 결합을 유지하면 「가격 상한 ↔ 후반 재료 증가」가 동시에 성립할 수
        #     없다. 이제 BUY_PREMIUM 은 «검산용»이다: 10개 사는 값 vs 1회 제작 채굴원가를
        #     아래 리포트가 비율로 보여준다(만드는 쪽이 싸야 한다).
        band = PRICE_BAND.get(grade)
        if band:
            f[2] = str(max(1, min(MAX_PRICE, int(round(
                band[0] + (band[1] - band[0]) * t)))))
            P["미끼"][n] = "|".join(f)
        report.append((grade, int(f[5]), n, dur, budget_h, got,
                       " · ".join(f"{i['displayName']}×{i['qty']}" for i in items)))

    # ── 상한을 «전» 미끼에 건다 ──
    #   위 루프는 레시피가 있는 미끼만 돈다. 잠수상점 전용 2종(잠수부·심해 잠수부 미끼)은
    #   레시피가 없어 가격이 손대지 않은 채 남는다 — 실측으로 심해 잠수부 미끼가
    #   12,000원으로 상한을 넘고 있었다. 상한은 상점 진열가의 «불변식»이므로 여기서
    #   한 번 더 훑는다(레시피 유무와 무관).
    #   레시피가 있는 미끼는 위에서 이미 띠에 맞춰졌다. 여기서는 «레시피 없는» 것들을
    #   같은 띠에 올린다 — 채굴 원가가 없으니 띠 값을 그대로 진열가로 쓴다.
    fixed = []
    priced = {r2.get("resultPartName") for r2 in recs.values()
              if r2.get("resultPartType") == "미끼"}
    for n2, v2 in P["미끼"].items():
        f2 = v2.split("|")
        if len(f2) < 6 or not f2[2].lstrip("-").isdigit():
            continue
        cur = int(f2[2])
        g2 = f2[1]
        band = PRICE_BAND.get(g2)
        if n2 in priced:
            want = min(cur, MAX_PRICE)          # 이미 원가에서 나온 값 — 상한만 확인
        elif band:
            lv2 = int(f2[5]) if f2[5].isdigit() else 0
            lo_lv, hi_lv = grade_lv.get(g2, (lv2, lv2))
            t2 = (lv2 - lo_lv) / max(1, hi_lv - lo_lv)
            want = int(min(MAX_PRICE, round(band[0] + (band[1] - band[0]) * t2)))
        else:
            want = min(cur, MAX_PRICE)
        if want != cur:
            fixed.append((n2, cur, want, n2 not in priced))
            f2[2] = str(want)
            P["미끼"][n2] = "|".join(f2)
    if fixed:
        print("가격 보정: " + " · ".join(
            f"{n2} {c:,}→{w:,}원{'(레시피 없음)' if noc else ''}" for n2, c, w, noc in fixed))

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
    print(f"{'급':<2}{'렙':>4} {'미끼':<14}{'채굴분':>7}{'개당가':>8}{'유지비중':>7}{'제작/구매':>9}  재료")
    for g, lv, n, dur, want, got, txt in sorted(report, key=lambda x: (x[1])):
        w = wage.get(n, 0)
        price = int(P["미끼"][n].split("|")[2])
        share = price / (dur / cph) / w * 100 if w else 0
        # 제작/구매 = (1회 제작 채굴원가) / (RESULT_AMOUNT 개 사는 값). 1 보다 작아야 한다.
        ratio = (got * w) / (price * RESULT_AMOUNT) if w and price else 0
        print(f"{g:<2}{lv:>4} {n:<14}{got*60:>7.1f}{price:>8,}{share:>6.0f}%"
              f"{ratio:>9.2f}  {txt}")
    print(f"\n※ 개당가 = 상점 진열가(1개) · 유지비중 = 사 쓸 때 미끼값이 낚시 수입에서 차지하는 비율")
    print(f"※ 제작/구매 = 1회 제작({RESULT_AMOUNT}개) 채굴원가 ÷ {RESULT_AMOUNT}개 구매가 "
          f"— 1 보다 작아야 «만드는 쪽이 싸다»")
    if dry:
        print("★ --dry: 아무것도 쓰지 않았다. 빼면 실제로 쓴다.")


if __name__ == "__main__":
    main()
