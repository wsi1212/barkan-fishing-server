#!/usr/bin/env python3
"""장비/작살 레시피의 «원재료» 수량을 기준값으로 되돌린다 (2026-08-24).

배경 — 2026-08-22~24 의 재료 75% 컷(RecipeLoader v1)은 재료 종류를 안 가리고
전부 1/4 로 깎았다. 그런데 가공재(정제된갈고리=낡은갈고리 8, 강철심=원재료 104
…)는 자기 레시피가 너프 대상이 아니었으므로, 결과적으로

    정제된 갈고리 2(=낡은 갈고리 16) + 녹슨 부품 2

처럼 자리수가 안 맞는 줄이 남았다. 장비 레시피 실질 재료비의 99.5% 가 가공재에서
나오고 낚시 드랍 원재료는 45% 가 «1개»인 장식이 됐다.

이 스크립트는 <b>원재료 수량만</b> 기준값으로 복원한다. 가공재와 희귀/화폐 재료
(진주·별빛진주·자수정·보석)는 손대지 않는다 — 그쪽까지 되돌리면 컷이 무의미해지고
(진주 1,095 → 4,047) 오아시스 2% 드랍인 보석은 벽이 된다.

★구성(어떤 재료가 들어가나)은 라이브를 그대로 둔다 — 수량만 바꾼다. 그래서
  2026-08-24 의 「C등급 이하 압축 흑정석 제외」 같은 후속 결정을 되돌리지 않는다.
  (git 스냅샷을 그대로 base 로 쓰면 흑정석이 되살아난다 — 실제로 밟은 함정이다.)

기준값 출처는 이 순서로 찾는다:
  1. 너프 직전 스냅샷(blockship-plugin fb6d5bd^:recipes.json) 의 같은 레시피·같은 재료
  2. 생성기 3종의 등급별 기준표(COMMON / MAT_QTY / BUILD_MAT_QTY / LOW_GRADE_*)
  3. 둘 다 없으면 건드리지 않는다(추정 배수 금지 — 재실행 때 또 불어난다)

이 규칙 덕에 몇 번 실행해도 결과가 같다(멱등).

사용:  restore_raw_material_qty.py <BlockShip 데이터 폴더> [--apply]
       (기본은 dry-run — 표만 출력한다)
"""
import json
import os
import re
import subprocess
import sys

PLUGIN_REPO = "/Users/user/development/blockship-plugin"
PRE_NERF_REV = "fb6d5bd^:recipes.json"   # 2026-08-22 22:11 직전 = 75% 컷 이전 기준 수량
# 희귀/화폐 재료 — 원재료지만 복원 대상에서 뺀다.
RARE = {"진주", "별빛진주", "자수정", "보석"}
PART_TYPES = {"릴", "줄", "바늘", "미끼", "찌", "작살"}
GRADES = ["E", "D", "C", "B", "A", "S", "SS", "G"]


def load_gen_tables(src):
    """생성기 3종의 등급별 기준 재료표를 그대로 읽어 온다(생성기가 권위)."""
    here = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, here)
    saved = sys.argv
    sys.argv = ["gen", src]          # 생성기들은 import 시점에 SRC = sys.argv[1] 을 읽는다
    try:
        import importlib
        rod = importlib.import_module("gen_rod_builds")
        part = importlib.import_module("gen_part_builds")
        spear = importlib.import_module("gen_spear_builds")
    finally:
        sys.argv = saved
    return {
        "낚싯대": (rod.COMMON, rod.BUILD_MAT_QTY, None),
        "작살": (spear.COMMON, spear.BUILD_MAT_QTY, None),
        "부품": (part.COMMON, part.MAT_QTY, (part.LOW_GRADE_COMMON, part.LOW_GRADE_TYPE_QTY)),
    }


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    src = sys.argv[1]
    apply_ = "--apply" in sys.argv[2:]
    rec_path = os.path.join(src, "recipes.json")
    R = json.load(open(rec_path, encoding="utf-8"))
    recs = R["recipes"]
    parts = json.load(open(os.path.join(src, "parts.json"), encoding="utf-8"))["parts"]

    grade, village = {}, {}
    for cat, items in parts.items():
        pairs = items.items() if isinstance(items, dict) else [(x.split("|")[0], x) for x in items]
        for name, spec in pairs:
            if isinstance(spec, str):
                f = spec.split("|")
                grade[(cat, name)] = f[1]
                village[(cat, name)] = f[6] if len(f) > 6 else ""

    # 가공재 = 「재료」 카테고리 레시피가 산출하는 mat id
    craft = set()
    for v in recs.values():
        if v.get("category") != "재료":
            continue
        for line in (v.get("result") or {}).get("lore") or []:
            m = re.search(r"mat:(\S+)", line)
            if m:
                craft.add(m.group(1))

    snap = json.loads(subprocess.run(
        ["git", "-C", PLUGIN_REPO, "show", PRE_NERF_REV],
        capture_output=True, text=True, check=True).stdout)["recipes"]
    tables = load_gen_tables(src)

    def key_of(v):
        if v.get("category") == "낚싯대":
            return ("낚싯대", v.get("rodPartName") or v.get("displayName"))
        if v.get("category") == "작살":
            return ("작살", v.get("displayName"))
        return (v.get("resultPartType"), v.get("resultPartName"))

    def is_equipment(v):
        return (v.get("category") in ("낚싯대", "작살")
                or (v.get("resultMode") == "part" and v.get("resultPartType") in PART_TYPES))

    def base_qty(rid, v, mat, g):
        # ① 너프 직전 스냅샷의 같은 레시피·같은 재료
        s = snap.get(rid)
        if s:
            for j in s.get("ingredients", []):
                if j["typeOrMatId"] == mat:
                    return j["qty"], "스냅샷"
        # ② 생성기 등급 기준표
        cat = "낚싯대" if v.get("category") == "낚싯대" else "작살" if v.get("category") == "작살" else "부품"
        common, build_qty, low = tables[cat]
        if low and g in low[0]:                          # 스폰마을 저티어(E·D) 전용 표
            for m, q in low[0][g]:
                if m == mat:
                    return q, "생성기(저티어)"
            if mat not in [m for m, _ in low[0][g]]:
                return low[1].get(g), "생성기(저티어 타입재)"
        for m, q in common.get(g, []):
            if m == mat:
                return q, "생성기(공통)"
        if g in build_qty:                               # 빌드 슬롯 재료
            return build_qty[g], "생성기(빌드)"
        return None, None

    rows, skipped = [], []
    for rid, v in recs.items():
        if not is_equipment(v):
            continue
        g = grade.get(key_of(v))
        if not g:
            continue
        for ing in v.get("ingredients", []):
            mat = ing["typeOrMatId"]
            if mat in craft or mat in RARE:
                continue
            b, why = base_qty(rid, v, mat, g)
            if b is None:
                skipped.append((g, rid, key_of(v)[1], ing["displayName"], ing["qty"]))
                continue
            if b != ing["qty"]:
                rows.append((g, village.get(key_of(v), ""), rid, key_of(v)[1],
                             ing["displayName"], ing["qty"], b, why))
                if apply_:
                    ing["qty"] = b

    rows.sort(key=lambda r: (GRADES.index(r[0]) if r[0] in GRADES else 9, r[2]))
    print(f"{'등급':<3}{'마을':<9}{'id':<7}{'장비':<18}{'재료':<11}{'지금':>4} → {'기준':>4}  근거")
    for g, vi, rid, nm, mat, now_q, b, why in rows:
        print(f"{g:<3}{vi:<9}{rid:<7}{nm:<18}{mat:<11}{now_q:>4} → {b:>4}  {why}")
    print(f"\n복원 대상 {len(rows)}개 항목 / 레시피 {len({r[2] for r in rows})}건")
    if skipped:
        print(f"기준값 없어 그대로 둔 항목 {len(skipped)}개:")
        for s in skipped:
            print("   ", s)
    if apply_:
        json.dump(R, open(rec_path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        print(f"\n적용 완료 → {rec_path}")
    else:
        print("\n(dry-run — 적용하려면 --apply)")


if __name__ == "__main__":
    main()
