#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""요리 3용도 전수 원가·가치 감사.

이전 cooking_full_audit.py의 결함을 의도적으로 고친 비교용 분석기다.

구 모델: 강화 농산물=0원, dish(...) 중간재=0원, 강화코코아=unknown=0원.
신 모델: 런타임 recipes.json을 재귀적으로 풀고, 강화 농산물은 **활성 섬상점
판매가 × 실제 레시피 수량**으로 평가한다. 판매용 하위 요리는 제작원가와 즉시
판매가 중 큰 값을 기회비용으로 사용한다.

주의: 특수작물·채집·낚시 드롭의 값은 현 LP/기회비용 앵커를 쓰며, 원화 환산의
근거가 아직 없는 재료는 unknown 목록으로 남긴다. 0원으로 숨기지 않는다.
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import re
import subprocess
import importlib.util
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path("/Users/user/Library/Application Support/feather/player-server/servers/"
            "07de2d81-991a-47e2-b62d-06c0d1b5150a/plugins/Skript/scripts")
DATA = ROOT.parent.parent / "BlockShip"
SRC = Path("/Users/user/development/blockship-plugin/src/main/java/com/blockship/cooking/DishSpecs.java")
PROD = "ubuntu@168.107.8.107"
KEY = Path("/Users/user/.ssh/oracle-mc.key")
REMOTE_SHOP = "~/mcserver/plugins/BlockShip/shop-items.json"

# price_ladder.py의 물고기 기본가와 최신 실측 평균 품질(69.3)에서의 판매 기회비용 하한.
FISH_BASE = {"E": 100, "D": 250, "C": 600, "B": 2000, "A": 6000,
             "S": 20000, "M": 65000, "L": 170000, "G": 450000}
FISH_SIZE = 0.5 + 69.3 / 200.0
CATCH_WON = 606.0

# 특수작물의 기존 cross-economy 앵커. 0원 취급을 막기 위한 보수적 floor이며,
# 새 농사 실측이 쌓이면 이 표를 대체한다.
CROP = {"작물_밀": 28.1, "작물_당근": 63.3, "작물_감자": 94.9,
        "작물_토마토": 126.6, "작물_양배추": 52.7, "작물_버섯": 56.3,
        "작물_수박": 1518.8}
# 교차경제 감사에서 산출한 조달 기회비용. 섬상점 판매가가 없더라도 드릴·낚시 파밍으로
# 실제 공급되는 재료이므로 unknown으로 빼면 상위 판매/제출 원가가 체계적으로 낮아진다.
MATERIAL_ANCHOR = {"흑정석": 64.0, "압축흑정석": 573.0, "진주조개": 15135.0}
# 채집의 행동비 floor. 종별 가치는 forage_node_values()가 prod 노드 수로 보정한다.
FORAGE_FLOOR = {"흔함": 355.0, "희귀": 4730.0}


def measured_buff_value() -> tuple[dict[str, float], str]:
    """stat_value.py의 현재 중반 실측 환율을 재사용한다(별도 하드코딩 금지)."""
    p = ROOT / ".agents/skills/balance-audit/scripts/stat_value.py"
    spec = importlib.util.spec_from_file_location("cooking_stat_value", p)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    result = module.compute("중반")
    labels = {"exp": "경험치 (1%)", "size": "크기 (1%)", "gradeup": "등급업 (1%)",
              "escape": "도주감소 (1%)", "crit": "크리확률 (1%)", "dbl": "더블찬스 (1%)",
              "sellBonus": "판매보너스 (1%)", "difficulty": "난이도 (1점)"}
    return ({k: result["V"][label][0] for k, label in labels.items()}, result.get("source", "중반 실측"))


def norm(s: str) -> str:
    return re.sub(r"[^A-Z0-9]", "_", (s or "").upper()).strip("_")


def split_top(s: str) -> list[str]:
    out, cur, depth, quoted = [], [], 0, False
    for ch in s:
        if ch == '"':
            quoted = not quoted
        elif not quoted and ch in "([{":
            depth += 1
        elif not quoted and ch in ")]}":
            depth -= 1
        if ch == "," and not quoted and depth == 0:
            out.append("".join(cur).strip()); cur = []
        else:
            cur.append(ch)
    if cur:
        out.append("".join(cur).strip())
    return out


def calls(name: str, src: str):
    for m in re.finditer(r"\b" + re.escape(name) + r"\(", src):
        depth, i = 1, m.end()
        while i < len(src) and depth:
            if src[i] == "(": depth += 1
            elif src[i] == ")": depth -= 1
            i += 1
        args = split_top(src[m.end():i - 1])
        if args and args[0].startswith('"'):
            yield args


def clean(s: str) -> str:
    return re.sub(r"§.", "", s.strip('"'))


@dataclass
class Dish:
    id: str
    name: str
    purpose: str
    tier: int
    sell: int = 0
    points: int = 0
    duration: int = 0
    stats: dict[str, float] = field(default_factory=dict)


def load_dishes() -> dict[str, Dish]:
    src = re.sub(r"//[^\n]*", "", SRC.read_text(encoding="utf-8"))
    out = {}
    stat_keys = ["exp", "size", "gradeup", "escape", "crit", "dbl", "sellBonus", "difficulty"]
    for a in calls("buff", src):
        try:
            nums = [float(x) for x in a[4:-1]]
            keys = stat_keys if len(nums[:-2]) == 8 else stat_keys[:-1]
            out[a[0].strip('"')] = Dish(a[0].strip('"'), clean(a[1]), "buff", int(a[3]),
                sell=int(nums[-1]), duration=int(nums[-2]),
                stats={k: v for k, v in zip(keys, nums[:-2]) if v})
        except (ValueError, IndexError):
            pass
    for purpose, fn in (("submit", "submit"), ("sell", "sell")):
        for a in calls(fn, src):
            try:
                did = a[0].strip('"')
                if purpose == "submit":
                    out[did] = Dish(did, clean(a[1]), purpose, int(a[3]), sell=int(a[5]), points=int(a[4]))
                else:
                    out[did] = Dish(did, clean(a[1]), purpose, int(a[3]), sell=int(a[4]), duration=int(a[5]))
            except (ValueError, IndexError):
                pass
    return out


def prod_shop() -> dict:
    cmd = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10", "-i", str(KEY),
           PROD, "cat " + REMOTE_SHOP]
    raw = subprocess.check_output(cmd, text=True, timeout=20)
    return json.loads(raw)


def prod_forage_nodes() -> dict:
    """운영 노드 구성에서 typeId별 노드 수를 읽는다(개별 플레이어 쿨다운의 공급량 분모)."""
    cmd = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10", "-i", str(KEY), PROD,
           "cat ~/mcserver/plugins/BlockShip/forage-nodes.json"]
    raw = subprocess.check_output(cmd, text=True, timeout=20)
    nodes = json.loads(raw)
    out = collections.Counter()
    for node in nodes.values():
        type_id = node.get("typeId") or node.get("type") or node.get("forageType")
        if type_id:
            out[type_id] += 1
    return dict(out)


def forage_node_values(forage: dict, node_counts: dict[str, int]) -> dict[str, float]:
    """희귀도 floor에 노드 밀도를 곱한다.

    모든 채집물이 같은 희귀도라는 이유만으로 같은 원가가 되는 오류를 막는다. 행동비는
    floor로 유지하고, 같은 희귀도 중앙 노드 수보다 희소한 종만 비례해 올린다. 노드가
    없는 종은 원가 0으로 숨기지 않고 호출자에게 unknown으로 남긴다.
    """
    by_rarity: dict[str, list[int]] = collections.defaultdict(list)
    for type_id, spec in forage.items():
        n = node_counts.get(type_id, 0)
        if n:
            by_rarity[spec.get("rarity", "흔함")].append(n)
    median = {rarity: sorted(ns)[len(ns) // 2] for rarity, ns in by_rarity.items()}
    out = {}
    for type_id, spec in forage.items():
        rarity, n = spec.get("rarity", "흔함"), node_counts.get(type_id, 0)
        if not n:
            continue
        floor = FORAGE_FLOOR[rarity]
        out["채집_" + spec.get("name", "").replace(" ", "")] = floor * max(1.0, median[rarity] / n)
    return out


def shop_sells(cfg: dict) -> dict[str, float]:
    out = {}
    for cat in cfg.get("categories", []):
        for item in cat.get("items", []):
            if item.get("mat") and item.get("sell") is not None:
                out[norm(item["mat"])] = float(item["sell"])
    return out


def lore_mat(recipe: dict) -> str | None:
    for line in (recipe.get("result") or {}).get("lore") or []:
        m = re.search(r"mat:([^&§\s]+)", line)
        if m: return m.group(1)
    return None


def source_recipe_overrides(recipes: dict) -> dict:
    """DishSpecs.java의 아직 부팅되지 않은 레시피도 분석할 수 있게 CK_*만 동기화한다."""
    src = re.sub(r"//[^\n]*", "", SRC.read_text(encoding="utf-8"))
    helper_kind = {"forage": "custom", "crop": "custom", "mat": "custom", "fish": "fish",
                   "dish": "dish", "herbAny": "herbany", "mushroomAny": "mushroomany"}
    for fn in ("buff", "submit", "sell"):
        for args in calls(fn, src):
            if not args:
                continue
            did, ing_src = args[0].strip('"'), args[-1]
            ingredients = []
            for helper, kind in helper_kind.items():
                for ing in calls(helper, ing_src):
                    try:
                        if helper == "forage":
                            key = "채집_" + ing[0].strip('"').replace(" ", "")
                        else:
                            key = ing[0].strip('"')
                        ingredients.append({"kind": kind, "typeOrMatId": key, "qty": int(ing[-1])})
                    except (ValueError, IndexError):
                        continue
            if ingredients:
                rec = dict(recipes.get("CK_" + did, {}))
                rec.update(id="CK_" + did, ingredients=ingredients)
                recipes[rec["id"]] = rec
    return recipes


@dataclass
class Cost:
    won: float = 0.0
    unknown: collections.Counter = field(default_factory=collections.Counter)
    terms: collections.Counter = field(default_factory=collections.Counter)

    def add(self, other: "Cost", n: int = 1) -> "Cost":
        self.won += other.won * n
        self.unknown.update({k: v * n for k, v in other.unknown.items()})
        self.terms.update({k: v * n for k, v in other.terms.items()})
        return self


class Model:
    def __init__(self, recipes: dict, dishes: dict, shop: dict, forage: dict, forage_values: dict[str, float], drops: dict):
        self.recipes, self.dishes, self.shop = recipes, dishes, shop
        self.by_mat = {m: r for r in recipes.values() if (m := lore_mat(r))}
        self.forage_rarity = {"채집_" + v.get("name", "").replace(" ", ""): v.get("rarity", "흔함")
                              for v in forage.values()}
        self.forage_values = forage_values
        self.drop = collections.defaultdict(float)
        for entries in drops.get("dropTables", {}).values():
            for e in entries:
                self.drop[e["matId"]] = max(self.drop[e["matId"]], float(e["chance"]) / 100.0)
        self.memo: dict[str, Cost] = {}
        self.stack: set[str] = set()

    def item(self, item: str, qty: int) -> Cost:
        p = self.shop.get(norm(item))
        if p is None:
            return Cost(unknown=collections.Counter({"바닐라:" + norm(item): qty}))
        return Cost(won=p * qty, terms=collections.Counter({"섬상점:" + norm(item): qty}))

    def material(self, mat: str, qty: int) -> Cost:
        if mat in CROP:
            return Cost(won=CROP[mat] * qty, terms=collections.Counter({mat: qty}))
        if mat in MATERIAL_ANCHOR:
            return Cost(won=MATERIAL_ANCHOR[mat] * qty, terms=collections.Counter({mat: qty}))
        if mat.startswith("채집_"):
            value = self.forage_values.get(mat)
            if value is None:
                return Cost(unknown=collections.Counter({mat: qty}))
            return Cost(won=value * qty, terms=collections.Counter({mat: qty}))
        if mat in self.by_mat:
            return self.recipe_cost(self.by_mat[mat]).scaled(qty)
        if mat in FISH_BASE:
            return Cost(won=FISH_BASE[mat] * FISH_SIZE * qty, terms=collections.Counter({mat + "등급물고기": qty}))
        if self.drop.get(mat):
            return Cost(won=(CATCH_WON / self.drop[mat]) * qty, terms=collections.Counter({mat: qty}))
        return Cost(unknown=collections.Counter({mat: qty}))

    def ingredient(self, ing: dict, child_transfer: bool = True) -> Cost:
        qty = int(ing.get("qty") or 1)
        kind, key = ing.get("kind"), ing.get("typeOrMatId", "")
        if kind == "item": return self.item(key, qty)
        if kind == "fish": return self.material(key, qty)
        if kind == "dish":
            d = self.dishes.get(key)
            r = self.recipes.get("CK_" + key)
            if not d or not r: return Cost(unknown=collections.Counter({"dish:" + key: qty}))
            c = self.recipe_cost(r)
            # 판매 완성품을 재료로 태우면 제작원가 대신 판매 선택지를 포기한다.
            if child_transfer and d.purpose == "sell": c.won = max(c.won, float(d.sell))
            return c.scaled(qty)
        return self.material(key, qty)

    def recipe_cost(self, recipe: dict) -> Cost:
        rid = recipe.get("id", "?")
        if rid in self.memo: return self.memo[rid].copy()
        if rid in self.stack: return Cost(unknown=collections.Counter({"순환:" + rid: 1}))
        self.stack.add(rid)
        c = Cost()
        for ing in recipe.get("ingredients") or []: c.add(self.ingredient(ing))
        self.stack.remove(rid); self.memo[rid] = c.copy()
        return c


def _copy(self): return Cost(self.won, self.unknown.copy(), self.terms.copy())
def _scaled(self, n): return Cost(self.won * n, collections.Counter({k:v*n for k,v in self.unknown.items()}), collections.Counter({k:v*n for k,v in self.terms.items()}))
Cost.copy, Cost.scaled = _copy, _scaled


def legacy_cost(recipe: dict, dishes: dict, forage: dict, drops: dict) -> Cost:
    """구 cooking_full_audit의 핵심 오독(압축농산물·dish=0)을 재현한다."""
    rarity = {"채집_" + v.get("name", "").replace(" ", ""): v.get("rarity", "흔함") for v in forage.values()}
    chance = collections.defaultdict(float)
    for entries in drops.get("dropTables", {}).values():
        for e in entries: chance[e["matId"]] = max(chance[e["matId"]], float(e["chance"]) / 100)
    c = Cost()
    for ing in recipe.get("ingredients") or []:
        q, k, v = int(ing.get("qty") or 1), ing.get("kind"), ing.get("typeOrMatId", "")
        if k == "dish": continue
        if k == "fish" or v in FISH_BASE: c.won += FISH_BASE.get(v, 0) * FISH_SIZE * q
        elif v in CROP: c.won += CROP[v] * q
        elif v.startswith("강화"): continue  # 이전 모델의 치명적 0원 처리
        elif v.startswith("채집_"): c.won += FORAGE_FLOOR[rarity.get(v, "흔함")] * q
        elif chance.get(v): c.won += (CATCH_WON / chance[v]) * q
        else: c.unknown[v] += q
    return c


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--shop-source", choices=("prod", "local"), default="prod")
    ap.add_argument("--recipe-source", choices=("runtime", "java"), default="java",
                    help="java는 DishSpecs.java 변경을 부팅 전에도 분석한다")
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()
    recipes = json.loads((DATA / "recipes.json").read_text(encoding="utf-8"))["recipes"]
    forage = json.loads((DATA / "forage-types.json").read_text(encoding="utf-8"))
    drops = json.loads((DATA / "materials.json").read_text(encoding="utf-8"))
    if args.recipe_source == "java":
        recipes = source_recipe_overrides(recipes)
    cfg = prod_shop() if args.shop_source == "prod" else json.loads((DATA / "shop-items.json").read_text(encoding="utf-8"))
    node_counts = prod_forage_nodes() if args.shop_source == "prod" else {
        type_id: 1 for type_id in forage  # local에는 노드 배치가 없으므로 희귀도 floor만 적용
    }
    forage_values = forage_node_values(forage, node_counts)
    shop = shop_sells(cfg); dishes = load_dishes(); model = Model(recipes, dishes, shop, forage, forage_values, drops)
    units, value_source = measured_buff_value()
    rows = []
    for did, d in dishes.items():
        r = recipes.get("CK_" + did)
        if not r: continue
        old, new = legacy_cost(r, dishes, forage, drops), model.recipe_cost(r)
        row = {"id": did, "name": d.name, "purpose": d.purpose, "tier": d.tier,
               "old_cost": round(old.won), "new_cost_floor": round(new.won),
               "added_floor": round(new.won - old.won), "unknown": dict(new.unknown),
               "stats": d.stats, "duration_s": d.duration, "sell": d.sell, "points": d.points}
        if d.purpose == "sell":
            row.update(roi=round(d.sell / new.won, 3) if new.won else None,
                       won_h=round(d.sell / (d.duration / 3600), 1) if d.duration else None)
        if d.purpose == "submit": row["pts_per_won"] = round(d.points / new.won, 4) if new.won else None
        if d.purpose == "buff":
            value = sum(units[k] * v for k, v in d.stats.items()) * d.duration / 3600.0
            row["buff_value"] = round(value)
            row["value_to_cost"] = round(value / new.won, 3) if new.won else None
        rows.append(row)
    rows.sort(key=lambda x: (x["purpose"], x["tier"], x["name"]))
    print(f"활성 섬상점 원재료 판매가: 밀 {shop.get('WHEAT')} · 코코아 {shop.get('COCOA_BEANS')} · 당근 {shop.get('CARROT')}")
    print(f"요리 {len(rows)}종 — 구모델 대비 추가 반영 원가 합계 {sum(r['added_floor'] for r in rows):,}원 (개별 레시피 합산; 공유 중간재 중복 포함)")
    for p in ("sell", "submit", "buff"):
        arr = [r for r in rows if r["purpose"] == p]
        print(f"\n[{p}] {len(arr)}종")
        for r in arr:
            extra = f" ROI {r.get('roi')}x · {r.get('won_h'):,.0f}원/h" if p == "sell" else (f" {r.get('pts_per_won')}점/원" if p == "submit" else "")
            unk = " ⚠" + ",".join(r["unknown"]) if r["unknown"] else ""
            print(f"  T{r['tier']} {r['name']:<16} 구 {r['old_cost']:>8,} → 신 {r['new_cost_floor']:>8,} (+{r['added_floor']:>8,}){extra}{unk}")
    payload = {"method": "DishSpecs/runtime recipes + prod island-shop sell opportunity + recursive dish/material cost",
               "recipe_source": args.recipe_source, "buff_value_source": value_source,
               "forage_node_counts": node_counts, "forage_values": forage_values, "rows": rows}
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\nJSON: {args.out}")

if __name__ == "__main__": main()
