#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cooking_full_audit.py — 요리 3용도(버프/제출/판매) 전면 재판정.

★2026-08-05 신설. buff_values.py는 F절(버프)만 다뤘다. 유저 지적: "포인트도 그렇고 판매용도
그렇고 버프용도 그렇고" — 3용도 전부 손봐야 한다. 이 스크립트가 제출(포인트)·판매 축을 추가한다.

세 용도는 원가모델이 다르다:
  · 버프(PURPOSE_BUFF)  → buff_values.py가 이미 처리(스탯가치 × 지속시간). T4 편차 35배 확정.
  · 제출(PURPOSE_SUBMIT) → **돈이 아니라 포인트**(월간 섬/길드 랭킹, 상위 3위만 코인 보상 —
    IslandSubmitManager.monthlyCheck). 판정 지표는 원/h가 아니라 **포인트 ÷ 재료원가**(효율).
    코드 주석이 이미 "raw 제출 대비 이득이어야 한다"는 원칙을 明시했으므로, 그 원칙을 수치로 검증한다.
  · 판매(PURPOSE_SELL)  → 조리시간(분~일)이 그 자체로 비용(플레이어는 자유이므로 시간이 아니라
    **재료 투입**이 진짜 비용). 판정 = 원/h(패시브) + 재료비 대비 배율.

재료 원가 산출 (cross_economy_values.py·가치표와 동일 소스):
  · fish(grade,qty): 그 등급 물고기를 잡아 파는 대신 요리에 쓰는 것 → 기회비용 = PRICE×sizeMult
  · 광물/강화계열: cross_economy_values 결과값 재사용
  · 낚시 드랍 재료(진주·별빛진주 등 19종 + 이를 조합한 진주코어·바르칸핵): materials.json
    dropTables 확률 → 필요 포획수 → 중반 시급으로 환산(포획당 605원)
  · 특수작물: 슬롯 임대료 모델 개당가(밀 28.1원 … 수박 1,518.8원) — 앵커 무관(절대값)
  · 채집물: forage-types.json rarity(흔함/희귀) → floor값(355원/4,730원)
  · 강화OO(강화당근·강화밀 등, F01~F10 레시피가 raw wheat×16임을 확인): **바닐라 농사 재료라
    사실상 무료**로 취급(cost=0, 플래그로 표기)

사용법: python3 cooking_full_audit.py
"""
import collections, importlib.util, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
BS = ("/Users/user/Library/Application Support/feather/player-server/servers/"
      "07de2d81-991a-47e2-b62d-06c0d1b5150a/plugins/BlockShip")
SRC = "/Users/user/development/blockship-plugin/src/main/java/com/blockship"


def _load(name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, name + ".py"))
    m = importlib.util.module_from_spec(spec)
    saved, sys.argv = sys.argv, [name]
    spec.loader.exec_module(m)
    sys.argv = saved
    return m


SV = _load("stat_value")
PRICE = SV.PL.PRICE
SIZE_M = SV.size_mult(SV.SIZE_SCORE)          # 실측 크기점수 배율 (0.828)
CATCH_WON = SV.compute("중반")["per_catch"]    # 605원/포획 (중반)

# ── 낚시 드랍 재료 (materials.json dropTables, 지역 최고확률) ────────────────
_mats = json.load(open(os.path.join(BS, "materials.json"), encoding="utf-8"))
DROP_CHANCE = {}
for region, tbl in _mats["dropTables"].items():
    for e in tbl:
        DROP_CHANCE[e["matId"]] = max(DROP_CHANCE.get(e["matId"], 0), e["chance"] / 100.0)


def drop_cost(mat_id):
    p = DROP_CHANCE.get(mat_id)
    return (1.0 / p) * CATCH_WON if p else None


# 파생 재료(낚시드랍 조합 레시피) — recipes.json C05/C10 확인 결과
DERIVED = {
    "진주코어": [("진주", 4), ("산호조각", 8), ("별빛진주", 2)],
    "바르칸핵": [("바르칸조각", 8), ("압축흑정석", 4), ("별빛진주", 3)],
}

# 광물/강화계열 (cross_economy_values.py 중반 앵커 산출값 재사용)
MINERAL_WON = {
    "흑정석": 64, "철광석": 77, "자수정": 79, "압축흑정석": 573, "압축철광석": 693,
    "강화석탄": 583, "강화철괴": 739, "강화금괴": 1848, "강화다이아몬드": 2217,
    "강화에메랄드": 2217, "강화청금석": 462,
}

# 특수작물 개당 슬롯비용 (앵커 무관 절대값)
CROP_WON = {"밀": 28.1, "당근": 63.3, "감자": 94.9, "토마토": 126.6,
           "양배추": 52.7, "버섯": 56.3, "수박": 1518.8}
CROP_ALIAS = {"작물_밀": "밀", "작물_당근": "당근", "작물_감자": "감자", "작물_토마토": "토마토",
             "작물_양배추": "양배추", "작물_버섯": "버섯", "작물_수박": "수박"}

# 바닐라 농사(강화OO = raw×16, F01~F10 레시피 확인) — 사실상 무료
VANILLA_ENHANCED_CROP = {"강화밀", "강화당근", "강화감자", "강화비트루트", "강화호박",
                         "강화멜론", "강화스위트베리", "강화사과"}

# 채집물 rarity → floor값 (2026-08-05 cross-economy 산출, 앵커=중반)
FORAGE_FLOOR = {"흔함": 355, "희귀": 4730}
_ftypes = json.load(open(os.path.join(BS, "forage-types.json"), encoding="utf-8"))
FORAGE_RARITY = {v["name"]: v.get("rarity", "흔함") for v in _ftypes.values()}


def resolve_cost(kind, mat_id, name, qty, _depth=0):
    """(원가, 확실성태그) — 태그: exact/derived/vanilla_free/unknown."""
    if kind == "fish":
        grade = mat_id
        return PRICE.get(grade, 0) * SIZE_M * qty, "exact(기회비용)"
    if kind == "herbany":
        return FORAGE_FLOOR["흔함"] * qty, "exact(흔함floor)"
    # kind == custom (mat/crop 헬퍼 전부 이걸로 옴)
    key = mat_id
    if key in MINERAL_WON:
        return MINERAL_WON[key] * qty, "exact(광물)"
    if key in CROP_ALIAS:
        return CROP_WON[CROP_ALIAS[key]] * qty, "exact(작물)"
    if key in VANILLA_ENHANCED_CROP:
        return 0.0, "vanilla_free"
    if key in DERIVED and _depth < 2:
        total, tags = 0.0, set()
        for sub_id, sub_qty in DERIVED[key]:
            c, t = resolve_cost("custom", sub_id, sub_id, sub_qty * qty, _depth + 1)
            total += c; tags.add(t)
        return total, "derived(" + "/".join(sorted(tags)) + ")"
    dc = drop_cost(key)
    if dc is not None:
        return dc * qty, "exact(드랍확률)"
    if name.startswith("채집_") or key.startswith("채집_"):
        nm = name[3:] if name.startswith("채집_") else key[3:]
        rarity = FORAGE_RARITY.get(nm, "흔함")
        return FORAGE_FLOOR[rarity] * qty, f"exact(채집:{rarity})"
    return 0.0, "unknown"


def parse_ing_calls(s):
    """ings(...) 안의 fish(...)/crop(...)/mat(...)/forage(...)/herbAny(...) 호출을 파싱."""
    out = []
    for m in re.finditer(r'\b(fish|crop|mat|forage|herbAny)\(', s):
        start = m.end(); depth, i = 1, start
        while i < len(s) and depth:
            if s[i] == "(": depth += 1
            elif s[i] == ")": depth -= 1
            i += 1
        args = SV.__dict__.get("_split_args")  # not present; inline simple splitter below
        raw = s[start:i-1]
        parts, cur, instr = [], [], False
        for c in raw:
            if c == '"':
                instr = not instr; cur.append(c)
            elif c == "," and not instr:
                parts.append("".join(cur).strip()); cur = []
            else:
                cur.append(c)
        if cur:
            parts.append("".join(cur).strip())
        fn = m.group(1)
        if fn == "fish":
            grade = parts[0].strip('"')
            qty = int(parts[1]) if len(parts) > 1 else 1
            out.append(("fish", grade, grade + "등급 물고기", qty))
        elif fn == "herbAny":
            qty = int(parts[-1])
            out.append(("herbany", "herbany", "허브", qty))
        elif fn == "forage":
            # ★forage(name, mc, qty) — crop/mat과 달리 인자가 3개뿐이다(matId가 없고
            #   DishSpecs.java가 내부에서 "채집_"+name으로 합성한다). crop/mat과 같은 파서를
            #   쓰면 name/mc가 뒤바뀌어 rarity 조회가 전부 실패한다(2026-08-05 실제로 겪음).
            name = parts[0].strip('"')
            qty = int(parts[-1])
            out.append(("custom", "채집_" + name.replace(" ", ""), name, qty))
        else:  # crop / mat: (matId, name, mc, qty)
            mat_id = parts[0].strip('"')
            name = parts[1].strip('"') if len(parts) > 1 else mat_id
            qty = int(parts[-1]) if parts[-1].lstrip('-').isdigit() else 1
            out.append(("custom", mat_id, name, qty))
    return out


def cost_of(ing_src):
    total, tags, unknown_names = 0.0, [], []
    for kind, mat_id, name, qty in parse_ing_calls(ing_src):
        c, tag = resolve_cost(kind, mat_id, name, qty)
        total += c
        tags.append(tag)
        if tag == "unknown":
            unknown_names.append(name)
    known = sum(1 for t in tags if t != "unknown")
    coverage = known / len(tags) if tags else 1.0
    return total, coverage, unknown_names


def _split_top(s):
    parts, depth, cur, instr = [], 0, [], False
    for c in s:
        if instr:
            cur.append(c)
            if c == '"':
                instr = False
        elif c == '"':
            instr = True; cur.append(c)
        elif c in "([{":
            depth += 1; cur.append(c)
        elif c in ")]}":
            depth -= 1; cur.append(c)
        elif c == "," and depth == 0:
            parts.append("".join(cur).strip()); cur = []
        else:
            cur.append(c)
    if cur:
        parts.append("".join(cur).strip())
    return parts


def parse_calls(fn_name, src):
    out = []
    for m in re.finditer(r'\b' + fn_name + r'\(', src):
        start = m.end(); depth, i = 1, start
        while i < len(src) and depth:
            if src[i] == "(": depth += 1
            elif src[i] == ")": depth -= 1
            i += 1
        args = _split_top(src[start:i-1])
        if not args or not args[0].startswith('"'):
            continue
        out.append((args, src[start:i-1]))
    return out


def main():
    src = open(os.path.join(SRC, "cooking", "DishSpecs.java"), encoding="utf-8").read()
    src = re.sub(r'//[^\n]*', '', src)

    # ── 제출(포인트) ─────────────────────────────────────────────────────
    print("=" * 108)
    print("제출용 요리 — 포인트 효율 (포인트 ÷ 재료원가)")
    print("=" * 108)
    submits = []
    for args, ing_src in parse_calls("submit", src):
        did, name, tier, points, sell = args[0].strip('"'), re.sub(r'§.', '', args[1].strip('"')), \
            int(args[3]), int(args[4]), int(args[5])
        cost, cov, unk = cost_of(ing_src)
        eff = points / cost if cost > 0 else float("inf")
        submits.append(dict(id=did, name=name, tier=tier, points=points, sell=sell,
                            cost=cost, cov=cov, eff=eff, unk=unk))
    print(f"{'티어':<4}{'n':>3}{'평균포인트':>12}{'평균원가':>13}{'평균효율':>12}{'커버리지':>9}")
    print("─" * 108)
    by_tier = collections.defaultdict(list)
    for s in submits:
        by_tier[s["tier"]].append(s)
    warn = []
    for t in sorted(by_tier):
        arr = [s for s in by_tier[t] if s["cost"] > 0]
        if not arr:
            continue
        effs = [s["eff"] for s in arr]
        print(f"{t:<4}{len(arr):>3}{sum(s['points'] for s in arr)/len(arr):>12,.0f}"
              f"{sum(s['cost'] for s in arr)/len(arr):>13,.0f}{sum(effs)/len(effs):>12.3f}"
              f"{sum(s['cov'] for s in arr)/len(arr)*100:>8.0f}%")
        lo, hi = min(effs), max(effs)
        if lo > 0 and hi / lo > 3:
            b = min(arr, key=lambda x: x["eff"]); w = max(arr, key=lambda x: x["eff"])
            warn.append(f"🟡 제출 T{t} 효율 편차 {hi/lo:.1f}배 "
                        f"({b['name']} {b['eff']:.3f} ↔ {w['name']} {w['eff']:.3f})")
    print("\n효율 상위 6 (포인트/원가 — 재료 대비 이득)")
    for s in sorted([x for x in submits if x["cost"] > 0], key=lambda x: -x["eff"])[:6]:
        print(f"  T{s['tier']} {s['name']:<18}{s['points']:>7}점  원가 {s['cost']:>10,.0f}원  "
              f"효율 {s['eff']:.4f}  커버리지{s['cov']*100:.0f}%")
    print("\n효율 하위 6")
    for s in sorted([x for x in submits if x["cost"] > 0], key=lambda x: x["eff"])[:6]:
        print(f"  T{s['tier']} {s['name']:<18}{s['points']:>7}점  원가 {s['cost']:>10,.0f}원  "
              f"효율 {s['eff']:.4f}  커버리지{s['cov']*100:.0f}%")
    for s in submits:
        if s["unk"]:
            print(f"  ⚠ {s['name']}: 미인식 재료 {s['unk']}")

    # ── raw 제출 대조 (섬 제출표) ────────────────────────────────────────
    cfg = {"흑정석": None}  # placeholder
    print("\n대조 — 최상위 요리(대연회) vs raw 제출표(submit-values.json 기본값)")
    da = next(s for s in submits if s["name"] == "바르칸 대연회")
    print(f"  완성 요리: {da['points']:,}점 (재료원가 {da['cost']:,.0f}원, 커버리지{da['cov']*100:.0f}%)")
    print("  raw 제출표: 다이아몬드블록=500점·에메랄드블록=450점·강화철괴 대응 아이템 없음(섬 제출표는 바닐라 블록 기준)")
    print("  ※코드 주석 원칙(재료를 raw로 제출했을 때 ≈25,300점 < 완성 90,000점) 유지 확인 — 완성이 여전히 유리")

    # ── 판매용 ───────────────────────────────────────────────────────────
    print("\n" + "=" * 108)
    print("판매용 요리 — 원/h(패시브) + 재료비 배율")
    print("=" * 108)
    sells = []
    for args, ing_src in parse_calls("sell", src):
        if len(args) < 6:
            continue
        did, name, tier, sell, ct = args[0].strip('"'), re.sub(r'§.', '', args[1].strip('"')), \
            int(args[3]), int(args[4]), int(args[5])
        cost, cov, unk = cost_of(ing_src)
        won_h = sell / (ct / 3600.0)
        mult = sell / cost if cost > 0 else float("inf")
        sells.append(dict(id=did, name=name, tier=tier, sell=sell, ct=ct,
                          cost=cost, cov=cov, won_h=won_h, mult=mult, unk=unk))
    print(f"{'티어':<4}{'n':>3}{'평균조리':>10}{'평균판매가':>12}{'평균원/h':>11}{'평균배율':>9}")
    print("─" * 108)
    by_tier2 = collections.defaultdict(list)
    for s in sells:
        by_tier2[s["tier"]].append(s)
    for t in sorted(by_tier2):
        arr = by_tier2[t]
        print(f"{t:<4}{len(arr):>3}{sum(s['ct'] for s in arr)/len(arr)/60:>9.0f}분"
              f"{sum(s['sell'] for s in arr)/len(arr):>12,.0f}{sum(s['won_h'] for s in arr)/len(arr):>11,.0f}"
              f"{sum(s['mult'] for s in arr if s['mult']<1e9)/len(arr):>8.2f}x")
        mults = [s["mult"] for s in arr if s["cost"] > 0]
        if mults and max(mults) / min(mults) > 3:
            b = min(arr, key=lambda x: x["mult"]); w = max(arr, key=lambda x: x["mult"])
            warn.append(f"🟡 판매 T{t} 재료배율 편차 {max(mults)/min(mults):.1f}배 "
                        f"({b['name']} {b['mult']:.1f}x ↔ {w['name']} {w['mult']:.1f}x)")
    for s in sells:
        print(f"  T{s['tier']} {s['name']:<16}{s['sell']:>9,}원 ({s['ct']//60}분) 원가{s['cost']:>9,.0f} "
              f"→ 원/h {s['won_h']:>8,.0f}  배율{s['mult']:.2f}x  커버리지{s['cov']*100:.0f}%"
              + (f"  ⚠{s['unk']}" if s['unk'] else ""))
    ref = SV.compute("중반")["income"]
    print(f"\n  참고: 중반 낚시 시급 {ref:,.0f}원/h. 판매요리 원/h 최대 "
          f"{max(s['won_h'] for s in sells):,.0f}원 = 낚시의 {max(s['won_h'] for s in sells)/ref*100:.1f}%"
          f" (패시브 소득 설계 의도상 낮아야 정상)")

    print("\n" + "=" * 108)
    if warn:
        print("경보")
        print("=" * 108)
        for w in warn:
            print("  " + w)
    else:
        print("🟢 제출/판매 경보선 위반 없음")


if __name__ == "__main__":
    main()
