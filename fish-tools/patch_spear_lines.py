#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
patch_spear_lines.py — 작살 스탯을 «라인 설계»로 갈아끼운다 (2026-08-27).

설계의 단일 권위는 `.claude/skills/balance-audit/scripts/spear_lines.py` 다.
여기서는 그 산출을 parts.json / recipes.json 에 반영하는 일만 한다.

하는 일 셋:
  ① ASSIGN 에 있는 작살의 **스탯 문자열 교체** (등급 기반 + 라인 가산)
  ② **죽은 스탯 «공격속도» → 도망감소 환산** — 코드 쿨타임 0.25s < 실측 조준 1.295s 라
     전 레벨 0원/h. ASSIGN 밖(사막·상단·왕도·심해) 작살에서도 없앤다. 남겨 두면 「스탯이
     붙어 있는데 아무 일도 안 하는」 상태가 유지된다 — 표시 사기다.
     ★단 **그냥 지우지 않고 도망감소로 바꾼다**(DEAD_SWAP). 이유 둘:
       · 지우기만 하면 사막칼날 작살이 스탯 3줄짜리 앙상한 아이템이 된다(체감 너프).
       · 둘 다 «교전»에 붙는 스탯이라 정체성이 이어진다 — 도망감소는 교전창을 늘려
         찌르기를 더 넣게 해 주므로, 「빨리 찌른다」의 실질을 「오래 붙잡는다」가 대신한다.
  ③ **채집형 3종 신규**(채집·수집·탐사 작살) + 레시피. 작살 어획도 낚싯대와 같은 재료
     드롭을 굴리는데(HarpoonManager.dropCatchMaterials) 재료확률 작살이 한 종도 없었다.

레시피 수량은 여기서 정하지 않는다 — 같은 등급 크리형 작살의 레시피를 씨앗으로 넣고,
**`patch_cast_cost.py` 를 다시 돌려** 요구 캐스트 사다리에 맞춘다(권위 분리).

사용:
    python3 patch_spear_lines.py <BlockShip경로>            # dry-run
    python3 patch_spear_lines.py <BlockShip경로> --apply
"""
import importlib.util, json, os, shutil, sys

SKILL = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                     ".claude", "skills", "balance-audit", "scripts")


def _load(name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(SKILL, name + ".py"))
    m = importlib.util.module_from_spec(spec)
    sv, sys.argv = sys.argv, [name]
    spec.loader.exec_module(m)
    sys.argv = sv
    return m


#: 신규 작살의 레시피 씨앗 — 같은 등급 «크리형» 작살을 베낀다(수량은 cast_cost 가 다시 맞춘다).
SEED_FROM = {"채집 작살": "벼린 작살", "수집 작살": "예봉 작살", "탐사 작살": "섬광 작살"}
#: 채집형답게 씨앗의 «테마 재료»를 거대비늘로 바꾼다(낚싯대 채집 라인과 같은 재료).
THEME = {"안개수정": "거대비늘", "진주": "거대비늘"}
#: 죽은 스탯 환산율 — 공격속도 N → 도망감소 round(N×0.6), 최소 5.
DEAD_SWAP = ("공격속도", "도망감소", 0.6, 5)


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    src, apply_ = sys.argv[1], "--apply" in sys.argv
    os.environ["BLOCKSHIP_DATA"] = src
    SL = _load("spear_lines")

    pp, rp = os.path.join(src, "parts.json"), os.path.join(src, "recipes.json")
    P = json.load(open(pp, encoding="utf-8"))
    R = json.load(open(rp, encoding="utf-8"))
    SP = P["parts"]["작살"]

    # ── ① 신규 작살 등록 ──────────────────────────────────────────────
    added = []
    for name, (grade, lvl, price, srcv) in SL.NEW.items():
        if name in SP:
            continue
        dur = max(int(SP[n].split("|")[3]) for n, l in SP.items()
                  if l.split("|")[1] == grade) if any(
            l.split("|")[1] == grade for l in SP.values()) else 100
        stats = ",".join(f"{k}:{v}" for k, v in
                         SL.ordered(SL.build_stats(grade, SL.ASSIGN[name][1])).items())
        SP[name] = "|".join([name, grade, str(price), str(dur), stats, str(lvl), srcv])
        added.append((name, grade, lvl, price, dur))

    # ── ② 스탯 교체 ───────────────────────────────────────────────────
    changed, dead_only = [], []
    for name, line in SP.items():
        f = line.split("|")
        old = f[4]
        if name in SL.ASSIGN:
            grade, ln = SL.ASSIGN[name]
            f[1] = grade
            new = ",".join(f"{k}:{v}" for k, v in
                           SL.ordered(SL.build_stats(grade, ln)).items())
        elif name in getattr(SL, "OVERRIDE", {}):
            # 라인 교체 없이 수치만 머지 (심해 3종의 야간투시 등 고유 스탯 보존)
            cur = dict(x.split(":") for x in old.split(","))
            for kk, vv in SL.OVERRIDE[name].items():
                cur[kk] = str(vv)
            cur.pop("공격속도", None)
            new = ",".join(f"{k}:{v}" for k, v in cur.items())
            if new != old:
                dead_only.append((name, old, new))
        else:
            # ASSIGN 밖 — 죽은 스탯만 제거하고 나머지는 손대지 않는다
            dk, tk, rate, floor = DEAD_SWAP
            cur = dict(x.split(":") for x in old.split(","))
            if dk in cur:
                add = max(floor, int(round(int(cur[dk]) * rate)))
                cur[tk] = str(int(cur.get(tk, 0)) + add)
                del cur[dk]
            new = ",".join(f"{k}:{v}" for k, v in cur.items())
            if new != old:
                dead_only.append((name, old, new))
        if new != old:
            f[4] = new
            SP[name] = "|".join(f)
            if name in SL.ASSIGN:
                changed.append((name, f[1], old, new))

    # ── ③ 신규 레시피 ─────────────────────────────────────────────────
    recs = []
    nxt = max(int(k[2:]) for k in R["recipes"] if k.startswith("HP") and k[2:].isdigit()) + 1
    byname = {(v.get("resultPartName") or v.get("rodPartName")): k
              for k, v in R["recipes"].items()}
    for name in SL.NEW:
        if name in byname:
            continue
        seed = R["recipes"][byname[SEED_FROM[name]]]
        rid = f"HP{nxt:02d}"
        nxt += 1
        ing = []
        for i in seed["ingredients"]:
            j = dict(i)
            j["typeOrMatId"] = THEME.get(j["typeOrMatId"], j["typeOrMatId"])
            if j["typeOrMatId"] != i["typeOrMatId"]:
                j["displayName"] = j["typeOrMatId"]
                for v in R["recipes"].values():
                    for x in v.get("ingredients", []):
                        if x.get("typeOrMatId") == j["typeOrMatId"]:
                            j["displayName"], j["mcItem"] = x.get("displayName"), x.get("mcItem")
                            break
            ing.append(j)
        # 같은 재료가 겹치면 합친다(진주·안개수정 → 거대비늘)
        merged = {}
        for i in ing:
            k = i["typeOrMatId"]
            if k in merged:
                merged[k]["qty"] += i["qty"]
            else:
                merged[k] = i
        R["recipes"][rid] = {**{k: v for k, v in seed.items()
                                if k not in ("id", "displayName", "resultPartName",
                                             "ingredients")},
                             "id": rid, "displayName": name, "resultPartName": name,
                             "ingredients": list(merged.values())}
        recs.append((rid, name, [(i["typeOrMatId"], i["qty"]) for i in merged.values()]))

    # ── 보고 ──────────────────────────────────────────────────────────
    print(f"신규 작살 {len(added)}종")
    for n, g, lv, pr, du in added:
        print(f"   {g} Lv{lv:<3}{n:<10} {pr:,}원 내구{du}  {SP[n].split('|')[4]}")
    print(f"\n신규 레시피 {len(recs)}건 (수량은 patch_cast_cost 가 다시 맞춘다)")
    for rid, n, ing in recs:
        print(f"   {rid} {n:<10} " + ", ".join(f"{a}×{b}" for a, b in ing))
    print(f"\n스탯 교체 {len(changed)}종")
    for n, g, o, w in changed:
        print(f"   {g} {n:<12}\n       전 {o}\n       후 {w}")
    print(f"\n죽은 스탯 «공격속도» → 도망감소 환산 {len(dead_only)}종 (ASSIGN 밖 — 다른 마을)")
    for n, o, w in dead_only:
        print(f"   {n:<16} {o}  →  {w}")

    if not apply_:
        print("\n[dry-run] --apply 로 실제 반영")
        return
    for path, data in ((pp, P), (rp, R)):
        shutil.copy(path, path + ".bak-spearlines")
        json.dump(data, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"\n✅ parts.json({len(SP)}종 작살) · recipes.json 반영")
    print("   → 다음: patch_cast_cost.py 를 다시 돌려 신규 3종의 요구 캐스트를 사다리에 맞출 것")


if __name__ == "__main__":
    main()
