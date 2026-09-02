#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""patch_d_outliers.py — prod D급 이상치 3건을 «목표 포획수 지정»으로 손본다.

## 왜 이 방식인가
`patch_cast_cost` 는 요구캐스트 사다리 전체를 다시 푼다 — 한 종을 고치려고 돌리면
305종이 흔들리고, 2026-09-02 에 그렇게 네 번 갈아엎다 C급을 +20~50% 악화시켰다.
여기서는 **손댈 종만, 목표 포획수를 직접 적어** 고친다. LP 를 쓰지 않는다.

## 무엇을 (유저 판단 2026-09-02, prod 실측 기준 · D급 중위 127포획)
② 여울 작살 Lv7 — `강화철괴 40` 이 병목인데 그건 광질/제작 재료라 낚시 지표에
   안 잡힌다(낚시로는 40포획 = D급 최저). 같은 Lv7 이웃과 성격이 완전히 다르다.
   ⇒ 강화철괴를 이웃(장터 작살 1개) 수준으로 낮추고 낚시 재료로 이웃 수준에 맞춘다.
③ 낚싯대 Lv3~5 가 Lv7(175포획)보다 비싸다(210·250·230) — 레벨 역전.
   ⇒ **많이 싸게** + 단조증가. 그리고 «단단한 자루»(mcItem=stick, 강화실+물고기비늘)를
     초반 3종에서 **뺀다** — 재료가 여럿인 중간재라 초반에 부담이 크다(유저 지시).
④ 작살 Lv3 두 종(갯벌 280 · 벼린 270)이 Lv6 쇠날(120)의 2.3배다.
   ⇒ Lv4 물때(200) 아래로 내린다.

★수량은 목표 포획수 × 그 재료의 «그 레벨 실드롭»으로 계산한다 — 손으로 적지 않는다.
  드롭률이 바뀌면 이 스크립트를 다시 돌리면 된다.

사용:  python3 patch_d_outliers.py [--apply]
"""
import argparse
import importlib.util
import json
import pathlib

LIVE = pathlib.Path(
    "/Users/user/Library/Application Support/feather/player-server/servers/"
    "07de2d81-991a-47e2-b62d-06c0d1b5150a/plugins/BlockShip")
REPO = pathlib.Path(__file__).resolve().parent.parent
PLUGIN = pathlib.Path.home() / "development" / "blockship-plugin"
CPH = 190.1

#: {장비명: (목표 포획수, 뺄 재료들)}
TARGETS = {
    # ③ 초반 낚싯대 — «많이 싸게»(유저) + Lv3<Lv4<Lv5<Lv7(167) 단조. 단단한자루 제거.
    "튼튼한 막대기":      (70,  {"단단한자루"}),
    "수련생 낚싯대":      (90,  {"단단한자루"}),
    "낚시견습생의 낚싯대": (110, {"단단한자루"}),
    # ④ Lv3 작살 두 종 — Lv6 쇠날(120) 아래로
    "갯벌 작살":         (100, set()),
    "벼린 작살":         (110, set()),
    # ② 여울 작살 — Lv6(120)~Lv8(167) 사이로. 강화철괴는 HARD_SET 이 정한다.
    "여울 작살":         (155, set()),
}

#: 낚시 드롭이 아닌 재료는 목표 환산이 안 된다 — 값을 직접 지정한다.
#  강화철괴 40 은 D급 이웃(장터 작살 1개)과 두 자릿수 차이라 그 수준으로 맞춘다.
HARD_SET = {("여울 작살", "강화철괴"): 3}


def _region_unlock():
    f = REPO / ".claude/skills/balance-audit/scripts/region_unlock.py"
    spec = importlib.util.spec_from_file_location("region_unlock", f)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()

    RU = _region_unlock()
    rec_p = LIVE / "recipes.json"
    root = json.loads(rec_p.read_text(encoding="utf-8"))
    recs = root["recipes"]
    parts = json.loads((LIVE / "parts.json").read_text(encoding="utf-8"))["parts"]
    drops = json.loads((LIVE / "materials.json").read_text(encoding="utf-8"))["dropTables"]

    lvl = {}
    for grp in parts.values():
        for n, v in grp.items():
            f = v.split("|")
            if len(f) >= 6:
                lvl[n] = int(f[5]) if f[5].isdigit() else 99

    inter = {}
    for rid, r in recs.items():
        if not rid.startswith("C0"):
            continue
        out = None
        for ln in (r.get("result") or {}).get("lore") or []:
            if ln.startswith("&8mat:"):
                out = ln.split(":", 1)[1].strip()
        if out:
            inter[out] = {(i.get("typeOrMatId") or i.get("mcItem")): i.get("qty", 1)
                          for i in r.get("ingredients") or []}

    def rate(mid, lv):
        """그 레벨에서 접근 가능한 지역의 최고 드롭률. 중간재는 원재료 중 최악으로 환산."""
        if mid in inter:
            worst = 0.0
            for m2, q2 in inter[mid].items():
                c = rate(m2, lv)
                if c:
                    worst = max(worst, q2 / c)      # 중간재 1개당 포획수
            return (1.0 / worst) if worst else None
        best = 0.0
        for rg, ds in drops.items():
            if RU.unlock_level(rg) > lv:
                continue
            for d in ds:
                if d["matId"] == mid:
                    best = max(best, d["chance"] / 100)
        return best or None

    def cost(ings, lv):
        w = 0.0
        for i in ings:
            mid = i.get("typeOrMatId") or i.get("mcItem")
            c = rate(mid, lv)
            if c:
                w = max(w, i.get("qty", 1) / c)
        return w

    changed = []
    for rid, v in recs.items():
        nm = v.get("rodPartName") or v.get("resultPartName") or v.get("displayName")
        if nm not in TARGETS:
            continue
        target, drop_set = TARGETS[nm]
        lv = lvl.get(nm, 99)
        before_ings = [dict(i) for i in v["ingredients"]]
        before = cost(before_ings, lv)

        ings = [i for i in v["ingredients"]
                if (i.get("typeOrMatId") or i.get("mcItem")) not in drop_set]
        if len(ings) < 2:                     # 다 빠지면 손대지 않는다
            ings = [dict(i) for i in v["ingredients"]]
        for i in ings:
            mid = i.get("typeOrMatId") or i.get("mcItem")
            if (nm, mid) in HARD_SET:
                i["qty"] = HARD_SET[(nm, mid)]
                continue
            c = rate(mid, lv)
            if c is None:                     # 낚시 드롭이 아니고 지정도 없다 → 유지
                continue
            want = max(1, round(target * c))
            if mid in inter:
                # ★중간재는 «줄이기만» 한다. 늘리면 조합 횟수가 늘어 체감이 나빠진다 —
                #   2026-09-02 에 목표를 맞추려고 자루를 1→5 로 늘렸다가 되돌렸다.
                i["qty"] = min(i.get("qty", 1), want)
            else:
                i["qty"] = want
        v["ingredients"] = ings
        changed.append((lv, nm, before, cost(ings, lv), target, before_ings, ings))

    changed.sort()
    print(f"D급 이상치 {len(changed)}종 (참고: prod D급 중위 127포획 = 0.7h)")
    for lv, nm, b, af, tg, bi, ai in changed:
        print(f"\n  Lv{lv:<3}{nm}   {b:.0f}포획 {b/CPH:.1f}h → {af:.0f}포획 {af/CPH:.1f}h  (목표 {tg})")
        print("      전: " + "  ".join(
            f"{i.get('typeOrMatId') or i.get('mcItem')}×{i.get('qty', 1)}" for i in bi))
        print("      후: " + "  ".join(
            f"{i.get('typeOrMatId') or i.get('mcItem')}×{i['qty']}" for i in ai))
    if not changed:
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
