#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""patch_early_recipes.py — 초반(Lv≤5) 장비 레시피를 «중간재 없이 원재료 소량»으로.

## 왜 (2026-09-02 유저 결정)
「Lv5 까지는 완전 초반이라 낮아도 된다. 중간재 하나로 하라는 게 아니라 **그냥 빼라**.
 낡은갈고리 5개. 단단한자루도 빼고 그 재료에서 5개 정도 소량만.」

그 전에 무슨 일이 있었나 — 요구캐스트 사다리(κ×상대성능)가 초반 장비까지 덮고 있어서:
 · 중간재 단가를 내리면 → 생성기가 개수를 늘렸다(정제된갈고리 2→5, 참나무 9→17)
 · 개수에 캡을 걸면 → 원재료로 새어나갔다(수집가 진주 43, 다목적 강화석탄 45)
 · 중간재를 1개로 묶으면 → UNWRAP 이 발동해 낡은갈고리 14개를 직접 요구했다
누르는 곳만 옮겨갔다. 원인은 «초반 구간에 캐스트 등가를 강요한 것» 자체다.

⇒ 초반은 사다리 밖으로 뺀다(cast_cost.EARLY_EXEMPT_LEVEL) + 이 스크립트가 수량을 정한다.
  기준은 캐스트 등가가 아니라 **체감**이다: 중간재 0개, 원재료 종당 MAX_QTY 개 이하.

★중간재는 «그 레시피의 원재료»로 풀어서 합산한다(recipes.json C0* 가 권위). 그래서
  중간재 레시피를 고치면 이 스크립트 결과도 따라온다 — 비율을 여기 적지 않는다.

사용:  python3 patch_early_recipes.py [--level 5] [--max 5] [--apply]
"""
import argparse
import json
import pathlib

LIVE = pathlib.Path(
    "/Users/user/Library/Application Support/feather/player-server/servers/"
    "07de2d81-991a-47e2-b62d-06c0d1b5150a/plugins/BlockShip")
REPO = pathlib.Path(__file__).resolve().parent.parent
PLUGIN = pathlib.Path.home() / "development" / "blockship-plugin"

#: 미끼는 광질 전용 소모품이라 재료 구성이 다르다(2026-08-27 결정) — 건드리지 않는다.
#  ★미끼의 category 는 "부품" 이고 «resultPartType» 이 "미끼" 다(실측 P84·P132·P142).
#    category 만 보면 필터를 통과해 압축흑정석 11→5 로 깎였다(2026-09-02 실측).
SKIP_PART_TYPES = {"미끼"}

#: 재료 해금 레벨이 «아이템 레벨 + 이 값» 을 넘으면 초반 레시피에서 뺀다.
#  ★유저 결정 A(2026-09-02): 초반 구간은 «체감»이 기준인데, Lv4 수련생 낚싯대가
#    깃털찌조각(기억의_연못 Lv48)을, Lv4 수습 줄이 보석(오아시스 Lv12)을 요구했다 —
#    그 원칙과 정면으로 어긋난다. 거대비늘(협곡 Lv4)은 경계선이라 남긴다(작살은 원래
#    대물용이라 테마도 맞다). 판정은 region_unlock.py 가 메인 체인에서 도출한 값이다.
REACH_MARGIN = 0

#: 종당 개수의 기준 레벨 — 이 레벨에서 --max 개, 레벨이 1 오를 때마다 +1.
#  ★완전 고정(전부 5개)으로 하면 «갯벌 작살(Lv3) == 물때 작살(Lv4)» 처럼 레시피가
#    글자 하나까지 같아진다. 2026-09-02 에 C급을 전부 2개로 통일해 유저가 지적한
#    그 평탄화와 같은 실패다 — 초반이라도 레벨 서열은 남겨야 한다.
ANCHOR = 3

#: 부품 종류별 «대표 재료» — 이 재료만 SIG_BONUS 개 더 넣는다.
#  ★없으면 새로 추가한다. 종당 개수를 평탄하게 맞추면 같은 레벨의 릴·줄·바늘·찌가
#    글자 하나까지 같은 레시피가 된다(2026-09-02 실측: Lv4 4종이 동일). 종류마다
#    무엇으로 만드는 물건인지가 드러나야 해서 테마에 맞는 재료를 하나씩 세웠다.
SIGNATURE = {
    "릴": "녹슨부품",        # 금속 기어
    "줄": "강화실",          # 실
    "바늘": "낡은갈고리",     # 갈고리
    "찌": "나뭇가지",        # 물에 뜨는 나무
}
#: 장비 본체(낚싯대·작살)는 부품 타입이 없다 — 물고기비늘로 가른다.
SIGNATURE_GEAR = "물고기비늘"

#: 대표 재료를 얼마나 더 넣나 — «개수»가 아니라 «포획수» 배율이다.
#  ★개수로 +3 을 주면 드롭률이 낮은 재료가 그대로 병목이 된다(실측: 나뭇가지 5% 라
#    찌 계열만 200포획, 같은 레벨 바늘 150 · 낚싯대 120). 재료마다 희귀도가 다르니
#    「기준 개수의 포획수 × 이 배율」을 그 재료의 드롭률로 되환산해서 개수를 정한다.
SIG_CAPTURE_MULT = 1.25
#: 배율 환산의 기준 드롭률 — 6% 재료(강화실·낡은갈고리·녹슨부품)가 초반 표준이다.
BASE_RATE = 0.06


def _unlock_table():
    import importlib.util as _u, pathlib as _p
    f = (_p.Path(__file__).resolve().parent.parent
         / ".claude/skills/balance-audit/scripts/region_unlock.py")
    spec = _u.spec_from_file_location("region_unlock", f)
    m = _u.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--level", type=int, default=5, help="이 레벨 이하를 대상으로")
    ap.add_argument("--max", type=int, default=5,
                    help=f"원재료 종당 개수 (Lv{ANCHOR} 기준, 레벨마다 ±1)")
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()

    rec_p = LIVE / "recipes.json"
    root = json.loads(rec_p.read_text(encoding="utf-8"))
    recs = root["recipes"]
    parts = json.loads((LIVE / "parts.json").read_text(encoding="utf-8"))["parts"]

    lvl, grade = {}, {}
    for grp in parts.values():
        for n, v in grp.items():
            f = v.split("|")
            if len(f) >= 6:
                grade[n] = f[1]
                lvl[n] = int(f[5]) if f[5].isdigit() else 99

    # 중간재 → 원재료 (recipes.json C0* 권위)
    inter = {}
    for rid, r in recs.items():
        if not rid.startswith("C0"):
            continue
        out = None
        for ln in (r.get("result") or {}).get("lore") or []:
            if ln.startswith("&8mat:"):
                out = ln.split(":", 1)[1].strip()
        if out:
            inter[out] = [(i.get("typeOrMatId") or i.get("mcItem"), i.get("qty", 1))
                          for i in r.get("ingredients") or []]

    def unwrap(ings):
        """중간재를 원재료로 풀어 «종별 1회»로 합친다(수량은 뒤에서 다시 정한다)."""
        seen, order = {}, []
        for i in ings:
            mid = i.get("typeOrMatId") or i.get("mcItem")
            if mid in inter:
                for m2, _q2 in inter[mid]:
                    if m2 not in seen:
                        seen[m2] = dict(i, typeOrMatId=m2, mcItem=_mc(recs, m2, i), qty=1)
                        order.append(m2)
            elif mid not in seen:
                seen[mid] = dict(i)
                order.append(mid)
        return [seen[m] for m in order]

    RU = _unlock_table()
    drops = json.loads((LIVE / "materials.json").read_text(encoding="utf-8"))["dropTables"]
    best_rate = {}
    for _rg, _ds in drops.items():
        for _d in _ds:
            _m, _c = _d["matId"], _d["chance"] / 100
            if _c > best_rate.get(_m, 0):
                best_rate[_m] = _c
    mat_open = {}
    for rg, ds in drops.items():
        lu = RU.unlock_level(rg)
        for d in ds:
            m = d["matId"]
            if m not in mat_open or lu < mat_open[m]:
                mat_open[m] = lu

    changed = []
    for rid, v in recs.items():
        cat = v.get("category")
        if cat not in ("낚싯대", "작살", "부품"):
            continue
        if v.get("resultPartType") in SKIP_PART_TYPES:
            continue
        nm = v.get("rodPartName") or v.get("resultPartName") or v.get("displayName")
        lv, g = lvl.get(nm, 99), grade.get(nm, "?")
        if lv > a.level or g == "E":
            continue
        before = [(i.get("typeOrMatId") or i.get("mcItem"), i.get("qty", 1))
                  for i in v["ingredients"]]
        new = unwrap(v["ingredients"])
        # 그 레벨에서 사실상 못 가는 재료는 뺀다(2종 이상 남을 때만).
        keep = [i for i in new
                if mat_open.get(i.get("typeOrMatId"), 0) <= lv + REACH_MARGIN]
        if len(keep) >= 2:
            new = keep
        want = max(1, a.max + (lv - ANCHOR))
        for i in new:
            i["qty"] = want           # 종당 «소량» — 절대량이 아니라 레벨 서열만 남긴다
        sig = SIGNATURE.get(v.get("resultPartType") or "", SIGNATURE_GEAR)
        cur = next((i for i in new if (i.get("typeOrMatId") or i.get("mcItem")) == sig), None)
        if cur is None and mat_open.get(sig, 99) <= lv:
            cur = {"type": "custom", "typeOrMatId": sig, "mcItem": _mc(recs, sig, new[0]),
                   "displayName": sig, "qty": want}
            new.append(cur)
        if cur is not None:
            rate = best_rate.get(sig, BASE_RATE)
            target = want / BASE_RATE * SIG_CAPTURE_MULT      # 목표 포획수
            cur["qty"] = max(want + 1, round(target * rate))
        after = [(i.get("typeOrMatId") or i.get("mcItem"), i["qty"]) for i in new]
        if before != after:
            v["ingredients"] = new
            changed.append((lv, g, cat, nm, before, after))

    changed.sort()
    print(f"초반(Lv≤{a.level}) 장비 {len(changed)}종 — 중간재 제거 + "
          f"원재료 종당 {a.max}개(Lv{ANCHOR} 기준, 레벨마다 +1)")
    for lv, g, cat, nm, b, af in changed:
        print(f"  {g} Lv{lv:<3}{nm:<18} {b}")
        print(f"  {'':<7}{'':<18} → {af}")
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


def _mc(recs, matid, like):
    """그 원재료의 mcItem — 다른 레시피에서 쓰던 값을 그대로 재사용(추측 금지)."""
    for r in recs.values():
        for i in r.get("ingredients") or []:
            if i.get("typeOrMatId") == matid and i.get("mcItem"):
                return i["mcItem"]
    return like.get("mcItem") or "paper"


if __name__ == "__main__":
    raise SystemExit(main())
