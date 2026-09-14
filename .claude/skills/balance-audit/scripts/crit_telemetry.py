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
import os
import shlex
import sqlite3
import subprocess
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

# ★기본 소스는 prod 캐시다.  맥(dev) 의 plugins/BlockShip/telemetry 는 부분 미러라
#   2026-09-14 실측으로 4,514캐치·16명(09-05 까지)뿐이었고 같은 시각 prod 는 80,208캐치·239명이었다.
#   그 미러를 읽은 09-13 감사가 "현행 체계 표본 0건 — 미측정" 으로 끝났다.
#   캐시 채우기:  python3 pull_players.py      (scp 로 prod events-*.db 를 내려받는다)
CACHE = Path(__file__).resolve().parent.parent / "audits" / "telemetry-cache"


VALID_RESULTS = {"성공", "크리티컬"}
BANDS = ((0, 0), (1, 5), (6, 10), (11, 15), (16, 20), (21, 30),
         (31, 45), (46, 60), (61, 80), (81, 1000))
# FishItem.fishPrice current grade bases. These are deliberately pre-critical and
# pre-sell-bonus so the metric below cannot be inflated by a separate sell stat.
GRADE_BASE_PRICE = {"E": 100, "D": 250, "C": 600, "B": 2000, "A": 6000,
                    "S": 20000, "M": 65000, "L": 170000, "G": 450000}
KST = timezone(timedelta(hours=9))


# ── 명목 크확 → 실현 크리율 (단일 권위) ──────────────────────────────────────
# ★`크리확률 20` 을 «캐치의 20%» 로 읽으면 안 된다.  금칸은 존의 칸마다 굴러가고 사람이 그걸
#   조준해야 하므로 실현치는 명목보다 훨씬 높다 — 명목 20% 의 실측 실현 크리율은 45.7% 다.
#   아래는 prod 실측 65,947캐치·56구간에 최대우도 적합한 «관측» 반응곡선이다(메커니즘 주장 아님).
#       r(p) = ceiling × (1 − (1−p)^cells)
#   cells 2.9 = 캐치당 «실효» 금칸 기회 수(존폭 그 자체가 아니라 조준까지 반영된 유효값),
#   ceiling 0.90 = 전 칸이 금칸일 때조차 남는 존 이탈·타임아웃 손실.
#   ★값을 손으로 고치지 말 것 — `fit_realised_curve()` 로 다시 뽑는다.
REALISED_FIT = {
    "ceiling": 0.900,
    "cells": 2.9,
    "fitted_on": "prod events-2026-08/09, 2026-09-14",
    "n_catches": 65947,
    "n_bands": 56,
}


def realised_from_nominal(nominal_pct: float, fit: dict | None = None) -> float:
    """명목 크확(%) → 실현 크리율(0~1).  크리 수입을 재는 모든 스크립트가 이 함수만 쓴다."""
    f = fit or REALISED_FIT
    p = max(0.0, min(100.0, float(nominal_pct))) / 100.0
    return f["ceiling"] * (1.0 - (1.0 - p) ** f["cells"])


def fit_realised_curve(paths, min_n: int = 50) -> dict:
    """반응곡선을 텔레메트리에서 다시 적합한다(REALISED_FIT 갱신용).  격자 최대우도."""
    pts: dict[int, list[int]] = defaultdict(lambda: [0, 0])
    for path in paths:
        con = open_read_only(Path(path))
        try:
            for (text,) in con.execute("SELECT ctx FROM ev WHERE type='fish.result'"):
                try:
                    ctx = json.loads(text)
                    if ctx.get("res") not in VALID_RESULTS:
                        continue
                    nominal = int(ctx["st"]["crit"])
                except (KeyError, TypeError, ValueError, json.JSONDecodeError):
                    continue
                if not 0 < nominal <= 100:
                    continue
                pts[nominal][0] += 1
                pts[nominal][1] += int(int(ctx.get("crit", 0)) == 1)
        finally:
            con.close()
    data = [(k, v[0], v[1]) for k, v in sorted(pts.items()) if v[0] >= min_n]
    if not data:
        return dict(REALISED_FIT, n_catches=0, n_bands=0, note="표본 부족 — 적합 불가")
    best = None
    for cells10 in range(10, 1201):
        cells = cells10 / 10
        for ceil100 in range(20, 101):
            ceiling = ceil100 / 100
            ll = 0.0
            for nominal, n, k in data:
                q = min(max(ceiling * (1 - (1 - nominal / 100) ** cells), 1e-6), 1 - 1e-6)
                ll += k * math.log(q) + (n - k) * math.log(1 - q)
            if best is None or ll > best[0]:
                best = (ll, cells, ceiling)
    _, cells, ceiling = best
    return {"ceiling": ceiling, "cells": cells, "n_catches": sum(d[1] for d in data),
            "n_bands": len(data), "fitted_on": "refit"}


# ── prod 원격 집계 ───────────────────────────────────────────────────────────
# ★DB 를 내려받지 않는다.  2026-09-14 기준 prod `events-2026-09.db` 만 698 MB 이고 하루 ~50 MB 씩
#   큰다 — `pull_players.py --fetch` 식 scp 는 이제 유지되지 않는다.  이 스크립트 자신을 박스에
#   올려 거기서 집계하고 **JSON 만** 가져온다.  라이브 WAL 이지만 `mode=ro` 로 그대로 읽힌다.
PROD_HOST = os.environ.get("BALANCE_PROD_HOST", "ubuntu@168.107.8.107")
PROD_KEY = os.environ.get("BALANCE_PROD_KEY", os.path.expanduser("~/.ssh/oracle-mc.key"))
PROD_TELEMETRY = "~/mcserver/plugins/BlockShip/telemetry"
PROD_WORKDIR = "~/crit-audit"


def remote_constants(revenue_since: str = "2026-09-13", months: int = 2) -> dict:
    """prod 박스에서 직접 집계해 상수 JSON 만 받아온다."""
    me = Path(__file__).resolve()
    scp = ["scp", "-q", "-o", "ConnectTimeout=20", "-i", PROD_KEY,
           str(me), f"{PROD_HOST}:{PROD_WORKDIR}/crit_telemetry.py"]
    mk = ["ssh", "-o", "ConnectTimeout=20", "-i", PROD_KEY, PROD_HOST,
          f"mkdir -p {PROD_WORKDIR}/run"]
    r = subprocess.run(mk, capture_output=True, text=True)
    if r.returncode:
        return {"evidence": "원격 실패", "error": r.stderr.strip()[:300]}
    r = subprocess.run(scp, capture_output=True, text=True)
    if r.returncode:
        return {"evidence": "원격 실패", "error": r.stderr.strip()[:300]}
    # ★`run/` 하위에서 돌린다 — 얕은 경로면 기본 인자의 Path.cwd().parents[1] 가 IndexError 를 낸다.
    #   그리고 박스 /tmp 에는 다른 작업이 둔 inspect.py 가 있어 표준 라이브러리를 가린다.
    dbs = " ".join(f"--db {PROD_TELEMETRY}/events-2026-{m:02d}.db"
                   for m in _recent_months(months))
    cmd = (f"cd {PROD_WORKDIR}/run && python3 ../crit_telemetry.py --json-constants "
           f"--revenue-since {shlex.quote(revenue_since)} {dbs}")
    r = subprocess.run(["ssh", "-o", "ConnectTimeout=20", "-i", PROD_KEY, PROD_HOST, cmd],
                       capture_output=True, text=True)
    if r.returncode:
        return {"evidence": "원격 실패", "error": (r.stderr or r.stdout).strip()[:300]}
    try:
        out = json.loads(r.stdout)
    except json.JSONDecodeError:
        return {"evidence": "원격 실패", "error": r.stdout.strip()[:300]}
    out["_source"] = f"prod {PROD_HOST} ({datetime.now(KST):%Y-%m-%d %H:%M} KST)"
    return out


def _recent_months(count: int) -> list[int]:
    now = datetime.now(KST)
    return sorted({(now - timedelta(days=31 * i)).month for i in range(count)})


def crit_constants(paths, revenue_since: str = "2026-09-13") -> dict:
    """`measured.py` 가 가져가는 압축 상수.  개수가중·금액가중을 **둘 다** 낸다.

    ★SB-eq 항등식 `r × d × 6%` 는 **금액가중**일 때만 성립한다.  크리배율이 높은 빌드가 비싼
      물고기를 잡기 때문에 개수평균 배율(8.23)과 금액가중 배율(9.77)이 다르고, 개수가중으로
      손계산하면 크리 가치를 약 17% 과소평가한다(2026-09-14 prod 실측).
    """
    epoch = epoch_kst(revenue_since)
    n = k = 0
    base_all = base_crit = 0
    dmg_n = dmg_w = 0
    inc = 0
    players: set = set()
    macro_opp = macro_hit = 0.0
    for path in paths:
        con = open_read_only(Path(path))
        try:
            rows = con.execute("SELECT ts, uuid, ctx FROM ev WHERE type='fish.result'").fetchall()
            macro_rows = con.execute("SELECT ctx FROM ev WHERE type='fish.macro'").fetchall()
        except sqlite3.Error:
            con.close()
            continue
        con.close()
        for ts, uuid, text in rows:
            if ts < epoch:
                continue
            try:
                ctx = json.loads(text)
                if ctx.get("res") not in VALID_RESULTS:
                    continue
                base = base_fish_price(str(ctx["g"]), float(ctx["q"]))
                if base is None:
                    continue
                crit = int(ctx.get("crit", 0)) == 1
                dmg = int(ctx["critd"]) if crit else 0
            except (KeyError, TypeError, ValueError, json.JSONDecodeError):
                continue
            n += 1
            base_all += base
            players.add(uuid)
            if crit:
                k += 1
                base_crit += base
                dmg_n += dmg
                dmg_w += dmg * base
                inc += math.floor(base * (1.0 + dmg * 0.06)) - base
        for (text,) in macro_rows:
            try:
                ctx = json.loads(text)
                opp = float(ctx.get("gold_n", 0))
                if opp <= 0:
                    continue
                macro_hit += opp * float(ctx.get("gold_conv", 0))
                macro_opp += opp
            except (TypeError, ValueError, json.JSONDecodeError):
                continue
    if not n:
        return {"evidence": "표본 없음", "catches": 0, "era_kst": revenue_since}
    return {
        "era_kst": revenue_since,
        "catches": n, "criticals": k, "players": len(players),
        "realised_rate": round(k / n, 5),
        "realised_rate_value_weighted": round(base_crit / base_all, 5) if base_all else None,
        "crit_damage_mean": round(dmg_n / k, 3) if k else None,
        "crit_damage_value_weighted": round(dmg_w / base_crit, 3) if base_crit else None,
        "sb_eq_pct": round(100 * inc / base_all, 4) if base_all else None,
        "extra_won_per_catch": round(inc / n, 3),
        "aim_conversion": round(macro_hit / macro_opp, 5) if macro_opp else None,
        "aim_opportunities": round(macro_opp, 1),
        "evidence": "측정 가능" if (n >= 100 and len(players) >= 3) else "표본 부족",
    }


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
    parser.add_argument("--telemetry-dir", type=Path, default=CACHE,
                        help=f"events-YYYY-MM.db가 있는 디렉터리 (기본: prod 캐시 {CACHE})")
    parser.add_argument("--db", type=Path, action="append", default=[],
                        help="개별 events DB (여러 번 지정 가능; telemetry-dir보다 우선)")
    parser.add_argument("--hook", help="특정 바늘 이름만 측정(로드아웃에 없는 결과는 제외)")
    parser.add_argument("--revenue-since", default="2026-09-13",
                        help="현행 직접 판매보너스 크리 체계가 적용된 KST 날짜 (기본: 2026-09-13)")
    parser.add_argument("--out", type=Path, help="집계 JSON 출력 경로(선택)")
    parser.add_argument("--json-constants", action="store_true",
                        help="measured.py 용 상수 JSON 만 stdout 으로 (다른 출력 없음)")
    parser.add_argument("--remote", action="store_true",
                        help="prod 박스에서 집계해 상수 JSON 만 받아온다 (DB 를 내려받지 않음)")
    args = parser.parse_args()

    if args.remote:
        print(json.dumps(remote_constants(args.revenue_since), ensure_ascii=False, indent=2))
        return

    files = sorted(args.db) if args.db else sorted(args.telemetry_dir.glob("events-*.db"))
    if not files:
        parser.error("읽을 events-YYYY-MM.db가 없습니다. --telemetry-dir 또는 --db를 지정하세요.")

    if args.json_constants:
        print(json.dumps(crit_constants(files, args.revenue_since), ensure_ascii=False))
        return
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
