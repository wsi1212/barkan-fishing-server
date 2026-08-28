#!/usr/bin/env python3
"""계열 고유 재료 + 드릴 티어 광물 사다리를 recipes.json 전체에 깐다.

★왜 생성기(gen_rod/spear/part_builds.py)로 안 하나
  세 생성기는 격자(GRID)를 권위로 삼는데, 라이브 카탈로그가 그 격자보다 **49종** 앞서 있다
  (2026-08-28 실측: 낚싯대 4 + 부품 45). 「라인 구멍 자동충전」으로 늘어난 몫이라 격자에 없다.
  그래서 지금 생성기를 돌리면 «이름 유지 원칙 위반» 으로 멈추고, 억지로 태우면 그 49종의
  스탯이 공식으로 재계산돼 최근 밸런스 작업이 통째로 뒤집힌다.
  ⇒ 스탯은 건드리지 않고 **레시피 조성만** 고친다. 생성기 쪽 COMMON 표도 같은 값으로
     맞춰 뒀으니 나중에 격자를 따라잡히면 결과가 일치한다.

━━ 계열 고유 재료 ━━ «이 계열이면 반드시 들어가고, 다른 계열엔 안 들어간다»
    낚싯대 = 정제된 갈고리 (낡은 갈고리×4 ← 부두)
    작살   = 거대 비늘     (협곡)
    부품   = 녹슨 부품     (강)
    통발   = 끈 + 대나무   (TrapSpecs.java — 이미 배타)
  개편 전엔 세 계열이 «단단한 자루·강철 심·진주·압축 흑정석» 넉 장을 똑같이 썼다.
  재료만 보고 무엇을 만드는 레시피인지 알 수 없었고, 어느 어장을 가야 하는지도 안 갈렸다.

━━ 광물 = 드릴 티어 사다리 ━━
    B → 압축 흑정석(T1) · A → + 압축 적철석(T2) · S → + 압축 자수정(T3)
  개편 전 압축 적철석은 쓰는 데가 드릴 T3 레시피 1건, 압축 자수정은 0건이었다.
  T2 드릴로 캔 적철석이 갈 곳이 없어 **T2 자체가 사문화**돼 있었다.

★수량은 여기서 정하지 않는다. 조성만 바꾸고, 요구 캐스트는 patch_cast_cost.py 가 다시 맞춘다
  (그쪽이 κ 사다리의 단일 권위다). 여기서 넣는 수량은 그 피팅의 «출발점»일 뿐이다.
"""
import json, os, sys, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = os.path.join(ROOT, "ops", "blockship-data")

# 계열 고유 재료 — (matId, 등급별 시작 수량)
SIGNATURE = {
    "낚싯대": ("정제된갈고리", {"E": 2, "D": 4, "C": 8, "B": 14, "A": 20, "S": 28}),
    # ★E(나무 작살=시작 무기)만 뺀다. G(네더라이트 작살)는 사다리 밖이지만 계열 최상위라 넣는다.
    "작살":   ("거대비늘",     {"D": 2, "C": 4, "B": 8, "A": 16, "S": 28, "G": 32}),
    "부품":   ("녹슨부품",     {"E": 2, "D": 4, "C": 8, "B": 12, "A": 20, "S": 30}),
}
# 다른 계열의 고유 재료는 그 계열에서 빼낸다.
ALL_SIG = {v[0] for v in SIGNATURE.values()}

# 드릴 티어 광물 — 등급별 시작 수량 (없으면 그 등급엔 안 넣는다)
ORE_LADDER = {
    "압축철광석": {"A": 5, "S": 10},    # T2
    "압축자수정": {"S": 2},             # T3 (자수정×9 = COMP_AME, 심층광맥 잭팟이 지름길)
}

CATS = ("낚싯대", "작살", "부품")


def mat_ing(mats, mid, qty):
    m = mats[mid]
    return {"kind": "custom", "typeOrMatId": mid, "displayName": m["name"],
            "mcItem": m["mcItem"], "qty": int(qty)}


def main():
    R = json.load(open(os.path.join(BASE, "recipes.json"), encoding="utf-8"))
    P = json.load(open(os.path.join(BASE, "parts.json"), encoding="utf-8"))["parts"]
    mats = json.load(open(os.path.join(BASE, "materials.json"), encoding="utf-8"))["materials"]
    recs, cats = R["recipes"], R["categories"]

    # 부품 이름 → 등급
    grade_of = {}
    for t, items in P.items():
        for n, line in items.items():
            grade_of[(t, n)] = line.split("|")[1]
            grade_of[n] = line.split("|")[1]

    for mid in list(ALL_SIG) + list(ORE_LADDER):
        if mid not in mats:
            raise SystemExit(f"★materials.json 에 없는 재료: {mid}")

    stat = collections.Counter()
    missing_grade = []
    for cat in CATS:
        sig_id, sig_qty = SIGNATURE[cat]
        for rid in cats.get(cat, []):
            r = recs[rid]
            name = r.get("rodPartName") or r.get("resultPartName") or r.get("displayName")
            g = grade_of.get(name)
            if g is None:
                missing_grade.append((cat, rid, name))
                continue
            ings = r.get("ingredients", [])
            # ① 남의 계열 고유 재료 제거
            before = len(ings)
            ings = [i for i in ings
                    if not (i.get("typeOrMatId") in ALL_SIG and i.get("typeOrMatId") != sig_id)]
            stat["타계열재료 제거"] += before - len(ings)
            # ② 자기 계열 고유 재료 보장
            have = next((i for i in ings if i.get("typeOrMatId") == sig_id), None)
            q = sig_qty.get(g)
            if q is None:
                pass                      # 그 등급엔 고유 재료를 안 건다(E 작살 등)
            elif have is None:
                ings.insert(0, mat_ing(mats, sig_id, q))
                stat["고유재료 추가"] += 1
            else:
                ings.insert(0, ings.pop(ings.index(have)))   # 맨 앞으로 — 계열이 한눈에 읽히게
                stat["고유재료 기존"] += 1
            # ③ 드릴 티어 광물
            for ore, table in ORE_LADDER.items():
                q = table.get(g)
                cur = next((i for i in ings if i.get("typeOrMatId") == ore), None)
                if q is None:
                    if cur is not None:
                        ings.remove(cur); stat[f"{ore} 제거"] += 1
                elif cur is None:
                    ings.append(mat_ing(mats, ore, q)); stat[f"{ore} 추가"] += 1
            r["ingredients"] = ings

    if missing_grade:
        for c, rid, n in missing_grade[:10]:
            print(f"🔴 등급을 못 찾음: [{c}] {rid} «{n}»")
        raise SystemExit(f"★parts.json 에 없는 결과물 {len(missing_grade)}종 — 중단")

    json.dump(R, open(os.path.join(BASE, "recipes.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)

    for k, v in stat.items():
        print(f"  {k:<18} {v}")
    print()
    # ── 검산: 배타성 ──
    bad = []
    for cat in CATS:
        sig_id = SIGNATURE[cat][0]
        for other in CATS:
            if other == cat:
                continue
            o_sig = SIGNATURE[other][0]
            for rid in cats.get(cat, []):
                if any(i.get("typeOrMatId") == o_sig for i in recs[rid].get("ingredients", [])):
                    bad.append((cat, rid, o_sig))
    if bad:
        for b in bad[:10]:
            print("🔴 배타성 위반", b)
        raise SystemExit(f"★계열 고유 재료 배타성 위반 {len(bad)}건")
    print("🟢 계열 고유 재료 배타성 OK")

    for cat in CATS:
        sig_id, sig_qty = SIGNATURE[cat]
        ids = cats.get(cat, [])
        n = sum(1 for rid in ids
                if any(i.get("typeOrMatId") == sig_id for i in recs[rid].get("ingredients", [])))
        elig = sum(1 for rid in ids
                   if grade_of.get(recs[rid].get("rodPartName")
                                   or recs[rid].get("resultPartName")) in sig_qty)
        print(f"  {cat}: 고유 재료 {n}/{elig}종 (전체 {len(ids)})")
    for ore in ORE_LADDER:
        n = sum(1 for r in recs.values()
                if any(i.get("typeOrMatId") == ore for i in r.get("ingredients", [])))
        print(f"  {mats[ore]['name']}: 소비 레시피 {n}종")


if __name__ == "__main__":
    main()
