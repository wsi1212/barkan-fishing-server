#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""patch_ore_ladder.py — 장비의 «압축 광물» 요구량을 등급 구간 사다리로 다시 깐다.

## 유저 지시 (2026-09-02)
「B 이상에서만 요구해야 함. 최소 5개 많으면 15개까지도 B에서.
 A는 최소 20개 많으면 60개. S는 50개~150개.
 추가로 B 상위권부터는 압축적철석, A 중상위부터는 자수정도 요구해야 함.」
앞선 지시(같은 날) 「캐는 거 ㅈㄴ 금방 해서 최소 5개부터」의 연장이다 — 채굴이 너무
싸서 광물이 재료 칸 채우기였다. 하한(patch_ore_floor)만으로는 상한이 그대로라
B 5~7 · A 6~30 처럼 폭이 좁았다.

## 구간 안에서 무엇이 개수를 정하나
레벨이 주(0.7)이고, 같은 레벨끼리 갈리도록 그 등급 안 «가격 순위»를 보조(0.3)로 섞는다.
순수 레벨만 쓰면 같은 레벨 장비가 전부 같은 수가 된다(2026-09-02 초반 레시피 평탄화).
★보조 지표로 «현재 요구량»을 쓰면 안 된다 — 한 번 돌리면 순위가 바뀌어 다시 돌릴 때마다
  값이 움직인다(실측: 재실행에서 159종이 또 변경됐다). 이 스크립트는 몇 번 돌려도 같은
  결과여야 한다. 그래서 이 작업이 건드리지 않는 값(parts.json 가격)을 기준으로 삼는다.

## 적철석·자수정 개수는 흑정석에 비례
유저가 개수를 지정한 건 흑정석뿐이다. 나머지 둘은 «그 장비의 흑정석 × 비중»으로 매긴다 —
현행 비율(A: 철광석/흑정석 ≈ 1/5, S: 자수정/흑정석 ≈ 1/9)을 참고해 세웠고, 흑정석
사다리를 고치면 따라 움직인다. 상수 두 벌을 만들지 않기 위한 선택이다.

## 등장 시점
등급 안 «레벨 위치»(0=그 등급 최저렙, 1=최고렙)로 문턱을 준다.
  압축철광석 — B 는 0.60 부터(상위권), A·S 는 전체
  압축자수정 — A 는 0.45 부터(중상위),  S 는 전체
★C 이하에는 넣지 않는다(「B 이상에서만」). 미끼도 대상이 아니다 — 미끼 광물은
  patch_bait_ore.py 가 채굴 시간 예산에서 역산한다.

사용:  python3 patch_ore_ladder.py [--apply]
"""
import argparse
import json
import pathlib

LIVE = pathlib.Path(
    "/Users/user/Library/Application Support/feather/player-server/servers/"
    "07de2d81-991a-47e2-b62d-06c0d1b5150a/plugins/BlockShip")
REPO = pathlib.Path(__file__).resolve().parent.parent
PLUGIN = pathlib.Path.home() / "development" / "blockship-plugin"

BG, IRON, AME = "압축흑정석", "압축철광석", "압축자수정"
#: 등급 → (최소, 최대) 흑정석 개수. 유저 지정값.
BG_RANGE = {"B": (5, 15), "A": (20, 60), "S": (50, 150)}
#: 등급 → 그 등급 레벨 구간 안에서 이 재료가 등장하기 시작하는 위치(0=최저렙, 1=최고렙)
IRON_FROM = {"B": 0.60, "A": 0.0, "S": 0.0}
AME_FROM = {"A": 0.45, "S": 0.0}
#: 흑정석 대비 비중
IRON_SHARE, AME_SHARE = 0.30, 0.15
#: 구간 안 개수 결정 가중 — 레벨 : 등급 내 가격순위
W_LEVEL, W_CUR = 0.7, 0.3


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
                price = int(f[2]) if f[2].lstrip("-").isdigit() else 0
                meta[n] = (f[1], int(f[5]) if f[5].isdigit() else 99, price)

    # 대상 수집 — 압축흑정석을 쓰는 B·A·S 장비(미끼 제외)
    items = []
    for rid, v in recs.items():
        if v.get("category") not in ("낚싯대", "작살", "부품"):
            continue
        if v.get("resultPartType") == "미끼":
            continue
        nm = v.get("rodPartName") or v.get("resultPartName") or v.get("displayName")
        if nm not in meta:
            continue
        g, lv, price = meta[nm]
        if g not in BG_RANGE:
            continue
        q = {(i.get("typeOrMatId") or i.get("mcItem")): i.get("qty", 1)
             for i in v["ingredients"]}
        if BG not in q:
            continue
        items.append({"rid": rid, "v": v, "nm": nm, "g": g, "lv": lv, "price": price,
                      "cat": v["category"], "q0": dict(q)})

    changed = []
    for g, (lo, hi) in BG_RANGE.items():
        grp = [d for d in items if d["g"] == g]
        if not grp:
            continue
        lvs = [d["lv"] for d in grp]
        lmin, lmax = min(lvs), max(lvs)
        span = max(1, lmax - lmin)
        order = sorted(grp, key=lambda d: (d["price"], d["nm"]))
        rank = {id(d): (i / max(1, len(order) - 1)) for i, d in enumerate(order)}
        for d in grp:
            t_lv = (d["lv"] - lmin) / span
            t = W_LEVEL * t_lv + W_CUR * rank[id(d)]
            q = dict(d["q0"])
            q[BG] = max(lo, min(hi, round(lo + (hi - lo) * t)))
            for mid, table, share in ((IRON, IRON_FROM, IRON_SHARE),
                                      (AME, AME_FROM, AME_SHARE)):
                start = table.get(g)
                if start is None:
                    if mid in q:
                        del q[mid]          # 그 등급엔 안 쓰는 재료
                    continue
                if t_lv + 1e-9 < start:
                    if mid in q:
                        del q[mid]
                    continue
                q[mid] = max(1, round(q[BG] * share))
            d["q1"] = q
            if q != d["q0"]:
                changed.append(d)

    print(f"═══ 장비 압축광물 사다리 — {len(changed)}/{len(items)}종 변경 ═══")
    for g in "BAS":
        grp = sorted([d for d in items if d["g"] == g], key=lambda d: d["lv"])
        if not grp:
            continue
        f = lambda d, m, k: d[k].get(m, 0)
        print(f"\n  ── {g}급 {len(grp)}종  (Lv{grp[0]['lv']}~{grp[-1]['lv']}) ──")
        print(f"     흑정석 {min(f(d,BG,'q0') for d in grp)}~{max(f(d,BG,'q0') for d in grp)}"
              f" → {min(f(d,BG,'q1') for d in grp)}~{max(f(d,BG,'q1') for d in grp)}")
        n_i = sum(1 for d in grp if IRON in d["q1"])
        n_a = sum(1 for d in grp if AME in d["q1"])
        print(f"     압축철광석 {sum(1 for d in grp if IRON in d['q0'])}종 → {n_i}종"
              f"   압축자수정 {sum(1 for d in grp if AME in d['q0'])}종 → {n_a}종")
        step = max(1, len(grp) // 8)
        for d in grp[::step]:
            s0 = "  ".join(f"{m}{d['q0'].get(m,0)}" for m in (BG, IRON, AME) if m in d["q0"])
            s1 = "  ".join(f"{m}{d['q1'].get(m,0)}" for m in (BG, IRON, AME) if m in d["q1"])
            print(f"       Lv{d['lv']:<3}{d['nm']:<18}{s0:<40} → {s1}")
    if not changed:
        return 0
    if not a.apply:
        print("\n(--apply 를 붙이면 실제로 씀)")
        return 0
    mats = json.loads((LIVE / "materials.json").read_text(encoding="utf-8"))["materials"]
    for d in changed:
        base = {(i.get("typeOrMatId") or i.get("mcItem")): i for i in d["v"]["ingredients"]}
        out = []
        for m, n in d["q1"].items():
            src = base.get(m)
            if src is None:
                mm = mats.get(m) or {}
                src = {"type": "custom", "typeOrMatId": m,
                       "displayName": mm.get("name", m), "mcItem": mm.get("mcItem", "paper")}
            out.append(dict(src, qty=n))
        d["v"]["ingredients"] = out
    blob = json.dumps(root, ensure_ascii=False, indent=2) + "\n"
    for t in (rec_p, REPO / "ops/blockship-data/recipes.json", PLUGIN / "recipes.json"):
        if t.parent.exists():
            t.write_text(blob, encoding="utf-8")
            print(f"  ✓ {t}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
