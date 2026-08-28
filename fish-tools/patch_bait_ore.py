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

#: 같은 등급 안에서 «성능 좋은 미끼가 더 비싸야» 한다. 성능/등급평균 비를 이 범위로 조인다.
#: (영구 장비의 κ 사다리와 같은 취지 — 다만 여기선 채굴 시간 예산에 곱한다.)
SPREAD = (0.75, 1.30)
#: 등급별 광물 구성 — (matId, 시간 배분 비중). 비중 합은 1.
MIX = {
    "E": [("압축흑정석", 1.0)],
    "D": [("압축흑정석", 1.0)],
    "C": [("압축흑정석", 1.0)],
    "B": [("압축흑정석", 1.0)],
    "A": [("압축흑정석", 0.35), ("압축철광석", 0.65)],
    "S": [("압축흑정석", 0.25), ("압축철광석", 0.45), ("압축자수정", 0.30)],
}
CATCH_PER_HOUR = 249.1     # cast_cost 와 같은 값 — 아래에서 실제로 읽어 검증한다


def load(name, d):
    sp = importlib.util.spec_from_file_location(name, os.path.join(d, name + ".py"))
    m = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(m)
    return m


def main():
    os.environ.setdefault("BLOCKSHIP_DATA", os.path.abspath(os.path.join(ROOT, "..", "..", "BlockShip")))
    CC = load("cast_cost", SKILL)
    MV = load("material_value", SKILL)
    D = MV.Data()
    _, _, rows, cph = CC.build_rows()
    if abs(cph - CATCH_PER_HOUR) > 1:
        print(f"🔴 캐스트/h 가 어긋난다: 상수 {CATCH_PER_HOUR} vs 실제 {cph}")
        sys.exit(1)

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
        items = []
        for mid, share in mix:
            q = max(1, round(budget_h * share / unit_h[mid]))
            items.append(ing(mid, q))
        r["ingredients"] = items
        changed += 1
        got = sum(i["qty"] * unit_h[i["typeOrMatId"]] for i in items)
        # ── 상점가 재산출 ── 채굴 원가 × BUY_PREMIUM. parts.json 3번째 필드(가격)를 덮어쓴다.
        w = wage.get(n)
        if w:
            f[2] = str(max(1, round(got * w * BUY_PREMIUM)))
            P["미끼"][n] = "|".join(f)
        report.append((grade, int(f[5]), n, dur, budget_h, got,
                       " · ".join(f"{i['displayName']}×{i['qty']}" for i in items)))

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
        price = round(got * w * BUY_PREMIUM)
        share = price / (dur / cph) / w * 100 if w else 0
        print(f"{g:<2}{lv:>4} {n:<14}{got*60:>7.1f}{price:>10,}{share:>7.0f}%  {txt}")
    print("\n※ 유지비중 = 상점에서 사 쓸 때 미끼값이 낚시 수입에서 차지하는 비율")


if __name__ == "__main__":
    main()
