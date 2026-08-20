#!/usr/bin/env python3
"""섬상점 농사 품목의 생산성·교차경제 감사.

바닐라 작물은 CropSpecs의 고정 성장시간을 쓰지 않고 random tick에 의존하므로,
성장 주기는 명시적인 운영 가정으로 둔다. 이 스크립트의 목적은 가격표를 같은
등급끼리 비교하는 것이 아니라, 같은 섬 슬롯 수에서 작물별 원/h와 낚시·작살
코호트의 원/h를 한 표에 놓는 것이다.

기본 기준:
  - 섬 농사 슬롯 32칸(현재 특수작물 최대 한도와 같은 비교 단위)
  - 스킬트리 보너스 0%인 기본 수확
  - 낚시와 작살 중 낮은 쪽(현재는 낚시)의 75%

성장시간은 서버 실측 telemetry가 쌓이면 --cycle-sec 인자로 대체하거나 이 표를
업데이트한다. 따라서 추천가는 "실측 전 운영안"이며, 실행할 때마다 현재 코드의
shop-items.json과 최신 코호트 스냅샷을 읽는다.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from cohort_sim import best_loadouts, latest_snapshot, load_catalog, load_snapshot


DEFAULT_SHOP = Path(
    "/Users/user/Library/Application Support/feather/player-server/servers/"
    "07de2d81-991a-47e2-b62d-06c0d1b5150a/plugins/BlockShip/shop-items.json"
)
DEFAULT_SLOTS = 32
DEFAULT_TARGET_RATIO = 0.75


@dataclass(frozen=True)
class CropModel:
    key: str
    label: str
    cycle_sec: int
    outputs: dict[str, float]
    # 한 사이클의 골드 중 각 출력물이 차지하는 비중. 수량이 여러 개인
    # 밀/비트는 원물 60%, 씨앗 40%로 두어 씨앗도 부산물로서 가치를 갖게 한다.
    value_share: dict[str, float]
    role_mult: float = 1.0


# randomTickSpeed=3, 충분한 광원/수분, 청크가 계속 로드된 밭의 보수적 운영 가정.
# 성숙 전환 이벤트가 없는 특수작물과 달리 실제 시간은 배치/청크/지형에 따라 달라진다.
MODELS = (
    CropModel("wheat", "밀", 600, {"WHEAT": 1.0, "WHEAT_SEEDS": 2.0},
              {"WHEAT": 0.60, "WHEAT_SEEDS": 0.40}),
    CropModel("carrot", "당근", 600, {"CARROT": 2.5}, {"CARROT": 1.0}),
    CropModel("potato", "감자", 600, {"POTATO": 2.45}, {"POTATO": 1.0}),
    CropModel("beetroot", "비트", 600, {"BEETROOT": 1.0, "BEETROOT_SEEDS": 2.0},
              {"BEETROOT": 0.60, "BEETROOT_SEEDS": 0.40}, role_mult=0.95),
    CropModel("melon", "수박", 900, {"MELON_SLICE": 4.5}, {"MELON_SLICE": 1.0}),
    CropModel("pumpkin", "호박", 900, {"PUMPKIN": 1.0}, {"PUMPKIN": 1.0}, role_mult=1.05),
    CropModel("sugar_cane", "사탕수수", 900, {"SUGAR_CANE": 2.0}, {"SUGAR_CANE": 1.0}, role_mult=0.90),
    CropModel("bamboo", "대나무", 300, {"BAMBOO": 3.0}, {"BAMBOO": 1.0}, role_mult=0.80),
    CropModel("cocoa", "코코아", 900, {"COCOA_BEANS": 2.5}, {"COCOA_BEANS": 1.0}),
)


def load_shop(path: Path) -> dict[str, dict[str, Any]]:
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    for category in data.get("categories", []):
        if category.get("key") == "농사":
            return {str(row.get("mat")): row for row in category.get("items", []) if row.get("mat")}
    raise SystemExit(f"농사 카테고리를 찾을 수 없습니다: {path}")


def anchor_rates(snapshot: dict[str, Any], level: int, region: str | None) -> tuple[float, float]:
    catalog = load_catalog(snapshot)
    top = best_loadouts(snapshot, catalog, level, goal="money", region=region, limit=1)
    rod = float(top["rod"][0]["money_per_hour"]) if top.get("rod") else 0.0
    harpoon = float(top["harpoon"][0]["money_per_hour"]) if top.get("harpoon") else 0.0
    if not rod or not harpoon:
        raise SystemExit("낚시/작살 코호트 기준선을 계산하지 못했습니다.")
    return rod, harpoon


def recommended_prices(model: CropModel, target_slot_hour: float) -> dict[str, int]:
    cycle_value = target_slot_hour * model.role_mult * model.cycle_sec / 3600.0
    out: dict[str, int] = {}
    for material, qty in model.outputs.items():
        share = model.value_share.get(material, 0.0)
        out[material] = max(1, int(round(cycle_value * share / qty)))
    return out


def model_row(model: CropModel, shop: dict[str, dict[str, Any]], target_slot_hour: float) -> dict[str, Any]:
    current_prices = {mat: int(shop.get(mat, {}).get("sell", 0)) for mat in model.outputs}
    current_missing = [mat for mat in model.outputs if mat not in shop]
    current_cycle = sum(qty * current_prices.get(mat, 0) for mat, qty in model.outputs.items())
    current_hour = current_cycle * 3600.0 / model.cycle_sec
    rec = recommended_prices(model, target_slot_hour)
    rec_cycle = sum(qty * rec[mat] for mat, qty in model.outputs.items())
    rec_hour = rec_cycle * 3600.0 / model.cycle_sec
    return {
        "key": model.key,
        "label": model.label,
        "cycle_sec": model.cycle_sec,
        "outputs": model.outputs,
        "current_sell": current_prices,
        "missing_sell_items": current_missing,
        "current_won_per_slot_h": round(current_hour, 2),
        "recommended_sell": rec,
        "recommended_won_per_slot_h": round(rec_hour, 2),
        "role_mult": model.role_mult,
    }


def print_report(report: dict[str, Any]) -> None:
    print("=== 섬상점 농사 교차경제 감사 ===")
    print(
        f"기준: Lv{report['level']} 최적 낚시 {report['rod_won_per_hour']:,.0f}원/h, "
        f"작살 {report['harpoon_won_per_hour']:,.0f}원/h"
    )
    print(
        f"목표: 낮은 기준({report['anchor_won_per_hour']:,.0f}원/h)의 "
        f"{report['target_ratio']:.0%} = {report['target_farm_won_per_hour']:,.0f}원/h "
        f"({report['slots']}칸, 슬롯당 {report['target_slot_won_per_hour']:,.0f}원/h)"
    )
    print("작물 | 가정 cycle | 현재 원/h/칸 | 추천 원/h/칸 | 현재 판매가 → 추천 판매가")
    print("-" * 122)
    for row in report["crops"]:
        current = row["current_sell"]
        recommended = row["recommended_sell"]
        price_text = ", ".join(
            f"{mat} {current.get(mat, 0)}→{recommended[mat]}" for mat in recommended
        )
        missing = " [판매품목 없음: " + ",".join(row["missing_sell_items"]) + "]" if row["missing_sell_items"] else ""
        print(
            f"{row['label']:<5} | {row['cycle_sec']/60:>4.0f}분      | "
            f"{row['current_won_per_slot_h']:>10,.0f} | {row['recommended_won_per_slot_h']:>11,.0f} | "
            f"{price_text}{missing}"
        )
    print("\n※ 추천가는 스킬트리 보너스와 청크 비활성 시간을 제외한 실측 전 운영안입니다.")
    print("※ 작살 75%를 농사 목표로 삼으려면 위 가격을 별도로 약 "
          f"{report['harpoon_won_per_hour']/report['anchor_won_per_hour']:.2f}배 해야 합니다.")


def main() -> None:
    parser = argparse.ArgumentParser(description="섬상점 농사 품목/낚시/작살 수익 비교")
    parser.add_argument("--shop", default=str(DEFAULT_SHOP))
    parser.add_argument("--snapshot", default=None)
    parser.add_argument("--level", type=int, default=1)
    parser.add_argument("--region", default=None)
    parser.add_argument("--slots", type=int, default=DEFAULT_SLOTS)
    parser.add_argument("--target-ratio", type=float, default=DEFAULT_TARGET_RATIO)
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()

    snapshot = load_snapshot(args.snapshot)
    shop = load_shop(Path(args.shop))
    rod, harpoon = anchor_rates(snapshot, args.level, args.region)
    anchor = min(rod, harpoon)
    target_total = anchor * args.target_ratio
    target_slot = target_total / max(1, args.slots)
    crops = [model_row(model, shop, target_slot) for model in MODELS]
    report = {
        "level": args.level,
        "region": args.region,
        "slots": args.slots,
        "target_ratio": args.target_ratio,
        "rod_won_per_hour": round(rod, 2),
        "harpoon_won_per_hour": round(harpoon, 2),
        "anchor_kind": "lower_of_rod_harpoon",
        "anchor_won_per_hour": round(anchor, 2),
        "target_farm_won_per_hour": round(target_total, 2),
        "target_slot_won_per_hour": round(target_slot, 2),
        "shop_path": str(Path(args.shop)),
        "assumptions": {
            "random_tick_speed": 3,
            "loaded_chunk": True,
            "skill_bonus_multiplier": 1.0,
            "normal_farm_slots": args.slots,
        },
        "crops": crops,
    }
    if args.as_json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print_report(report)


if __name__ == "__main__":
    main()
