#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
patch_trap_materials.py — 통발 13종의 재료를 «우리 커스텀 재료 체계»로 교체 (2026-09-01).

설계 권위는 `.claude/skills/balance-audit/scripts/trap_cost.py --design` 이다. 이 스크립트는
그 산출을 **TrapSpecs.java 에 써 넣고**, 부팅 전에도 값이 맞도록 recipes.json 통발 항목을
같이 갱신한다(런타임 권위는 `RecipeLoader.ensureTrapRecipes` 가 부팅마다 Java 에서 재주입).

## 왜
통발 재료 17종이 전부 바닐라였고 **어느 활동에서도 안 나왔다** — 일반 월드는
`MapProtectionListener` 가 블록 파괴를 취소하고 드롭도 안 준다. 프리즈머린·마그마 크림은
파는 데도 없고, 자재 탭이 라이브 `shop-items.json` 에서 빠지면서 끈·슬라임볼·점토도 끊겼다.
실측: prod 32명 중 통발을 설치해 본 사람이 1명, 설치된 통발 1개(부두 = 유일하게 조달 가능).

## 새 규칙
    지역 전용 재료(정체성) + 강화 실(엮기) + 물고기 비늘(유인) + 진주(등급)
전부 그 지역 낚시 드롭이다 — 통발을 놓을 자리에서 나는 것으로 통발을 짠다.

사용:
    python3 patch_trap_materials.py                 # dry-run
    python3 patch_trap_materials.py --apply
"""
import importlib.util, json, os, pathlib, re, shutil, sys

HERE = pathlib.Path(__file__).resolve().parent
SKILL = HERE.parent / ".claude" / "skills" / "balance-audit" / "scripts"
JAVA = pathlib.Path(os.path.expanduser(
    "~/development/blockship-plugin/src/main/java/com/blockship/trap/TrapSpecs.java"))
LIVE = pathlib.Path(os.environ.get("BLOCKSHIP_DATA",
    "/Users/user/Library/Application Support/feather/player-server/servers/"
    "07de2d81-991a-47e2-b62d-06c0d1b5150a/plugins/BlockShip"))
REPO = HERE.parent / "ops" / "blockship-data"
APPLY = "--apply" in sys.argv


def _mod(name):
    spec = importlib.util.spec_from_file_location(name, SKILL / f"{name}.py")
    m = importlib.util.module_from_spec(spec)
    sv, sys.argv = sys.argv, [name]
    spec.loader.exec_module(m)
    sys.argv = sv
    return m


TC = _mod("trap_cost")
MV = _mod("material_value")


def java_args(ings):
    return ", ".join(f'mat("{i["typeOrMatId"]}", "{i["mcItem"]}", "{i["displayName"]}", {i["qty"]})'
                     for i in ings)


def rewrite_java(src, plan):
    """put(new Spec("<region>", …, <price>, <재료들>)); 의 재료 인자만 교체."""
    out, misses = src, []
    for region, ings in plan.items():
        # 그 지역의 put(new Spec( … )); 블록을 찾아 마지막 인자군(재료)만 갈아 끼운다.
        pat = re.compile(r'(put\(new Spec\("' + re.escape(region) +
                         r'",\s*"[^"]*",\s*"[^"]*",\s*\d+,\s*\d+,\s*"[^"]+",\s*\d+,)(.*?)(\)\);)', re.S)
        m = pat.search(out)
        if not m:
            misses.append(region)
            continue
        out = out[:m.start()] + m.group(1) + "\n                " + java_args(ings) + m.group(3) + out[m.end():]
    return out, misses


def sync_recipes(path, plan, specs_by_region):
    """recipes.json 통발 항목의 ingredients 를 맞춘다 (부팅 전 정합용)."""
    P = pathlib.Path(path) / "recipes.json"
    if not P.exists():
        return 0, f"{P} 없음"
    R = json.loads(P.read_text(encoding="utf-8"))
    recs = R["recipes"]
    n = 0
    for region, ings in plan.items():
        rid = specs_by_region[region]["recipeId"]
        r = recs.get(rid)
        if r is None:
            continue
        r["ingredients"] = [{"kind": "custom", "typeOrMatId": i["typeOrMatId"],
                             "displayName": i["displayName"], "mcItem": i["mcItem"],
                             "qty": i["qty"]} for i in ings]
        n += 1
    if APPLY:
        shutil.copy(P, str(P) + ".bak-trapmat")
        P.write_text(json.dumps(R, ensure_ascii=False, indent=2), encoding="utf-8")
    return n, None


def main():
    D = MV.Data()
    rows = TC.design(D)
    plan = {r["spec"]["region"]: r["ings"] for r in rows}
    specs_by_region = {r["spec"]["region"]: r["spec"] for r in rows}

    print(f"{'적용' if APPLY else 'dry-run'} — 통발 {len(plan)}종 재료 교체\n")
    for r in rows:
        old = " · ".join(f'{i["displayName"]}×{i["qty"]}' for i in r["spec"]["ingredients"])
        new = " · ".join(f'{i["displayName"]}×{i["qty"]}' for i in r["ings"])
        print(f"  {r['spec']['label']}")
        print(f"    구: {old}")
        print(f"    신: {new}   (τ {r['tau_real']:.0%} · 비용 {r['cost_h']:.2f}h)")

    src = JAVA.read_text(encoding="utf-8")
    out, misses = rewrite_java(src, plan)
    if misses:
        raise SystemExit(f"\n❌ TrapSpecs.java 에서 못 찾은 지역: {misses} — 정규식/코드 구조 확인")
    if "prismarine" in out or 'ing("' in out.split("static {", 1)[1].split("// ── 변종 폐지", 1)[0]:
        leftovers = re.findall(r'ing\("([^"]+)"', out)
        raise SystemExit(f"\n❌ 바닐라 재료가 남아 있다: {sorted(set(leftovers))}")
    print(f"\n  TrapSpecs.java: 바닐라 재료 잔존 0 · {len(plan)}종 치환")

    n, err = sync_recipes(LIVE, plan, specs_by_region)
    print(f"  recipes.json(라이브): {n}종 갱신" + (f"  ⚠ {err}" if err else ""))
    n2, err2 = sync_recipes(REPO, plan, specs_by_region)
    print(f"  recipes.json(레포):   {n2}종 갱신" + (f"  ⚠ {err2}" if err2 else ""))

    if not APPLY:
        print("\n※ dry-run. 실제로 쓰려면 --apply")
        return
    shutil.copy(JAVA, str(JAVA) + ".bak-trapmat")
    JAVA.write_text(out, encoding="utf-8")
    print(f"\n  → {JAVA}")
    # 재파싱 검증 — 쓴 파일을 다시 읽어 13종이 그대로 나오는지
    again = TC.load_specs()
    bad = [s["label"] for s in again
           if any(i["kind"] != "custom" for i in s["ingredients"])]
    print("  🟢 재파싱 13종 · 커스텀 전환 완료" if len(again) == len(plan) and not bad
          else f"  🔴 재파싱 이상: {len(again)}종, 바닐라 잔존 {bad}")


if __name__ == "__main__":
    main()
