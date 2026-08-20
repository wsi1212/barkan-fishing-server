#!/usr/bin/env python3
"""플레이어 코호트·로드아웃·낚싯대/작살 비교 시뮬레이터.

이 파일의 목적은 ``같은 등급 장비끼리 비교``를 없애는 것이다. 입력 레벨에서
실제로 쓸 수 있는 부품만 고르고, 같은 레벨의 최적 공통 부품을 붙인 뒤, 낚싯대와
작살을 각각 그 도구의 처리량/실패/품질/전용 스탯까지 포함해 비교한다.

정확한 라이브 PRD를 Python에서 재현하기 위해 기준 캐스트 분포는 Java
GradeRoller의 현재 상수로 Monte Carlo를 한 번만 산출하고 캐시한다. 장비별
비교에서는 행운과 등급업의 질량이동을 적용한다. 작살은 Java의 스폰 5초,
캐치 쿨다운 7초, 물고기 HP/공격력 공식을 반영한 처리량 근사이며, 실제 적중률은
텔레메트리로 보정할 수 있는 명시적 입력이다.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import random
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from catalog import GRADE_ORDER, ROD_CATEGORIES, build_catalog, eligible_parts, stat_sum
from minigame_sim import ms_to_ticks, simulate_catch


DEFAULT_REACTION_MS = 250
DEFAULT_PING_MS = 50
DEFAULT_ROD_ACTIONS = 150
DEFAULT_HARPOON_HIT_RATE = 0.75
HARPOON_SPAWN_SEC = 5.0
HARPOON_CATCH_COOLDOWN_SEC = 7.0
HARPOON_BASE_JAB_TICKS = 5
FISH_HP = {"E": 1, "D": 2, "C": 3, "B": 5, "A": 8, "S": 12, "M": 18, "L": 25, "G": 35}
ROD_XP = {"E": 2, "D": 3, "C": 4, "B": 6, "A": 12, "S": 30, "M": 200, "L": 800, "G": 3000}
HARPOON_XP = {"E": 3, "D": 5, "C": 10, "B": 20, "A": 40, "S": 80, "M": 160, "L": 320, "G": 640}


def latest_snapshot(skill_dir: Path = HERE.parent) -> Path | None:
    snap_dir = skill_dir / "audits" / "snapshots"
    paths = sorted(p for p in snap_dir.glob("*.raw.json") if "pending" not in p.name)
    return paths[-1] if paths else None


def load_snapshot(path: str | Path | None) -> dict[str, Any]:
    if path is None:
        path = latest_snapshot()
    if path is None:
        return {"raw": {}}
    with Path(path).open(encoding="utf-8") as f:
        return json.load(f)


def load_catalog(snapshot: dict[str, Any]) -> dict[str, Any]:
    embedded = snapshot.get("raw", {}).get("equipment", {}).get("catalog")
    if embedded and embedded.get("parts"):
        return embedded
    return build_catalog()


def grade_gate(snapshot: dict[str, Any], level: int) -> int:
    entries = snapshot.get("raw", {}).get("leveling", {}).get("max_grade_unlock", [])
    gate = 6
    for entry in entries:
        if level >= int(entry.get("level", 0)):
            gate = max(gate, int(entry.get("grade_num", gate)))
    return gate


def _base_prob(snapshot: dict[str, Any]) -> dict[str, float]:
    return snapshot.get("raw", {}).get("rng", {}).get("grade_base_prob", {}) or {}


@lru_cache(maxsize=32)
def _prd_distribution_cached(base_json: str, gate: int, trials: int, seed: int) -> dict[str, float]:
    """Java GradeRoller의 희귀→흔함 순서와 피티 증가를 그대로 근사한다."""
    base = json.loads(base_json)
    order = ["G", "L", "M", "S", "A", "B", "C", "D"]
    available = set(GRADE_ORDER[:gate])
    pity = {grade: 0 for grade in order}
    counts = {grade: 0 for grade in GRADE_ORDER}
    rng = random.Random(seed)
    for _ in range(max(1, trials)):
        grade = "E"
        for candidate in order:
            if grade != "E" or candidate not in available:
                continue
            probability = float(base.get(candidate, 0.0)) * (1 + pity[candidate])
            if rng.random() < probability / 100.0:
                grade = candidate
                pity[candidate] = 0
        for candidate in order:
            if candidate != grade:
                pity[candidate] += 1
        counts[grade] += 1
    total = float(max(1, trials))
    return {grade: counts[grade] / total for grade in GRADE_ORDER}


def base_grade_distribution(snapshot: dict[str, Any], level: int, trials: int = 120_000) -> dict[str, float]:
    base = _base_prob(snapshot)
    return _prd_distribution_cached(
        json.dumps(base, sort_keys=True), grade_gate(snapshot, level), trials, 0xBA7CA + level
    )


def apply_luck_and_gradeup(dist: dict[str, float], stats: dict[str, float]) -> dict[str, float]:
    """현재 GradeRoller의 행운 배율과 한 티어 등급업을 분포 단계에서 적용."""
    luck = max(0.0, float(stats.get("행운", 0.0)))
    gradeup = max(0.0, float(stats.get("등급업", 0.0))) / 100.0
    shifted = {grade: 0.0 for grade in GRADE_ORDER}
    for grade, probability in dist.items():
        if grade == "E":
            shifted[grade] += probability
            continue
        # 등급업/행운의 합성은 실제 롤의 비선형성을 보수적으로 과대적용하지
        # 않도록, 행운은 비-E 질량에만 적용한 뒤 남는 질량을 E로 환원한다.
        shifted[grade] += probability * (1.0 + luck / 100.0)
    non_e = sum(shifted[g] for g in GRADE_ORDER if g != "E")
    shifted["E"] = max(0.0, 1.0 - non_e)
    if gradeup:
        after = {grade: 0.0 for grade in GRADE_ORDER}
        for idx, grade in enumerate(GRADE_ORDER):
            move = shifted[grade] * min(1.0, gradeup)
            after[grade] += shifted[grade] - move
            after[GRADE_ORDER[min(idx + 1, len(GRADE_ORDER) - 1)]] += move
        shifted = after
    total = sum(shifted.values()) or 1.0
    return {grade: shifted[grade] / total for grade in GRADE_ORDER}


def qmult(score: float) -> float:
    return 0.5 + max(0.0, min(100.0, score)) * 0.5 / 100.0


def stat(stats: dict[str, float], key: str) -> float:
    return float(stats.get(key, 0.0))


def max_grade_for_region(catalog: dict[str, Any], region: str | None) -> set[str] | None:
    if not region:
        return None
    rows = catalog.get("fish", {}).get("region_grade_sets", {}).get(region, {})
    grades = rows.get("기본") if isinstance(rows, dict) else None
    return set(grades) if grades else None


def region_filter(dist: dict[str, float], grades: set[str] | None) -> dict[str, float]:
    if not grades:
        return dist
    allowed = {grade for grade in GRADE_ORDER if grade in grades}
    # GradeRoller는 해당 지역 풀에 없는 희귀 등급을 롤에서 건너뛰고
    # 그 확률 질량을 E(또는 지역의 폴백 등급)로 남긴다. 단순 정규화하면
    # 존재하지 않는 희귀 등급을 낮은 등급으로 재분배하는 오류가 난다.
    out = {grade: (dist[grade] if grade in allowed else 0.0) for grade in GRADE_ORDER}
    out["E"] += sum(dist[grade] for grade in GRADE_ORDER if grade not in allowed)
    return out


@lru_cache(maxsize=256)
def _rod_success_cached(difficulty: int, escape: int, delay: int) -> tuple[float, ...]:
    result = {"E": 1.0, "D": 1.0, "C": 1.0}
    for index, grade in enumerate(GRADE_ORDER[3:], start=3):
        result[grade] = simulate_catch(
            grade,
            difficulty,
            escape,
            delay,
            trials=700,
            seed=0xC0DE + index * 101 + difficulty * 7 + escape,
            size=0,
        )
    return tuple(result.get(grade, 0.0) for grade in GRADE_ORDER)


def rod_success_by_grade(stats: dict[str, float], reaction_ms: int, ping_ms: int) -> dict[str, float]:
    delay = ms_to_ticks(reaction_ms + ping_ms)
    difficulty = int(round(stat(stats, "난이도")))
    escape = int(round(stat(stats, "도주감소")))
    values = _rod_success_cached(difficulty, escape, delay)
    return dict(zip(GRADE_ORDER, values))


def crit_multiplier(stats: dict[str, float], tool: str) -> float:
    if tool == "harpoon":
        chance = (5.0 + stat(stats, "크리확률")) / 100.0
        damage = 2.0 + stat(stats, "크리배율")
    else:
        chance = stat(stats, "크리확률") / 100.0
        damage = 1.0 + stat(stats, "크리배율")
    chance = max(0.0, min(1.0, chance))
    # FishingListener의 직접 판매배수(크리배율×6%)와 크기경로의 평균 효과.
    return 1.0 + chance * damage * (0.06 + 0.10 * 0.005 / qmult(50))


def average_price(snapshot: dict[str, Any], dist: dict[str, float], stats: dict[str, float], tool: str) -> float:
    prices = snapshot.get("raw", {}).get("economy", {}).get("grade_base_price", {}) or {}
    base_quality = 85.0 if tool == "harpoon" else 50.0
    size_score = base_quality * (1.0 + stat(stats, "크기") / 100.0)
    size_bonus = qmult(size_score)
    sell_bonus = 1.0 + stat(stats, "판매보너스") / 100.0
    crit = crit_multiplier(stats, tool)
    return sum(dist.get(grade, 0.0) * float(prices.get(grade, 0.0)) for grade in GRADE_ORDER) * size_bonus * sell_bonus * crit


def weighted_xp(dist: dict[str, float], stats: dict[str, float], tool: str) -> float:
    table = HARPOON_XP if tool == "harpoon" else ROD_XP
    exp_bonus = 1.0 + stat(stats, "경험치") / 100.0
    return sum(dist.get(grade, 0.0) * table[grade] for grade in GRADE_ORDER) * exp_bonus


def extra_fish_multiplier(stats: dict[str, float]) -> float:
    return 1.0 + stat(stats, "더블찬스") / 100.0 + 2.0 * stat(stats, "트리플찬스") / 100.0


def harpoon_cycle(stats: dict[str, float], dist: dict[str, float], hit_rate: float) -> dict[str, float]:
    attack = max(1.0, stat(stats, "공격력"))
    attack_speed = max(0.0, stat(stats, "공격속도"))
    gap = max(2.0, HARPOON_BASE_JAB_TICKS / (1.0 + attack_speed / 100.0)) * 0.05
    avg_hits = sum(math.ceil(FISH_HP[g] / attack) * dist.get(g, 0.0) for g in GRADE_ORDER)
    engagement = 1.2 + max(0.0, avg_hits - 1.0) * gap
    effective_hit = max(0.15, min(1.0, hit_rate))
    # Miss는 다음 유효 공격까지의 시간을 늘리지만, Java의 7초 catch cooldown이
    # 한계이면 그 쿨다운이 우선한다.
    cycle = max(HARPOON_CATCH_COOLDOWN_SEC, HARPOON_SPAWN_SEC + engagement / effective_hit)
    return {
        "avg_hits": avg_hits,
        "engagement_sec": engagement,
        "cycle_sec": cycle,
        "catches_per_hour": 3600.0 / cycle,
        "hit_rate": effective_hit,
    }


def simulate_loadout(
    snapshot: dict[str, Any],
    catalog: dict[str, Any],
    level: int,
    items: list[dict[str, Any]],
    tool: str,
    region: str | None = None,
    reaction_ms: int = DEFAULT_REACTION_MS,
    ping_ms: int = DEFAULT_PING_MS,
    harpoon_hit_rate: float = DEFAULT_HARPOON_HIT_RATE,
) -> dict[str, Any]:
    stats = stat_sum(items)
    base = base_grade_distribution(snapshot, level)
    dist = region_filter(apply_luck_and_gradeup(base, stats), max_grade_for_region(catalog, region))
    avg_price = average_price(snapshot, dist, stats, tool)
    extras = extra_fish_multiplier(stats)
    if tool == "rod":
        success = rod_success_by_grade(stats, reaction_ms, ping_ms)
        actions = float(DEFAULT_ROD_ACTIONS)
        catches = actions * sum(dist[g] * success.get(g, 1.0) for g in GRADE_ORDER)
        mode = {
            "actions_per_hour": actions,
            "success_rate": catches / actions if actions else 0,
            "success_by_grade": success,
        }
    else:
        mode = harpoon_cycle(stats, dist, harpoon_hit_rate)
        catches = mode["catches_per_hour"]
    money = catches * avg_price * extras
    xp = catches * weighted_xp(dist, stats, tool) * extras
    return {
        "tool": tool,
        "level": level,
        "region": region,
        "items": [{"category": i.get("category"), "name": i.get("name"), "grade": i.get("grade"), "level": i.get("level")} for i in items],
        "acquisition": {
            "part_price_sum": sum(int(i.get("price", 0)) for i in items),
            "tool_price": next((int(i.get("price", 0)) for i in items if i.get("category") == ("작살" if tool == "harpoon" else "낚싯대")), 0),
            "tool_source": next((i.get("source", "") for i in items if i.get("category") == ("작살" if tool == "harpoon" else "낚싯대")), ""),
            "recipe_found": next((any(r.get("result_part_name") == i.get("name") or r.get("name") == i.get("name") for r in catalog.get("recipes", [])) for i in items if i.get("category") == ("작살" if tool == "harpoon" else "낚싯대")), False),
        },
        "stats": {k: round(v, 4) for k, v in sorted(stats.items())},
        "grade_distribution": {g: round(dist.get(g, 0.0), 6) for g in GRADE_ORDER},
        "avg_quality": 85.0 if tool == "harpoon" else 50.0,
        "avg_price": round(avg_price, 2),
        "catches_per_hour": round(catches, 3),
        "fish_multiplier": round(extras, 5),
        "money_per_hour": round(money, 2),
        "xp_per_hour": round(xp, 2),
        "mode": mode,
        "assumptions": {
            "reaction_ms": reaction_ms,
            "ping_ms": ping_ms,
            "harpoon_hit_rate": harpoon_hit_rate if tool == "harpoon" else None,
            "rod_actions_per_hour": DEFAULT_ROD_ACTIONS if tool == "rod" else None,
            "harpoon_spawn_sec": HARPOON_SPAWN_SEC if tool == "harpoon" else None,
            "harpoon_catch_cooldown_sec": HARPOON_CATCH_COOLDOWN_SEC if tool == "harpoon" else None,
        },
    }


def stat_score(item: dict[str, Any], goal: str) -> float:
    stats = item.get("stats", {}) or {}
    weights = {
        "money": {"판매보너스": 3.0, "더블찬스": 3.0, "트리플찬스": 6.0, "등급업": 2.0, "크기": 1.5, "크리확률": 1.5, "크리배율": 1.0, "행운": 0.6, "난이도": 1.2, "도주감소": 0.1, "공격력": 0.5, "공격속도": 0.7, "돌진쿨감": 0.1},
        "xp": {"경험치": 5.0, "난이도": 1.0, "공격력": 0.4, "공격속도": 0.4},
        "safety": {"난이도": 5.0, "도주감소": 1.5, "공격력": 1.2, "공격속도": 1.0, "수중호흡": 0.4, "수영속도": 0.2},
    }.get(goal, {})
    return sum(float(value) * weights.get(key, 0.0) for key, value in stats.items())


def best_common_parts(catalog: dict[str, Any], level: int, goal: str) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    for category in ROD_CATEGORIES[1:]:
        candidates = eligible_parts(catalog, category, level)
        if candidates:
            selected.append(max(candidates, key=lambda item: stat_score(item, goal)))
    return selected


def best_loadouts(
    snapshot: dict[str, Any],
    catalog: dict[str, Any],
    level: int,
    goal: str = "money",
    region: str | None = None,
    reaction_ms: int = DEFAULT_REACTION_MS,
    ping_ms: int = DEFAULT_PING_MS,
    harpoon_hit_rate: float = DEFAULT_HARPOON_HIT_RATE,
    limit: int = 3,
) -> dict[str, list[dict[str, Any]]]:
    common = best_common_parts(catalog, level, goal)
    output: dict[str, list[dict[str, Any]]] = {}
    for tool, category in (("rod", "낚싯대"), ("harpoon", "작살")):
        rows = []
        for item in eligible_parts(catalog, category, level):
            result = simulate_loadout(snapshot, catalog, level, [item, *common], tool, region, reaction_ms, ping_ms, harpoon_hit_rate)
            score = result["money_per_hour"] if goal == "money" else result["xp_per_hour"] if goal == "xp" else result["mode"].get("success_rate", result["mode"].get("hit_rate", 0.0))
            result["objective"] = goal
            result["objective_value"] = round(score, 2)
            rows.append(result)
        output[tool] = sorted(rows, key=lambda row: row["objective_value"], reverse=True)[: max(1, limit)]
    return output


def compare_levels(snapshot: dict[str, Any], catalog: dict[str, Any], levels: list[int], **kwargs: Any) -> list[dict[str, Any]]:
    rows = []
    for level in levels:
        top = best_loadouts(snapshot, catalog, level, **kwargs)
        rod = top["rod"][0] if top["rod"] else None
        harpoon = top["harpoon"][0] if top["harpoon"] else None
        rows.append({
            "level": level,
            "rod": rod,
            "harpoon": harpoon,
            "harpoon_vs_rod_money_ratio": round(harpoon["money_per_hour"] / rod["money_per_hour"], 4) if rod and rod["money_per_hour"] else None,
            "harpoon_vs_rod_xp_ratio": round(harpoon["xp_per_hour"] / rod["xp_per_hour"], 4) if rod and rod["xp_per_hour"] else None,
        })
    return rows


def print_comparison(rows: list[dict[str, Any]]) -> None:
    print("레벨 | 도구 | 최적 장비 | 골드/h | XP/h | 캐치/h | 평균품질 | 상대(작살/낚싯대)")
    print("-" * 100)
    for row in rows:
        for tool in ("rod", "harpoon"):
            result = row.get(tool)
            if not result:
                continue
            name = next((i["name"] for i in result["items"] if i["category"] in ("낚싯대", "작살")), "-")
            ratio = "-" if tool == "rod" else f"{row['harpoon_vs_rod_money_ratio']:.2f}x"
            print(f"{row['level']:>3} | {tool:>7} | {name[:20]:<20} | {result['money_per_hour']:>8,.0f} | {result['xp_per_hour']:>8,.0f} | {result['catches_per_hour']:>7.1f} | {result['avg_quality']:>4.0f} | {ratio:>8}")


def main() -> None:
    parser = argparse.ArgumentParser(description="레벨 코호트별 낚싯대/작살/로드아웃 비교")
    parser.add_argument("--snapshot", default=None)
    parser.add_argument("--level", type=int, action="append", dest="levels")
    parser.add_argument("--region", default=None)
    parser.add_argument("--goal", choices=("money", "xp", "safety"), default="money")
    parser.add_argument("--reaction-ms", type=int, default=DEFAULT_REACTION_MS)
    parser.add_argument("--ping-ms", type=int, default=DEFAULT_PING_MS)
    parser.add_argument("--harpoon-hit-rate", type=float, default=DEFAULT_HARPOON_HIT_RATE)
    parser.add_argument("--top", type=int, default=3)
    parser.add_argument("--json", action="store_true", dest="as_json")
    parser.add_argument("--sensitivity", action="store_true", help="작살 적중률 0.50/0.75/0.90 세 시나리오")
    args = parser.parse_args()
    snapshot = load_snapshot(args.snapshot)
    catalog = load_catalog(snapshot)
    levels = args.levels or [1, 10, 30, 45, 60, 70, 100]
    def run(hit_rate: float) -> list[dict[str, Any]]:
        return compare_levels(
            snapshot,
            catalog,
            levels,
            goal=args.goal,
            region=args.region,
            reaction_ms=args.reaction_ms,
            ping_ms=args.ping_ms,
            harpoon_hit_rate=hit_rate,
            limit=args.top,
        )

    scenarios = {str(rate): run(rate) for rate in (0.50, 0.75, 0.90)} if args.sensitivity else {str(args.harpoon_hit_rate): run(args.harpoon_hit_rate)}
    rows = scenarios[str(args.harpoon_hit_rate)] if not args.sensitivity else scenarios["0.75"]
    if args.as_json:
        output = {"catalog_hash": catalog.get("catalog_hash"), "rows": rows}
        if args.sensitivity:
            output["sensitivity"] = scenarios
        print(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        if args.sensitivity:
            for rate, scenario_rows in scenarios.items():
                print(f"\n=== 작살 적중률 {rate} ===")
                print_comparison(scenario_rows)
        else:
            print_comparison(rows)
        print("\n※ 작살 hit-rate는 아직 라이브 계측 전 가정값입니다. --harpoon-hit-rate로 민감도 분석하세요.")


if __name__ == "__main__":
    main()
