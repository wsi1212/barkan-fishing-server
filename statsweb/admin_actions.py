"""
admin_actions.py — Phase 6 통합 어드민 콘솔 액션 카탈로그 (stats-system-plan.md §10-6).

★"쓰기 액션 4원칙"(§10-6): ① 사전 정의된 액션 카탈로그만(임의 콘솔 명령 전달 절대 금지)
② 전 액션 CSRF 토큰(app.py가 검사) ③ 실행 전 확인 다이얼로그(템플릿이 confirm()) ④ 성공/실패
무관 audit_log 기록(이 파일의 record()). 플레이어 이름/메시지는 절대 명령 문자열에 그대로
이어붙이지 않고 화이트리스트 정규식으로 검증한 뒤에만 각 함수 전용 템플릿에 꽂는다 — 그래서
"임의 명령 전달"이 원천적으로 불가능하다(호출부가 ACTION_CATALOG에 없는 함수를 부를 방법이 없음).
"""
import datetime
import json
import os
import re
import sqlite3
import time

import queries
import rcon_client

_PLAYER_RE = re.compile(r"^[A-Za-z0-9_]{1,16}$")


def _valid_player(name):
    return bool(name) and bool(_PLAYER_RE.match(name))


def _clean_text(s, max_len=200):
    """개행/제어문자 제거 + 길이 제한 — RCON 프로토콜 자체는 텍스트 프레이밍이라 인젝션 여지는
    없지만(길이-프리픽스 패킷, 셸 아님) 표시 오염 방지 차원의 위생 처리."""
    if not s:
        return ""
    s = "".join(ch for ch in s if ch >= " ")
    return s.strip()[:max_len]


def kick(player, reason=""):
    if not _valid_player(player):
        raise ValueError(f"잘못된 플레이어 이름: {player!r}")
    reason = _clean_text(reason) or "운영자에 의한 추방"
    return rcon_client.exec_command(f"kick {player} {reason}")


def ban(player, reason=""):
    if not _valid_player(player):
        raise ValueError(f"잘못된 플레이어 이름: {player!r}")
    reason = _clean_text(reason) or "운영자에 의한 차단"
    return rcon_client.exec_command(f"ban {player} {reason}")


def pardon(player, reason=""):
    if not _valid_player(player):
        raise ValueError(f"잘못된 플레이어 이름: {player!r}")
    return rcon_client.exec_command(f"pardon {player}")


def whitelist_add(player, reason=""):
    if not _valid_player(player):
        raise ValueError(f"잘못된 플레이어 이름: {player!r}")
    return rcon_client.exec_command(f"whitelist add {player}")


def whitelist_remove(player, reason=""):
    if not _valid_player(player):
        raise ValueError(f"잘못된 플레이어 이름: {player!r}")
    return rcon_client.exec_command(f"whitelist remove {player}")


def say(player="", reason=""):
    """공지(say) — 여기서는 'reason' 필드를 메시지 본문으로 재사용(카탈로그 필드 통일용)."""
    message = _clean_text(reason, max_len=400)
    if not message:
        raise ValueError("메시지가 비어있습니다")
    return rcon_client.exec_command(f"say {message}")


def list_players(player="", reason=""):
    return rcon_client.exec_command("list")


# key: (표시명, 필요 필드 목록, 함수) — /console이 이 카탈로그에 없는 액션은 절대 실행 못 한다.
ACTION_CATALOG = {
    "kick": {"label": "추방 (kick)", "fields": ["player", "reason"], "fn": kick},
    "ban": {"label": "차단 (ban)", "fields": ["player", "reason"], "fn": ban},
    "pardon": {"label": "차단 해제 (pardon)", "fields": ["player"], "fn": pardon},
    "whitelist_add": {"label": "화이트리스트 추가", "fields": ["player"], "fn": whitelist_add},
    "whitelist_remove": {"label": "화이트리스트 제거", "fields": ["player"], "fn": whitelist_remove},
    "say": {"label": "전체 공지 (say)", "fields": ["reason"], "fn": say},
    "list": {"label": "온라인 목록 조회", "fields": [], "fn": list_players},
}

AUDIT_LOG_DDL = """CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY, ts INTEGER NOT NULL,
    actor_discord TEXT NOT NULL, actor_name TEXT,
    action TEXT NOT NULL, target TEXT, args TEXT, result TEXT)"""


def _stats_write_conn():
    """audit_log 전용 쓰기 커넥션 — queries.py의 읽기전용 연결(PRAGMA query_only)과 별개로
    새로 연다. 테이블은 Java TeleDb.java와 동일 DDL(이미 있으면 CREATE IF NOT EXISTS no-op)."""
    conn = sqlite3.connect(queries.STATS_DB, timeout=5)
    conn.execute("PRAGMA busy_timeout = 5000")
    conn.execute(AUDIT_LOG_DDL)
    return conn


def _events_write_conn():
    """이번 달 events-YYYY-MM.db에 admin.action(P0)을 미러(§10-6 마지막 항목) — 실제 서버가
    쓰는 파일과 동일 경로에 WAL 동시쓰기(busy_timeout으로 재시도, TeleDb.java와 동일 관례).
    ★prod에서는 이 파일이 Java TeleWriter가 이미 만들어둔 상태라 CREATE는 대개 no-op."""
    now = datetime.datetime.now()
    month_key = f"{now.year:04d}-{now.month:02d}"
    path = os.path.join(queries.DATA_DIR, f"events-{month_key}.db")
    conn = sqlite3.connect(path, timeout=5)
    conn.execute("PRAGMA busy_timeout = 5000")
    conn.execute("""CREATE TABLE IF NOT EXISTS ev (
        id INTEGER PRIMARY KEY, ts INTEGER NOT NULL, type TEXT NOT NULL,
        uuid TEXT, name TEXT, world TEXT, region TEXT, ctx TEXT)""")
    return conn


def record(admin, action, target, args, result):
    """audit_log 기록 + admin.action 이벤트 미러 — 실행 성공/실패 상관없이 항상 호출(§10-6 원칙④).
    감사로그 자체가 실패해도(디스크 문제 등) 액션 결과 표시를 막지 않는다(§0 설계원칙 3 정신)."""
    ts = int(time.time() * 1000)
    try:
        c = _stats_write_conn()
        c.execute(
            "INSERT INTO audit_log(ts,actor_discord,actor_name,action,target,args,result) VALUES(?,?,?,?,?,?,?)",
            (ts, admin.get("discord_id", ""), admin.get("name", ""), action, target,
             json.dumps(args, ensure_ascii=False), result))
        c.commit()
        c.close()
    except Exception:
        pass
    try:
        ec = _events_write_conn()
        ctx = {"action": action, "target": target, "args": args, "result": result,
               "actor": admin.get("name", ""), "actor_discord": admin.get("discord_id", "")}
        ec.execute("INSERT INTO ev(ts,type,uuid,name,world,region,ctx) VALUES(?,?,?,?,?,?,?)",
                   (ts, "admin.action", None, admin.get("name", ""), None, None,
                    json.dumps(ctx, ensure_ascii=False)))
        ec.commit()
        ec.close()
    except Exception:
        pass


def recent_audit_log(n=20):
    """콘솔 페이지용 최근 감사로그(읽기전용 취급 — SELECT만)."""
    if not os.path.exists(queries.STATS_DB):
        return []
    c = sqlite3.connect(queries.STATS_DB, timeout=5)
    c.row_factory = sqlite3.Row
    try:
        c.execute(AUDIT_LOG_DDL)  # 샌드박스 등 아직 테이블 없을 수 있음(읽기 전 보장)
        rows = [dict(r) for r in c.execute(
            "SELECT ts,actor_name,action,target,args,result FROM audit_log ORDER BY ts DESC LIMIT ?", (n,))]
    finally:
        c.close()
    return rows


def run_action(action_key, player="", reason=""):
    """/console POST가 호출하는 단일 진입점 — action_key가 카탈로그에 없으면 즉시 거부."""
    entry = ACTION_CATALOG.get(action_key)
    if not entry:
        raise ValueError(f"알 수 없는 액션: {action_key}")
    return entry["fn"](player, reason)
