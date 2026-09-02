#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""생성기 공통 히든 장비 ↔ 레시피 무결성 검사."""

EQUIPMENT_TYPES = ("낚싯대", "릴", "줄", "바늘", "찌", "미끼", "작살")


def _result_key(recipe):
    mode = recipe.get("resultMode")
    if mode == "rod":
        return "낚싯대", recipe.get("rodPartName") or recipe.get("displayName")
    if mode == "part":
        return recipe.get("resultPartType"), recipe.get("resultPartName")
    return None, None


def assert_hidden_recipe_integrity(parts_root, recipes_root):
    """히든 parts 항목마다 정확히 하나의 locked 레시피와 표시 카테고리가 있는지 검사한다."""
    parts = parts_root.get("parts", {})
    recipes = recipes_root.get("recipes", {})
    categories = recipes_root.get("categories", {})
    errors = []
    hidden = []
    for ptype in EQUIPMENT_TYPES:
        for name, value in parts.get(ptype, {}).items():
            fields = str(value).split("|")
            if len(fields) < 7:
                errors.append(f"{ptype}/{name}: parts 필드 부족")
                continue
            if fields[6].startswith("히든"):
                hidden.append((ptype, name))

    for ptype, name in hidden:
        matches = [(rid, rec) for rid, rec in recipes.items() if _result_key(rec) == (ptype, name)]
        label = f"{ptype}/{name}"
        if len(matches) != 1:
            errors.append(f"{label}: 대응 레시피 {len(matches)}개 (정확히 1개 필요)")
            continue
        rid, rec = matches[0]
        if rec.get("locked") is not True:
            errors.append(f"{rid} {label}: locked=true 아님")
        if rid not in categories.get(rec.get("category"), []):
            errors.append(f"{rid} {label}: 조합대 카테고리 목록에 없음")

    if errors:
        raise SystemExit("히든 장비 레시피 감사 실패:\n  - " + "\n  - ".join(errors))
    return len(hidden)
