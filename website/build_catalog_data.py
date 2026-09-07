#!/usr/bin/env python3
"""웹 통합 도감 산출기 — 라이브 장비·재료 원본 → assets/catalog-data.js.

`/gear`와 `/catalog`이 서로 다른 사본을 들고 있어 장비가 누락되는 일을 막는다.
장비 행은 갱신된 gear-data.js를 기준으로 전부 다시 만들고, 재료는 라이브
materials.json의 전체 정의와 드롭표에서 매번 파생한다.

사용:
    python3 build_catalog_data.py
    python3 build_catalog_data.py --check
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parent
LIVE = ROOT.parents[2] / "BlockShip"
GEAR_DATA = ROOT / "assets" / "gear-data.js"
OUT = ROOT / "assets" / "catalog-data.js"
MATERIAL_DIR = ROOT / "assets" / "materials"
RESOURCEPACK = Path.home() / "development" / "barkan-resourcepack"
RESOURCEPACK_ICONS = RESOURCEPACK / "assets" / "minecraft" / "textures" / "item" / "barkan_icon"
HEAD = "/* 서버 parts.json · materials.json · recipes.json · gear-data.js에서 생성됨. */\n"
ICON_PX = 128

# RecipeLoader가 코드 기본값으로 채우는 압축 재료 레시피. 라이브 recipes.json에
# 없더라도 실제 조합대에는 있으므로 웹에도 빠지면 안 된다.
DEFAULT_MATERIAL_RECIPES = {
    "압축석탄블록": {"id": "A01", "locked": False, "village": "", "ingredients": [{"name": "강화 석탄", "qty": 32}]},
    "압축철블록": {"id": "A02", "locked": False, "village": "", "ingredients": [{"name": "강화 철괴", "qty": 32}]},
    "압축금블록": {"id": "A03", "locked": False, "village": "", "ingredients": [{"name": "강화 금괴", "qty": 32}]},
    "압축다이아블록": {"id": "A04", "locked": False, "village": "", "ingredients": [{"name": "강화 다이아몬드", "qty": 32}]},
    "압축에메랄드블록": {"id": "A05", "locked": False, "village": "", "ingredients": [{"name": "강화 에메랄드", "qty": 32}]},
}


def load_js(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    return json.loads(text[text.index("{"):text.rindex("}") + 1])


def write_js(path: Path, variable: str, payload: dict) -> None:
    path.write_text(HEAD + variable + "=" + json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + ";\n", encoding="utf-8")


def strip_color(value: str | None) -> str:
    import re
    return re.sub(r"&[0-9a-fk-orA-FK-OR]", "", value or "").strip()


def icon_id(kind: str, name: str) -> str:
    digest = hashlib.sha1((kind + "\0" + name).encode("utf-8")).hexdigest()[:10]
    return f"catalog_material_{digest}"


def equipment_recipe_index(recipes: dict) -> dict[tuple[str, str], dict]:
    index: dict[tuple[str, str], dict] = {}
    for recipe in recipes.values():
        if recipe.get("resultMode") == "rod" and recipe.get("rodPartName"):
            key = ("낚싯대", recipe["rodPartName"])
        elif recipe.get("resultMode") == "part" and recipe.get("resultPartType") and recipe.get("resultPartName"):
            key = (recipe["resultPartType"], recipe["resultPartName"])
        else:
            continue
        index[key] = {
            "id": recipe.get("id", ""),
            "locked": bool(recipe.get("locked")),
            "village": recipe.get("village", ""),
            "ingredients": [{"name": item.get("displayName") or item.get("typeOrMatId", ""), "qty": item.get("qty", 1)}
                            for item in recipe.get("ingredients") or []],
        }
    return index


def material_recipe_index(materials: dict, recipes: dict) -> dict[str, dict]:
    names = {strip_color(row.get("name")): material_id for material_id, row in materials.items()}
    index: dict[str, dict] = {}
    for recipe in recipes.values():
        ids = set()
        for candidate in (strip_color(recipe.get("displayName")), strip_color((recipe.get("result") or {}).get("name"))):
            if candidate in materials:
                ids.add(candidate)
            if candidate in names:
                ids.add(names[candidate])
        for lore in (recipe.get("result") or {}).get("lore") or []:
            marker = strip_color(lore)
            if "mat:" in marker:
                material_id = marker.split("mat:", 1)[1].split()[0]
                if material_id in materials:
                    ids.add(material_id)
        if not ids:
            continue
        summary = {
            "id": recipe.get("id", ""),
            "locked": bool(recipe.get("locked")),
            "village": recipe.get("village", ""),
            "ingredients": [{"name": item.get("displayName") or item.get("typeOrMatId", ""), "qty": item.get("qty", 1)}
                            for item in recipe.get("ingredients") or []],
        }
        for material_id in ids:
            index.setdefault(material_id, summary)
    for material_id, recipe in DEFAULT_MATERIAL_RECIPES.items():
        index.setdefault(material_id, recipe)
    return index


def material_sources(material_root: dict) -> dict[str, list[dict]]:
    index: dict[str, list[dict]] = {}
    for region, drops in (material_root.get("dropTables") or {}).items():
        for drop in drops or []:
            index.setdefault(drop["matId"], []).append({"region": region, "chance": drop["chance"]})
    for weather, drops in (material_root.get("weatherDrops") or {}).items():
        for drop in drops or []:
            index.setdefault(drop["matId"], []).append({"region": f"{weather} (전역 날씨)", "chance": drop["chance"]})
    return index


def stat_lines(stats: dict) -> list[str]:
    lines = []
    for key, value in (stats or {}).items():
        if isinstance(value, float) and value.is_integer():
            value = int(value)
        lines.append(f"{key}:{value}")
    return lines


def acquisition(origin: str, recipe: dict | None) -> dict:
    if origin.startswith("히든-"):
        return {"kind": "hidden", "label": "히든 레시피", "detail": "수집품 발견 또는 퀘스트 보상으로 레시피를 해금한 뒤 조합대에서 제작", "price": None, "priceLabel": None}
    if recipe:
        village = recipe.get("village") or origin
        if recipe.get("locked"):
            return {"kind": "recipe", "label": "레시피 해금", "detail": f"{village}에서 레시피를 해금한 뒤 조합대에서 제작", "price": None, "priceLabel": None}
        return {"kind": "recipe", "label": "기본 레시피", "detail": "조합대에서 바로 제작할 수 있는 레시피", "price": None, "priceLabel": None}
    return {"kind": "direct", "label": "직접 획득", "detail": f"{origin or '게임 내 획득처'}에서 획득", "price": None, "priceLabel": None}


def export_material_icons(materials: dict) -> list[str]:
    MATERIAL_DIR.mkdir(parents=True, exist_ok=True)
    errors = []
    keep = set()
    for material_id in materials:
        icon = icon_id("재료", material_id)
        keep.add(icon + ".png")
        source = RESOURCEPACK_ICONS / (icon + ".png")
        destination = MATERIAL_DIR / source.name
        if not source.is_file():
            errors.append(f"리소스팩 재료 아이콘 없음: {material_id} ({source.name})")
            continue
        with Image.open(source) as image:
            image = image.convert("RGBA")
            if image.size != (ICON_PX, ICON_PX):
                image = image.resize((ICON_PX, ICON_PX), Image.Resampling.LANCZOS)
            image.save(destination, format="PNG", optimize=True)
    for path in MATERIAL_DIR.glob("*.png"):
        if path.name not in keep:
            path.unlink()
    return errors


def build() -> dict:
    gear = load_js(GEAR_DATA).get("gear", [])
    material_root = json.loads((LIVE / "materials.json").read_text(encoding="utf-8"))
    materials = material_root.get("materials", {})
    recipes = json.loads((LIVE / "recipes.json").read_text(encoding="utf-8")).get("recipes", {})
    equipment_recipes = equipment_recipe_index(recipes)
    rows = []
    for item in gear:
        recipe = equipment_recipes.get((item["category"], item["name"]))
        rows.append({
            "kind": "equipment", "type": item["category"], "name": item["name"], "grade": item["grade"],
            "price": item["price"], "durability": item["durability"], "stats": stat_lines(item.get("stats", {})),
            "level": item["level"], "source": item["origin"], "recipe": recipe,
            "acquisition": acquisition(item["origin"], recipe), "icon": item["icon"],
        })
    recipes_by_material = material_recipe_index(materials, recipes)
    sources = material_sources(material_root)
    for material_id, material in materials.items():
        rows.append({
            "kind": "material", "id": material_id, "type": "재료", "name": strip_color(material.get("name")) or material_id,
            "desc": material.get("desc", ""), "sources": sources.get(material_id, []),
            "recipe": recipes_by_material.get(material_id), "icon": icon_id("재료", material_id),
        })
    return {
        "generatedAt": datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
        "count": len(rows), "equipmentCount": len(gear), "materialCount": len(materials),
        "items": rows, "materialIconCount": len(materials),
    }


def validate(payload: dict) -> list[str]:
    errors = []
    expected = build()
    actual = load_js(OUT)
    for field in ("count", "equipmentCount", "materialCount", "items", "materialIconCount"):
        if actual.get(field) != expected.get(field):
            errors.append(f"{field}가 라이브 원본과 다름")
    for item in actual.get("items", []):
        icon = item.get("icon", "")
        path = (ROOT / "assets" / "gear" / f"{icon}.png") if item.get("kind") == "equipment" else MATERIAL_DIR / f"{icon}.png"
        if not icon or not path.is_file():
            errors.append(f"아이콘 없음: {item.get('name', '?')}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="라이브 원본과 현재 웹 산출물만 대조")
    args = parser.parse_args()
    if args.check:
        errors = validate({})
        if errors:
            print("\n".join(f"ERROR: {error}" for error in errors))
            return 1
        current = load_js(OUT)
        print(f"PASS: 장비 {current['equipmentCount']}종 · 재료 {current['materialCount']}종 · 아이콘 전부 존재")
        return 0
    payload = build()
    errors = export_material_icons(json.loads((LIVE / "materials.json").read_text(encoding="utf-8")).get("materials", {}))
    if errors:
        print("\n".join(f"ERROR: {error}" for error in errors))
        return 1
    write_js(OUT, "window.BARKAN_CATALOG_DATA", payload)
    errors = validate(payload)
    if errors:
        print("\n".join(f"ERROR: {error}" for error in errors))
        return 1
    print(f"catalog updated: 장비 {payload['equipmentCount']}종 · 재료 {payload['materialCount']}종")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
