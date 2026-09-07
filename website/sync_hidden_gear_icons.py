#!/usr/bin/env python3
"""Sync the restored hidden-equipment icons into both web catalog datasets.

The game-facing resource pack is authoritative for the pixels.  The hidden
equipment manifest is authoritative for the 62-item scope, while parts.json
and recipes.json provide the catalog fields for rows that were not in the
older web export yet.

Usage:
    python3 sync_hidden_gear_icons.py          # update data and 128px assets
    python3 sync_hidden_gear_icons.py --check  # write nothing; fail on drift
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parent
DATA = ROOT.parents[2] / "BlockShip"
PARTS = DATA / "parts.json"
RECIPES = DATA / "recipes.json"
MANIFEST = PROJECT / "icon-forge" / "imagegen-hidden" / "manifest.json"
RESOURCEPACK = Path(os.path.expanduser("~/development/barkan-resourcepack"))
RP_TEXTURES = RESOURCEPACK / "assets/minecraft/textures/item/barkan_icon"
WEB_TEXTURES = ROOT / "assets/gear"
GEAR_DATA = ROOT / "assets/gear-data.js"
CATALOG_DATA = ROOT / "assets/catalog-data.js"
WEB_ICON_SIZE = 128

TYPE_KEY = {
    "낚싯대": "rod",
    "릴": "reel",
    "줄": "line",
    "바늘": "hook",
    "미끼": "bait",
    "찌": "bobber",
    "작살": "harpoon",
}

GEAR_HEAD = "/* 서버 parts.json + recipes.json 에서 생성됨. 직접 수정하지 말고 원본을 갱신하세요. */\n"
CATALOG_HEAD = "/* 서버 parts.json · materials.json · recipes.json · gear-data.js에서 생성됨. */\n"
HIDDEN_ACQUISITION = {
    "kind": "hidden",
    "label": "히든 레시피",
    "detail": "수집품 발견 또는 퀘스트 보상으로 레시피를 해금한 뒤 조합대에서 제작",
    "price": None,
    "priceLabel": None,
}


def icon_id(kind: str, name: str) -> str:
    digest = hashlib.sha1((kind + "\0" + name).encode("utf-8")).hexdigest()[:10]
    return f"catalog_{TYPE_KEY[kind]}_{digest}"


def load_js(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    if "=" not in text:
        raise ValueError(f"JS 데이터 대입문 없음: {path}")
    return json.loads(text.split("=", 1)[1].rstrip(" ;\n"))


def write_js(path: Path, head: str, variable: str, payload: dict) -> None:
    path.write_text(
        head
        + variable
        + "="
        + json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        + ";\n",
        encoding="utf-8",
    )


def parse_int(value: str, fallback: int = 0) -> int:
    return int(value) if value.lstrip("-").isdigit() else fallback


def parse_stats(raw: str) -> dict[str, int | float | str]:
    stats: dict[str, int | float | str] = {}
    for chunk in raw.split(","):
        if ":" not in chunk:
            continue
        key, value = chunk.split(":", 1)
        key, value = key.strip(), value.strip()
        try:
            stats[key] = float(value) if "." in value else int(value)
        except ValueError:
            stats[key] = value
    return stats


def recipe_result_key(recipe: dict) -> tuple[str, str] | None:
    mode = recipe.get("resultMode")
    if mode == "rod" and recipe.get("rodPartName"):
        return "낚싯대", recipe["rodPartName"]
    if mode == "part" and recipe.get("resultPartType") and recipe.get("resultPartName"):
        return recipe["resultPartType"], recipe["resultPartName"]
    return None


def recipe_summary(recipe: dict) -> dict:
    return {
        "id": recipe.get("id", ""),
        "locked": bool(recipe.get("locked")),
        "village": recipe.get("village", ""),
        "ingredients": [
            {
                "name": item.get("displayName") or item.get("typeOrMatId", ""),
                "qty": item.get("qty", 1),
            }
            for item in recipe.get("ingredients") or []
        ],
    }


def load_hidden_rows() -> tuple[list[dict], dict[tuple[str, str], str]]:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    rows = manifest.get("rows")
    if not isinstance(rows, list) or len(rows) != 62:
        raise ValueError(f"히든 매니페스트 행 수가 62가 아님: {len(rows) if isinstance(rows, list) else '없음'}")

    parts = json.loads(PARTS.read_text(encoding="utf-8")).get("parts", {})
    recipes = json.loads(RECIPES.read_text(encoding="utf-8")).get("recipes", {})
    by_recipe_id = {recipe.get("id", key): recipe for key, recipe in recipes.items()}
    recipe_by_item = {}
    for recipe in recipes.values():
        key = recipe_result_key(recipe)
        if key:
            recipe_by_item[key] = recipe_summary(recipe)

    target_keys: dict[tuple[str, str], str] = {}
    normalized: list[dict] = []
    for manifest_row in rows:
        kind, name, recipe_id = (
            manifest_row.get("type"),
            manifest_row.get("name"),
            manifest_row.get("recipe"),
        )
        if kind not in TYPE_KEY or not name or not recipe_id:
            raise ValueError(f"매니페스트 행 형식 오류: {manifest_row}")
        expected_id = icon_id(kind, name)
        if manifest_row.get("id") != expected_id:
            raise ValueError(f"아이콘 ID 불일치: {kind}/{name} -> {manifest_row.get('id')} (expected {expected_id})")
        if name not in parts.get(kind, {}):
            raise ValueError(f"parts.json에 장비 없음: {kind}/{name}")
        recipe = by_recipe_id.get(recipe_id)
        if recipe is None or recipe_result_key(recipe) != (kind, name):
            raise ValueError(f"레시피 결과 불일치: {recipe_id} -> {kind}/{name}")
        if (kind, name) in target_keys:
            raise ValueError(f"히든 장비 중복: {kind}/{name}")

        fields = parts[kind][name].split("|", -1)
        if len(fields) < 7:
            raise ValueError(f"parts 포맷 필드 부족: {kind}/{name}")
        row = {
            "name": name,
            "category": kind,
            "grade": fields[1],
            "price": parse_int(fields[2]),
            "durability": parse_int(fields[3]),
            "stats": parse_stats(fields[4]),
            "level": parse_int(fields[5], 1),
            "origin": fields[6],
            "icon": expected_id,
            "recipe": recipe_by_item.get((kind, name)),
            "manifestRecipe": recipe_id,
        }
        if row["recipe"] is None:
            raise ValueError(f"장비 레시피 없음: {kind}/{name}")
        normalized.append(row)
        target_keys[(kind, name)] = expected_id

    return normalized, target_keys


def catalog_row(gear_row: dict) -> dict:
    raw_stats = [f"{key}:{value}" for key, value in gear_row["stats"].items()]
    recipe = gear_row["recipe"]
    catalog_recipe = {
        "id": recipe["id"],
        "locked": recipe["locked"],
        "village": recipe["village"],
        "ingredients": recipe["ingredients"],
    }
    return {
        "kind": "equipment",
        "type": gear_row["category"],
        "name": gear_row["name"],
        "grade": gear_row["grade"],
        "price": gear_row["price"],
        "durability": gear_row["durability"],
        "stats": raw_stats,
        "level": gear_row["level"],
        "source": gear_row["origin"],
        "recipe": catalog_recipe,
        "acquisition": HIDDEN_ACQUISITION.copy(),
        "icon": gear_row["icon"],
    }


def merge_rows(existing: list[dict], rows: list[dict], key_fields: tuple[str, str]) -> list[dict]:
    replacements = {(row[key_fields[0]], row[key_fields[1]]): row for row in rows}
    merged: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for item in existing:
        key = (item.get(key_fields[0]), item.get(key_fields[1]))
        if key in replacements:
            merged.append(replacements[key])
            seen.add(key)
        else:
            merged.append(item)
    merged.extend(row for row in rows if (row[key_fields[0]], row[key_fields[1]]) not in seen)
    return merged


def sync_assets(rows: list[dict]) -> None:
    WEB_TEXTURES.mkdir(parents=True, exist_ok=True)
    for row in rows:
        source = RP_TEXTURES / f"{row['icon']}.png"
        if not source.is_file():
            raise ValueError(f"리소스팩 아이콘 없음: {source}")
        destination = WEB_TEXTURES / source.name
        with Image.open(source) as image:
            image = image.convert("RGBA")
            if image.size != (WEB_ICON_SIZE, WEB_ICON_SIZE):
                image = image.resize((WEB_ICON_SIZE, WEB_ICON_SIZE), Image.Resampling.LANCZOS)
            image.save(destination, format="PNG", optimize=True)


def asset_errors(payload: dict, label: str) -> list[str]:
    errors: list[str] = []
    items = payload.get("gear") if label == "gear-data" else payload.get("items")
    if not isinstance(items, list):
        return [f"{label}: 항목 배열 없음"]
    equipment = items if label == "gear-data" else [item for item in items if item.get("kind") == "equipment"]
    for item in equipment:
        icon = item.get("icon")
        name = item.get("name", "(이름 없음)")
        if not isinstance(icon, str) or not icon:
            errors.append(f"{label}: 아이콘 없음 — {name}")
            continue
        if Path(icon).name != icon or icon.endswith(".png"):
            errors.append(f"{label}: 아이콘 경로 형식 오류 — {name}: {icon}")
            continue
        kind = item.get("category") if label == "gear-data" else item.get("type")
        if kind in TYPE_KEY and name != "(이름 없음)":
            expected = icon_id(kind, name)
            if icon != expected:
                errors.append(f"{label}: 아이콘 ID 불일치 — {kind}/{name}: {icon} (expected {expected})")
        path = WEB_TEXTURES / f"{icon}.png"
        if not path.is_file():
            errors.append(f"{label}: 아이콘 파일 없음 — {name}: {path}")
            continue
        try:
            with Image.open(path) as image:
                image.verify()
        except OSError as exc:
            errors.append(f"{label}: PNG 읽기 실패 — {name}: {exc}")
    return errors


def hidden_asset_errors(rows: list[dict]) -> list[str]:
    """Ensure the web copy still represents the current RP output for hidden rows."""
    errors: list[str] = []
    for row in rows:
        source = RP_TEXTURES / f"{row['icon']}.png"
        destination = WEB_TEXTURES / source.name
        if not source.is_file() or not destination.is_file():
            continue
        try:
            with Image.open(source) as source_image, Image.open(destination) as web_image:
                expected = source_image.convert("RGBA")
                if expected.size != (WEB_ICON_SIZE, WEB_ICON_SIZE):
                    expected = expected.resize((WEB_ICON_SIZE, WEB_ICON_SIZE), Image.Resampling.LANCZOS)
                actual = web_image.convert("RGBA")
                if actual.size != expected.size or actual.tobytes() != expected.tobytes():
                    errors.append(f"웹 아이콘이 리소스팩 산출물과 다름 — {row['name']}: {destination}")
        except OSError as exc:
            errors.append(f"웹/RP 아이콘 비교 실패 — {row['name']}: {exc}")
    return errors


def check(rows: list[dict], target_keys: dict[tuple[str, str], str]) -> int:
    errors: list[str] = []
    for row in rows:
        source = RP_TEXTURES / f"{row['icon']}.png"
        if not source.is_file():
            errors.append(f"리소스팩 아이콘 없음 — {row['name']}: {source}")

    gear = load_js(GEAR_DATA)
    catalog = load_js(CATALOG_DATA)
    errors.extend(hidden_asset_errors(rows))
    errors.extend(asset_errors(gear, "gear-data"))
    errors.extend(asset_errors(catalog, "catalog-data"))
    for label, payload, key_fields in (
        ("gear-data", gear, ("category", "name")),
        ("catalog-data", catalog, ("type", "name")),
    ):
        items = payload.get("gear") if label == "gear-data" else payload.get("items", [])
        by_key = {
            (item.get(key_fields[0]), item.get(key_fields[1])): item
            for item in items
            if label == "gear-data" or item.get("kind") == "equipment"
        }
        for key, expected_icon in target_keys.items():
            item = by_key.get(key)
            if item is None:
                errors.append(f"{label}: 히든 장비 데이터 없음 — {key[0]}/{key[1]}")
            elif item.get("icon") != expected_icon:
                errors.append(f"{label}: 아이콘 ID 불일치 — {key[0]}/{key[1]}: {item.get('icon')}")

    if errors:
        print("\n".join(f"ERROR: {error}" for error in errors), file=sys.stderr)
        return 1
    gear_items = len(gear.get("gear", []))
    catalog_items = sum(item.get("kind") == "equipment" for item in catalog.get("items", []))
    print(f"PASS: 히든 62종 · gear-data 장비 {gear_items}종 · catalog-data 장비 {catalog_items}종 · 아이콘 파일 전부 존재")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="파일을 쓰지 않고 모든 웹 장비 아이콘을 검증")
    args = parser.parse_args()
    rows, target_keys = load_hidden_rows()
    if args.check:
        return check(rows, target_keys)

    gear = load_js(GEAR_DATA)
    catalog = load_js(CATALOG_DATA)
    gear_rows = []
    for row in rows:
        gear_row = {key: value for key, value in row.items() if key != "manifestRecipe"}
        # gear-data.js historically exposes the compact recipe shape without
        # the catalog-only locked flag. Keep that public schema stable.
        gear_row["recipe"] = {key: value for key, value in row["recipe"].items() if key != "locked"}
        gear_rows.append(gear_row)
    catalog_rows = [catalog_row(row) for row in rows]
    sync_assets(rows)

    gear["gear"] = merge_rows(gear.get("gear", []), gear_rows, ("category", "name"))
    gear["count"] = len(gear["gear"])
    gear["generatedAt"] = datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
    write_js(GEAR_DATA, GEAR_HEAD, "window.BARKAN_GEAR_DATA", gear)

    catalog["items"] = merge_rows(catalog.get("items", []), catalog_rows, ("type", "name"))
    catalog["count"] = len(catalog["items"])
    catalog["equipmentCount"] = sum(item.get("kind") == "equipment" for item in catalog["items"])
    catalog["materialCount"] = sum(item.get("kind") == "material" for item in catalog["items"])
    catalog["generatedAt"] = datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
    write_js(CATALOG_DATA, CATALOG_HEAD, "window.BARKAN_CATALOG_DATA", catalog)

    result = check(rows, target_keys)
    if result == 0:
        print(f"synced hidden web icons: {len(rows)} (new/updated assets in {WEB_TEXTURES})")
    return result


if __name__ == "__main__":
    raise SystemExit(main())
