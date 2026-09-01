#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""재료 도달성 감사 — 「그 레벨의 플레이어가 실제로 모을 수 있는 재료인가」.

## 왜 있나 (2026-09-01)
유저 제보: 「D급이 정제된 갈고리 5개, 진주 32개를 요구한다」. 파 보니 **어떤 감사도 이걸
못 잡는 구조**였다:

 ① `cast_cost` 의 LP 가 재료 단가를 «전 지역 최적 출처»로 매겼다 — Lv7 아이템의 진주를
    Lv12 해금인 오아시스(10%) 가격으로 계산했다. 실제 Lv7 은 부두(4%)뿐이다.
    ⇒ 초반 장비 원가가 2~3배 과소평가되고 「배율 1.00 정상」으로 나왔다.
 ② 중간재가 초반 낚싯대 원가의 65~91% 였다(단단한 자루 1개 = 167 포획 = 0.88h).
 ③ **BOM 을 전개하지 않으면 병목이 안 보인다** — 첫 조사에서 중간재를 「직드롭 아님」으로
    스킵했다가 진짜 원인을 통째로 놓쳤다. 정제된갈고리 5 = 낡은갈고리 20 이다.

그래서 이 감사는 **BOM 을 원재료까지 전개하고, 그 아이템의 레벨제한으로 접근 가능한
지역의 실드롭만** 써서 판정한다. LP 를 안 쓴다 — LP 는 통발·다지역 혼합을 섞으므로
「그 지역에 앉아서 이 아이템 하나 만들기」의 체감을 못 준다.

## 판정
 🔴 도달불가   그 레벨에서 «어느 지역에서도» 안 나오는 재료를 요구한다
 🔴 등급내이상  같은 등급 안에서 중위값의 OUTLIER_X 배를 넘는다
 🟡 쏠림       한 재료가 그 아이템 원가의 CONC_MAX 이상을 차지한다

사용:  python3 ops/audit-material-reachability.py [--full] [--quiet]
"""
import argparse
import json
import pathlib
import statistics
import sys

LIVE = pathlib.Path(
    "/Users/user/Library/Application Support/feather/player-server/servers/"
    "07de2d81-991a-47e2-b62d-06c0d1b5150a/plugins/BlockShip")
SKILL = pathlib.Path(__file__).resolve().parent.parent / ".claude/skills/balance-audit/scripts"

CPH = 190.1          # 실측 포획/h — 배수 판정에만 쓰므로 상수여도 결론이 안 바뀐다
OUTLIER_X = 2.5      # 같은 등급 중위값의 몇 배까지 허용
CONC_MAX = 0.75      # 한 재료가 원가에서 차지할 수 있는 최대 비중
GRADES = ("D", "C", "B", "A", "S")   # E(튜토)는 사다리 밖


def _region_unlock():
    sys.path.insert(0, str(SKILL))
    import importlib.util as u
    spec = u.spec_from_file_location("region_unlock", SKILL / "region_unlock.py")
    m = u.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--full", action="store_true")
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()

    RU = _region_unlock()
    recs = json.loads((LIVE / "recipes.json").read_text(encoding="utf-8"))["recipes"]
    drops = json.loads((LIVE / "materials.json").read_text(encoding="utf-8"))["dropTables"]
    parts = json.loads((LIVE / "parts.json").read_text(encoding="utf-8"))["parts"]

    lvl = {}
    for grp in parts.values():
        for n, v in grp.items():
            f = v.split("|")
            if len(f) >= 6:
                lvl[n] = (f[1], int(f[5]) if f[5].isdigit() else 99)

    # 중간재 전개표 — recipes.json 이 권위(하드코딩 금지)
    inter = {}
    for rid, r in recs.items():
        if r.get("category") in ("재료", "고급") or rid.startswith("C0"):
            out = None
            for ln in (r.get("result") or {}).get("lore") or []:
                if ln.startswith("&8mat:"):
                    out = ln.split(":", 1)[1].strip()
            if out:
                inter[out] = {(i.get("typeOrMatId") or i.get("mcItem")): i.get("qty", 1)
                              for i in r.get("ingredients") or []}

    def explode(ing, depth=0):
        out = {}
        for mid, q in ing.items():
            if mid in inter and depth < 5:
                for k2, q2 in explode(inter[mid], depth + 1).items():
                    out[k2] = out.get(k2, 0) + q * q2
            else:
                out[mid] = out.get(mid, 0) + q
        return out

    def rate_at(mid, level):
        """그 레벨에서 접근 가능한 지역 중 최고 드롭률."""
        best = 0.0
        for reg, ds in drops.items():
            if not RU.reachable(reg, level):
                continue
            for d in ds:
                if d["matId"] == mid:
                    best = max(best, d["chance"] / 100)
        return best or None

    items = []
    for rid, v in recs.items():
        if v.get("category") not in ("낚싯대", "작살", "부품"):
            continue
        nm = v.get("rodPartName") or v.get("resultPartName") or v.get("displayName")
        g, lv = lvl.get(nm, ("?", 99))
        if g not in GRADES:
            continue
        raw = explode({(i.get("typeOrMatId") or i.get("mcItem")): i.get("qty", 1)
                       for i in v.get("ingredients") or []})
        per, unreach = {}, []
        for mid, q in raw.items():
            c = rate_at(mid, lv)
            if c is None:
                # 낚시 드롭이 아닌 것(광석·바닐라)은 이 감사의 범위가 아니다.
                if any(mid == d["matId"] for ds in drops.values() for d in ds):
                    unreach.append((mid, q))
                continue
            per[mid] = q / c
        if not per:
            continue
        tot = sum(per.values())
        top_mid, top_t = max(per.items(), key=lambda t: t[1])
        items.append(dict(id=rid, name=nm, cat=v["category"], grade=g, lvl=lv,
                          catches=tot, worst=top_t / tot, worst_mid=top_mid,
                          worst_qty=raw[top_mid], unreach=unreach))

    errors, warns = [], []
    for it in items:
        for mid, q in it["unreach"]:
            opens = [RU.unlock_level(rg) for rg, ds in drops.items()
                     if any(d["matId"] == mid for d in ds)]
            need = min(opens) if opens else "?"
            errors.append(f"🔴 {it['grade']} Lv{it['lvl']} {it['name']}: "
                          f"{mid}×{q} — Lv{it['lvl']} 에서 접근 가능한 어느 지역에서도 안 나온다 "
                          f"(가장 빠른 해금 Lv{need})")
    # 등급 내 이상치
    for cat in sorted({i["cat"] for i in items}):
        for g in GRADES:
            grp = [i for i in items if i["cat"] == cat and i["grade"] == g]
            if len(grp) < 4:
                continue
            med = statistics.median(i["catches"] for i in grp)
            for i in grp:
                if med > 0 and i["catches"] > med * OUTLIER_X:
                    errors.append(
                        f"🔴 {g} Lv{i['lvl']} {i['name']}({cat}): {i['catches']:.0f}포획 = "
                        f"{i['catches']/CPH:.1f}h — 같은 등급 중위 {med:.0f}포획의 "
                        f"{i['catches']/med:.1f}배 (병목 {i['worst_mid']}×{i['worst_qty']})")
    for i in items:
        if i["worst"] > CONC_MAX:
            warns.append(f"🟡 {i['grade']} Lv{i['lvl']} {i['name']}: "
                         f"{i['worst_mid']}×{i['worst_qty']} 하나가 원가의 {i['worst']*100:.0f}%")

    if not a.quiet or errors:
        print(f"— 재료 도달성 감사: 검사 {len(items)}종 / ERROR {len(errors)}건 / WARN {len(warns)}건")
    if errors:
        for e in errors[: (None if a.full else 15)]:
            print("  " + e)
        if not a.full and len(errors) > 15:
            print(f"  … 외 {len(errors)-15}건 (--full)")
    if a.full:
        for w in warns:
            print("  " + w)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
