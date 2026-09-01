#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""patch_intermediate_cost.py — 중간재(C01·C02) 1개의 원가를 «목표 시간»에 맞춘다.

## 왜 (2026-09-01 유저 제보 → BOM 완전전개로 확인)
「수련생 낚싯대가 정제된 갈고리 5개를 요구하는데 그게 낡은갈고리 20개다」.
실제로 재 보니 **중간재가 초반 낚싯대 원가의 65~91%** 였다:

    단단한 자루 1개 = 강화실 10 + 물고기비늘 12  →  167 포획 (0.88h)   ← 자루 하나에 1시간
    정제된 갈고리 1개 = 낡은갈고리 4            →   67 포획 (0.35h)

수련생 낚싯대(D Lv4)는 4.3h 중 3.5h 가 중간재였고 직접 재료는 0.8h 뿐이었다.
중간재는 «부재료»여야 하는데 사실상 그게 장비 원가 전부였다.

★어떤 감사도 이걸 못 잡았다 — `cast_cost` 의 LP 가 재료 단가를 «전 지역 최적 출처»로
  매겨서(Lv7 아이템의 진주를 Lv12 해금인 오아시스 가격으로 계산) 초반 원가를 2~3배 과소
  평가했고, 그래서 「배율 1.00 정상」으로 나왔다. LP 레벨 게이트는 별도로 고쳤다
  (material_value.reachable_acts + region_unlock.py).

## 목표
중간재 1개 = TARGET_H 시간. 초반에 접근 가능한 지역(부두·강)의 실드롭으로 계산한다 —
중간재는 전부 초반부터 쓰이므로 그게 옳은 기준이다.

★수량은 이 스크립트가 «계산»한다. 손으로 적지 말 것.

사용:  python3 patch_intermediate_cost.py [--target 0.15] [--apply]
"""
import argparse
import json
import pathlib

LIVE = pathlib.Path(
    "/Users/user/Library/Application Support/feather/player-server/servers/"
    "07de2d81-991a-47e2-b62d-06c0d1b5150a/plugins/BlockShip")
REPO = pathlib.Path(__file__).resolve().parent.parent
PLUGIN = pathlib.Path.home() / "development" / "blockship-plugin"

#: 조정 대상 — 초반(D~C)부터 쓰이는 중간재만. 상위 중간재(행운의매듭·진주코어 등)는
#  그 등급 구간의 재료로 만들어지므로 여기서 건드리지 않는다.
TARGETS = ("C01", "C02")
#: 초반 플레이어가 실제로 갈 수 있는 지역 (region_unlock.py 기준 Lv1)
EARLY = ("부두", "강")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", type=float, default=0.15,
                    help="중간재 1개당 목표 채집시간(h). 기본 0.15h ≈ 9분")
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()

    rec_p = LIVE / "recipes.json"
    root = json.loads(rec_p.read_text(encoding="utf-8"))
    mats = json.loads((LIVE / "materials.json").read_text(encoding="utf-8"))["dropTables"]
    cph = json.loads((LIVE / "fish.json").read_text(encoding="utf-8")) and 190.1  # 실측 포획/h

    def early_rate(mid):
        c = [d["chance"] / 100 for reg in EARLY for d in mats.get(reg, []) if d["matId"] == mid]
        return max(c) if c else None

    changed = 0
    for rid in TARGETS:
        rec = root["recipes"].get(rid)
        if not rec:
            print(f"  ⚠ {rid} 없음 — 스킵")
            continue
        ings = rec["ingredients"]
        before = {(i.get("typeOrMatId") or i.get("mcItem")): i["qty"] for i in ings}
        # 각 재료를 «단독으로 목표시간을 채우는 수량»으로 잡는다. 병목이 목표에 정확히
        # 닿고 나머지는 그 이하가 된다 → 1개 원가 = 목표시간.
        for i in ings:
            mid = i.get("typeOrMatId") or i.get("mcItem")
            c = early_rate(mid)
            if c is None:
                print(f"  ⚠ {rid}: {mid} 는 초반 지역에서 안 나온다 — 수량 유지")
                continue
            i["qty"] = max(1, round(a.target * cph * c))
        after = {(i.get("typeOrMatId") or i.get("mcItem")): i["qty"] for i in ings}
        worst = max((q / early_rate(m) for m, q in after.items() if early_rate(m)), default=0)
        worst_b = max((q / early_rate(m) for m, q in before.items() if early_rate(m)), default=0)
        nm = rec.get("displayName")
        print(f"  {rid} {nm}")
        print(f"      전: {before}  → {worst_b:>5.0f}포획 {worst_b/cph:.2f}h")
        print(f"      후: {after}  → {worst:>5.0f}포획 {worst/cph:.2f}h")
        if before != after:
            changed += 1

    if not changed:
        print("\n변경 없음")
        return 0
    if not a.apply:
        print("\n(--apply 를 붙이면 실제로 씀)")
        return 0

    blob = json.dumps(root, ensure_ascii=False, indent=2) + "\n"
    for t in (rec_p, REPO / "ops/blockship-data/recipes.json", PLUGIN / "recipes.json"):
        if t.parent.exists():
            t.write_text(blob, encoding="utf-8")
            print(f"  ✓ {t}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
