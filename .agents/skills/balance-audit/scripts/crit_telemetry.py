#!/usr/bin/env python3
"""Measure realised fishing-critical behaviour from read-only telemetry SQLite files.

The fishing minigame rolls a gold cell *per zone cell*, then the player chooses whether
to hit it.  Therefore ``st.crit`` is not a catch-level critical rate.  This tool keeps
those layers separate and, importantly, refuses to call a thin or single-player slice
generalisable evidence.

It reads only ``events-YYYY-MM.db`` files and emits aggregates: no player names, UUIDs,
or individual results are written to stdout or the optional JSON artifact.
"""
from __future__ import annotations

import argparse
import json
import math
import sqlite3
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path


VALID_RESULTS = {"성공", "크리티컬"}
BANDS = ((0, 0), (1, 5), (6, 10), (11, 15), (16, 20), (21, 30),
         (31, 45), (46, 60), (61, 80), (81, 1000))
# FishItem.fishPrice current grade bases. These are deliberately pre-critical and
# pre-sell-bonus so the metric below cannot be inflated by a separate sell stat.
GRADE_BASE_PRICE = {"E": 100, "D": 250, "C": 600, "B": 2000, "A": 6000,
                    "S": 20000, "M": 65000, "L": 170000, "G": 450000}
KST = timezone(timedelta(hours=9))


def wilson(successes: int, total: int) -> tuple[float | None, float | None]:
    """95% Wilson interval; robust for low counts unlike a normal approximation."""
    if total == 0:
        return None, None
    z = 1.959963984540054
    p = successes / total
    denom = 1 + z * z / total
    centre = (p + z * z / (2 * total)) / denom
    half = z * math.sqrt((p * (1 - p) + z * z / (4 * total)) / total) / denom
    return max(0.0, centre - half), min(1.0, centre + half)


def evidence_level(total: int, players: int) -> str:
    if total >= 100 and players >= 3:
        return "측정 가능"
    if total >= 30 and players >= 2:
        return "참고만"
    return "표본 부족"


def band_name(lo: int, hi: int) -> str:
    return f"{lo}%" if lo == hi else (f"{lo}%+" if hi >= 1000 else f"{lo}–{hi}%")


def open_read_only(path: Path) -> sqlite3.Connection:
    return sqlite3.connect(f"file:{path.absolute()}?mode=ro", uri=True)


def epoch_kst(date_text: str) -> int:
    """Start of YYYY-MM-DD in KST, returned in telemetry's millisecond epoch."""
    return int(datetime.strptime(date_text, "%Y-%m-%d").replace(tzinfo=KST).timestamp() * 1000)


def base_fish_price(grade: str, quality: float) -> int | None:
    """FishItem.fishPrice: base × (0.5 + quality × 0.5 / 100), rounded down."""
    if grade not in GRADE_BASE_PRICE:
        return None
    return math.floor(GRADE_BASE_PRICE[grade] * (0.5 + max(0.0, quality) * 0.5 / 100.0))


def main() -> None:
    parser = argparse.ArgumentParser(description="fish.result / fish.macro 기반 크리 실현율 측정")
    parser.add_argument("--telemetry-dir", type=Path,
                        default=Path.cwd().parents[1] / "BlockShip" / "telemetry",
                        help="events-YYYY-MM.db가 있는 디렉터리")
    parser.add_argument("--db", type=Path, action="append", default=[],
                        help="개별 events DB (여러 번 지정 가능; telemetry-dir보다 우선)")
    parser.add_argument("--hook", help="특정 바늘 이름만 측정(로드아웃에 없는 결과는 제외)")
    parser.add_argument("--revenue-since", default="2026-09-13",
                        help="현행 직접 판매보너스 크리 체계가 적용된 KST 날짜 (기본: 2026-09-13)")
    parser.add_argument("--out", type=Path, help="집계 JSON 출력 경로(선택)")
    args = parser.parse_args()

    files = sorted(args.db) if args.db else sorted(args.telemetry_dir.glob("events-*.db"))
    if not files:
        parser.error("읽을 events-YYYY-MM.db가 없습니다. --telemetry-dir 또는 --db를 지정하세요.")
    try:
        revenue_epoch = epoch_kst(args.revenue_since)
    except ValueError:
        parser.error("--revenue-since는 YYYY-MM-DD 형식이어야 합니다.")

    # chance -> [valid catches, realised crits, players]
    exact: dict[int, list] = defaultdict(lambda: [0, 0, set()])
    macro = [0, 0.0, 0.0, set()]  # snapshots, gold opportunities, estimated gold hits, players
    # current-reward-era only: catches, pre-bonus base sales, crit's exact pre-bonus increment, players
    revenue = [0, 0, 0, set()]
    revenue_by_chance: dict[int, list[int]] = defaultdict(lambda: [0, 0, 0])
    valid, malformed = 0, 0
    file_summary = []

    for path in files:
        con = None
        try:
            con = open_read_only(path)
            rows = con.execute("SELECT ts, uuid, ctx FROM ev WHERE type='fish.result'").fetchall()
            macro_rows = con.execute("SELECT uuid, ctx FROM ev WHERE type='fish.macro'").fetchall()
            loadouts = {}
            for loadout_hash, payload in con.execute("SELECT hash, json FROM loadout"):
                try:
                    loadouts[loadout_hash] = json.loads(payload).get("parts", {}).get("바늘")
                except (TypeError, json.JSONDecodeError):
                    continue
        except sqlite3.Error as exc:
            print(f"경고: {path.name} 건너뜀 ({exc})")
            continue
        finally:
            if con is not None:
                con.close()

        file_valid = 0
        for ts, uuid, text in rows:
            try:
                ctx = json.loads(text)
                if ctx.get("res") not in VALID_RESULTS:
                    continue
                chance = int(ctx["st"]["crit"])
                critical = int(ctx.get("crit", 0)) == 1
                if args.hook and loadouts.get(ctx.get("lo")) != args.hook:
                    continue
            except (KeyError, TypeError, ValueError, json.JSONDecodeError):
                malformed += 1
                continue
            valid += 1
            file_valid += 1
            exact[chance][0] += 1
            exact[chance][1] += int(critical)
            exact[chance][2].add(uuid)

            # Current valuation: rebuild the fish's price before *both* critical and
            # sell bonus.  This makes "equivalent sell bonus" an intrinsic value;
            # a player's unrelated sale bonus cannot make critical look stronger.
            if ts >= revenue_epoch:
                try:
                    base = base_fish_price(str(ctx["g"]), float(ctx["q"]))
                    if base is None:
                        continue
                    damage = int(ctx["critd"]) if critical else 0
                except (KeyError, TypeError, ValueError):
                    continue
                increment = math.floor(base * (1.0 + damage * 0.06)) - base if critical else 0
                revenue[0] += 1
                revenue[1] += base
                revenue[2] += increment
                revenue[3].add(uuid)
                revenue_by_chance[chance][0] += 1
                revenue_by_chance[chance][1] += base
                revenue_by_chance[chance][2] += increment

        # Macro snapshots contain neither loadout nor nominal chance, so a hook-level
        # query must not accidentally claim their all-player conversion as this hook's.
        for uuid, text in (macro_rows if not args.hook else ()):
            try:
                ctx = json.loads(text)
                opportunities = float(ctx.get("gold_n", 0))
                conversion = float(ctx.get("gold_conv", 0))
                if opportunities <= 0:
                    continue
            except (TypeError, ValueError, json.JSONDecodeError):
                continue
            macro[0] += 1
            macro[1] += opportunities
            macro[2] += opportunities * conversion
            macro[3].add(uuid)
        file_summary.append({"file": path.name, "valid_catches": file_valid})

    def row(label: str, values: list) -> dict:
        total, criticals, players = values[0], values[1], len(values[2])
        low, high = wilson(criticals, total)
        return {
            "nominal_cell_chance": label,
            "catches": total,
            "players": players,
            "criticals": criticals,
            "realised_crit_rate": round(criticals / total, 5) if total else None,
            "ci95": [round(low, 5), round(high, 5)] if low is not None else None,
            "evidence": evidence_level(total, players),
        }

    exact_rows = [row(f"{chance}%", values) for chance, values in sorted(exact.items())]
    band_rows = []
    for lo, hi in BANDS:
        merged = [0, 0, set()]
        for chance, values in exact.items():
            if lo <= chance <= hi:
                merged[0] += values[0]
                merged[1] += values[1]
                merged[2].update(values[2])
        if merged[0]:
            band_rows.append(row(band_name(lo, hi), merged))

    macro_opps, macro_players = macro[1], len(macro[3])
    macro_evidence = evidence_level(int(macro_opps), macro_players)

    def revenue_row(label: str, values: list[int]) -> dict:
        catches, base, increment = values
        return {
            "nominal_cell_chance": label,
            "catches": catches,
            "pre_bonus_base_won": base,
            "critical_increment_won": increment,
            "extra_won_per_catch": round(increment / catches, 3) if catches else None,
            "equivalent_sell_bonus_pct": round(100 * increment / base, 4) if base else None,
        }

    revenue_rows = [revenue_row(f"{chance}%", values)
                    for chance, values in sorted(revenue_by_chance.items())]
    revenue_evidence = ("측정 가능" if revenue[0] >= 100 and len(revenue[3]) >= 3
                        else "표본 부족")
    result = {
        "schema": 1,
        "filter": {"hook": args.hook} if args.hook else {},
        "files": file_summary,
        "valid_catches": valid,
        "malformed_or_missing_stat": malformed,
        "unique_players": len(set().union(*(v[2] for v in exact.values()))) if exact else 0,
        "critical_model": {
            "nominal_stat_meaning": "미니게임 존의 각 칸에 독립 적용되는 금칸 생성확률",
            "required_layers": ["금칸 존재율", "금칸이 있을 때 조준 전환율", "결과 크리율", "크리 보상 프리미엄"],
            "historical_limit": "fish.result에는 금칸 존재/존폭이 없어, 과거 자료만으로 첫 두 층을 장비별로 분해할 수 없음",
        },
        "realised_rate_by_exact_chance": exact_rows,
        "realised_rate_by_chance_band": band_rows,
        "macro_gold_conversion": {
            "snapshots": macro[0], "gold_opportunities": round(macro_opps, 3),
            "estimated_gold_hits": round(macro[2], 3), "players": macro_players,
            "conversion": round(macro[2] / macro_opps, 5) if macro_opps else None,
            "evidence": macro_evidence,
            "limit": ("바늘 필터에서는 macro에 loadout이 없어 사용할 수 없음" if args.hook else
                      "20판 요약이며 loadout/명목크확/존폭과 결합되지 않아 장비별 인과 추정에는 사용 불가"),
        },
        "outcome_premium_diagnostics": {
            "available": False,
            "reason": "현재 fish.result는 critd를 크리 결과에만 기록해 같은 빌드의 비크리 대조군을 만들 수 없다. "
                      "보상 프리미엄은 코드 공식(판매 +6d%, XP +10d%)을 사용한다.",
        },
        "sale_value_excluding_sell_bonus": {
            "mechanics_epoch_kst": args.revenue_since,
            "formula": "Σ[floor(base_price × (1 + 0.06 × crit_damage)) - base_price for critical catches] / Σ base_price",
            "meaning": "판매보너스·신선도 이전의 등급×품질 기본가만 분모로 쓰므로, 결과는 판매보너스와 직접 비교 가능한 등가 %다.",
            "catches": revenue[0], "pre_bonus_base_won": revenue[1],
            "critical_increment_won": revenue[2],
            "players": len(revenue[3]),
            "extra_won_per_catch": round(revenue[2] / revenue[0], 3) if revenue[0] else None,
            "equivalent_sell_bonus_pct": round(100 * revenue[2] / revenue[1], 4) if revenue[1] else None,
            "evidence": revenue_evidence,
            "by_exact_nominal_chance": revenue_rows,
            "limit": ("현행 직접 판매보너스 크리 체계 이후 fish.result가 없어 수익 등가치는 미측정. "
                      "이전 체계의 price/critd는 현재 공식과 섞지 않는다." if not revenue[0] else
                      "이 값은 실제 발생한 크리와 최종 크리배율의 묶음 가치다. 명목 크확 1점의 한계가치는 별도 계측이 필요하다."),
        },
        "verdict": {
            "realised_crit_rate": "측정 가능" if valid >= 500 and len(set().union(*(v[2] for v in exact.values()))) >= 5 else "표본 부족",
            "gold_opportunity_and_aim_split": macro_evidence,
            "allowed_for_balance": "실현 크리율은 구간·표본·신뢰구간을 함께 보고 사용. 금칸 발생/조준 전환의 장비별 값은 신규 계측 전 미판정.",
        },
    }

    print(f"유효 낚시결과 {valid:,}건 · 플레이어 {result['unique_players']}명 · 누락/파싱제외 {malformed}건")
    print("\n[명목 크확별 실제 크리율]")
    print("명목칸확률  결과수  유저  실제크리율 (95% CI)       판정")
    for item in exact_rows:
        ci = item["ci95"]
        print(f"{item['nominal_cell_chance']:>10} {item['catches']:>6} {item['players']:>5} "
              f"{item['realised_crit_rate'] * 100:>8.1f}% ({ci[0] * 100:>4.1f}–{ci[1] * 100:>4.1f}) {item['evidence']}")
    print("\n[금칸 조준 전환 — macro 스냅샷]")
    conversion = result["macro_gold_conversion"]["conversion"]
    print(f"스냅샷 {macro[0]} · 금칸기회 {macro_opps:.0f} · 전환 "
          f"{conversion * 100:.1f}%" if conversion is not None else "데이터 없음")
    print(f"판정: {macro_evidence}. {result['macro_gold_conversion']['limit']}")
    sales = result["sale_value_excluding_sell_bonus"]
    print("\n[판매보너스 제외 크리 수익 등가치]")
    if sales["catches"]:
        print(f"현행 체계 {args.revenue_since} 이후 {sales['catches']}캐치: "
              f"기본가 대비 +{sales['equivalent_sell_bonus_pct']:.2f}% "
              f"({sales['extra_won_per_catch']:.1f}원/캐치)")
    else:
        print(f"현행 체계 {args.revenue_since} 이후 유효 캐치 0건 — 수익 등가치 미측정")

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"\n집계 저장: {args.out}")


if __name__ == "__main__":
    main()
