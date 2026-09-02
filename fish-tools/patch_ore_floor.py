#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""patch_ore_floor.py — 장비 레시피의 «압축 광물» 요구량에 등급별 하한을 세운다.

## 왜 (유저 지시 2026-09-02)
「B급들 압축 흑정석 요구가 너무 적어. 캐는 거 ㅈㄴ 금방 해서 최소 5개부터 요구 시작해도
될 것 같아.」 실측으로 B급 82종의 압축흑정석이 1~7개(중위 2)였고 **18종이 1개**였다.
압축흑정석 1개 = 흑정석 9개 — 드릴로 몇 초다. 사실상 「재료 칸 채우기」였다.

## 왜 이게 사다리를 안 흔드나
원가 지표(요구 포획수)는 낚시 드롭만 센다. 압축 광물은 채굴 재료라 지표에 안 잡히므로
이 하한을 올려도 등급·계열의 원가 순서가 전혀 바뀌지 않는다 — 순수 가산이다.
(그래서 반대로, 이 재료는 지표만 보고 있으면 아무리 적어도 「정상」으로 보인다.
 2026-09-02 에 유저가 손으로 잡아낸 종류의 구멍이다.)

## 하한을 등급 단조로 두는 이유
B 만 5 로 올리고 A(최소 2)·S(최소 1)를 두면 「등급 올라갔는데 요구량이 줄었다」가 된다 —
자루에서 이미 지적받은 그 실패다. 그래서 B 를 기준으로 위 등급도 같이 세운다.
★내리지는 않는다. 하한이므로 이미 그보다 많은 건 그대로 둔다.

## 미끼는 대상이 아니다
미끼 광물 수량은 patch_bait_ore.py 가 «채굴 시간 예산»(UPKEEP_SHARE)에서 역산한다.
여기서 손대면 그 예산이 깨지고 다음 생성 때 되돌아간다.

사용:  python3 patch_ore_floor.py [--apply]
"""
import argparse
import json
import pathlib

LIVE = pathlib.Path(
    "/Users/user/Library/Application Support/feather/player-server/servers/"
    "07de2d81-991a-47e2-b62d-06c0d1b5150a/plugins/BlockShip")
REPO = pathlib.Path(__file__).resolve().parent.parent
PLUGIN = pathlib.Path.home() / "development" / "blockship-plugin"

#: {광물: {등급: 최소 개수}} — 등급 단조. 유저 기준은 「B 최소 5」이고 위는 그에 맞춰 세웠다.
ORE_FLOOR = {
    "압축흑정석": {"B": 5, "A": 6, "S": 8},
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()

    rec_p = LIVE / "recipes.json"
    root = json.loads(rec_p.read_text(encoding="utf-8"))
    recs = root["recipes"]
    parts = json.loads((LIVE / "parts.json").read_text(encoding="utf-8"))["parts"]

    meta = {}
    for grp in parts.values():
        for n, v in grp.items():
            f = v.split("|")
            if len(f) >= 6:
                meta[n] = (f[1], int(f[5]) if f[5].isdigit() else 99)

    changed = []
    for rid, v in recs.items():
        if v.get("category") not in ("낚싯대", "작살", "부품"):
            continue
        if v.get("resultPartType") == "미끼":       # patch_bait_ore 소관
            continue
        nm = v.get("rodPartName") or v.get("resultPartName") or v.get("displayName")
        if nm not in meta:
            continue
        g, lv = meta[nm]
        for i in v.get("ingredients") or []:
            mid = i.get("typeOrMatId") or i.get("mcItem")
            floor = (ORE_FLOOR.get(mid) or {}).get(g)
            if floor is None:
                continue
            cur = i.get("qty", 1)
            if cur < floor:
                i["qty"] = floor
                changed.append((g, lv, v["category"], nm, mid, cur, floor))

    changed.sort(key=lambda t: ("EDCBASG".find(t[0]), t[1]))
    print(f"등급 하한 적용 {len(changed)}건")
    for g, lv, cat, nm, mid, a0, a1 in changed:
        print(f"  {g} Lv{lv:<3}{cat:<4}{nm:<20}{mid} {a0} → {a1}")
    by = {}
    for g, lv, cat, nm, mid, a0, a1 in changed:
        by[(g, mid)] = by.get((g, mid), 0) + (a1 - a0)
    print("\n등급별 순증(개):")
    for (g, mid), d in sorted(by.items()):
        print(f"  {g}  {mid}  +{d}")
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
