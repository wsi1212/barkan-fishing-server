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

## ★2026-09-02 정정 — 스토리 체인은 «게이트»가 아니었다
메인 체인의 지역 언급으로 판정했더니 두 방향으로 크게 틀렸다:
 · `기억의_연못` → Lv48 로 판정. 그런데 통발가 7,000원(13지역 중 3번째로 쌈),
   어종이 E4·D4·C1·B2 로 **초반 어장**이다. 왕도13 이 그 이름을 언급한 건 스토리
   회수일 뿐 접근 조건이 아니었다.
 · `폭포_뒤_동굴_1층` → Lv4 로 판정. 통발가 24,000원(2번째로 비쌈), 어종 B10·A10·S2 로
   **완전한 후반 지역**이다. 본섬03 이 초반에 이름을 언급했을 뿐이다.
⇒ 지역 접근에 레벨 게이트가 없다는 것(regions.json requiredLevel 이 원양만 50)이
  이미 확인됐으므로, 실제로 «가느냐»는 이동이 아니라 **콘텐츠 티어**가 정한다.
  그 티어를 명시적으로 인코딩한 설계 데이터가 **통발 가격**(TrapSpecs)이다 —
  부두2k → 강5k → 오아시스6k → 기억의연못7k → … → 원양45k 로 단조롭다.
  ⇒ 통발가를 레벨로 선형 환산하고, regions.json 의 requiredLevel 을 하한으로 존중한다.

## 왜 스토리 체인을 안 쓰는가 (다른 후보도 전부 확인함)
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


def _trap_prices() -> dict[str, int]:
    """지역 → 통발 가격. TrapSpecs.java 가 단일 권위다(사본 금지)."""
    import re
    src = (pathlib.Path.home() / "development/blockship-plugin/src/main/java/com/blockship"
           / "trap/TrapSpecs.java")
    try:
        text = src.read_text(encoding="utf-8")
    except OSError:
        return {}
    return {m.group(1): int(m.group(2))
            for m in re.finditer(r'new Spec\("([^"]+)",[^)]*?"TR\d+", (\d+)', text, re.S)}


def build(live: pathlib.Path = LIVE) -> dict[str, int]:
    quests = json.loads((live / "quests.json").read_text(encoding="utf-8"))["퀘스트"]
    regions = sorted(json.loads((live / "fish.json").read_text(encoding="utf-8"))["regions"])
    rg_json = json.loads((live / "regions.json").read_text(encoding="utf-8"))

    out: dict[str, int] = {}
    # ── 통발 가격 = 지역 콘텐츠 티어 (TrapSpecs 가 권위) ──
    prices = _trap_prices()
    if prices:
        lo_p = min(prices.values())
        hi_p = max(prices.values())
        # 앵커: 가장 싼 지역 = Lv1, 가장 비싼 지역 = regions.json 이 명시한 최고 하한(원양 50)
        hi_lv = max([(rg_json.get(r) or {}).get("requiredLevel") or 0 for r in regions] + [50])
        for rg in regions:
            pr = prices.get(rg)
            if pr is None:
                continue
            span = max(1, hi_p - lo_p)
            out[rg] = max(1, round(1 + (pr - lo_p) / span * (hi_lv - 1)))
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
    print("낚시 지역 접근 레벨 — 통발 가격(TrapSpecs) 티어에서 환산")
    for rg, lv in sorted(tbl.items(), key=lambda t: (t[1], t[0])):
        print(f"  Lv{lv:<4}{rg}")
