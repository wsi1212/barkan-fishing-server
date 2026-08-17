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
    """★2026-07-28 수정: ctx.cur(money/cash/afkp 등 재화 종류)를 안 가리고 reason만으로 묶었더니
    골드·캐시·잠수포인트가 전부 한 숫자로 합산되던 버그(유저 발견) — cur도 같이 GROUP BY해서
    재화별로 행을 분리한다. app.py가 cur별로 섹션을 나눠 표시."""
    c, aliases = _conn_with_events(months)
    union = _union_ev(aliases)
    sql = f"""
    WITH ev AS ({union})
    SELECT COALESCE(json_extract(ctx,'$.cur'), '(미지정)') cur, json_extract(ctx,'$.r') reason,
           SUM(CASE WHEN CAST(json_extract(ctx,'$.d') AS INTEGER) > 0 THEN json_extract(ctx,'$.d') ELSE 0 END) sourced,
           SUM(CASE WHEN CAST(json_extract(ctx,'$.d') AS INTEGER) < 0 THEN json_extract(ctx,'$.d') ELSE 0 END) sunk,
           COUNT(*) n
    FROM ev WHERE type='money.txn' GROUP BY cur, reason ORDER BY cur, ABS(sourced + sunk) DESC
    """
    rows = [dict(r) for r in c.execute(sql)]
    c.close()
    return rows


# ── C7: 시스템별 이용률 ──────────────────────────────────────────
def c7_usage(days=7):
    c = _stats_conn()
    sql = """
    SELECT type, SUM(n) n, SUM(players) players FROM day_type
    -- ★SQLite 의 date('now') 는 «호스트 TZ 와 무관하게 항상 UTC» 다(localtime 수식어가 없으면).
    --   day_type.date 는 BlockShip 이 KST 로 쓴 키라, 그냥 비교하면 00:00~09:00 KST 구간에
    --   창의 하단 경계가 하루 앞당겨져 최근 7일이 8일치로 집계된다. +9 시간으로 KST 로 맞춘다
    --   (한국은 서머타임이 없어 +9 고정이 안전하다).
    WHERE date >= date('now', '+9 hours', ?) GROUP BY type ORDER BY n DESC
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
    """★2026-07-29 수정: GradeRoller.Result.matchedProb(→ctx.prd.p)는 Java에서 "확률(%)"로
    저장된다(0~100 스케일, 예: 65.0=65%) — 이 쿼리가 0~1 소수로 착각하고 그대로 버킷팅+화면에서
    다시 ×100 해서 표시하는 바람에 최대 7000%대 값이 뜨던 버그(유저 발견). /100.0으로 0~1
    소수로 정규화한 뒤 버킷팅한다."""
    c, aliases = _conn_with_events(months)
    union = _union_ev(aliases)
    sql = f"""
    WITH ev AS ({union})
    SELECT CAST(ROUND(json_extract(ctx,'$.prd.p') / 100.0 * 20) AS INTEGER) / 20.0 p_bucket,
           COUNT(*) n,
           SUM(CASE WHEN json_extract(ctx,'$.gu')=1 THEN 1 ELSE 0 END) * 1.0 / COUNT(*) realized_rate
    FROM ev WHERE type='fish.result' AND json_extract(ctx,'$.prd.p') IS NOT NULL
    GROUP BY p_bucket ORDER BY p_bucket
    """
    rows = [dict(r) for r in c.execute(sql)]
    c.close()
    return rows


def c9_rng_enhance(months=None):
    """★2026-07-29 수정: EnhanceManager의 ctx.p_succ도 0~100 퍼센트 스케일(succ 변수 자체가
    SUCCESS[next] 퍼센트값) — c9_rng_fish와 동일한 이중 ×100 버그라 /100.0 정규화."""
    c, aliases = _conn_with_events(months)
    union = _union_ev(aliases)
    sql = f"""
    WITH ev AS ({union})
    SELECT CAST(ROUND(json_extract(ctx,'$.p_succ') / 100.0 * 20) AS INTEGER) / 20.0 p_bucket,
           COUNT(*) n,
           SUM(CASE WHEN json_extract(ctx,'$.res')='success' THEN 1 ELSE 0 END) * 1.0 / COUNT(*) realized_rate
    FROM ev WHERE type='enh.attempt' AND json_extract(ctx,'$.p_succ') IS NOT NULL
    GROUP BY p_bucket ORDER BY p_bucket
    """
    rows = [dict(r) for r in c.execute(sql)]
    c.close()
    return rows


# ── C10: 강화 레벨별(몇강) 시도/성공/실패 — "몇강에서 몇번 있었고 몇번 실패했고"(2026-07-28 요청) ──
def c10_enhance_by_level(months=None):
    """enh.attempt를 명목확률(p_bucket)이 아니라 실제 강화 단계(from, "몇강")로 그룹핑 — C9가
    "이론상 65%인 시도들이 실제로 65% 나오나"를 보면, 이건 "+7강 시도가 총 몇 번 있었고 그 중
    몇 번 성공/실패했나"를 그대로 센다. res는 success/keep(유지)/down(하락) 3종(§8-3 스키마)."""
    c, aliases = _conn_with_events(months)
    union = _union_ev(aliases)
    sql = f"""
    WITH ev AS ({union})
    SELECT CAST(json_extract(ctx,'$.from') AS INTEGER) enh_from,
           COUNT(*) n,
           SUM(CASE WHEN json_extract(ctx,'$.res')='success' THEN 1 ELSE 0 END) success,
           SUM(CASE WHEN json_extract(ctx,'$.res')!='success' THEN 1 ELSE 0 END) fail,
           AVG(json_extract(ctx,'$.p_succ')) / 100.0 avg_p_succ,
           SUM(CASE WHEN json_extract(ctx,'$.res')='success' THEN 1 ELSE 0 END) * 1.0 / COUNT(*) success_rate
    FROM ev WHERE type='enh.attempt' AND json_extract(ctx,'$.from') IS NOT NULL
    GROUP BY enh_from ORDER BY enh_from
    """
    rows = [dict(r) for r in c.execute(sql)]
    c.close()
    return rows


# ── C11: 채집(forage) 성과 — 타입별 성공률/희귀율/산출/소요시간 ──────────
def c11_forage_performance(months=None):
    """forage.do(§8-11)는 노드 하나당 성공/실패 종결 시점 1행 — 타입(나무열매/광물 등 채집물
    종류)별로 성공률·희귀 발견율·평균 산출량·평균 소요시간을 낸다. ⑤ 생산 페이지 전용(2026-07-28
    "광질이나 채집 탐험 뭐 그런것들" 요청으로 신설 — 이전엔 crop.harvest 기반 C4만 있었음)."""
    c, aliases = _conn_with_events(months)
    union = _union_ev(aliases)
    sql = f"""
    WITH ev AS ({union})
    SELECT json_extract(ctx,'$.type') forage_type, COUNT(*) n,
           SUM(CASE WHEN json_extract(ctx,'$.ok')=1 THEN 1 ELSE 0 END) * 1.0 / COUNT(*) ok_rate,
           SUM(CASE WHEN json_extract(ctx,'$.rare')=1 THEN 1 ELSE 0 END) * 1.0 / COUNT(*) rare_rate,
           AVG(json_extract(ctx,'$.qty')) avg_qty,
           AVG(json_extract(ctx,'$.dur_ms')) / 1000.0 avg_dur_s
    FROM ev WHERE type='forage.do' GROUP BY forage_type ORDER BY n DESC
    """
    rows = [dict(r) for r in c.execute(sql)]
    c.close()
    return rows


# ── C12: 통발(trap) 지역별 실적 — 설치/회수/파손 ────────────────────────
def c12_trap_performance(months=None):
    """trap.place/collect/break(§8-11)를 지역별로 합쳐서 본다 — 설치 대비 파손율이 높은
    지역은 내구도/위치 밸런스 확인 후보, 회수당 평균 대기시간(wait_s)은 "너무 자주 와야 하나"
    체감의 근거가 된다."""
    c, aliases = _conn_with_events(months)
    union = _union_ev(aliases)
    sql = f"""
    WITH ev AS ({union}),
    placed AS (SELECT json_extract(ctx,'$.region') region, COUNT(*) n FROM ev
        WHERE type='trap.place' GROUP BY region),
    collected AS (SELECT json_extract(ctx,'$.region') region, COUNT(*) n,
        AVG(json_extract(ctx,'$.n')) avg_catch, AVG(json_extract(ctx,'$.wait_s')) avg_wait_s
        FROM ev WHERE type='trap.collect' GROUP BY region),
    broken AS (SELECT json_extract(ctx,'$.region') region, COUNT(*) n FROM ev
        WHERE type='trap.break' GROUP BY region),
    regions AS (SELECT region FROM placed UNION SELECT region FROM collected UNION SELECT region FROM broken)
    SELECT r.region,
           COALESCE(p.n, 0) placed, COALESCE(c.n, 0) collected, COALESCE(b.n, 0) broken,
           COALESCE(c.avg_catch, 0) avg_catch_per_collect, COALESCE(c.avg_wait_s, 0) avg_wait_s,
           CASE WHEN COALESCE(p.n, 0) > 0 THEN COALESCE(b.n, 0) * 1.0 / p.n ELSE NULL END break_rate
    FROM regions r
    LEFT JOIN placed p ON p.region = r.region
    LEFT JOIN collected c ON c.region = r.region
    LEFT JOIN broken b ON b.region = r.region
    ORDER BY collected DESC
    """
    rows = [dict(r) for r in c.execute(sql)]
    c.close()
    return rows


# ── C13: 광질(드릴) 티어별 실적 ──────────────────────────────────────
def c13_mining_by_tier(months=None):
    """mine.min(§8-12, 드릴 60초 분당 집계)을 드릴 티어별로 — flush 1건=그 유저가 그 분에 캔
    총량. ore_per_flush가 낮은 티어는 성능이 기대만 못한 드릴일 수 있음."""
    c, aliases = _conn_with_events(months)
    union = _union_ev(aliases)
    sql = f"""
    WITH ev AS ({union})
    SELECT json_extract(ctx,'$.tier') tier, COUNT(*) flushes,
           SUM(json_extract(ctx,'$.n')) total_ore,
           AVG(json_extract(ctx,'$.chain')) avg_chain,
           SUM(json_extract(ctx,'$.xp')) total_xp,
           SUM(json_extract(ctx,'$.n')) * 1.0 / NULLIF(COUNT(*), 0) ore_per_flush
    FROM ev WHERE type='mine.min' GROUP BY tier ORDER BY tier
    """
    rows = [dict(r) for r in c.execute(sql)]
    c.close()
    return rows


# ── C14: 광물 종류별 채굴량(드릴+섬광산 통합) ────────────────────────────
def c14_ore_breakdown(months=None):
    """mine.min/imine.min의 ctx.ores(광물명→개수 딕셔너리)를 json_each로 풀어서 광물별 합계.
    특정 광물이 압도적으로 많이 나오면 그 광물 시세/드랍률이 밸런스 밖일 수 있음."""
    c, aliases = _conn_with_events(months)
    union = _union_ev(aliases)
    sql = f"""
    WITH ev AS ({union})
    SELECT je.key ore, SUM(je.value) qty, COUNT(*) events
    FROM ev, json_each(ev.ctx, '$.ores') je
    WHERE ev.type IN ('mine.min', 'imine.min')
    GROUP BY je.key ORDER BY qty DESC
    """
    rows = [dict(r) for r in c.execute(sql)]
    c.close()
    return rows


# ── C15: 섬 광산(imine) 요약 — 한도 도달 빈도 ─────────────────────────
def c15_island_mine_summary(months=None):
    """imine.min(§8-12, 섬광산)은 유저별 채굴 한도가 있음(capped 플래그) — capped_rate가
    높으면 한도가 너무 낮아 유저가 자주 막힌다는 뜻, 낮으면 한도가 사실상 무의미(체감 없음)."""
    c, aliases = _conn_with_events(months)
    union = _union_ev(aliases)
    sql = f"""
    WITH ev AS ({union})
    SELECT COUNT(*) flushes, SUM(json_extract(ctx,'$.n')) total_ore,
           SUM(json_extract(ctx,'$.xp')) total_xp,
           SUM(CASE WHEN json_extract(ctx,'$.capped')=1 THEN 1 ELSE 0 END) * 1.0 / COUNT(*) capped_rate
    FROM ev WHERE type='imine.min'
    """
    rows = [dict(r) for r in c.execute(sql)]
    c.close()
    return rows


# ── C16: 상점(섬/드릴/잠수/통발레시피) 품목별 구매/판매 — "어떤 품목이 얼마나 팔렸는지"(2026-07-28 요청) ──
def c16_shop_sales(months=None):
    """shop.buy/shop.sell(ctx.shop=island/drill/... , item, n=수량, price=총액)를 상점×품목으로
    묶는다. IslandShopGui는 buy·sell 둘 다 이 타입을 쓰고(shop='island'), 다른 상점(드릴/잠수/
    통발레시피)은 buy만(sell 없음) — 그래서 품목당 bought/sold를 한 행에 같이 두고 없는 쪽은 0."""
    c, aliases = _conn_with_events(months)
    union = _union_ev(aliases)
    sql = f"""
    WITH ev AS ({union})
    SELECT json_extract(ctx,'$.shop') shop, json_extract(ctx,'$.item') item,
           SUM(CASE WHEN type='shop.buy' THEN CAST(json_extract(ctx,'$.n') AS INTEGER) ELSE 0 END) bought_qty,
           SUM(CASE WHEN type='shop.buy' THEN CAST(json_extract(ctx,'$.price') AS INTEGER) ELSE 0 END) bought_revenue,
           SUM(CASE WHEN type='shop.sell' THEN CAST(json_extract(ctx,'$.n') AS INTEGER) ELSE 0 END) sold_qty,
           SUM(CASE WHEN type='shop.sell' THEN CAST(json_extract(ctx,'$.price') AS INTEGER) ELSE 0 END) sold_payout
    FROM ev WHERE type IN ('shop.buy', 'shop.sell')
    GROUP BY shop, item
    ORDER BY (bought_qty + sold_qty) DESC
    """
    rows = [dict(r) for r in c.execute(sql)]
    c.close()
    return rows


# ── C17: 유저마켓 품목별 판매 실적 + 등록→판매 소요시간 ─────────────────
def c17_market_by_item(months=None):
    """market.list/buy/cancel/expire를 listing id로 조인해 품목별 등록·판매·취소·만료 건수와
    등록 후 판매까지 걸린 평균 시간을 낸다(2026-07-28 로깅 보강으로 id가 4개 이벤트에 다 실린
    뒤에야 가능해진 조인 — 이전엔 등록↔결과를 연결할 방법이 아예 없었음)."""
    c, aliases = _conn_with_events(months)
    union = _union_ev(aliases)
    sql = f"""
    WITH ev AS ({union}),
    listed AS (SELECT json_extract(ctx,'$.id') id, json_extract(ctx,'$.item') item,
        CAST(json_extract(ctx,'$.price') AS INTEGER) price, ts listed_ts
        FROM ev WHERE type='market.list' AND json_extract(ctx,'$.id') IS NOT NULL),
    bought AS (SELECT json_extract(ctx,'$.id') id, ts bought_ts
        FROM ev WHERE type='market.buy' AND json_extract(ctx,'$.id') IS NOT NULL),
    cancelled AS (SELECT json_extract(ctx,'$.id') id FROM ev WHERE type='market.cancel'),
    expired AS (SELECT json_extract(ctx,'$.id') id FROM ev WHERE type='market.expire')
    SELECT l.item item, COUNT(*) listings,
           SUM(CASE WHEN b.id IS NOT NULL THEN 1 ELSE 0 END) sold,
           SUM(CASE WHEN cx.id IS NOT NULL THEN 1 ELSE 0 END) cancelled,
           SUM(CASE WHEN ex.id IS NOT NULL THEN 1 ELSE 0 END) expired,
           AVG(l.price) avg_price,
           AVG(CASE WHEN b.id IS NOT NULL THEN (b.bought_ts - l.listed_ts) / 60000.0 END) avg_sell_min
    FROM listed l
    LEFT JOIN bought b ON b.id = l.id
    LEFT JOIN cancelled cx ON cx.id = l.id
    LEFT JOIN expired ex ON ex.id = l.id
    GROUP BY l.item ORDER BY sold DESC
    """
    rows = [dict(r) for r in c.execute(sql)]
    c.close()
    return rows


# ── C18: 직거래 편측(불공정) 탐지 ───────────────────────────────────────
def c18_trade_fairness(months=None, limit=50):
    """trade.done의 value_a/value_b(수표+물고기 실가치 합)로 비율을 내되, unknown_a/unknown_b가
    0인(양쪽 다 100% 값을 아는) 거래만 본다 — 일반 아이템이 섞이면 ratio가 왜곡되므로 "확실히
    아는 거래"만 골라 상위 편측 거래를 보여준다(2026-07-28, §8-6 실질 자금이동 추적 요건 대응)."""
    c, aliases = _conn_with_events(months)
    union = _union_ev(aliases)
    sql = f"""
    WITH ev AS ({union}),
    trades AS (
        SELECT ts, json_extract(ctx,'$.a') player_a, json_extract(ctx,'$.b') player_b,
               CAST(json_extract(ctx,'$.value_a') AS INTEGER) value_a,
               CAST(json_extract(ctx,'$.value_b') AS INTEGER) value_b,
               CAST(json_extract(ctx,'$.unknown_a') AS INTEGER) unknown_a,
               CAST(json_extract(ctx,'$.unknown_b') AS INTEGER) unknown_b
        FROM ev WHERE type='trade.done'
    )
    SELECT ts, player_a, player_b, value_a, value_b,
           MAX(value_a, value_b) * 1.0 / NULLIF(MIN(NULLIF(value_a, 0), NULLIF(value_b, 0)), 0) ratio
    FROM trades
    WHERE unknown_a = 0 AND unknown_b = 0 AND (value_a > 0 OR value_b > 0)
    ORDER BY ratio DESC NULLS LAST
    LIMIT {int(limit)}
    """
    rows = [dict(r) for r in c.execute(sql)]
    c.close()
    return rows


def c18b_trade_overview(months=None):
    """직거래 전체 개요 — 값을 전혀 모르는(unknown>0) 거래 비율이 높으면 c18의 편측탐지가
    표본 일부만 커버한다는 뜻이니 같이 봐야 한다."""
    c, aliases = _conn_with_events(months)
    union = _union_ev(aliases)
    sql = f"""
    WITH ev AS ({union})
    SELECT COUNT(*) trades,
           SUM(CASE WHEN CAST(json_extract(ctx,'$.unknown_a') AS INTEGER) = 0
                     AND CAST(json_extract(ctx,'$.unknown_b') AS INTEGER) = 0 THEN 1 ELSE 0 END) fully_priced,
           SUM(CAST(json_extract(ctx,'$.value_a') AS INTEGER)) total_value_a,
           SUM(CAST(json_extract(ctx,'$.value_b') AS INTEGER)) total_value_b
    FROM ev WHERE type='trade.done'
    """
    rows = [dict(r) for r in c.execute(sql)]
    c.close()
    return rows


# ── C19: 송금 경로별(via) 집계 — 수수료 정책 불일치 확인 ─────────────────
def c19_xfer_by_via(months=None):
    """xfer.send를 via(transfer_cmd=/송금 10%수수료 / money_cmd=/돈 송금·보내기 0%수수료)별로
    — money_cmd 경로 총액이 크면 수수료 우회 규모가 그만큼이라는 뜻(2026-07-28, plan §14가
    지적한 정책 불일치를 실측하기 위해 via 필드를 새로 로깅하기 시작한 뒤에야 가능해진 집계)."""
    c, aliases = _conn_with_events(months)
    union = _union_ev(aliases)
    sql = f"""
    WITH ev AS ({union})
    SELECT COALESCE(json_extract(ctx,'$.via'), '(via 필드 없음·구버전)') via, COUNT(*) n,
           SUM(CAST(json_extract(ctx,'$.amt') AS INTEGER)) total_amt,
           SUM(CAST(json_extract(ctx,'$.fee') AS INTEGER)) total_fee,
           AVG(CAST(json_extract(ctx,'$.amt') AS INTEGER)) avg_amt
    FROM ev WHERE type='xfer.send' GROUP BY via ORDER BY total_amt DESC
    """
    rows = [dict(r) for r in c.execute(sql)]
    c.close()
    return rows


# ── C20: 수표 발행/입금 요약 ────────────────────────────────────────────
def c20_check_summary(months=None):
    """check.issue(발행) vs check.deposit(입금) 총액 비교 — outstanding_estimate는 "발행됐지만
    아직 안 들어온" 대략치(직거래로 옮겨다니는 수표가 있어 정확한 유통량은 아니지만 추세 참고용)."""
    c, aliases = _conn_with_events(months)
    union = _union_ev(aliases)
    sql = f"""
    WITH ev AS ({union}),
    iss AS (SELECT COUNT(*) n, SUM(CAST(json_extract(ctx,'$.face') AS INTEGER) * CAST(json_extract(ctx,'$.n') AS INTEGER)) total,
            SUM(CAST(json_extract(ctx,'$.fee') AS INTEGER)) total_fee FROM ev WHERE type='check.issue'),
    dep AS (SELECT COUNT(*) n, SUM(CAST(json_extract(ctx,'$.face') AS INTEGER) * CAST(json_extract(ctx,'$.n') AS INTEGER)) total
            FROM ev WHERE type='check.deposit')
    SELECT iss.n issued_n, COALESCE(iss.total, 0) issued_value, COALESCE(iss.total_fee, 0) issued_fee,
           dep.n deposited_n, COALESCE(dep.total, 0) deposited_value,
           COALESCE(iss.total, 0) - COALESCE(dep.total, 0) outstanding_estimate
    FROM iss, dep
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
    -- ★date('now') 는 항상 UTC — KST 키와 맞추려면 +9 시간(위 c7_usage 주석 참조)
    FROM day_player WHERE date >= date('now', '+9 hours', ?) GROUP BY date ORDER BY date DESC
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
    "c10": c10_enhance_by_level,
    "c11": c11_forage_performance,
    "c12": c12_trap_performance,
    "c13": c13_mining_by_tier,
    "c14": c14_ore_breakdown,
    "c15": c15_island_mine_summary,
    "c16": c16_shop_sales,
    "c17": c17_market_by_item,
    "c18": c18_trade_fairness,
    "c18b": c18b_trade_overview,
    "c19": c19_xfer_by_via,
    "c20": c20_check_summary,
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
