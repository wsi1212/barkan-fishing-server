#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""patch_feather_swap.py — E·D 등급에서 «깃털찌조각»을 뺀다.

## 왜 (유저 결정 2026-09-02: 「깃털 찌 조각 빼줘 D까지는, 그거 찾기 쉽지 않음」)
깃털찌조각은 **기억의_연못 6% 단독 출처**다(materials.json 실측 — 다른 지역·날씨 드롭 전무).
기억의_연못은 통발가 7,000원 티어라 접근 레벨이 Lv7 이다. 그런데 이걸 요구하는 장비 중
E Lv1 2종 · D Lv4~5 5종이 있었다 — **해금 전에 만들라고 요구하는 상태**였다.
(요구캐스트 지표에서는 「드롭 없음」으로 빠져 원가가 과소평가돼 정상으로 보였다.)

## 대체재를 왜 나뭇가지로 골랐나
Lv1 접근 재료는 부두(물고기비늘10·강화실6·낡은갈고리6·진주4·별빛진주1·나뭇가지5)와
강(…녹슨부품6)뿐이다. 이 중 **나뭇가지 5%** 가 깃털찌조각 6% 와 가장 가깝고,
쓰는 곳이 2건(초보 낚싯대·부둣가 통발)뿐이라 다른 곳의 병목을 건드리지 않는다.
찌·줄 계열 초반 부품에 나무 부속이라 테마도 맞는다.

## 수량
드롭률 비로 환산한다 — qty × (6% ÷ 5%) = ×1.2, 올림. 원가 중립이 목표지만
원래 «도달 불가»였으므로 측정 원가는 오히려 올라간다(그게 정상화다).
★비율을 상수로 적지 않는다. materials.json 을 읽어 계산한다.

사용:  python3 patch_feather_swap.py [--apply]
"""
import argparse
import json
import math
import pathlib

LIVE = pathlib.Path(
    "/Users/user/Library/Application Support/feather/player-server/servers/"
    "07de2d81-991a-47e2-b62d-06c0d1b5150a/plugins/BlockShip")
REPO = pathlib.Path(__file__).resolve().parent.parent
PLUGIN = pathlib.Path.home() / "development" / "blockship-plugin"
OLD, NEW = "깃털찌조각", "나뭇가지"
GRADES = {"E", "D"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()

    rec_p = LIVE / "recipes.json"
    root = json.loads(rec_p.read_text(encoding="utf-8"))
    recs = root["recipes"]
    parts = json.loads((LIVE / "parts.json").read_text(encoding="utf-8"))["parts"]
    drops = json.loads((LIVE / "materials.json").read_text(encoding="utf-8"))["dropTables"]

    grade = {}
    for grp in parts.values():
        for n, v in grp.items():
            f = v.split("|")
            if len(f) >= 6:
                grade[n] = (f[1], int(f[5]) if f[5].isdigit() else 99)

    def best(mid):
        return max([d["chance"] for ds in drops.values() for d in ds
                    if d["matId"] == mid] or [0])

    r_old, r_new = best(OLD), best(NEW)
    if not r_old or not r_new:
        print(f"⛔ 드롭률을 못 읽었다 ({OLD}={r_old}% {NEW}={r_new}%)")
        return 1
    ratio = r_old / r_new
    print(f"{OLD} {r_old}%  →  {NEW} {r_new}%   환산비 ×{ratio:.2f}")

    # 새 재료의 mcItem 등 필드는 기존 레시피에서 그대로 가져온다(추측 금지)
    proto = None
    for v in recs.values():
        for i in v.get("ingredients") or []:
            if (i.get("typeOrMatId") or "") == NEW:
                proto = dict(i)
    if proto is None:
        print(f"⛔ {NEW} 를 쓰는 기존 레시피가 없어 mcItem 을 알 수 없다")
        return 1

    changed = []
    for rid, v in recs.items():
        ings = v.get("ingredients") or []
        hit = next((i for i in ings if (i.get("typeOrMatId") or "") == OLD), None)
        if hit is None:
            continue
        nm = v.get("rodPartName") or v.get("resultPartName") or v.get("displayName")
        g, lv = grade.get(nm, ("?", 99))
        if g not in GRADES:
            continue
        want = max(1, math.ceil(hit.get("qty", 1) * ratio))
        cur = next((i for i in ings if (i.get("typeOrMatId") or "") == NEW), None)
        if cur is not None:                       # 이미 있으면 합친다
            cur["qty"] = cur.get("qty", 1) + want
            ings.remove(hit)
        else:
            idx = ings.index(hit)
            ings[idx] = dict(proto, qty=want)
        changed.append((g, lv, nm, hit.get("qty", 1), want, rid))

    changed.sort(key=lambda t: (t[0], t[1]))
    print(f"\nE·D {len(changed)}종에서 {OLD} 제거")
    for g, lv, nm, q0, q1, rid in changed:
        print(f"  {g} Lv{lv:<3}{nm:<16} {OLD}×{q0} → {NEW}×{q1}   ({rid})")
    left = sorted({(grade.get(v.get('rodPartName') or v.get('resultPartName')
                              or v.get('displayName'), ('?', 99))[0])
                   for v in recs.values()
                   if any((i.get("typeOrMatId") or "") == OLD
                          for i in v.get("ingredients") or [])})
    print(f"남은 {OLD} 사용 등급: {left}  (C 이상은 유지 — 기억의_연못 Lv7 이라 도달 가능)")
    if not changed:
        return 0
    if not a.apply:
        print("(--apply 를 붙이면 실제로 씀)")
        return 0
    blob = json.dumps(root, ensure_ascii=False, indent=2) + "\n"
    for t in (rec_p, REPO / "ops/blockship-data/recipes.json", PLUGIN / "recipes.json"):
        if t.parent.exists():
            t.write_text(blob, encoding="utf-8")
            print(f"  ✓ {t}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
