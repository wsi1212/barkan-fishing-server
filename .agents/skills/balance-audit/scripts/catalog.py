#!/usr/bin/env python3
"""BlockShip 런타임 카탈로그 공통 로더.

밸런스 감사에서 ``parts.json``의 개수만 세면 실제 플레이어가 고를 수 있는
선택지(요구 레벨, 가격, 재료, 해금 경로, 지역)를 잃는다. 이 모듈은 모든
장비/레시피/어종을 하나의 정규화된 카탈로그로 읽어 시뮬레이터와 스냅샷이
동일한 입력을 사용하게 한다.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any


DEFAULT_JAVA_ROOT = "/Users/user/development/blockship-plugin/src/main/java/com/blockship"
DEFAULT_JSON_ROOT = (
    "/Users/user/Library/Application Support/feather/player-server/servers/"
    "07de2d81-991a-47e2-b62d-06c0d1b5150a/plugins/BlockShip"
)

PART_CATEGORIES = ("낚싯대", "릴", "줄", "바늘", "미끼", "찌", "작살")
ROD_CATEGORIES = PART_CATEGORIES[:6]
GRADE_ORDER = ("E", "D", "C", "B", "A", "S", "M", "L", "G")


def expand_grade_spec(spec: str) -> set[str]:
    if "~" not in spec:
        return {spec} if spec in GRADE_ORDER else set()
    left, right = (part.strip() for part in spec.split("~", 1))
    if left not in GRADE_ORDER or right not in GRADE_ORDER:
        return set()
    a, b = GRADE_ORDER.index(left), GRADE_ORDER.index(right)
    lo, hi = sorted((a, b))
    return set(GRADE_ORDER[lo : hi + 1])


def roots() -> tuple[Path, Path]:
    return (
        Path(os.environ.get("BLOCKSHIP_JAVA", DEFAULT_JAVA_ROOT)),
        Path(os.environ.get("BLOCKSHIP_JSON", DEFAULT_JSON_ROOT)),
    )


def load_json(json_root: Path, name: str) -> Any:
    with (json_root / name).open(encoding="utf-8") as f:
        return json.load(f)


def parse_stats(raw: str) -> dict[str, float]:
    out: dict[str, float] = {}
    for pair in (raw or "").split(","):
        if ":" not in pair:
            continue
        key, value = pair.split(":", 1)
        try:
            out[key] = float(value)
        except ValueError:
            continue
    return out


def parse_part(raw: str, category: str, part_id: str | None = None) -> dict[str, Any]:
    fields = raw.split("|")
    fields += [""] * max(0, 7 - len(fields))
    name, grade, price, durability, stat_text, level, source = fields[:7]
    try:
        price_n = int(float(price))
    except (TypeError, ValueError):
        price_n = 0
    try:
        durability_n = int(float(durability))
    except (TypeError, ValueError):
        durability_n = 0
    try:
        level_n = int(float(level))
    except (TypeError, ValueError):
        level_n = 1
    return {
        "id": part_id or name,
        "name": name,
        "category": category,
        "grade": grade,
        "price": price_n,
        "durability": durability_n,
        "level": level_n,
        "stats": parse_stats(stat_text),
        "source": source,
        "raw": raw,
    }


def load_parts(json_root: Path) -> list[dict[str, Any]]:
    data = load_json(json_root, "parts.json")
    raw_parts = data.get("parts", data)
    out: list[dict[str, Any]] = []
    if not isinstance(raw_parts, dict):
        return out
    for category, entries in raw_parts.items():
        if not isinstance(entries, dict):
            continue
        for part_id, raw in entries.items():
            if isinstance(raw, str):
                out.append(parse_part(raw, category, str(part_id)))
    return out


def load_recipes(json_root: Path) -> list[dict[str, Any]]:
    data = load_json(json_root, "recipes.json")
    recipes = data.get("recipes", data)
    if isinstance(recipes, dict):
        recipes = list(recipes.values())
    return [r for r in recipes if isinstance(r, dict)]


def recipe_result_name(recipe: dict[str, Any]) -> str | None:
    for key in ("rodPartName", "resultPartName", "displayName", "resultName"):
        value = recipe.get(key)
        if value:
            return str(value)
    result = recipe.get("result")
    if isinstance(result, dict):
        for key in ("name", "displayName", "partName"):
            if result.get(key):
                return str(result[key])
    return None


def recipe_result_category(recipe: dict[str, Any]) -> str | None:
    category = recipe.get("resultPartType")
    if category:
        return str(category)
    result = recipe.get("result")
    if isinstance(result, dict) and result.get("partType"):
        return str(result["partType"])
    return str(recipe.get("category")) if recipe.get("category") else None


def recipe_index(recipes: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    by_name: dict[str, list[dict[str, Any]]] = {}
    for recipe in recipes:
        name = recipe_result_name(recipe)
        if name:
            by_name.setdefault(name, []).append(recipe)
    return by_name


def load_fish_summary(json_root: Path) -> dict[str, Any]:
    data = load_json(json_root, "fish.json")
    fish = data.get("fish", [])
    by_grade: dict[str, int] = {}
    regions: dict[str, dict[str, int]] = {}
    min_size = None
    max_size = None
    if isinstance(fish, dict):
        fish_values = fish.values()
        for item in fish_values:
            if not isinstance(item, dict):
                continue
            grade = str(item.get("grade", "?"))
            by_grade[grade] = by_grade.get(grade, 0) + 1
            for key, reducer in (("minSize", min), ("maxSize", max)):
                value = item.get(key)
                if isinstance(value, (int, float)):
                    if key == "minSize":
                        min_size = value if min_size is None else min(min_size, value)
                    else:
                        max_size = value if max_size is None else max(max_size, value)
    raw_regions = data.get("regions", {})
    if isinstance(raw_regions, dict):
        for region, modes in raw_regions.items():
            if not isinstance(modes, dict):
                continue
            regions[str(region)] = {
                str(mode): len(values) if isinstance(values, list) else 0
                for mode, values in modes.items()
            }
    return {
        "fish_count": len(fish) if isinstance(fish, dict) else 0,
        "fish_by_grade": by_grade,
        "regions": regions,
        "region_grade_sets": {
            str(region): {
                str(mode): sorted(
                    {
                        grade
                        for name in (values if isinstance(values, list) else [])
                        for grade in expand_grade_spec(str((fish.get(name) or {}).get("grade", "E")))
                        if isinstance(fish, dict) and name in fish
                    }
                )
                for mode, values in (modes.items() if isinstance(modes, dict) else [])
            }
            for region, modes in (raw_regions.items() if isinstance(raw_regions, dict) else [])
        },
        "region_count": len(regions),
        "size_range": {"min": min_size, "max": max_size},
        "environment_modes": sorted((data.get("environment") or {}).keys())
        if isinstance(data.get("environment"), dict)
        else [],
    }


def _safe_source_hash(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()[:16]
    except OSError:
        return None


def _canonical_item(item: dict[str, Any]) -> dict[str, Any]:
    return {
        key: item[key]
        for key in ("id", "name", "category", "grade", "price", "durability", "level", "stats", "source")
        if key in item
    }


def build_catalog(json_root: Path | None = None) -> dict[str, Any]:
    _, default_json = roots()
    json_root = json_root or default_json
    parts = load_parts(json_root)
    recipes = load_recipes(json_root)
    by_recipe = recipe_index(recipes)
    by_category: dict[str, list[dict[str, Any]]] = {}
    for item in parts:
        by_category.setdefault(item["category"], []).append(item)

    recipe_rows = []
    for recipe in recipes:
        row = {
            "id": recipe.get("id"),
            "category": recipe.get("category"),
            "result_part_type": recipe_result_category(recipe),
            "result_part_name": recipe.get("resultPartName") or recipe.get("rodPartName"),
            "name": recipe_result_name(recipe),
            "locked": recipe.get("locked"),
            "result_mode": recipe.get("resultMode"),
            "ingredients": recipe.get("ingredients", []),
            "village": recipe.get("village"),
        }
        recipe_rows.append(row)

    missing_recipe_names = {
        category: sorted(
            item["name"]
            for item in by_category.get(category, [])
            if item["name"] not in by_recipe
        )
        for category in PART_CATEGORIES
    }
    duplicate_names: list[str] = []
    # Same display name across categories is legal, but duplicate rows within a category
    # make acquisition and loadout attribution ambiguous.
    for category, rows in by_category.items():
        seen: dict[str, int] = {}
        for row in rows:
            seen[row["name"]] = seen.get(row["name"], 0) + 1
        duplicate_names.extend(f"{category}:{name}" for name, n in seen.items() if n > 1)

    counts = {category: len(rows) for category, rows in by_category.items()}
    catalog_rows = [_canonical_item(item) for item in parts]
    canonical = json.dumps(
        {"parts": catalog_rows, "recipes": recipe_rows},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return {
        "part_counts": counts,
        "part_total": len(parts),
        "parts": catalog_rows,
        "recipes": recipe_rows,
        "recipe_counts": {
            category: sum(1 for row in recipe_rows if row.get("result_part_type") == category)
            for category in PART_CATEGORIES
        },
        "missing_recipe_names": missing_recipe_names,
        "duplicate_names": sorted(set(duplicate_names)),
        "fish": load_fish_summary(json_root),
        "source_fingerprints": {
            name: _safe_source_hash(json_root / name)
            for name in ("parts.json", "recipes.json", "fish.json", "enhance.json")
        },
        "catalog_hash": hashlib.sha256(canonical).hexdigest()[:16],
    }


def eligible_parts(catalog: dict[str, Any], category: str, level: int) -> list[dict[str, Any]]:
    return [
        item
        for item in catalog.get("parts", [])
        if item.get("category") == category
        and int(item.get("level", 1)) <= level
        and not (item.get("grade") == "S" and int(item.get("level", 1)) == 0)
    ]


def stat_sum(items: list[dict[str, Any]]) -> dict[str, float]:
    result: dict[str, float] = {}
    for item in items:
        for key, value in (item.get("stats") or {}).items():
            result[key] = result.get(key, 0.0) + float(value)
    return result


if __name__ == "__main__":
    java_root, json_root = roots()
    catalog = build_catalog(json_root)
    print(json.dumps({k: v for k, v in catalog.items() if k not in ("parts", "recipes")}, ensure_ascii=False, indent=2))
