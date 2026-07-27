#!/usr/bin/env python3
"""
stats-lab/queries.py — 텔레메트리 쿼리 쿡북 (stats-system-plan.md §10-3, Q1~Q9).

data/stats-latest.db(export/VACUUM INTO 사본) + data/events-YYYY-MM.db(월별 원본)를 읽는다.
쓰기는 하지 않음(read-only 취급 — sqlite3 모듈로 그냥 열되 SELECT만 실행).

CLI:
    python3 queries.py <c1|c2|...|c9> [--months 2026-07,2026-08] [--json]

다른 스크립트(report.py, 향후 statsweb)가 이 모듈의 함수를 그대로 import해서 쓴다 —
쿼리 정의는 이 파일 한 곳에만 존재(§10-5 "쿼리는 웹과 CLI가 공유").
"""
import argparse
import json
import os
import sqlite3
import sys

def _default_data_dir():
    # statsweb(§10-5)은 박스 위에서 실제 telemetry/ 폴더를 직접 가리키도록 이 값을 오버라이드해서
    # import한다(STATSLAB_DATA_DIR 환경변수 또는 set_data_dir() 호출) — CLI는 pull.sh가 받아온
    # data/ 사본을 그대로 쓰는 게 기본값.
    env = os.environ.get("STATSLAB_DATA_DIR")
    if env:
        return env
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")


DATA_DIR = _default_data_dir()
STATS_DB = os.path.join(DATA_DIR, "stats-latest.db")


def set_data_dir(path):
    """DATA_DIR/STATS_DB를 런타임에 교체(statsweb이 박스의 실제 telemetry/ 경로를 가리키게 할 때 사용)."""
    global DATA_DIR, STATS_DB
    DATA_DIR = path
    STATS_DB = os.path.join(DATA_DIR, "export", "stats-latest.db") if os.path.isdir(os.path.join(path, "export")) \
        else os.path.join(DATA_DIR, "stats-latest.db")


class StatsDataUnavailable(Exception):
    """stats.db/events db가 아직 없을 때(텔레메트리 미배포·롤업 전 등) — CLI는 종료 메시지로,
    statsweb은 친절한 '데이터 없음' 페이지로 각자 다르게 처리하도록 sys.exit() 대신 예외로 던진다."""


def _stats_conn():
    if not os.path.exists(STATS_DB):
        raise StatsDataUnavailable(f"stats.db 사본이 없습니다: {STATS_DB} — pull.sh로 먼저 받아오세요.")
    c = sqlite3.connect(STATS_DB)
    c.row_factory = sqlite3.Row
    return c


def _event_months():
    """data/ 안에 있는 events-YYYY-MM.db 전부(최신순)."""
    if not os.path.isdir(DATA_DIR):
        return []
    files = sorted(f for f in os.listdir(DATA_DIR) if f.startswith("events-") and f.endswith(".db"))
    return files


def _conn_with_events(months=None):
    """stats.db에 지정 월(또는 발견된 전부)의 events db를 ATTACH해서 반환. alias: evd0, evd1, ..."""
    c = _stats_conn()
    files = months or _event_months()
    aliases = []
    for i, f in enumerate(files):
        path = f if os.path.isabs(f) else os.path.join(DATA_DIR, f)
        if not os.path.exists(path):
            print(f"경고: {path} 없음, 건너뜀", file=sys.stderr)
            continue
        alias = f"evd{i}"
        c.execute(f"ATTACH DATABASE ? AS {alias}", (path,))
        aliases.append(alias)
    if not aliases:
        raise StatsDataUnavailable("ATTACH할 events-YYYY-MM.db가 data/ 에 없습니다 — pull.sh 확인.")
    return c, aliases


# 관리자(OP) 테스트/디버그 행동을 실제 유저 통계에서 제외(§7 규약 확장, 2026-07-28) — Telemetry.log()가
# 모든 이벤트에 ctx.op을 자동 태깅(RollupJob.java도 day_player 집계에 동일 필터 적용). C7(이용률)은
# 예외 — OP의 명령 사용도 "이 기능이 살아있다"는 유효 신호라 여긴 필터하지 않는다(day_type 직접 조회라
# _union_ev를 안 거침 — 그대로 둘 것).
NOT_OP = "(json_extract(ctx,'$.op') IS NULL OR json_extract(ctx,'$.op') != 1)"


def _union_ev(aliases):
    """여러 월 DB의 ev 테이블을 UNION ALL로 합친 서브쿼리 SQL 문자열. OP 행동은 여기서 일괄 제외."""
    return " UNION ALL ".join(f"SELECT * FROM {a}.ev WHERE {NOT_OP}" for a in aliases)


# ── C1: 성장곡선 백분위 ─────────────────────────────────────────
def c1_growth_curve(months=None):
    """레벨별 도달까지의 활동시간(playtime_s 누적, afk 제외) 백분위.
    level.up 이벤트 ts와 sess.end(dur_s-afk_s) 누적을 uuid별로 근사 조인한다.
    """
    c, aliases = _conn_with_events(months)
    union = _union_ev(aliases)
    sql = f"""
    WITH ev AS ({union}),
    levelups AS (
        SELECT uuid, ts, CAST(json_extract(ctx,'$.to') AS INTEGER) lv
        FROM ev WHERE type='level.up' AND json_extract(ctx,'$.sys')='낚시'
    ),
    playtime AS (
        SELECT uuid, ts, CAST(json_extract(ctx,'$.dur_s') AS INTEGER) - CAST(json_extract(ctx,'$.afk_s') AS INTEGER) net_s
        FROM ev WHERE type='sess.end'
    )
    SELECT l.lv level,
           (SELECT SUM(p.net_s) FROM playtime p WHERE p.uuid=l.uuid AND p.ts<=l.ts) cum_playtime_s
    FROM levelups l ORDER BY l.uuid, l.ts
    """
    rows = [dict(r) for r in c.execute(sql)]
    c.close()
    return rows


# ── C2: 밸붕 퀘스트 ─────────────────────────────────────────────
def c2_quest_efficiency(months=None):
    c, aliases = _conn_with_events(months)
    union = _union_ev(aliases)
    sql = f"""
    WITH ev AS ({union})
    SELECT json_extract(ctx,'$.qid') qid, COUNT(*) n,
           AVG(json_extract(ctx,'$.rw.money')) avg_money,
           AVG(json_extract(ctx,'$.dur_s')) avg_dur_s,
           AVG(json_extract(ctx,'$.rw.money')) / NULLIF(AVG(json_extract(ctx,'$.dur_s')), 0) money_per_sec
    FROM ev WHERE type='quest.done' GROUP BY qid ORDER BY money_per_sec DESC
    """
    rows = [dict(r) for r in c.execute(sql)]
    c.close()
    return rows


# ── C3: 낚싯대/로드아웃 OP 여부 ──────────────────────────────────
def c3_loadout_perf(min_catches=50, months=None):
    c, aliases = _conn_with_events(months)
    union_l = " UNION ALL ".join(f"SELECT * FROM {a}.loadout" for a in aliases)
    union_e = _union_ev(aliases)
    sql = f"""
    WITH ev AS ({union_e}), l AS ({union_l})
    SELECT json_extract(l.json,'$.rod') rod, json_extract(l.json,'$.enh') enh,
           COUNT(*) catches, AVG(json_extract(e.ctx,'$.price')) avg_price,
           SUM(CASE WHEN json_extract(e.ctx,'$.g') IN ('S','M','L','G') THEN 1 ELSE 0 END) * 1.0 / COUNT(*) high_rate
    FROM ev e JOIN l ON l.hash = json_extract(e.ctx,'$.lo')
    WHERE e.type='fish.result' AND json_extract(e.ctx,'$.res') NOT IN ('도주','대기')
    GROUP BY 1, 2 HAVING catches >= ?
    ORDER BY avg_price DESC
    """
    rows = [dict(r) for r in c.execute(sql, (min_catches,))]
    c.close()
    return rows


# ── C4: 작물 ROI ────────────────────────────────────────────────
def c4_crop_roi(months=None):
    c, aliases = _conn_with_events(months)
    union = _union_ev(aliases)
    sql = f"""
    WITH ev AS ({union})
    SELECT json_extract(ctx,'$.crop') crop, COUNT(*) harvests,
           AVG(json_extract(ctx,'$.qty')) avg_qty,
           AVG(json_extract(ctx,'$.grow_actual_s')) avg_grow_s,
           AVG(json_extract(ctx,'$.qty')) / NULLIF(AVG(json_extract(ctx,'$.grow_actual_s')), 0) qty_per_sec
    FROM ev WHERE type='crop.harvest' GROUP BY crop ORDER BY qty_per_sec DESC
    """
    rows = [dict(r) for r in c.execute(sql)]
    c.close()
    return rows


# ── C5: 가격 대비 성능(구매 실적 하위) ────────────────────────────
def c5_zero_purchase(months=None):
    """part.buy 품목별 구매 횟수(오름차순) — parts.json 카탈로그 전체 목록과 대조해
    아예 등장하지 않는 품목(구매 0)을 찾는 diff는 이 결과 + parts.json을 report.py가 수행한다
    (SQL만으로는 "이벤트에 없는 카탈로그 항목"을 뽑을 수 없음 — 카탈로그가 DB 밖에 있으므로)."""
    c, aliases = _conn_with_events(months)
    union = _union_ev(aliases)
    sql = f"""
    WITH ev AS ({union})
    SELECT json_extract(ctx,'$.name') name, COUNT(*) n
    FROM ev WHERE type='part.buy' GROUP BY name ORDER BY n ASC
    """
    rows = [dict(r) for r in c.execute(sql)]
    c.close()
    return rows


# ── C6: 인플레(일별 순발행) ──────────────────────────────────────
def c6_inflation(months=None):
    c, aliases = _conn_with_events(months)
    union = _union_ev(aliases)
    sql = f"""
    WITH ev AS ({union})
    SELECT json_extract(ctx,'$.r') reason,
           SUM(CASE WHEN CAST(json_extract(ctx,'$.d') AS INTEGER) > 0 THEN json_extract(ctx,'$.d') ELSE 0 END) sourced,
           SUM(CASE WHEN CAST(json_extract(ctx,'$.d') AS INTEGER) < 0 THEN json_extract(ctx,'$.d') ELSE 0 END) sunk,
           COUNT(*) n
    FROM ev WHERE type='money.txn' GROUP BY reason ORDER BY ABS(sourced + sunk) DESC
    """
    rows = [dict(r) for r in c.execute(sql)]
    c.close()
    return rows


# ── C7: 시스템별 이용률 ──────────────────────────────────────────
def c7_usage(days=7):
    c = _stats_conn()
    sql = """
    SELECT type, SUM(n) n, SUM(players) players FROM day_type
    WHERE date >= date('now', ?) GROUP BY type ORDER BY n DESC
    """
    rows = [dict(r) for r in c.execute(sql, (f"-{days} days",))]
    c.close()
    return rows


# ── C8: 카지노 실현 RTP ──────────────────────────────────────────
def c8_casino_rtp(months=None):
    c, aliases = _conn_with_events(months)
    union = _union_ev(aliases)
    sql = f"""
    WITH ev AS ({union})
    SELECT json_extract(ctx,'$.game') game,
           SUM(json_extract(ctx,'$.bet')) total_bet,
           SUM(json_extract(ctx,'$.net')) total_net,
           SUM(json_extract(ctx,'$.rake')) total_rake,
           COUNT(*) rounds,
           1.0 + (SUM(json_extract(ctx,'$.net')) * 1.0 / NULLIF(SUM(json_extract(ctx,'$.bet')), 0)) realized_rtp
    FROM ev WHERE type='casino.round' GROUP BY game ORDER BY rounds DESC
    """
    rows = [dict(r) for r in c.execute(sql)]
    c.close()
    return rows


# ── C9: RNG 검증(명목 vs 실측) ───────────────────────────────────
def c9_rng_fish(months=None):
    c, aliases = _conn_with_events(months)
    union = _union_ev(aliases)
    sql = f"""
    WITH ev AS ({union})
    SELECT CAST(ROUND(json_extract(ctx,'$.prd.p') * 20) AS INTEGER) / 20.0 p_bucket,
           COUNT(*) n,
           SUM(CASE WHEN json_extract(ctx,'$.gu')=1 THEN 1 ELSE 0 END) * 1.0 / COUNT(*) realized_rate
    FROM ev WHERE type='fish.result' AND json_extract(ctx,'$.prd.p') IS NOT NULL
    GROUP BY p_bucket ORDER BY p_bucket
    """
    rows = [dict(r) for r in c.execute(sql)]
    c.close()
    return rows


def c9_rng_enhance(months=None):
    c, aliases = _conn_with_events(months)
    union = _union_ev(aliases)
    sql = f"""
    WITH ev AS ({union})
    SELECT CAST(ROUND(json_extract(ctx,'$.p_succ') * 20) AS INTEGER) / 20.0 p_bucket,
           COUNT(*) n,
           SUM(CASE WHEN json_extract(ctx,'$.res')='success' THEN 1 ELSE 0 END) * 1.0 / COUNT(*) realized_rate
    FROM ev WHERE type='enh.attempt' AND json_extract(ctx,'$.p_succ') IS NOT NULL
    GROUP BY p_bucket ORDER BY p_bucket
    """
    rows = [dict(r) for r in c.execute(sql)]
    c.close()
    return rows


# ── 홈 KPI(오늘/7일) — statsweb ①홈 + /통계 오늘의 공용 원천 ──────────
def home_kpis(days=7):
    c = _stats_conn()
    sql = """
    SELECT date, COUNT(*) players, SUM(playtime_s) playtime_s, SUM(catches) catches,
           SUM(money_in) money_in, SUM(money_out) money_out, SUM(casino_net) casino_net,
           SUM(quests_done) quests_done, SUM(crafts) crafts, SUM(submits) submits
    FROM day_player WHERE date >= date('now', ?) GROUP BY date ORDER BY date DESC
    """
    rows = [dict(r) for r in c.execute(sql, (f"-{days} days",))]
    c.close()
    return rows


def collection_health():
    """수집 헬스 — meta 테이블의 최근 스냅샷/롤업/export 날짜(SnapshotJob/RollupJob/ExportJob이 기록)."""
    c = _stats_conn()
    keys = ["last_player_snapshot_date", "last_rollup_date", "last_export_date"]
    out = {}
    for k in keys:
        row = c.execute("SELECT v FROM meta WHERE k=?", (k,)).fetchone()
        out[k] = row[0] if row else None
    c.close()
    return out


COOKBOOK = {
    "c1": c1_growth_curve,
    "c2": c2_quest_efficiency,
    "c3": c3_loadout_perf,
    "c4": c4_crop_roi,
    "c5": c5_zero_purchase,
    "c6": c6_inflation,
    "c7": c7_usage,
    "c8": c8_casino_rtp,
    "c9f": c9_rng_fish,
    "c9e": c9_rng_enhance,
}


def main():
    ap = argparse.ArgumentParser(description="stats-lab 쿼리 쿡북 CLI")
    ap.add_argument("query", choices=sorted(COOKBOOK.keys()), help="C1~C9 쿠키북 쿼리")
    ap.add_argument("--months", help="쉼표구분 events-YYYY-MM.db 파일명(생략시 data/의 전부)")
    ap.add_argument("--json", action="store_true", help="JSON으로 출력(기본은 표)")
    args = ap.parse_args()

    months = args.months.split(",") if args.months else None
    fn = COOKBOOK[args.query]
    try:
        rows = fn(months) if fn.__code__.co_argcount > 0 and "months" in fn.__code__.co_varnames else fn()
    except StatsDataUnavailable as e:
        sys.exit(str(e))

    if args.json:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
        return
    if not rows:
        print("(결과 없음)")
        return
    cols = list(rows[0].keys())
    print(" | ".join(cols))
    for r in rows[:200]:
        print(" | ".join(str(r[c]) for c in cols))
    if len(rows) > 200:
        print(f"... ({len(rows)}행 중 200행만 표시, --json으로 전체 확인)")


if __name__ == "__main__":
    main()
