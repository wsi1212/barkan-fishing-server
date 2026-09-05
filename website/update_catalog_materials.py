#!/usr/bin/env python3
"""현재 재료 목록과 조합 레시피를 웹 카탈로그에 반영한다.

장비 데이터는 기존 생성 결과를 보존하고, 재료 항목만 BlockShip 운영 데이터와
대조한다. 재료의 완성 아이템은 recipes.json 결과 lore의 ``mat:<id>``를 기준으로
연결한다. 직접 수정한 catalog-data.js는 다음 데이터 갱신 때 다시 어긋나므로
이 스크립트를 다시 실행한다.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parent
CATALOG = ROOT / "assets" / "catalog-data.js"
MATERIALS = PROJECT / "ops" / "blockship-data" / "materials.json"
RECIPES = PROJECT / "ops" / "blockship-data" / "recipes.json"
HEAD = "/* 서버 parts.json · materials.json · recipes.json · gear-data.js에서 생성됨. */\n"

# 실제 시스템에서 제거된 재료. 표시명과 ID가 같은 항목은 모두 제외한다.
REMOVED_MATERIALS = {"심해수정", "고대비늘", "용암수지", "강화자갈", "강화모래", "강화부싯돌"}

# RecipeLoader가 코드 기본값으로 보충하는 A01~A05. 저장된 recipes.json에는
# 빠져 있을 수 있지만 실제 조합대에는 존재하므로 웹 도감에도 표시한다.
JAVA_DEFAULT_MATERIAL_RECIPES = {
    "압축석탄블록": {"id": "A01", "locked": False, "village": "", "ingredients": [{"name": "강화 석탄", "qty": 32}]},
    "압축철블록": {"id": "A02", "locked": False, "village": "", "ingredients": [{"name": "강화 철괴", "qty": 32}]},
    "압축금블록": {"id": "A03", "locked": False, "village": "", "ingredients": [{"name": "강화 금괴", "qty": 32}]},
    "압축다이아블록": {"id": "A04", "locked": False, "village": "", "ingredients": [{"name": "강화 다이아몬드", "qty": 32}]},
    "압축에메랄드블록": {"id": "A05", "locked": False, "village": "", "ingredients": [{"name": "강화 에메랄드", "qty": 32}]},
}


def strip_color(value: str | None) -> str:
    return re.sub(r"&[0-9a-fk-orA-FK-OR]", "", value or "").strip()


def load_catalog() -> dict:
    raw = CATALOG.read_text(encoding="utf-8")
    return json.loads(raw.split("=", 1)[1].rstrip(" ;\n"))


def material_recipe_index(materials: dict, recipes: dict) -> dict[str, dict]:
    by_name = {definition.get("name"): material_id for material_id, definition in materials.items()}
    result = {}
    for recipe_id, recipe in recipes.items():
        material_ids = set()
        display_name = strip_color(recipe.get("displayName"))
        if display_name in materials:
            material_ids.add(display_name)
        if display_name in by_name:
            material_ids.add(by_name[display_name])

        result_data = recipe.get("result") or {}
        result_name = strip_color(result_data.get("name"))
        if result_name in materials:
            material_ids.add(result_name)
        if result_name in by_name:
            material_ids.add(by_name[result_name])
        for line in result_data.get("lore") or []:
            match = re.search(r"mat:([^\s]+)", strip_color(line))
            if match and match.group(1) in materials:
                material_ids.add(match.group(1))

        if not material_ids:
            continue
        summary = {
            "id": recipe.get("id", recipe_id),
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
        for material_id in material_ids:
            result.setdefault(material_id, summary)
    for material_id, summary in JAVA_DEFAULT_MATERIAL_RECIPES.items():
        result.setdefault(material_id, summary)
    return result


def drop_source_index(root: dict) -> dict[str, list[dict]]:
    """재료 → 낚시 획득처([{region, chance}]) — materials.json 드롭테이블에서 매번 다시 뽑는다.

    ★예전엔 catalog-data.js 안의 ``sources``/``desc``/``name`` 를 손으로 넣고 얼려 뒀다.
    그래서 녹슨부품이 「강 12% · 협곡 7% · 바르칸 10%」처럼 지금은 없는 지역과 옛 확률을
    계속 보여 줬다(실제로는 13개 어장 6%). 얼린 사본을 고치지 말고 여기서 파생시킨다.
    """
    index: dict[str, list[dict]] = {}
    for area, table in (root.get("dropTables") or {}).items():
        for drop in table or []:
            index.setdefault(drop["matId"], []).append(
                {"region": area.replace("_", " "), "chance": drop["chance"]})
    for weather, table in (root.get("weatherDrops") or {}).items():
        for drop in table or []:
            index.setdefault(drop["matId"], []).append(
                {"region": f"{weather} (전역 날씨)", "chance": drop["chance"]})
    return index


def main() -> None:
    catalog = load_catalog()
    materials_root = json.loads(MATERIALS.read_text(encoding="utf-8"))
    materials = materials_root["materials"]
    recipes = json.loads(RECIPES.read_text(encoding="utf-8"))["recipes"]
    recipe_index = material_recipe_index(materials, recipes)
    source_index = drop_source_index(materials_root)

    before = [item for item in catalog["items"] if item.get("kind") == "material"]
    kept = []
    removed = []
    attached = 0
    for item in catalog["items"]:
        if item.get("kind") != "material":
            kept.append(item)
            continue
        material_id = item.get("id", "")
        if material_id in REMOVED_MATERIALS or item.get("name") in REMOVED_MATERIALS:
            removed.append(item.get("name", material_id))
            continue
        item["recipe"] = recipe_index.get(material_id)
        if item["recipe"]:
            attached += 1
        # 표시이름·설명·획득처는 materials.json 이 권위 — 매번 덮어쓴다.
        live = materials.get(material_id)
        if live:
            if live.get("name"):
                item["name"] = strip_color(live["name"])
            if live.get("desc"):
                item["desc"] = live["desc"]
        # 낚시 드롭이 없는 재료(광질·조합 산출물)는 기존 값을 건드리지 않는다.
        if source_index.get(material_id):
            item["sources"] = source_index[material_id]
        kept.append(item)

    catalog["items"] = kept
    catalog["count"] = len(kept)
    catalog["equipmentCount"] = sum(item.get("kind") == "equipment" for item in kept)
    catalog["materialCount"] = sum(item.get("kind") == "material" for item in kept)
    catalog["generatedAt"] = datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
    CATALOG.write_text(HEAD + "window.BARKAN_CATALOG_DATA=" + json.dumps(catalog, ensure_ascii=False, separators=(",", ":")) + ";\n", encoding="utf-8")
    print(f"재료 {len(before)}종 → {catalog['materialCount']}종 · 삭제 {len(removed)}종 · 레시피 연결 {attached}종")
    if removed:
        print("삭제:", ", ".join(removed))


if __name__ == "__main__":
    main()
