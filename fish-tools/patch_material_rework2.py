#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
patch_material_rework2.py — 전용 재료 «확률↓ + 요구량↓», 오아시스 감정 특화,
사막 계열 미감정유물 확산, 상단마을 전용 재료 신설 (2026-08-27).

유저 지시:
  "전용재료들이 확률이 좀 높은거같은데 거대비늘 이거 필요한게 10몇게씩만 있으면 되는거
   아닌가? 확률을 낮추고 요구개수도 낮추는게 유저 입장에서 덜 불퀘할거 같은데
   그리고 오아시스가 오래캐 많음? 그리고 상단마을도 전용 있어야해.
   오아시스는 미감정유물을 전용으로 밀고가줘. 오아시스에 감정사가 있어서
   레드로드랑 붉은협곡인가? 그거 두개도 사막이라서 미감정 유물 나와야해"

## ① 전용 재료: 확률과 요구량을 **같은 비율로** 내린다 (캐스트 보존)

착수 실측 — 최고확률 지역에서 «최대 요구량 1벌»을 모으는 캐스트:

    거대비늘  13% · 사용처 39곳 · 중앙 20개 · 최대 48개 → 484 캐스트
    안개수정  10% ·        21곳 ·        8 ·       40 → 524
    산호조각   9% ·         8곳 ·       27 ·       33 → 481
    행운의구슬 8% ·        28곳 ·       15 ·       37 → 606

★«48개 모아라»와 «18개 모아라»는 총 시간이 같아도 체감이 다르다. 확률과 요구량을 같은
  비율로 내리면 **총 캐스트는 그대로**인데 드롭 한 번의 무게가 커지고 목표 숫자가 작아진다.
  유저 표현대로 «덜 불쾌»하다. 캐스트가 보존되므로 밸런스 불변식(κ 사다리)도 안 깨진다.

## ② 오아시스 = «미감정 유물»의 산지

`ArtifactAppraisalGui` 확률표: 깨진토기 55 / 진주조개 20 / 보석 15 / 고대유물 8 / 별빛진주×3 2.
즉 깨진토기·진주조개·고대유물은 **감정 산출물**인데 오아시스 드롭에도 **직접** 들어 있었다
— 그러면 감정할 이유가 없다. 드롭에서 빼고 감정으로만 나오게 한다.
★보석은 예외로 남긴다: 사용처 46곳(총 181개)이라 감정 전용으로 돌리면 병목이 된다.
  대신 확률을 낮춰 «감정이 주 경로, 낚시는 보조»가 되게 한다.
★사용처 0인 «미끼»도 뺀다. 나뭇가지는 사용처 1곳이라 남긴다(빼면 그 아이템을 못 만든다).

## ③ 사막 계열은 미감정 유물이 나온다
붉은사막·레드_로드도 사막이다(regions.json: 레드_로드 parent=붉은사막). 유물이 나와야 한다.

## ④ 상단마을 전용 재료 «교역인장»
13지역 중 **유일하게 전용 재료가 없고** 합계도 최하(22%)였다. 상단마을 A급 47종이 있는데
그 마을에서 캘 수 있는 고유 재료가 없어 재료를 전부 딴 데서 가져와야 했다.

★요구 수량은 여기서 정하지 않는다 — `patch_cast_cost.py` 가 사다리에 맞춘다.

사용:
    python3 patch_material_rework2.py <BlockShip경로> [--apply]
"""
import collections, json, os, shutil, sys

#: 전용 재료 확률 재설정 — (현재%, 목표%). 요구량은 같은 비율로 내린다(캐스트 보존).
RESCALE = {
    "거대비늘":   (13, 5),
    "안개수정":   (10, 5),
    "산호조각":   (9, 5),
    "행운의구슬": (8, 5),
    "깃털찌조각": (9, 6),
    "녹슨부품":   (9, 6),
    "낡은갈고리": (8, 6),
    #  바르칸조각은 반대다 — 4% 인데 최대 43개(1,409 캐스트)라 «개수»가 문제다.
    #  확률을 올려 요구량을 줄인다. 방향은 달라도 목적은 같다(작은 숫자·같은 시간).
    "바르칸조각": (4, 6),
}
#: 오아시스에서 뺄 것 — 감정 산출물(감정으로만 나오게) + 사용처 0.
OASIS_DROP = ["깨진 토기 조각", "고대 유물", "진주조개", "미끼"]
#: ★배치 오류 이전 — 「나뭇가지」는 **오아시스 전용**인데 쓰는 곳이 «초보 낚싯대»(E급 Lv1,
#  스폰마을) 하나뿐이었다. 튜토 직후 플레이어가 사막 오아시스까지 가야 첫 낚싯대를 만든다.
#  스폰마을 낚시터인 «부두»로 옮긴다.
MOVE = {"나뭇가지": ("오아시스", "부두")}
#: 오아시스 확률 재설정
OASIS_SET = {"미감정 유물": 14, "보석": 4}
#: 사막 계열에 미감정 유물 추가
DESERT_ARTIFACT = {"붉은사막": 8, "레드_로드": 8}
#: 상단마을 전용 재료 신설
NEW_MAT = dict(matId="교역인장", displayName="교역 인장", mcItem="gold nugget",
               region="상단마을", chance=6)


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    src, apply_ = sys.argv[1], "--apply" in sys.argv
    mp, rp = os.path.join(src, "materials.json"), os.path.join(src, "recipes.json")
    M = json.load(open(mp, encoding="utf-8"))
    R = json.load(open(rp, encoding="utf-8"))
    P = json.load(open(os.path.join(src, "parts.json"), encoding="utf-8"))["parts"]
    dt = M["dropTables"]
    before = {r: sum(d["chance"] for d in t) for r, t in dt.items()}

    # ── ① 전용 재료 확률 + 요구량 ─────────────────────────────────────
    rescaled = []
    for mid, (old, new) in RESCALE.items():
        k = new / old
        hit = 0
        for r, t in dt.items():
            for d in t:
                if d["matId"] == mid and d["chance"] == old:
                    d["chance"] = new
                    hit += 1
        qb = qa = 0
        for v in R["recipes"].values():
            for i in v.get("ingredients", []):
                if i.get("typeOrMatId") == mid:
                    qb += i["qty"]
                    i["qty"] = max(1, round(i["qty"] * k))
                    qa += i["qty"]
        rescaled.append((mid, old, new, hit, qb, qa))

    # ── ② 오아시스 재편 ───────────────────────────────────────────────
    oa = dt.get("오아시스", [])
    removed = [d["matId"] for d in oa if d["matId"] in OASIS_DROP]
    dt["오아시스"] = [d for d in oa if d["matId"] not in OASIS_DROP]
    for d in dt["오아시스"]:
        if d["matId"] in OASIS_SET:
            d["chance"] = OASIS_SET[d["matId"]]

    # ── ②-b 배치 오류 재료 이전 ───────────────────────────────────────
    moved = []
    for mid, (frm, to) in MOVE.items():
        e = next((d for d in dt.get(frm, []) if d["matId"] == mid), None)
        if e is None:
            continue
        dt[frm] = [d for d in dt[frm] if d["matId"] != mid]
        if not any(d["matId"] == mid for d in dt.get(to, [])):
            dt[to].append(e)
        moved.append((mid, frm, to, e["chance"]))

    # ── ③ 사막 계열 미감정 유물 ───────────────────────────────────────
    proto = next((dict(d) for d in dt["오아시스"] if d["matId"] == "미감정 유물"), None)
    added_art = []
    for reg, ch in DESERT_ARTIFACT.items():
        if reg not in dt:
            continue
        if any(d["matId"] == "미감정 유물" for d in dt[reg]):
            continue
        e = dict(proto) if proto else {"matId": "미감정 유물", "chance": ch}
        e["chance"] = ch
        dt[reg].append(e)
        added_art.append((reg, ch))

    # ── ④ 상단마을 전용 재료 ──────────────────────────────────────────
    nm = NEW_MAT
    if not any(d["matId"] == nm["matId"] for d in dt.get(nm["region"], [])):
        sample = dt[nm["region"]][0]
        e = {k: v for k, v in sample.items() if k not in ("matId", "chance")}
        e.update(matId=nm["matId"], chance=nm["chance"])
        for f, val in (("displayName", nm["displayName"]), ("mcItem", nm["mcItem"]),
                       ("name", nm["displayName"])):
            if f in sample or f in ("displayName", "mcItem"):
                e[f] = val
        dt[nm["region"]].append(e)
    # 상단마을 레시피에 편입 — 그 마을 아이템이 자기 마을 재료를 쓰게
    sd = {n for v in P.values() for n, l in v.items()
          if l.split("|")[6] in ("상단마을", "히든-상단마을")}
    ing_meta = {"kind": "custom", "typeOrMatId": nm["matId"],
                "displayName": nm["displayName"], "mcItem": nm["mcItem"], "qty": 3}
    joined = 0
    for v in R["recipes"].values():
        n = v.get("rodPartName") or v.get("resultPartName")
        if n in sd and not any(i.get("typeOrMatId") == nm["matId"]
                               for i in v.get("ingredients", [])):
            v["ingredients"].append(dict(ing_meta))
            joined += 1

    # ── 보고 ──────────────────────────────────────────────────────────
    print("① 전용 재료 확률↓ + 요구량↓ (캐스트 보존)")
    print(f"   {'재료':<10}{'확률':>10}{'지역':>4}{'총요구':>14}")
    for mid, o, n2, hit, qb, qa in rescaled:
        print(f"   {mid:<10}{o:>4}% → {n2:>2}%{hit:>4}{qb:>7} → {qa:<6}")
    print(f"\n② 오아시스 재편 — 제거 {removed} · 재설정 {OASIS_SET}")
    for mid, frm, to, ch in moved:
        print(f"②-b 배치 이전: {mid} {ch}%  {frm} → {to}  (E급 Lv1 «초보 낚싯대» 재료)")
    print(f"③ 사막 계열 미감정 유물 추가: {added_art}")
    print(f"④ 상단마을 전용 «{nm['matId']}» {nm['chance']}% · 레시피 편입 {joined}건")

    after = {r: sum(d["chance"] for d in t) for r, t in dt.items()}
    print(f"\n지역 합계(%)  {'전':>6} {'후':>6}")
    for r in sorted(dt, key=lambda r: -after[r]):
        mark = "  ←" if abs(after[r] - before[r]) > 0.01 else ""
        print(f"   {r:<14}{before[r]:>6.0f} {after[r]:>6.0f}{mark}")

    if not apply_:
        print("\n[dry-run] --apply 로 실제 반영")
        return
    for path, data in ((mp, M), (rp, R)):
        shutil.copy(path, path + ".bak-rework2")
        json.dump(data, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print("\n✅ materials.json · recipes.json 반영")
    print("   → 다음: MaterialLoader.buildDefaults() 동기화 + patch_cast_cost.py")


if __name__ == "__main__":
    main()
