#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
selftest.py — 이 스킬의 회귀 테스트. 감사를 시작하기 전에 한 번 돌린다.

★2026-08-26 신설. 이 스킬의 실패 양식은 «틀린 수치가 조용히 오래 사는 것»이다. 실제로 넉 달간
①가정 상수(220 포획/h)가 실측(190.1)과 어긋난 채 ②재료 확률 오기(별빛진주 8% vs 실제 2%)가
표에 남아 ③부품 총계가 84/131/255 로 세 갈래인 상태로 돌았다. 셋 다 «돌려 보면 바로 아는» 것들
이었는데 돌려 볼 것이 없었다. 이 파일이 그것이다.

검사 항목 (하나라도 실패하면 감사를 진행하지 말 것)
  1. 라이브 데이터 로드 — materials/recipes/parts JSON 이 읽히고 스키마가 맞는가
  2. 실측 스냅샷 — measured.py 가 폴백이 아닌 실제 스냅샷을 쓰는가 + 상수 정합성
  3. 상수 단일화 — stat_value / price_ladder / material_value 가 같은 값을 쓰는가
  4. LP 검산 — 강한 쌍대성 Σλq == 총게이트, 원문제 실현가능
  5. 작살 모델 — 예측 «포획 가능» vs prod 실측 포획 기록 전건 일치
  6. 모델 커버리지 — 원/h 모델이 없는 스탯이 절반 이상인 아이템 수
  7. 문서 드리프트 — 문서에 박힌 수치 vs 라이브 실측 (부품 총계·확률표)
  8. 획득 불가 콘텐츠 — LP 공급원이 없는 재료를 요구하는 아이템

사용:
    python3 selftest.py            # 전체
    python3 selftest.py --quick    # 무거운 항목(4·5) 생략
"""
import argparse, collections, importlib.util, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
BS = os.environ.get("BLOCKSHIP_DATA",
                    "/Users/user/Library/Application Support/feather/player-server/servers/"
                    "07de2d81-991a-47e2-b62d-06c0d1b5150a/plugins/BlockShip")

FAILS, WARNS = [], []


def _load(name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, name + ".py"))
    m = importlib.util.module_from_spec(spec)
    sv, sys.argv = sys.argv, [name]
    spec.loader.exec_module(m)
    sys.argv = sv
    return m


def ok(cond, label, detail="", warn_only=False):
    icon = "🟢" if cond else ("🟡" if warn_only else "🔴")
    print(f"  {icon} {label}" + (f" — {detail}" if detail else ""))
    if not cond:
        (WARNS if warn_only else FAILS).append(f"{label}: {detail}")
    return cond


def t1_data():
    print("\n[1] 라이브 데이터")
    try:
        M = json.load(open(os.path.join(BS, "materials.json"), encoding="utf-8"))
        R = json.load(open(os.path.join(BS, "recipes.json"), encoding="utf-8"))["recipes"]
        P = json.load(open(os.path.join(BS, "parts.json"), encoding="utf-8"))["parts"]
    except Exception as e:
        return ok(False, "JSON 로드", str(e)[:120])
    ok(all(x in M for x in ("materials", "dropTables", "weatherDrops")),
       "materials.json 스키마", f"재료 {len(M['materials'])}종 · 지역 {len(M['dropTables'])}")
    ok(len(R) > 300, "recipes.json", f"{len(R)}건")
    tot = sum(len(v) for v in P.values())
    ok(tot > 200, "parts.json", f"{tot}종 " + " ".join(f"{k}{len(v)}" for k, v in P.items()))
    # 스탯 포맷 검사 — 필드 7개, 레벨/가격/내구가 숫자
    bad = []
    for cat, items in P.items():
        for n, line in items.items():
            f = line.split("|")
            if len(f) < 6 or not f[2].lstrip("-").isdigit() or not f[5].lstrip("-").isdigit():
                bad.append(f"{cat}/{n}")
    ok(not bad, "parts.json 필드 포맷", f"깨진 항목 {len(bad)}: {bad[:4]}")
    return True


def t2_measured():
    print("\n[2] 실측 스냅샷")
    MEAS = _load("measured")
    k = MEAS.load()
    ok(not k["is_fallback"], "스냅샷 사용", k["_source"],
       warn_only=True)   # 폴백도 동작은 하니 경고
    ok(0 < k["catches_per_active_h"] < 1000, "포획/h 범위", f"{k['catches_per_active_h']}")
    ok(k["attempts_per_active_h"] >= k["catches_per_active_h"],
       "소모 ≥ 포획", f"{k['attempts_per_active_h']} ≥ {k['catches_per_active_h']}")
    ok(k["casts_per_active_h"] >= k["attempts_per_active_h"],
       "캐스트 ≥ 소모", f"{k['casts_per_active_h']} ≥ {k['attempts_per_active_h']}")
    inc = k["income_by_band"]
    bands = sorted(inc)
    ok(all(inc[a] <= inc[b] for a, b in zip(bands, bands[1:])),
       "구간 시급 단조증가", " / ".join(f"{b} {inc[b]:,}" for b in bands))
    ok(bool(k.get("harpoon", {}).get("aim_gap_sample")), "작살 조준간격 경험분포",
       f"{len(k.get('harpoon',{}).get('aim_gap_sample') or [])}건", warn_only=True)
    return k


def t3_constants(k):
    print("\n[3] 상수 단일화 (스크립트 간 동일 값)")
    SV = _load("stat_value")
    PL = _load("price_ladder")
    MV = _load("material_value")
    D = MV.Data()
    vals = {
        "stat_value.CATCH_PER_HOUR": SV.CATCH_PER_HOUR,
        "price_ladder.CATCH_PER_HOUR": PL.CATCH_PER_HOUR,
        "material_value(k)": D.k["catches_per_active_h"],
        "measured": k["catches_per_active_h"],
    }
    ok(len(set(round(v, 3) for v in vals.values())) == 1, "포획/h 일치",
       " · ".join(f"{a}={b}" for a, b in vals.items()))
    sizes = {"stat_value.SIZE_SCORE": SV.SIZE_SCORE, "price_ladder.SIZE_SCORE": PL.SIZE_SCORE,
             "measured": k["size_score"]}
    ok(len(set(round(v, 3) for v in sizes.values())) == 1, "크기점수 일치",
       " · ".join(f"{a}={b}" for a, b in sizes.items()))
    # income_of 기본인자까지 갈렸는지 (조용한 오차의 단골)
    ok(abs(SV.income_of.__defaults__[0] - k["size_score"]) < 1e-6,
       "income_of 기본인자 주입", f"{SV.income_of.__defaults__[0]} vs {k['size_score']}")
    # ★2026-08-27 신설 — 시급 단일화. 이걸 안 봐서 결함이 통과했다:
    #   material_value 는 Lv30+ 에 «관측 최고 구간»(115,083)을, item_ledger 는 «종결 모델»
    #   (327,043)을 쓰고 있었다. A 세트 관문 판정이 그 차이 하나로 뒤집혔다
    #   (돈 34.6h ↔ 12.2h → 「돈이 관문」 오판).
    end_model = SV.compute("종결")["income"]
    end_mv = D.wage(None, "종결")
    ok(abs(end_model - end_mv) < 1.0, "종결 시급 일치 (material_value ↔ stat_value)",
       f"stat_value {end_model:,.0f} · material_value {end_mv:,.0f}")
    # stat_value 의 게이트가 LP 에서 오는지 (구 하드코딩 표가 되살아나면 잡는다)
    G = SV._gates()
    MVD = MV.Data()
    lp = {}
    for g in ("D", "C", "B", "A", "S"):
        names, bom, price = MV.full_set_bom(MVD, g)
        if names:
            lp[g] = round(MVD.gate(bom)[0], 2)
    ok(all(abs(G[g][0] - lp[g]) < 0.01 for g in lp if g in G),
       "재료 게이트 = LP 쌍대해", " ".join(f"{g} {G[g][0]:.2f}" for g in sorted(G)))
    return D


def t4_lp(D):
    print("\n[4] LP 검산 (강한 쌍대성 · 실현가능)")
    MV = _load("material_value")
    bad = 0
    for g in ("D", "C", "B", "A", "S"):
        names, bom, price = MV.full_set_bom(D, g)
        if not names:
            continue
        h, lam, hact, _ = D.gate(bom)
        dem = collections.Counter()
        for (kind, m), q in bom.items():
            if kind in ("fish", "ore", "vanilla"):
                dem[m] += q
        s = sum(lam.get(m, 0) * q for m, q in dem.items())
        feas = all(sum(hh * D.act[ac].get(m, 0) for ac, hh in hact.items()) >= q - 1e-6
                   for m, q in dem.items())
        good = abs(h - s) < 1e-6 and abs(sum(hact.values()) - h) < 1e-6 and feas
        bad += not good
        print(f"      {g}: {h:.4f}h  Σλq {s:.4f}h  실현가능 {feas}  {'OK' if good else '✗'}")
    return ok(bad == 0, "5등급 전부 통과", f"실패 {bad}건")


def t5_harpoon():
    print("\n[5] 작살 모델 검증 (예측 vs prod 실측 포획)")
    HV = _load("harpoon_value")
    M = HV.Model()
    bad = HV.validate(M)
    return ok(bad == 0, "예측 = 실측", f"불일치 {bad}건")


def t6_coverage(D):
    print("\n[6] 모델 커버리지")
    IL = _load("item_ledger")
    SV = _load("stat_value")
    HV = _load("harpoon_value")
    MEAS = _load("measured")
    k = MEAS.apply(SV)
    statvals, incomes = {}, {}
    for stage in SV.STAGES:
        r = SV.compute(stage)
        statvals[stage] = {kk: v[0] for kk, v in r["V"].items()}
        incomes[stage] = r["income"]
    HM = HV.Model()
    hs = k.get("harpoon") or {}
    ratio = ((hs.get("catches_per_active_h") or 174.8) / SV.CATCH_PER_HOUR) * \
            (SV.size_mult(hs.get("quality_mean") or 84.3) / SV.size_mult(k["size_score"]))
    rows = IL.build(D, statvals, incomes, ratio, HM)
    low = [r for r in rows if r["cover"] < 0.5 and r["currency"] == "원"]
    ok(not low, "판정 불가 아이템", f"{len(low)}종 " +
       str(dict(collections.Counter(r["cat"] for r in low))))
    unk = collections.Counter(u for r in rows for u in r["unknown"])
    ok(not unk, "미인식 스탯", str(dict(unk)))
    nan = [r for r in rows if r["currency"] == "원" and r["total"] != r["total"]]
    ok(not nan, "원 통화 NaN 누수", f"{len(nan)}종")
    return rows


def t7_drift(rows):
    print("\n[7] 문서 드리프트 (문서 수치 vs 라이브)")
    P = json.load(open(os.path.join(BS, "parts.json"), encoding="utf-8"))["parts"]
    tot = sum(len(v) for v in P.values())
    # ★«stale 표기와 함께 인용된 것»은 정상이다 — 이력 보존이 이 스킬의 설계 목적이니
    #   그 줄까지 잡으면 경고가 영구히 남아 무시하는 습관이 생긴다. 같은 줄에 폐기 표시가
    #   없을 때만 잡는다.
    MARK = ("stale", "폐기", "구 ", "구값", "구 값", "→", "이었다", "철회", "이력", "아니다")
    hits = []
    for rel in ("references/data-sources.md", "references/metrics.md",
                "references/cross-economy-values.md", "references/stat-values.md", "SKILL.md"):
        p = os.path.join(SKILL, rel)
        if not os.path.exists(p):
            continue
        for i, line in enumerate(open(p, encoding="utf-8"), 1):
            if any(m in line for m in MARK):
                continue
            for stale in ("84종", "131종", "220 포획", "포획 220", "259 시도", "시도 259",
                          "95,403", "133,022", "370,210", "65.6"):
                if stale in line:
                    hits.append(f"{rel}:{i}«{stale}»")
    ok(not hits, "stale 수치 문구", f"{len(hits)}건 {hits[:6]}  (라이브 부품 총계 {tot}종)",
       warn_only=True)
    # 확률표를 문서에 옮겨 적은 흔적 — materials.json 과 대조
    M = json.load(open(os.path.join(BS, "materials.json"), encoding="utf-8"))
    # ★2026-08-27 «단일 값» 검사 폐지 — 재료 지역 분배 재설계로 진주·별빛진주에
    #   접근 비용 기울기가 들어갔다(그전엔 16/16 지역 균일 8%/2% 라 지역 차별이 0 이었다).
    #   이제 검사할 것은 «값이 하나인가»가 아니라 «기울기가 살아 있는가»다.
    star = {d["chance"] for t in M["dropTables"].values() for d in t if d["matId"] == "별빛진주"}
    pearl = {d["chance"] for t in M["dropTables"].values() for d in t if d["matId"] == "진주"}
    ok(len(star) > 1, "별빛진주 지역 기울기", f"{sorted(star)}%  (1종이면 균일=설계 위반)")
    ok(len(pearl) > 1, "진주 지역 기울기", f"{sorted(pearl)}%")
    # 드랍표 항목은 «영역이 있고 어종 풀이 있는» 지역에만 — 2026-08-27 규칙
    Fj = json.load(open(os.path.join(BS, "fish.json"), encoding="utf-8"))
    Rj = json.load(open(os.path.join(BS, "regions.json"), encoding="utf-8"))
    ghost = []
    for a in M["dropTables"]:
        rd = Rj.get(a) or {}
        has_area = len(rd.get("polygon") or []) >= 3 or (
            rd.get("pos1") and rd.get("pos1") != [0, 0, 0])
        if a not in Rj or not has_area or a not in Fj.get("regions", {}):
            ghost.append(a)
    #  ★지역 ID 는 명령어 인자라 공백 대신 밑줄을 쓴다(기억의_연못 · 레드_로드 · 폭포_뒤_동굴_1층).
    #    밑줄을 빠뜨리면 `MaterialLoader.normalizeDropTableRegionIds` 가 정규 ID 로 승격하고
    #    `mergeMissingDefaults` 가 원래 키를 다시 넣어 **같은 지역이 두 항목**이 된다
    #    (실측: 기억의연못 + 기억의_연못 = 14 지역). 이 검사가 그 중복도 잡는다.
    ok(not ghost, "드랍표 유령 지역", f"{ghost or '없음'}  (영역·어종 풀 없는 지역)")
    p = os.path.join(SKILL, "references/cross-economy-values.md")
    if os.path.exists(p):
        s = open(p, encoding="utf-8").read()
        ok("별빛진주" not in s or "8%" not in s.split("별빛진주")[1][:120],
           "cross-economy 별빛진주 확률", "문서에 8% 잔존 여부", warn_only=True)


def t8_unobtainable(rows):
    print("\n[8] 획득 불가 콘텐츠")
    # ★이건 «도구 결함»이 아니라 «콘텐츠 발견»이다 — 감사를 막지 말고 리포트로 올려야 한다.
    #   초안은 이걸 🔴 실패로 잡아 「감사를 진행하지 말 것」을 띄웠는데, 정작 감사가 보고해야
    #   하는 항목을 감사 시작 자체를 막는 데 쓴 셈이었다.
    unres = collections.Counter()
    for r in rows:
        for kind, mid, q in r["unresolved"]:
            unres[(kind, mid)] += 1
    ok(not unres, "LP 공급원 없는 재료 (콘텐츠 발견 — 리포트 항목)",
       ", ".join(f"{m}[{k}]×{c}종" for (k, m), c in unres.items()), warn_only=True)
    nopath = [r for r in rows if not r["craftable"] and r["price"] == 0
              and r["currency"] == "원" and r["src"] not in ("튜토", "스폰마을")]
    ok(not nopath, "획득경로 불명", f"{len(nopath)}종 {[r['name'] for r in nopath[:5]]}",
       warn_only=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    a = ap.parse_args()
    print("=" * 78)
    print("balance-audit selftest")
    print("=" * 78)
    t1_data()
    k = t2_measured()
    D = t3_constants(k)
    if not a.quick:
        t4_lp(D)
        t5_harpoon()
    rows = t6_coverage(D)
    t7_drift(rows)
    t8_unobtainable(rows)
    print("\n" + "=" * 78)
    if FAILS:
        print(f"🔴 실패 {len(FAILS)}건 — 감사를 진행하지 말 것")
        for f in FAILS:
            print("   " + f)
    if WARNS:
        print(f"🟡 경고 {len(WARNS)}건 (진행 가능, 리포트에 명시할 것)")
        for w in WARNS:
            print("   " + w)
    if not FAILS and not WARNS:
        print("🟢 전항목 통과")
    sys.exit(1 if FAILS else 0)


if __name__ == "__main__":
    main()
