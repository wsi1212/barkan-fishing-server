#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""region_unlock.py — 「이 낚시 지역은 몇 레벨부터 갈 수 있나」의 단일 권위 (2026-09-01).

## 왜 필요한가
`material_value.py` 의 LP 는 재료 단가를 **전 지역 중 최적 출처**로 매긴다. 레벨 게이트가
없으므로 Lv7 아이템의 진주도 오아시스(10%) 가격으로 계산된다 — 그런데 오아시스는 메인 체인
`본섬12 「오아시스에 닿다」(필요레벨 16)` 를 깨야 닿는다. 실제 Lv7 플레이어는 부두(4%)뿐이다.

그래서 **초반 장비의 재료 원가가 체계적으로 2~3배 과소평가**됐고, 그 위에서 요구 수량을
정하는 `cast_cost` 가 「정상」이라고 판정했다. 실측으로는 D급 낚싯대 하나가 1.8~3.4h,
C급이 최대 5.8h 였다(2026-09-01 유저 제보 → BOM 완전전개로 확인).

## 왜 이 방식인가 (다른 후보가 전부 데이터로 안 서는 것을 확인함)
 · `regions.json` 의 `requiredLevel` — **원양(50) 말고 전부 0**. 게이트가 아니다.
 · `regions.json` 의 parent/island — 전 지역 None. 계층이 없다.
 · 퀘스트 `필요레벨` 전체 — 사이드 퀘가 거의 다 1 이라 순서를 못 만든다.
 ⇒ **메인 체인만** 본다. 메인은 선행퀘스트로 한 줄로 이어지고 필요레벨이 단조증가하므로,
   「그 지역을 처음 언급하는 메인 퀘스트의 필요레벨」이 곧 접근 가능 레벨이다.

★히든/사이드는 제외한다 — 그것들은 필요레벨이 1 이어도 실제로는 후반 콘텐츠라 포함하면
  전 지역이 Lv1 로 붕괴한다.

사용:  python3 region_unlock.py            # 표 출력
       from region_unlock import unlock_level, reachable
"""
import json
import pathlib

LIVE = pathlib.Path(
    "/Users/user/Library/Application Support/feather/player-server/servers/"
    "07de2d81-991a-47e2-b62d-06c0d1b5150a/plugins/BlockShip"
)

# 튜토 구간에서 바로 쓰는 지역 — 메인 체인 언급이 튜토라 필요레벨 1 로 나오는 게 맞다.
_TUTORIAL_REGIONS = ("부두", "강")


def _main_chain(quests: dict) -> list[str]:
    """선행/다음 퀘스트로 이어진 메인 체인을 순서대로. 튜토_선원 이 기점이다."""
    chain, cur, seen = [], "튜토_선원", set()
    while cur and cur in quests and cur not in seen:
        seen.add(cur)
        chain.append(cur)
        cur = quests[cur].get("다음퀘스트")
    return chain


def build(live: pathlib.Path = LIVE) -> dict[str, int]:
    quests = json.loads((live / "quests.json").read_text(encoding="utf-8"))["퀘스트"]
    regions = sorted(json.loads((live / "fish.json").read_text(encoding="utf-8"))["regions"])
    rg_json = json.loads((live / "regions.json").read_text(encoding="utf-8"))

    chain = _main_chain(quests)
    out: dict[str, int] = {}
    for qid in chain:                       # 체인 순서 = 진행 순서
        e = quests[qid]
        lv = e.get("필요레벨")
        if not isinstance(lv, int):
            continue
        blob = json.dumps(e, ensure_ascii=False)
        for rg in regions:
            if rg in out:
                continue
            if rg in blob or rg.replace("_", " ") in blob:
                out[rg] = lv
    for rg in _TUTORIAL_REGIONS:
        out[rg] = 1
    # regions.json 의 명시적 requiredLevel 이 더 크면 그걸 존중한다(원양 50).
    for rg in regions:
        req = (rg_json.get(rg) or {}).get("requiredLevel") or 0
        if req > out.get(rg, 0):
            out[rg] = req
    # 메인 체인이 한 번도 언급하지 않는 지역(레드_로드 등) — 「체인 최대」로 두면 그 지역
    # «전용» 재료를 쓰는 정상 아이템이 전부 도달불가로 잡힌다(2026-09-01 실측: 바르칸조각
    # 44건 오탐). 대신 **그 재료를 요구하는 최저 레벨 아이템**에서 역산한다 —
    # 「누군가 Lv68 에 그걸 요구한다 ⇒ 늦어도 Lv68 엔 갈 수 있다」가 데이터로 성립한다.
    missing = [rg for rg in regions if rg not in out]
    if missing:
        recs = json.loads((live / "recipes.json").read_text(encoding="utf-8"))["recipes"]
        parts = json.loads((live / "parts.json").read_text(encoding="utf-8"))["parts"]
        drops = json.loads((live / "materials.json").read_text(encoding="utf-8"))["dropTables"]
        lvl = {}
        for grp in parts.values():
            for n, v in grp.items():
                f = v.split("|")
                if len(f) >= 6 and f[5].isdigit():
                    lvl[n] = int(f[5])
        for rg in missing:
            # 이 지역에서만 나오는 재료
            here = {d["matId"] for d in drops.get(rg, [])}
            elsewhere = {d["matId"] for r2, ds in drops.items() if r2 != rg for d in ds}
            only = here - elsewhere
            best = None
            for r2 in recs.values():
                ids = {(i.get("typeOrMatId") or "") for i in r2.get("ingredients") or []}
                if not (ids & only):
                    continue
                nm = r2.get("rodPartName") or r2.get("resultPartName") or r2.get("displayName")
                lv = lvl.get(nm)
                if lv and (best is None or lv < best):
                    best = lv
            out[rg] = best or max([quests[q].get("필요레벨") or 0 for q in chain] + [1])
    return out


_CACHE: dict[str, int] | None = None


def unlock_level(region: str) -> int:
    global _CACHE
    if _CACHE is None:
        _CACHE = build()
    return _CACHE.get(region, 1)


def reachable(region: str, level: int) -> bool:
    """그 레벨의 플레이어가 이 지역에서 낚시할 수 있나."""
    return unlock_level(region) <= level


if __name__ == "__main__":
    tbl = build()
    print("낚시 지역 접근 레벨 — 메인 체인에서 도출 (사이드·히든 제외)")
    for rg, lv in sorted(tbl.items(), key=lambda t: (t[1], t[0])):
        print(f"  Lv{lv:<4}{rg}")
