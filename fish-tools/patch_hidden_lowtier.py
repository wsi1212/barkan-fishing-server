#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
patch_hidden_lowtier.py — 저티어 히든 낚싯대 6종 신설 (2026-09-01).

## 왜
히든 출처(`히든-*`) 장비가 전부 **Lv57~70** 에 몰려 있었다. 젖은 보물상자의
「숨겨진 레시피」 보상은 후보를 «본인 레벨 ±10» 으로 자르므로
(`WetTreasureChestManager.RECIPE_LEVEL_BAND`), **Lv47 미만은 히든 후보가 구조적으로 0** 이고
항상 폴백 풀(상점 사다리의 잠긴 레시피 + 통발)만 뽑혔다. 실측: Lv11·Lv20 폴백 후보의
낚싯대는 **100% 가 NPC 상점 판매품** — 26,000원이면 사는 물건을 「발견」이라고 주고 있었다.

스폰 C(Lv16~20) 3종 + 사막 B(Lv30~36) 3종을 신설해 히든 레벨대를 Lv6 부터 이어 붙인다.
  히든 C Lv16~20 → 상자 후보 Lv6~30 · 히든 B Lv30~36 → Lv20~46 · 기존 히든 A Lv57~ → Lv47~

## 왜 gen_rod_builds.py 가 아니라 패치 레이어인가
`gen_rod_builds.py` 의 기본 공식(SUB_BAND·PRIMARY·CAP)으로 이 6종을 뽑으면 **라이브보다 약하다.**
라이브 C/B 는 이미 2 번 레이어 패치들이 끌어올려 놨기 때문이다 — 공식상 C 행운 상한은 6 인데
라이브 「잉어꾼의 낚싯대」는 행운 14 다. 공식값으로 넣으면 신설 히든이 상점 C 낚싯대의
완전열등이 된다(실측 확인). 그래서 **라이브 같은 등급·같은 빌드 낚싯대를 씨앗**으로 삼아
그 위로 올린다. 6종은 `gen_rod_builds.KEEP_AS_IS` 에 등록돼 있어 전체 재생성에도 안 지워진다.
  → [[feedback_check_layered_patch_authority]]

## 값
스탯은 아래 SPEC 에 박혀 있다(씨앗 대비 주력 +15~25%, 히든 표식으로 행운 상단).
레시피는 **씨앗 낚싯대의 라이브 레시피 × RECIPE_SCALE + 별빛진주** — 별빛진주는 상자에서만
나오는 재료라 「상자로 발견하고 상자로 만든다」가 재료로도 읽힌다.
수량 미세조정은 종전대로 `patch_cast_cost.py` 소관.

사용:
    python3 patch_hidden_lowtier.py <BlockShip데이터폴더>            # dry-run
    python3 patch_hidden_lowtier.py <BlockShip데이터폴더> --apply
"""
import json, os, shutil, sys

SRC = None
APPLY = "--apply" in sys.argv

#: 씨앗 대비 재료 배수 — 히든 프리미엄은 «부피» 보다 아래 표식 재료로 낸다.
#   ★씨앗 레시피 자체가 균일하지 않다(잉어꾼은 같은 C 안에서도 유독 무겁다 — patch_cast_cost.py
#     소관). 배수를 키우면 그 편차가 그대로 증폭돼 C 히든이 B 상점품보다 무거워진다.
RECIPE_SCALE = 1.3
#: 「발견」 표식 재료 — 젖은 보물상자에서만 나오는 별빛 진주.
#   상자로 레시피를 발견하고 상자로 재료를 모아 만든다는 뜻이 재료에도 남는다.
SIGNATURE = {"C": ("별빛진주", 2), "B": ("별빛진주", 3)}

#: (이름, 등급, 출처, Lv, 가격, 내구, 스탯, 씨앗 낚싯대)
#   씨앗 = 라이브 같은 등급·같은 빌드 최상위. 스탯은 씨앗 대비 주력을 올리고 히든 행운을 얹는다.
SPEC = [
    # ── 히든-스폰마을 C (Lv16~20) ──
    ("밀물의 낚싯대",     "C", "히든-스폰마을", 16,  62000, 200,
     "난이도:1,행운:17,등급업:5",                      "잉어꾼의 낚싯대"),
    ("갯바위의 낚싯대",   "C", "히든-스폰마을", 18,  70000, 200,
     "난이도:2,행운:8,크리확률:13,크기:18",              "낚시꾼의 낚싯대"),
    ("뱃사공의 낚싯대",   "C", "히든-스폰마을", 20,  78000, 200,
     "난이도:2,행운:8,판매보너스:16,더블찬스:5",          "장사꾼의 낚싯대"),
    # ── 히든-사막마을 B (Lv30~36) ──
    #   사막 테마(등급업·크기)를 계승. 왕도 B(Lv35~38)와 같은 층이라 완전열등 검사를 꼭 볼 것.
    ("모래시계의 낚싯대", "B", "히든-사막마을", 30, 218000, 320,
     "난이도:3,행운:12,등급업:5,크리확률:12,크기:16",     "전갈 낚싯대"),
    #   ★카라반 난이도가 2 인 건 실수가 아니다 — 3 으로 올리면 라이브 「문서고 낚싯대」가
    #     (난3·등4·경15·행6) 전 축에서 카라반 이하가 돼 완전열등으로 잡힌다. 사막=극단형
    #     (주력↑ 보조↓)이라 난이도를 낮추는 쪽이 테마와도 맞다.
    ("카라반의 낚싯대",   "B", "히든-사막마을", 33, 231000, 320,
     "난이도:2,행운:12,등급업:5,트리플찬스:2,경험치:20",   "유목민 낚싯대"),
    ("사막여우의 낚싯대", "B", "히든-사막마을", 36, 245000, 320,
     "난이도:4,행운:14,등급업:8,도망감소:18",             "모래 낚싯대"),
]

STAT_ORDER = ["난이도", "행운", "등급업", "크리확률", "크기", "판매보너스",
              "더블찬스", "트리플찬스", "경험치", "도망감소", "재료확률", "크리배율"]


def parse_stats(s):
    """'난이도:1,행운:14,등급특화:C:50' → {난이도:1, 행운:14}. 등급특화 같은 3토큰은 뺀다."""
    out = {}
    for token in s.split(","):
        f = token.split(":")
        if len(f) == 2:
            try:
                out[f[0]] = float(f[1])
            except ValueError:
                pass
    return out


def dominated(a_st, a_price, a_lv, b_st, b_price, b_lv):
    """a 가 b 의 완전열등인가 — gen_rod_builds.check 와 같은 규칙."""
    keys = set(a_st) | set(b_st)
    return (all(a_st.get(k, 0) <= b_st.get(k, 0) for k in keys)
            and a_price >= b_price and a_lv >= b_lv)


def main():
    global SRC
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        raise SystemExit("사용: patch_hidden_lowtier.py <BlockShip데이터폴더> [--apply]")
    SRC = args[0]
    pp = os.path.join(SRC, "parts.json")
    rp = os.path.join(SRC, "recipes.json")
    ep = os.path.join(SRC, "enhance.json")
    mp = os.path.join(SRC, "materials.json")

    P = json.load(open(pp, encoding="utf-8"))
    R = json.load(open(rp, encoding="utf-8"))
    E = json.load(open(ep, encoding="utf-8"))
    mats = json.load(open(mp, encoding="utf-8"))["materials"]
    rods = P["parts"]["낚싯대"]
    recs, cats, n2i = R["recipes"], R["categories"], R.setdefault("rodNameToId", {})

    # ── 1. 사전 검증 ────────────────────────────────────────────────
    errs = []
    for name, grade, origin, lv, price, dur, st, seed in SPEC:
        if name in rods:
            errs.append(f"{name}: 이미 parts.json 에 있다 (재실행? 값이 다르면 손으로 확인할 것)")
        if seed not in rods:
            errs.append(f"{name}: 씨앗 낚싯대 «{seed}» 가 parts.json 에 없다")
        elif seed not in n2i or n2i[seed] not in recs:
            errs.append(f"{name}: 씨앗 «{seed}» 의 레시피가 없다")
        if not origin.startswith("히든"):
            errs.append(f"{name}: 출처가 히든-* 가 아니면 상자 히든 풀에 안 들어간다")
        sig = SIGNATURE[grade][0]
        if sig not in mats:
            errs.append(f"{name}: materials.json 에 없는 재료 {sig}")
    if errs:
        raise SystemExit("사전 검증 실패:\n  - " + "\n  - ".join(errs))

    # ── 2. 라이브 전체와 완전열등 대조 (양방향) ─────────────────────
    live = []
    for n, v in rods.items():
        f = v.split("|")
        live.append((n, f[1], parse_stats(f[4]), int(f[2]), int(f[5])))
    new_rows = [(name, grade, parse_stats(st), price, lv)
                for name, grade, origin, lv, price, dur, st, seed in SPEC]
    dom = []
    for n1, g1, s1, p1, l1 in new_rows:
        for n2, g2, s2, p2, l2 in live + [x for x in new_rows]:
            if n1 == n2 or g1 != g2:
                continue
            if dominated(s1, p1, l1, s2, p2, l2):
                dom.append(f"{n1} ⊂ {n2}  (신설이 열등)")
            if dominated(s2, p2, l2, s1, p1, l1):
                dom.append(f"{n2} ⊂ {n1}  (기존이 열등해짐)")
    if dom:
        raise SystemExit("완전열등 발생 — SPEC 을 고칠 것:\n  - " + "\n  - ".join(sorted(set(dom))))

    # ── 3. parts.json ───────────────────────────────────────────────
    lines = {}
    for name, grade, origin, lv, price, dur, st, seed in SPEC:
        ordered = ",".join(f"{k}:{int(v)}" for k in STAT_ORDER
                           for v in [parse_stats(st).get(k)] if v)
        lines[name] = "|".join([name, grade, str(price), str(dur), ordered, str(lv), origin])

    # ── 4. recipes.json — 씨앗 레시피 × RECIPE_SCALE + 별빛진주 ─────
    new_recs = {}
    nxt = 60
    for name, grade, origin, lv, price, dur, st, seed in SPEC:
        seed_rec = recs[n2i[seed]]
        items = []
        for ig in seed_rec["ingredients"]:
            items.append({**ig, "qty": max(1, int(round(ig["qty"] * RECIPE_SCALE)))})
        sid, sqty = SIGNATURE[grade]
        if not any(i["typeOrMatId"] == sid for i in items):
            items.append({"kind": "custom", "typeOrMatId": sid,
                          "displayName": mats[sid]["name"], "mcItem": mats[sid]["mcItem"],
                          "qty": sqty})
        while f"R{nxt}" in recs or f"R{nxt}" in new_recs:
            nxt += 1
        rid = f"R{nxt}"
        nxt += 1
        new_recs[name] = {"id": rid, "category": "낚싯대", "displayName": name,
                          # ★locked=true 필수 — randomLockedRecipe 가 locked 만 후보로 본다.
                          "locked": True, "resultMode": "rod", "drillTier": 0,
                          # ★village="" — 히든은 어느 마을 상점에도 안 오른다.
                          "village": "", "rodPartName": name, "ingredients": items}

    # ── 5. enhance.json — 등급 관행대로 (C=10, B=13) ────────────────
    ENH_MAX = {"C": 10, "B": 13}
    new_enh = {}
    for name, grade, origin, lv, price, dur, st, seed in SPEC:
        stt = parse_stats(st)
        axes = [k for k in STAT_ORDER if stt.get(k) and k != "난이도"]
        main_ax = axes[0] if axes else "난이도"
        mx = ENH_MAX[grade]
        levels = {}
        for n in range(1, mx + 1):
            parts_ = [f"{main_ax}:{4 if main_ax == '경험치' else 1}"]
            if n % 2 == 0 and len(axes) > 1:
                parts_.append(f"{axes[1]}:1")
            if n % 5 == 0:
                parts_.append("행운:1")
            if n == mx:
                parts_.append("난이도:1")
            levels[str(n)] = ",".join(parts_)
        new_enh[name] = {"max": mx, "levels": levels}

    # ── 6. 출력 / 쓰기 ──────────────────────────────────────────────
    print(f"{'적용' if APPLY else 'dry-run'} — 저티어 히든 낚싯대 {len(SPEC)}종\n")
    for name, grade, origin, lv, price, dur, st, seed in SPEC:
        rid = new_recs[name]["id"]
        ing = ", ".join(f"{i['displayName']}x{i['qty']}" for i in new_recs[name]["ingredients"])
        print(f"  {name}  [{grade}] Lv{lv} {price:,}원 {origin}  (씨앗: {seed})")
        print(f"    스탯 {lines[name].split('|')[4]}")
        print(f"    {rid} {ing}")
    print("\n  완전열등 0건 · 강화표 6종")

    if not APPLY:
        print("\n※ dry-run. 실제로 쓰려면 --apply")
        return

    for path in (pp, rp, ep):
        shutil.copy(path, path + ".bak-hiddenlowtier")
    for name, line in lines.items():
        rods[name] = line
        if ["낚싯대", name] not in P["order"]:
            P["order"].append(["낚싯대", name])
    for name, rec in new_recs.items():
        recs[rec["id"]] = rec
        n2i[name] = rec["id"]
        if rec["id"] not in cats["낚싯대"]:
            cats["낚싯대"].append(rec["id"])
    tbl, eorder = E["table"], E.setdefault("order", [])
    for name, prof in new_enh.items():
        tbl[name] = prof
        if name not in eorder:
            eorder.append(name)
    json.dump(P, open(pp, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    json.dump(R, open(rp, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    json.dump(E, open(ep, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"\n  parts.json 낚싯대 {len(rods)}종 / recipes.json 낚싯대 {len(cats['낚싯대'])}개 "
          f"/ enhance.json {len(tbl)}종")


if __name__ == "__main__":
    main()
