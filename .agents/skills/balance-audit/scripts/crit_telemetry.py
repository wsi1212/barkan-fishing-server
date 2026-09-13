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
from pathlib import Path


VALID_RESULTS = {"성공", "크리티컬"}
BANDS = ((0, 0), (1, 5), (6, 10), (11, 15), (16, 20), (21, 30),
         (31, 45), (46, 60), (61, 80), (81, 1000))


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


def main() -> None:
    parser = argparse.ArgumentParser(description="fish.result / fish.macro 기반 크리 실현율 측정")
    parser.add_argument("--telemetry-dir", type=Path,
                        default=Path.cwd().parents[1] / "BlockShip" / "telemetry",
                        help="events-YYYY-MM.db가 있는 디렉터리")
    parser.add_argument("--db", type=Path, action="append", default=[],
                        help="개별 events DB (여러 번 지정 가능; telemetry-dir보다 우선)")
    parser.add_argument("--hook", help="특정 바늘 이름만 측정(로드아웃에 없는 결과는 제외)")
    parser.add_argument("--out", type=Path, help="집계 JSON 출력 경로(선택)")
    args = parser.parse_args()

    files = sorted(args.db) if args.db else sorted(args.telemetry_dir.glob("events-*.db"))
    if not files:
        parser.error("읽을 events-YYYY-MM.db가 없습니다. --telemetry-dir 또는 --db를 지정하세요.")

    # chance -> [valid catches, realised crits, players]
    exact: dict[int, list] = defaultdict(lambda: [0, 0, set()])
    macro = [0, 0.0, 0.0, set()]  # snapshots, gold opportunities, estimated gold hits, players
    valid, malformed = 0, 0
    file_summary = []

    for path in files:
        try:
            con = open_read_only(path)
            rows = con.execute("SELECT uuid, ctx FROM ev WHERE type='fish.result'").fetchall()
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
            try:
                con.close()
            except UnboundLocalError:
                pass

        file_valid = 0
        for uuid, text in rows:
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

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"\n집계 저장: {args.out}")


if __name__ == "__main__":
    main()
