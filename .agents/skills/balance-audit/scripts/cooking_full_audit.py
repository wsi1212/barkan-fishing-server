#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DishSpecs.java의 현재 요리 원가·보상 체인을 재현하는 감사기."""

from __future__ import annotations

import collections
import json
import os
import re
from dataclasses import dataclass


HERE = os.path.dirname(os.path.abspath(__file__))
BS = "/Users/user/Library/Application Support/feather/player-server/servers/07de2d81-991a-47e2-b62d-06c0d1b5150a/plugins/BlockShip"
SRC = "/Users/user/development/blockship-plugin/src/main/java/com/blockship/cooking/DishSpecs.java"

# 현재 balance-audit 공통 앵커와 같은 값. 강화 농산물은 별도 판매경로가 없는
# 압축 재료라 raw 바닐라 농사 재료의 기회비용을 중복 계산하지 않는다.
CROP_WON = {
    "작물_밀": 28.1,
    "작물_당근": 63.3,
    "작물_감자": 94.9,
    "작물_토마토": 126.6,
    "작물_양배추": 52.7,
    "작물_버섯": 56.3,
    "작물_수박": 1518.8,
}
VANILLA_ENHANCED = {
    "강화밀", "강화당근", "강화감자", "강화비트루트", "강화호박",
    "강화멜론", "강화스위트베리", "강화사탕수수", "강화코코아",
}
MINERAL_WON = {
    "압축흑정석": 95.8,
    "강화다이아몬드": 148.3,
    "강화에메랄드": 148.3,
    "강화청금석": 25.0,
}
FORAGE_FLOOR = {"흔함": 59.3, "희귀": 790.8}
FISH_WON = {"D": 187.5, "C": 450.0, "B": 1500.0, "A": 4500.0, "S": 15000.0}


def load_drop_values() -> dict[str, float]:
    """현재 낚시 드롭확률을 포획당 기회비용으로 환산한다."""
    path = os.path.join(BS, "materials.json")
    data = json.load(open(path, encoding="utf-8"))
    max_chance: dict[str, float] = {}
    for table in data.get("dropTables", {}).values():
        for entry in table:
            chance = float(entry.get("chance", 0)) / 100.0
            if chance > 0:
                max_chance[entry["matId"]] = max(max_chance.get(entry["matId"], 0), chance)
    # stat_value.py의 현재 기본 평균 캐치(22,240원/h ÷ 150캐스트/h).
    per_catch = 148.3
    return {mat_id: per_catch / chance for mat_id, chance in max_chance.items()}


DROP_WON = load_drop_values()
DERIVED = {
    "진주코어": [("진주", 4), ("산호조각", 8), ("별빛진주", 2)],
    # 바르칸핵은 강화 네더라이트 파편/강화 흑요석의 최신 원가가 별도
    # 모델에 없어, 해당 재료가 들어가는 대연회는 미상 태그를 남긴다.
    "바르칸핵": [("바르칸조각", 8), ("강화네더라이트파편", 2), ("강화흑요석", 2), ("별빛진주", 3)],
}


@dataclass(frozen=True)
class Ingredient:
    kind: str
    key: str
    name: str
    qty: int


@dataclass
class Dish:
    dish_id: str
    name: str
    purpose: str
    tier: int
    reward: int
    aux: int
    ingredients: list[Ingredient]


def split_top(text: str) -> list[str]:
    parts, current, depth, quoted = [], [], 0, False
    for ch in text:
        if ch == '"':
            quoted = not quoted
            current.append(ch)
        elif not quoted and ch in "([{":
            depth += 1
            current.append(ch)
        elif not quoted and ch in ")]}":
            depth -= 1
            current.append(ch)
        elif not quoted and ch == "," and depth == 0:
            parts.append("".join(current).strip())
            current = []
        else:
            current.append(ch)
    if current:
        parts.append("".join(current).strip())
    return parts


def calls(fn: str, source: str):
    pattern = re.compile(r"\b" + re.escape(fn) + r"\(")
    for match in pattern.finditer(source):
        start, depth, quoted, i = match.end(), 1, False, match.end()
        while i < len(source) and depth:
            ch = source[i]
            if ch == '"':
                quoted = not quoted
            elif not quoted and ch == '(':
                depth += 1
            elif not quoted and ch == ')':
                depth -= 1
            i += 1
        yield split_top(source[start:i - 1]), source[start:i - 1]


def arg_text(value: str) -> str:
    return value.strip().strip('"')


def int_arg(value: str) -> int:
    return int(value.strip())


def parse_ingredients(ings_source: str) -> list[Ingredient]:
    result = []
    for fn in ("fish", "crop", "mat", "forage", "herbAny", "dish"):
        for args, _ in calls(fn, ings_source):
            if fn == "fish":
                result.append(Ingredient("fish", arg_text(args[0]), arg_text(args[0]), int_arg(args[-1])))
            elif fn == "herbAny":
                result.append(Ingredient("herbany", "herbany", "허브", int_arg(args[-1])))
            elif fn == "forage":
                name = arg_text(args[0])
                result.append(Ingredient("forage", "채집_" + name.replace(" ", ""), name, int_arg(args[-1])))
            elif fn == "dish":
                result.append(Ingredient("dish", arg_text(args[0]), arg_text(args[1]), int_arg(args[-1])))
            else:
                result.append(Ingredient("custom", arg_text(args[0]), arg_text(args[1]), int_arg(args[-1])))
    return result


def load_forage_rarity() -> dict[str, str]:
    path = os.path.join(BS, "forage-types.json")
    data = json.load(open(path, encoding="utf-8"))
    return {v.get("name"): v.get("rarity", "흔함") for v in data.values() if v.get("name")}


def load_dishes() -> dict[str, Dish]:
    source = open(SRC, encoding="utf-8").read()
    source = re.sub(r"//[^\n]*", "", source)
    result = {}
    # order matters only for human output; recursive cost resolution handles the graph.
    for purpose, fn in (("buff", "buff"), ("submit", "submit"), ("heal", "heal"), ("sell", "sell")):
        for args, raw in calls(fn, source):
            if not args or not args[0].startswith('"'):
                continue
            dish_id, name = arg_text(args[0]), arg_text(args[1])
            if purpose == "buff":
                # buff(id,name,base,tier,...) — stats are audited separately from the compiled class.
                tier, reward, aux = int_arg(args[3]), 0, 0
            elif purpose == "submit":
                tier, reward, aux = int_arg(args[3]), int_arg(args[4]), int_arg(args[5])
            elif purpose == "heal":
                tier, reward, aux = int_arg(args[3]), int(float(args[4])), int_arg(args[5])
            else:
                tier, reward, aux = int_arg(args[3]), int_arg(args[4]), int_arg(args[5])
            ing_match = re.search(r"ings\((.*)\)", raw, re.DOTALL)
            if ing_match:
                ingredients = parse_ingredients(ing_match.group(1))
            else:
                ingredients = []
            result[dish_id] = Dish(dish_id, name, purpose, tier, reward, aux, ingredients)
    return result


def main() -> None:
    dishes = load_dishes()
    forage_rarity = load_forage_rarity()
    memo: dict[str, tuple[float, list[str]]] = {}
    visiting: set[str] = set()

    def ingredient_cost(ing: Ingredient, qty_mul: int = 1) -> tuple[float, list[str]]:
        qty = ing.qty * qty_mul
        if ing.kind == "dish":
            raw_cost, tags = dish_cost(ing.key, qty)
            child = dishes.get(ing.key)
            # 완성 요리는 원재료뿐 아니라 판매하거나 버프에 쓸 수 있는
            # 선택권도 포기하므로, 판매용 중간재는 판매가를 기회비용 하한으로 둔다.
            if child is not None and child.purpose == "sell":
                return max(raw_cost, child.reward * qty), tags + [f"sell_opportunity:{ing.key}"]
            return raw_cost, tags
        if ing.kind == "fish":
            return FISH_WON.get(ing.key, 0.0) * qty, []
        if ing.kind == "herbany":
            return FORAGE_FLOOR["흔함"] * qty, []
        if ing.kind == "forage":
            rarity = forage_rarity.get(ing.name, "흔함")
            return FORAGE_FLOOR[rarity] * qty, []
        if ing.key in CROP_WON:
            return CROP_WON[ing.key] * qty, []
        if ing.key in VANILLA_ENHANCED:
            return 0.0, [f"vanilla_free:{ing.key}"]
        if ing.key in MINERAL_WON:
            return MINERAL_WON[ing.key] * qty, []
        if ing.key in DROP_WON:
            return DROP_WON[ing.key] * qty, []
        if ing.key in DERIVED:
            total, tags = 0.0, []
            for child_key, child_qty in DERIVED[ing.key]:
                child = Ingredient("custom", child_key, child_key, child_qty)
                child_cost, child_tags = ingredient_cost(child, qty_mul=qty)
                total += child_cost
                tags.extend(child_tags)
            return total, tags
        return 0.0, [f"unknown:{ing.key}"]

    def dish_cost(dish_id: str, qty: int = 1) -> tuple[float, list[str]]:
        if dish_id in memo and qty == 1:
            cost, tags = memo[dish_id]
            return cost, list(tags)
        if dish_id in visiting:
            return 0.0, [f"cycle:{dish_id}"]
        dish = dishes.get(dish_id)
        if dish is None:
            return 0.0, [f"missing_dish:{dish_id}"]
        visiting.add(dish_id)
        total, tags = 0.0, []
        for ing in dish.ingredients:
            cost, child_tags = ingredient_cost(ing, qty)
            total += cost
            tags.extend(child_tags)
        visiting.remove(dish_id)
        if qty == 1:
            memo[dish_id] = (total, list(tags))
        return total, tags

    purpose_counts = collections.Counter(d.purpose for d in dishes.values())
    dish_refs = [(d.dish_id, i.key, i.qty) for d in dishes.values() for i in d.ingredients if i.kind == "dish"]
    print(f"dish_count={len(dishes)} purpose_counts={dict(purpose_counts)} dish_refs={len(dish_refs)}")
    print("\n[판매용 — 현재 DishSpecs 원가모델]")
    for d in dishes.values():
        if d.purpose != "sell":
            continue
        cost, tags = dish_cost(d.dish_id)
        multiplier = d.reward / cost if cost else float("inf")
        print(f"T{d.tier} {d.name}: reward={d.reward:,} cost={cost:,.1f} multiplier={multiplier:.3f}x "
              f"cook={d.aux}s tags={','.join(sorted(set(tags))) or 'exact'}")
    print("\n[제출용 — 현재 DishSpecs 원가모델]")
    for d in dishes.values():
        if d.purpose != "submit":
            continue
        cost, tags = dish_cost(d.dish_id)
        efficiency = d.reward / cost if cost else float("inf")
        print(f"T{d.tier} {d.name}: points={d.reward:,} cost={cost:,.1f} efficiency={efficiency:.4f}x "
              f"tags={','.join(sorted(set(tags))) or 'exact'}")
    print("\n[발효케이크 체인]")
    cost, tags = dish_cost("발효케이크")
    print(f"current_total_cost={cost:,.1f} reward={dishes['발효케이크'].reward:,} "
          f"multiplier={dishes['발효케이크'].reward / cost:.3f}x")
    for ing in dishes["발효케이크"].ingredients:
        child, _ = ingredient_cost(ing)
        print(f"  {ing.kind}:{ing.key} x{ing.qty} -> {child:,.1f}")


if __name__ == "__main__":
    main()
