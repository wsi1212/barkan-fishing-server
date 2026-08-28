"""
statsweb/app.py — 텔레메트리 웹 대시보드 (stats-system-plan.md §10-5).

FastAPI 단일 프로세스. DB는 read-only로만 접근(stats-lab/queries.py 재사용 — 쿼리 정의는
한 곳에만). 쓰기 엔드포인트 0개 — 킬스위치 등 조작은 인게임 /통계 명령만. 웹이 털려도
서버 조작 불가(§10-5 설계 원칙).

로컬 실행:
    cd statsweb && cp .env.example .env  # 값 채우기
    python3 -m venv venv && venv/bin/pip install -r requirements.txt
    venv/bin/uvicorn app:app --reload --port 8080
"""
import datetime
import json
import math
import os
import re
import secrets
import sys
import time

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

STATS_LAB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "stats-lab")
sys.path.insert(0, os.path.abspath(STATS_LAB_DIR))
import queries  # noqa: E402  (stats-lab/queries.py — 웹·CLI 공유 쿼리 모듈)
import charts  # noqa: E402
import insights  # noqa: E402  (표시 직전 "좋음/나쁨" 배지 — queries.py는 순수 쿼리만 유지)
import admin_actions  # noqa: E402  (Phase 6 — §10-6 통합 어드민 콘솔 액션 카탈로그)
import rcon_client  # noqa: E402
import vip_billing  # noqa: E402  (월 구독/환불은 전용 결제 DB가 권위)

data_dir_override = os.environ.get("STATSLAB_DATA_DIR")
if data_dir_override:
    queries.set_data_dir(data_dir_override)

import auth  # noqa: E402

app = FastAPI(title="바르칸 통계")

templates = Jinja2Templates(directory=os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates"))

# 샌드박스 모드(로컬 전용, run_sandbox.sh가 설정) — Discord OAuth 없이 바로 전 페이지 열람.
# ★prod .env에는 이 값을 절대 넣지 않는다(인증 우회이므로) — SANDBOX_MODE가 truthy일 때만 활성.
# ★미들웨어 등록 순서 주의: FastAPI.add_middleware()는 리스트 맨 앞에 insert하므로 "나중에 등록한
# 것"이 실행 스택의 바깥쪽(=먼저 실행)이 된다. 이 블록을 SessionMiddleware 등록보다 먼저 둬야
# SessionMiddleware가 더 바깥쪽에서 먼저 실행되어 request.session이 세팅된 뒤 샌드박스 미들웨어가
# 그걸 읽을 수 있다 — 순서를 바꾸면 "SessionMiddleware must be installed" AssertionError가 난다.
SANDBOX_MODE = os.environ.get("SANDBOX_MODE", "").lower() in ("1", "true", "yes")
if SANDBOX_MODE:
    @app.middleware("http")
    async def _sandbox_auto_login(request: Request, call_next):
        if not request.session.get("admin"):
            # role=admin으로 둬야 Phase 6 콘솔(§10-6, admin 전용)까지 샌드박스에서 눈으로 확인 가능.
            # ★RCON_PASSWORD는 run_sandbox.sh가 비워두므로 실제 명령은 절대 안 나감(rcon_client.RconDisabled).
            request.session["admin"] = {"discord_id": "sandbox", "name": "샌드박스", "role": "admin"}
        return await call_next(request)

    templates.env.globals["sandbox_mode"] = True
else:
    templates.env.globals["sandbox_mode"] = False

app.add_middleware(SessionMiddleware, secret_key=os.environ.get("SESSION_SECRET", "dev-only-insecure-key"))

# Caddy가 barkan.kr/admin/* → 127.0.0.1:8080/* 로 프리픽스를 벗겨서 프록시하므로(handle_path),
# 이 앱 자체는 자기가 /admin 밑에서 서빙되는 걸 모른다. 그래서 앱이 내보내는 절대경로 링크·리다이렉트는
# 전부 BASE_PATH를 붙여야 브라우저가 다시 /admin/* 으로 들어와 Caddy 라우팅을 통과한다.
# 로컬 개발(prefix 없음)은 .env에 BASE_PATH를 비워두면 된다.
BASE_PATH = os.environ.get("BASE_PATH", "").rstrip("/")
templates.env.globals["base_path"] = BASE_PATH

# Phase 6(§10-6) 조회 확장 — playerdata JSON 뷰어 + 밴목록. 박스 배치 시 .env에서 실제 경로로
# 오버라이드(예: /home/ubuntu/mcserver/plugins/BlockShip/playerdata, .../banned-players.json).
# 값이 없으면 뷰어가 "설정 안 됨" 안내만 하고 조용히 빈 화면(§0 원칙3 — 죽지 않고 우회).
PLAYERDATA_DIR = os.environ.get("PLAYERDATA_DIR", "")
BANNED_PLAYERS_FILE = os.environ.get("BANNED_PLAYERS_FILE", "")


def redirect(path: str, status_code: int = 307) -> RedirectResponse:
    return RedirectResponse(BASE_PATH + path, status_code=status_code)


@app.exception_handler(queries.StatsDataUnavailable)
async def stats_unavailable_handler(request: Request, exc: queries.StatsDataUnavailable):
    return templates.TemplateResponse(request, "no_data.html",
                                       {"user": request.session.get("admin"), "active": "", "error": str(exc)})


def _health_badge(date_str):
    if not date_str:
        return '<span class="badge warn">기록없음</span>'
    try:
        d = datetime.date.fromisoformat(date_str)
        age = (datetime.date.today() - d).days
    except ValueError:
        return '<span class="badge warn">?</span>'
    return '<span class="badge ok">정상</span>' if age <= 2 else f'<span class="badge warn">{age}일 지남</span>'


templates.env.globals["health_badge"] = _health_badge


def _require_admin(request: Request):
    """세션에 admin 정보가 없으면 None 반환(호출부가 리다이렉트 처리)."""
    return request.session.get("admin")


def _blockship_data_dir():
    """실시간 공개 랭킹이 읽을 BlockShip 데이터 루트.

    공개 랭킹은 일일 telemetry snapshot이 아니라 게임 서버의 현재 playerdata를
    읽어야 한다. 운영에서는 BLOCKSHIP_DATA_DIR/PLAYERDATA_DIR을 명시하고, 둘 다
    없을 때만 STATSLAB_DATA_DIR이 .../telemetry인 경우를 안전하게 역산한다.
    """
    configured = os.environ.get("BLOCKSHIP_DATA_DIR")
    if configured:
        return os.path.abspath(configured)
    configured_playerdata = os.environ.get("PLAYERDATA_DIR")
    if configured_playerdata:
        return os.path.dirname(os.path.abspath(configured_playerdata))
    telemetry_dir = getattr(queries, "DATA_DIR", "")
    if os.path.basename(os.path.normpath(telemetry_dir)) == "telemetry":
        return os.path.dirname(os.path.abspath(telemetry_dir))
    return ""


def _number(value, default=0):
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return default


_CASINO_NET_KEY = "카지노순익"  # BlockShip CasinoLedger/RankingManager와 같은 PlayerData.extraNums 키


_KST = datetime.timezone(datetime.timedelta(hours=9))
_ISO_DATE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})")
# 구 DateFormat(SHORT,SHORT) 잔재 — "4/7/26," 처럼 공백에서 잘린 조각까지 받는다.
_US_DATE = re.compile(r"^(\d{1,2})/(\d{1,2})/(\d{2})\s*,?\s*$")


def _parse_date_millis(raw):
    """날짜 문자열 → 그날 00:00 KST 의 epoch millis. 못 읽으면 0.

    인게임 RankingActivity.parseDateMillis 와 같은 규칙이다 — 저장 포맷인 yyyy-MM-dd 를
    먼저 보고, 안 되면 구 US 포맷을 시도한다. "26." 같은 조각은 0(=단서 없음)이다.
    """
    if not raw:
        return 0
    text = str(raw).strip()
    match = _ISO_DATE.match(text)
    if not match:
        match_us = _US_DATE.match(text)
        if not match_us:
            return 0
        month, day, year = int(match_us.group(1)), int(match_us.group(2)), 2000 + int(match_us.group(3))
    else:
        year, month, day = int(match.group(1)), int(match.group(2)), int(match.group(3))
    try:
        return int(datetime.datetime(year, month, day, tzinfo=_KST).timestamp() * 1000)
    except ValueError:
        return 0


def _ranking_dormant_days(blockship_dir):
    """휴면 제외 기준일 — plugins/BlockShip/config.yml 의 ranking.dormant-days 가 권위다.

    인게임 RankingExclusion 이 ops.json 하나를 보는 것과 같은 이유로 값을 여기 베끼지 않는다.
    config.yml 을 못 읽으면 인게임 기본값과 같은 90 을 쓴다(=제외가 조용히 꺼지지 않는다).
    PyYAML 의존을 늘리지 않으려고 두 줄짜리 키 하나만 직접 훑는다.
    """
    override = os.environ.get("RANKING_DORMANT_DAYS")
    if override:
        try:
            return max(0, int(override))
        except ValueError:
            pass
    if not blockship_dir:
        return 90
    path = os.path.join(blockship_dir, "config.yml")
    try:
        with open(path, encoding="utf-8") as file:
            in_ranking = False
            for line in file:
                if not line.strip() or line.lstrip().startswith("#"):
                    continue
                if not line[:1].isspace():                    # 최상위 키로 되돌아옴
                    in_ranking = line.strip().startswith("ranking:")
                    continue
                if in_ranking:
                    found = re.match(r"\s+dormant-days:\s*(\d+)", line)
                    if found:
                        return max(0, int(found.group(1)))
    except (OSError, ValueError):
        pass
    return 90


def _drop_dormant(rows, days, now_millis=None):
    """마지막 활동일이 days 일보다 오래된 행을 뺀다. 단서가 없는 행(0)은 남긴다."""
    if days <= 0:
        return rows
    cutoff = (now_millis or int(datetime.datetime.now().timestamp() * 1000)) - days * 86_400_000
    kept = []
    for row in rows:
        last = _number(row.get("last_active"), 0)
        if last and last < cutoff:
            continue
        kept.append(row)
    return kept


def _read_live_player_rows(playerdata_dir, world_playerdata_dir=""):
    """현재 playerdata/*.json을 공개 랭킹 행으로 변환한다.

    PlayerDataManager가 원자 교체로 저장하므로 읽는 순간 파일이 교체돼도
    찢어진 JSON을 보지 않는다. 개별 파일 오류는 해당 유저만 건너뛴다.

    ★last_active(마지막 활동 epoch millis)를 같이 실어 휴면 제외에 쓴다. 인게임은
    OfflinePlayer.getLastSeen() 을 보지만 여기서는 그 값의 출처인 world/playerdata/<uuid>.dat
    의 mtime 으로 대신한다(로그아웃 때 쓰이는 파일이다). 최대 몇 시간 어긋날 수 있으나
    기준이 90일 단위라 판정이 갈리지 않는다.
    """
    if not playerdata_dir or not os.path.isdir(playerdata_dir):
        return []
    rows = []
    try:
        entries = os.scandir(playerdata_dir)
    except OSError:
        return []
    with entries:
        for entry in entries:
            if not entry.name.endswith(".json"):
                continue
            try:
                with open(entry.path, encoding="utf-8") as file:
                    player = json.load(file)
                if not isinstance(player, dict):
                    continue
                extra_nums = player.get("extraNums")
                if not isinstance(extra_nums, dict):
                    extra_nums = {}
                uuid = str(player.get("uuid") or entry.name[:-5])
                name = str(player.get("name") or "").strip()
                if not name:
                    continue
                extra_strs = player.get("extraStrs")
                if not isinstance(extra_strs, dict):
                    extra_strs = {}
                last_active = max(
                    _parse_date_millis(extra_strs.get("마지막접속날짜")),
                    _parse_date_millis(extra_strs.get("주간접속날짜")),
                )
                if world_playerdata_dir:
                    try:
                        last_active = max(last_active, int(os.path.getmtime(
                            os.path.join(world_playerdata_dir, uuid + ".dat")) * 1000))
                    except OSError:
                        pass    # 지금 월드에서 논 적 없는 계정 — 위 날짜 단서로만 판단한다
                level = player.get("fishingLevel", player.get("level"))
                current_exp = player.get("currentExp", player.get("curExp"))
                total_fish = extra_nums.get("총낚시", player.get("totalFish"))
                dex_discovery = player.get("dexDiscovery")
                rows.append({
                    "name": name,
                    "uuid": uuid,
                    "level": _number(level, 0),
                    "cur_exp": current_exp or 0,
                    "money": _number(player.get("money"), 0),
                    "cash": _number(player.get("cash"), 0),
                    "coins": _number(player.get("recommendCoins", player.get("coins")), 0),
                    "max_combo": _number(player.get("maxCombo"), 0),
                    "total_fish": _number(total_fish, 0),
                    "dex_fish": len(dex_discovery.get("물고기", []))
                    if isinstance(dex_discovery, dict) else _number(player.get("dexFish"), 0),
                    "popularity": _number(player.get("popularity"), 0),
                    "casino_net": _number(extra_nums.get(_CASINO_NET_KEY), 0),
                    # 카지노 원장이 생기기 전의 playerdata는 값이 없는 정상적인 구 데이터다.
                    # 이 표식으로만 이벤트 로그 fallback 여부를 결정하고 API에는 내보내지 않는다.
                    "casino_net_recorded": _CASINO_NET_KEY in extra_nums,
                    "last_active": last_active,
                })
            except (OSError, ValueError, TypeError):
                continue
    return rows


def _op_uuids(blockship_dir):
    """랭킹에서 뺄 OP UUID 집합.

    권위는 게임 서버 루트의 ops.json 하나다 — 인게임 RankingExclusion 이 보는 Bukkit op 목록이
    바로 그 파일이라, /op·/deop 한 번에 인게임과 홈페이지가 함께 따라온다. 별도 제외 명단을
    만들면 한쪽만 갱신되는 날이 온다.

    경로는 BLOCKSHIP_DATA_DIR(=plugins/BlockShip)에서 두 단계 위(서버 루트)로 역산하고,
    다른 배치에서는 OPS_FILE 로 직접 지정한다. 못 읽으면 빈 집합(=아무도 안 뺌)이지만 조용히
    넘기지 않고 로그를 남긴다 — 안 그러면 제외가 사라진 걸 아무도 모른다.
    """
    path = os.environ.get("OPS_FILE")
    if not path:
        if not blockship_dir:
            return set()
        path = os.path.join(os.path.dirname(os.path.dirname(blockship_dir)), "ops.json")
    try:
        with open(path, encoding="utf-8") as file:
            entries = json.load(file)
    except OSError as error:
        print(f"[ranking] ops.json 을 읽지 못해 OP 제외를 건너뜁니다 ({path}): {error}", flush=True)
        return set()
    except (ValueError, TypeError) as error:
        print(f"[ranking] ops.json 이 손상돼 OP 제외를 건너뜁니다 ({path}): {error}", flush=True)
        return set()
    if not isinstance(entries, list):
        return set()
    return {str(entry.get("uuid")).strip().lower()
            for entry in entries
            if isinstance(entry, dict) and entry.get("uuid")}


def _guild_owner_uuid(guild):
    """길드장 UUID — ownerUuid 가 UUID 가 아닌 옛 레코드면 MASTER 멤버 키로 대신 찾는다.

    ownerId 는 닉네임이라 op 판정에 쓰면 닉 변경 한 번에 어긋난다
    (인게임 GuildData.resolveOwnerUuid 과 같은 규칙).
    """
    raw = str(guild.get("ownerUuid") or "").strip().lower()
    if len(raw) == 36 and raw.count("-") == 4:
        return raw
    for uuid, member in (guild.get("members") or {}).items():
        if isinstance(member, dict) and member.get("role") == "MASTER":
            return str(uuid).strip().lower()
    return ""


def _drop_ops(rows, op_uuids, key="uuid"):
    """행 목록에서 OP 소유 행을 뺀다. uuid 가 비어 있는 행은 판정 불가라 남긴다."""
    if not op_uuids:
        return rows
    return [row for row in rows
            if str(row.get(key) or "").strip().lower() not in op_uuids]


def _sort_player_rows(rows, field, secondary):
    """공개 랭킹용 개인 행 정렬(동점이면 보조 수치·이름 순)."""
    return sorted(
        rows,
        key=lambda row: (-float(row.get(field) or 0),
                         -float(row.get(secondary) or 0),
                         str(row.get("name") or "").casefold()),
    )[:100]


@app.get("/api/ranking")
def public_ranking():
    """공식 홈페이지 전용 공개 랭킹.

    개인 랭킹은 일일 player_snapshot이 아니라 현재 playerdata를 우선한다.
    snapshot은 playerdata가 아직 없거나 읽을 수 없을 때만 fallback으로 쓴다.
    """
    import sqlite3
    conn = None
    latest = None
    snapshot_rows = []
    if os.path.exists(queries.STATS_DB):
        conn = sqlite3.connect(queries.STATS_DB)
        conn.row_factory = sqlite3.Row
    try:
        if conn is not None:
            try:
                latest = conn.execute("SELECT MAX(date) AS date FROM player_snapshot").fetchone()["date"]
                if latest:
                    snapshot_rows = [dict(row) for row in conn.execute(
                        """SELECT name, uuid, level, total_fish, money, cash, coins, max_combo
                           FROM player_snapshot
                           WHERE date=? AND name IS NOT NULL AND TRIM(name) != ''""",
                        (latest,),
                    ).fetchall()]
            except sqlite3.DatabaseError:
                latest = None
                snapshot_rows = []

        blockship_dir = _blockship_data_dir()
        playerdata_dir = os.environ.get(
            "PLAYERDATA_DIR",
            os.path.join(blockship_dir, "playerdata") if blockship_dir else "",
        )
        world_playerdata_dir = os.environ.get("WORLD_PLAYERDATA_DIR", "")
        if not world_playerdata_dir and blockship_dir:
            world_playerdata_dir = os.path.join(
                os.path.dirname(os.path.dirname(blockship_dir)), "world", "playerdata")
        live_player_rows = _read_live_player_rows(playerdata_dir, world_playerdata_dir)
        player_rows = live_player_rows or snapshot_rows

        # ★공개 순위표에서 OP 를 뺀다(인게임 /랭킹 과 같은 ops.json 기준).
        #   길드 점수 계산에 쓰는 player_levels 는 원본을 그대로 쓴다 — 길드는 「유저」가 아니라
        #   여기서 op 멤버를 빼면 그 길드의 점수만 조용히 깎여 순위가 뒤틀린다.
        op_uuids = _op_uuids(blockship_dir)
        public_player_rows = _drop_ops(player_rows, op_uuids)
        # ★휴면 계정도 뺀다(인게임 RankingActivity 와 같은 config.yml 기준). 개인 랭킹은
        #   playerdata 를 전부 읽어 접속 여부를 안 보기 때문에, 떠난 계정이 파일만 남아
        #   상위권에 눌러앉는다 — 2026-08-26 prod 에서 5개월 미접속 계정이 레벨 1위였다.
        #   길드/섬 점수는 그대로 둔다(엔티티 랭킹이고, 시즌 리셋이 이미 낡은 기록을 턴다).
        public_player_rows = _drop_dormant(public_player_rows, _ranking_dormant_days(blockship_dir))

        def read_plugin_json(filename):
            if not blockship_dir:
                return {}
            try:
                with open(os.path.join(blockship_dir, filename), encoding="utf-8") as file:
                    return json.load(file)
            except (OSError, ValueError, TypeError):
                return {}

        level_rows = _sort_player_rows(public_player_rows, "level", "total_fish")
        fish_rows = _sort_player_rows(public_player_rows, "total_fish", "level")
        wealth_rows = _sort_player_rows(public_player_rows, "money", "level")
        player_levels = {
            str(row["uuid"]): _number(row.get("level"), 0)
            for row in player_rows if row.get("uuid")
        }

        def guild_level(score):
            thresholds = (3_000, 8_000, 16_000, 28_000, 45_000, 70_000, 100_000, 140_000,
                          190_000, 250_000, 330_000, 430_000, 560_000, 720_000, 920_000)
            return sum(score >= threshold for threshold in thresholds)

        # 엠블럼 색표는 BlockShip이 기동마다 다시 뽑는다(emblem-palette.json). 여기서 베껴 두면
        # 인게임 팔레트를 늘렸을 때 웹만 옛 색으로 남는다.
        emblem_palette = read_plugin_json("emblem-palette.json")
        emblem_colors = [entry.get("hex") for entry in (emblem_palette.get("colors") or [])
                         if isinstance(entry, dict) and entry.get("hex")]
        palette_size = len(emblem_colors)

        def emblem_array(raw, expected):
            """팔레트 범위를 벗어난 값은 빈 픽셀로 떨어뜨린다."""
            if not isinstance(raw, list) or len(raw) != expected:
                return [-1] * expected
            return [int(value) if isinstance(value, (int, float)) and 0 <= int(value) < palette_size else -1
                    for value in raw]

        def emblem_rgb_array(raw, expected):
            """고급 RGB 팔레트로 저장된 실제 RGB 미리보기."""
            if not isinstance(raw, list) or len(raw) != expected:
                return []
            return [int(value) if isinstance(value, (int, float)) and 0 <= int(value) <= 0xFFFFFF else 0
                    for value in raw]

        guild_rows = []
        for guild_id, guild in read_plugin_json("guilds.json").items():
            # ★길드장이 op 인 길드는 순위표에서 뺀다(인게임 GuildManager 와 같은 기준) —
            #   1인 op 길드가 점수 1,000만으로 1위를 차지하고 있었다. op 멤버의 기여분만 빼면
            #   그 길드 점수만 조용히 깎여 무고한 길드원의 순위가 뒤틀리므로 길드장 기준으로 자른다.
            if _guild_owner_uuid(guild) in op_uuids:
                continue
            members = guild.get("members") or {}
            score = (
                sum(player_levels.get(str(uuid), 0) * 100 for uuid in members)
                + int(guild.get("submitTotal") or 0)
                + len(members) * 500
                + int(guild.get("treasury") or 0) // 10_000
            )
            owner = guild.get("ownerId") or ""
            # 8×8·64×64 미리보기는 둘 다 BlockShip이 권위 캔버스에서 파생해 넣어 준다.
            emblem = emblem_array(guild.get("emblemPixels"), 8 * 8)
            canvas_emblem = emblem_array(guild.get("emblemCanvasPixels"), 64 * 64)
            if all(value < 0 for value in canvas_emblem):
                canvas_emblem = []
            canvas_rgb = emblem_rgb_array(guild.get("emblemCanvasRgb"), 64 * 64)
            canvas_rgb_full = emblem_rgb_array(guild.get("emblemCanvasRgbFull"), 128 * 128)
            guild_rows.append({
                "id": guild_id,
                "name": guild.get("displayName") or guild_id,
                "skinName": owner,
                "owner": owner,
                "members": len(members),
                "level": guild_level(score),
                "score": score,
                "emblemPixels": emblem,
                "emblemCanvasPixels": canvas_emblem,
                "emblemCanvasRgb": canvas_rgb,
                "emblemCanvasRgbFull": canvas_rgb_full,
            })
        guild_rows.sort(key=lambda row: (-row["score"], row["name"].casefold()))

        island_rows = []
        for island in read_plugin_json("islands.json").values():
            if str(island.get("ownerUuid") or "").strip().lower() in op_uuids:
                continue
            owner = island.get("ownerName") or "알 수 없는 섬장"
            visitors = int(island.get("visitCount") or len(island.get("visitLog") or {}))
            island_rows.append({
                "name": f"{owner}의 섬",
                "skinName": owner,
                "owner": owner,
                "uuid": island.get("ownerUuid"),
                "visitors": visitors,
            })
        island_rows.sort(key=lambda row: (-row["visitors"], row["name"].casefold()))

        popularity_rows = []
        for player in public_player_rows:
            popularity = _number(player.get("popularity"), 0)
            if popularity != 0:
                popularity_rows.append({
                    "name": player["name"],
                    "uuid": player.get("uuid"),
                    "popularity": popularity,
                })
        popularity_rows.sort(key=lambda row: (-row["popularity"], row["name"].casefold()))

        casino_rows = []
        # 인게임 /랭킹과 같은 CasinoLedger 누적 원장을 우선 사용한다. 새 원장이 없는
        # 옛 playerdata만 남아 있는 배치에서는 기존 telemetry를 fallback으로 읽는다.
        has_live_casino_ledger = any(
            player.get("casino_net_recorded") for player in public_player_rows
        )
        if has_live_casino_ledger:
            for player in public_player_rows:
                net = _number(player.get("casino_net"), 0)
                if net != 0:
                    casino_rows.append({
                        "name": player["name"],
                        "uuid": player.get("uuid"),
                        "net": net,
                    })
            casino_rows.sort(key=lambda row: (-row["net"], row["name"].casefold()))
            casino_rows = casino_rows[:100]
        else:
            event_files = []
            try:
                event_files = sorted(
                    entry.path for entry in os.scandir(queries.DATA_DIR)
                    if entry.name.startswith("events-") and entry.name.endswith(".db")
                )
            except OSError:
                pass
        if not has_live_casino_ledger and conn is not None and event_files:
            aliases = []
            try:
                for index, path in enumerate(event_files):
                    alias = f"casino_events_{index}"
                    conn.execute(f"ATTACH DATABASE ? AS {alias}", (path,))
                    aliases.append(alias)
                union = " UNION ALL ".join(
                    f"SELECT uuid, name, ctx FROM {alias}.ev "
                    "WHERE type='casino.round' "
                    "AND (json_extract(ctx, '$.ok') IS NULL OR json_extract(ctx, '$.ok') = 1)"
                    for alias in aliases
                )
                casino_rows = [dict(row) for row in conn.execute(
                    f"""SELECT COALESCE(NULLIF(MAX(name), ''), uuid) AS name, uuid,
                               SUM(CAST(COALESCE(json_extract(ctx, '$.net'), 0) AS INTEGER)) AS net
                        FROM ({union})
                        GROUP BY uuid
                        HAVING net <> 0
                        ORDER BY net DESC, name COLLATE NOCASE ASC
                        LIMIT 100"""
                ).fetchall()]
                casino_rows = _drop_ops(casino_rows, op_uuids)
            except sqlite3.DatabaseError:
                casino_rows = []
            finally:
                for alias in aliases:
                    try:
                        conn.execute(f"DETACH DATABASE {alias}")
                    except sqlite3.DatabaseError:
                        pass

        if not player_rows and not guild_rows and not island_rows and not popularity_rows and not casino_rows:
            return JSONResponse({"updatedAt": None, "categories": {}}, status_code=503)

        updated_at = (datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                      if live_player_rows else latest)
        return {
            "updatedAt": updated_at,
            "emblemColors": emblem_colors,
            "emblemBackground": emblem_palette.get("background"),
            "categories": {
                "level": {"label": "낚시 레벨", "field": "level", "suffix": "Lv.", "rows": level_rows},
                "fish": {"label": "누적 어획", "field": "total_fish", "suffix": "마리", "rows": fish_rows},
                "wealth": {"label": "보유 자산", "field": "money", "suffix": "원", "rows": wealth_rows},
                "guild": {"label": "길드 랭킹", "field": "level", "suffix": "Lv.", "rows": guild_rows},
                "island": {"label": "섬 방문자", "field": "visitors", "suffix": "명", "rows": island_rows},
                "casino": {"label": "카지노 순수익", "field": "net", "suffix": "원", "rows": casino_rows},
                "popularity": {"label": "인기도", "field": "popularity", "suffix": "♥", "rows": popularity_rows},
            },
        }
    finally:
        if conn is not None:
            conn.close()


def _money_fmt(v):
    if v is None:
        return "-"
    try:
        return f"{float(v):,.1f}원"
    except (TypeError, ValueError):
        return v


def _num1(v):
    """모든 표시용 숫자는 소숫점 한 자리로 통일(2026-07-28 피드백) — 문자열/None은 그대로 통과.
    ★단, 1보다 작은 값(qty_per_sec 등 초당 산출량처럼 원래 0.003 같은 값)을 무조건 1자리로 반올림하면
    전부 "0.0"으로 뭉개져 정보가 사라진다(2026-07-28 두번째 피드백으로 발견) — 그래서 1 미만인 값은
    유효숫자 2자리가 보이도록 소숫점 자리수를 자동으로 늘린다(0.5→0.50, 0.003→0.0030)."""
    if v is None:
        return "-"
    try:
        v = float(v)
    except (TypeError, ValueError):
        return v
    if v != 0 and abs(v) < 1:
        decimals = max(1, 1 - math.floor(math.log10(abs(v))))
        return f"{v:,.{decimals}f}"
    return f"{v:,.1f}"


def _pct1(v):
    if v is None:
        return "-"
    try:
        v = float(v) * 100
    except (TypeError, ValueError):
        return v
    if v != 0 and abs(v) < 1:
        decimals = max(1, 1 - math.floor(math.log10(abs(v))))
        return f"{v:,.{decimals}f}%"
    return f"{v:,.1f}%"


def _ts_fmt(v):
    """epoch ms → "MM-DD HH:MM" (user.html 최근 이벤트 목록과 동일 포맷)."""
    if v is None:
        return "-"
    try:
        return time.strftime("%m-%d %H:%M", time.localtime(float(v) / 1000))
    except (TypeError, ValueError, OSError):
        return v


templates.env.filters["num1"] = _num1
templates.env.filters["pct1"] = _pct1
templates.env.filters["money1"] = _money_fmt


def _fmt_rows(rows, col_fmt):
    """listing.html 표시 직전 포맷팅 — col_fmt: {컬럼명: 포맷함수}. 원본 rows는 그대로 두고
    표시용 사본을 반환한다(인사이트 배지는 원본 숫자 기준으로 이미 계산된 뒤라 순서 안전)."""
    out = []
    for r in rows:
        d = dict(r)
        for col, fn in col_fmt.items():
            if col in d:
                d[col] = fn(d[col])
        out.append(d)
    return out


# ── 인증 ─────────────────────────────────────────────────────────
@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request, error: str = ""):
    if request.session.get("admin"):
        return redirect("/")
    return templates.TemplateResponse(request, "login.html", {"request": request, "error": error})


@app.get("/login/discord")
def login_discord(request: Request):
    state = auth.new_state()
    request.session["oauth_state"] = state
    return RedirectResponse(auth.build_authorize_url(state))  # 외부(Discord) 절대 URL — BASE_PATH 붙이면 안 됨


@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    return redirect("/login")


@app.get("/callback")
async def callback(request: Request, code: str = "", state: str = "", error: str = ""):
    if error:
        return redirect(f"/login?error={error}")
    if state != request.session.get("oauth_state"):
        return redirect("/login?error=state_mismatch")
    token = await auth.exchange_code(code)
    if not token:
        return redirect("/login?error=token_exchange_failed")
    user = await auth.fetch_discord_user(token)
    if not user:
        return redirect("/login?error=user_fetch_failed")
    admin = auth.resolve_admin(user.get("id"))
    if not admin:
        return redirect("/login?error=not_an_admin")
    request.session["admin"] = admin
    return redirect("/")


def guard(request: Request):
    admin = _require_admin(request)
    if not admin:
        return None, redirect("/login")
    return admin, None


def guard_admin(request: Request):
    """Phase 6(§10-6) 역할 2단 게이팅 — viewer는 통계 열람 전부 가능하지만 쓰기 액션(콘솔)은
    admin 역할만. admins.json의 role 필드가 그대로 권위(승격은 파일 수정 = 운영자만 가능)."""
    admin, err = guard(request)
    if err:
        return None, err
    if admin.get("role") != "admin":
        return None, HTMLResponse(
            "<h1>403</h1><p>이 페이지는 admin 권한이 필요합니다(viewer는 통계 열람만 가능).</p>",
            status_code=403)
    return admin, None


def _csrf_token(request: Request) -> str:
    """세션당 1개 발급해 재사용 — §10-6 쓰기 액션 4원칙 ②. 폼 hidden 필드로 내려주고
    POST에서 세션 값과 대조(불일치면 403 — 새로고침 유도)."""
    tok = request.session.get("csrf")
    if not tok:
        tok = secrets.token_urlsafe(24)
        request.session["csrf"] = tok
    return tok


# ── ① 홈 ─────────────────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
def home(request: Request, days: int = 14):
    admin, redirect = guard(request)
    if redirect:
        return redirect
    rows = queries.home_kpis(days)
    today_str = datetime.date.today().isoformat()
    today = next((r for r in rows if r["date"] == today_str), None)
    today_playtime_h = round((today["playtime_s"] or 0) / 3600, 1) if today else 0
    today_net = ((today["money_in"] or 0) - (today["money_out"] or 0)) if today else 0
    today_casino = (today["casino_net"] or 0) if today else 0

    # "오늘"이 좋은 건지 나쁜 건지 숫자만 봐서는 안 보인다는 피드백(2026-07-28) — 최근 며칠(오늘 제외)
    # 평균과 비교한 등락 배지를 붙인다. 표본이 0이면(첫날 등) delta_badge가 알아서 빈 문자열 반환.
    prev = [r for r in rows if r["date"] != today_str]

    def _avg(field, transform=lambda r: r):
        vals = [transform(r) for r in prev if transform(r) is not None]
        return sum(vals) / len(vals) if vals else 0

    avg_players = _avg("players", lambda r: r["players"])
    avg_playtime_h = _avg("playtime_s", lambda r: (r["playtime_s"] or 0) / 3600)
    avg_catches = _avg("catches", lambda r: r["catches"] or 0)
    avg_net = _avg("net", lambda r: (r["money_in"] or 0) - (r["money_out"] or 0))
    avg_casino = _avg("casino_net", lambda r: r["casino_net"] or 0)
    avg_quests = _avg("quests_done", lambda r: r["quests_done"] or 0)

    deltas = {
        "players": insights.delta_badge((today["players"] if today else 0), avg_players),
        "playtime": insights.delta_badge(today_playtime_h, avg_playtime_h),
        "catches": insights.delta_badge((today["catches"] if today else 0), avg_catches),
        # 순발행/카지노 net은 부호가 있고 기준값이 0 근처를 오가므로 %가 아니라 절대 증감으로 표시.
        "net": insights.delta_badge_abs(today_net, avg_net, _money_fmt),
        "casino": insights.delta_badge_abs(today_casino, avg_casino, _money_fmt),
        "quests": insights.delta_badge((today["quests_done"] if today else 0), avg_quests),
    }

    ordered = sorted(rows, key=lambda r: r["date"])
    players_chart = charts.bar_chart([r["date"][5:] for r in ordered], [r["players"] for r in ordered],
                                      value_fmt=lambda v: f"{v:,.1f}", title=None)
    net_chart = charts.bar_chart([r["date"][5:] for r in ordered],
                                  [(r["money_in"] or 0) - (r["money_out"] or 0) for r in ordered],
                                  value_fmt=_money_fmt, title=None)
    health = queries.collection_health()
    return templates.TemplateResponse(request, "home.html", {
        "request": request, "user": admin, "active": "home", "days": days,
        "today": today, "today_playtime_h": today_playtime_h,
        "today_net_str": _money_fmt(today_net), "today_casino_str": _money_fmt(today_casino),
        "deltas": deltas,
        "players_chart": players_chart, "net_chart": net_chart, "health": health,
    })


# ── ② 성장곡선 ────────────────────────────────────────────────────
@app.get("/growth", response_class=HTMLResponse)
def growth(request: Request):
    admin, redirect = guard(request)
    if redirect:
        return redirect
    rows = queries.c1_growth_curve()
    by_level = {}
    for r in rows:
        lv = r["level"]
        if r["cum_playtime_s"] is None:
            continue
        by_level.setdefault(lv, []).append(r["cum_playtime_s"])
    levels = sorted(by_level.keys())
    points = [(lv, sum(by_level[lv]) / len(by_level[lv]) / 3600) for lv in levels]
    chart_svg = charts.line_chart(points, value_fmt=lambda v: f"{v:.1f}h", x_fmt=lambda v: f"Lv{v}",
                                   title="레벨별 평균 누적 플레이시간(실측)") if points else None
    curve_path = os.path.join(STATS_LAB_DIR, "intended-curve.json")
    import json
    intended = {}
    if os.path.exists(curve_path):
        with open(curve_path, encoding="utf-8") as f:
            intended = json.load(f)
    sections = [{
        "heading": "실측 vs 목표 앵커",
        "chart_svg": chart_svg,
        "table_cols": ["level", "avg_hours(실측)"],
        "table_rows": [{"level": lv, "avg_hours(실측)": f"{h:.1f}"} for lv, h in points],
    }]
    return templates.TemplateResponse(request, "listing.html", {
        "request": request, "user": admin, "active": "growth", "page_title": "② 성장곡선",
        "page_intro": "<b>이 페이지가 하는 일</b>: 유저가 각 레벨에 도달할 때까지 실제로 얼마나 "
                      "플레이했는지(누적 플레이타임, AFK 제외)를 보여줍니다. 기획 의도(intended-curve.json)보다 "
                      "너무 빠르면 콘텐츠 소모가 과함, 너무 느리면 성장이 지루하다는 신호일 수 있어요.",
        "page_note": f"목표 앵커(intended-curve.json): {intended.get('anchors', '없음')}",
        "sections": sections,
    })


# ── ③ 경제 ────────────────────────────────────────────────────────
@app.get("/economy", response_class=HTMLResponse)
def economy(request: Request):
    admin, redirect = guard(request)
    if redirect:
        return redirect
    # ★2026-07-28 유저 지적으로 발견: 예전엔 reason만 GROUP BY해서 골드(money)·캐시(cash)·
    # 잠수포인트(afkp)가 전부 한 숫자로 합쳐져 나왔음 — 서로 다른 재화라 섞으면 안 됨. 이제
    # c6_inflation이 cur도 같이 묶어서 반환하니, 재화별로 섹션을 분리해서 렌더링한다.
    all_money_rows = queries.c6_inflation()
    for r in all_money_rows:
        r["net"] = (r["sourced"] or 0) + (r["sunk"] or 0)
    # 순액이 가장 큰 소스(=인플레 유발 주범, 주의 필요)와 가장 큰 싱크(=화폐 회수, 건강한 신호)를
    # 구분해서 표시 — 숫자만 봐서는 "이게 좋은 건지 나쁜 건지" 안 보인다는 피드백(2026-07-28).
    # ★재화별로 따로(전역이 아니라 cur 단위로) 상위/하위를 매겨야 캐시 몇 건이 골드 상위권을 밀어내지 않는다.
    CUR_LABELS = {"money": "골드(money)", "cash": "캐시(cash)", "afkp": "잠수포인트(afkp)"}
    seen_curs = []
    for r in all_money_rows:
        if r["cur"] not in seen_curs:
            seen_curs.append(r["cur"])
    seen_curs.sort(key=lambda c: (c != "money", c))  # 골드를 항상 맨 위로
    money_sections = []
    for cur in seen_curs:
        cur_rows = [r for r in all_money_rows if r["cur"] == cur]
        insights.flag_extremes(cur_rows, "net", good_label="📉 최대 머니싱크(건강)",
                                bad_label="📈 최대 인플레 소스(주의)", n=2, good="low")
        label = CUR_LABELS.get(cur, cur)
        cur_chart = charts.bar_chart(
            [r["reason"] or "(없음)" for r in cur_rows[:15]], [r["net"] or 0 for r in cur_rows[:15]],
            value_fmt=_money_fmt, title=f"{label} — reason별 순액(상위 15)") if cur_rows else None
        cur_table_rows = _fmt_rows(cur_rows, {"sourced": _money_fmt, "sunk": _money_fmt, "n": _num1})
        money_sections.append({
            "heading": f"{label} 사유별 순액",
            "chart_svg": cur_chart,
            "table_cols": ["reason", "sourced", "sunk", "n"],
            "table_rows": cur_table_rows,
        })

    # ── 상점(섬/드릴 등) 품목별 구매/판매(C16) — "섬상점에서 어떤 품목이 얼마나 팔렸고"(2026-07-28 요청) ──
    shop = queries.c16_shop_sales()
    shop_chart = charts.bar_chart(
        [f"[{r['shop']}]{r['item']}" for r in shop[:15]], [r["bought_qty"] or 0 for r in shop[:15]],
        value_fmt=_num1, title="상점별 품목 구매량(상위 15)") if shop else None
    insights.flag_extremes(shop, "bought_qty", good_label="🔥 최다 판매", bad_label="⚠️ 판매 저조", n=2, good="high")
    shop_rows = _fmt_rows(shop, {"bought_qty": _num1, "bought_revenue": _money_fmt,
                                  "sold_qty": _num1, "sold_payout": _money_fmt})

    # ── 유저마켓 품목별 실적(C17) ──
    market_rows_raw = queries.c17_market_by_item()
    market_chart = charts.bar_chart(
        [r["item"] for r in market_rows_raw[:15]], [r["sold"] or 0 for r in market_rows_raw[:15]],
        value_fmt=_num1, title="유저마켓 품목별 판매 건수") if market_rows_raw else None
    insights.flag_extremes(market_rows_raw, "sold", good_label="🔥 잘 팔림", bad_label="⚠️ 안 팔림", n=2, good="high")
    market_rows = _fmt_rows(market_rows_raw, {"listings": _num1, "sold": _num1, "cancelled": _num1,
                                               "expired": _num1, "avg_price": _money_fmt, "avg_sell_min": _num1})

    # ── 직거래 편측(불공정) 탐지(C18) ──
    fairness_raw = queries.c18_trade_fairness(limit=30)
    overview = queries.c18b_trade_overview()
    ov = overview[0] if overview else {"trades": 0, "fully_priced": 0, "total_value_a": 0, "total_value_b": 0}
    for r in fairness_raw:
        if (r.get("ratio") or 0) >= 10:
            r["_flag"], r["_flag_cls"] = "🚨 극단적 편측(사기/실수 의심)", "bad"
        elif (r.get("ratio") or 0) >= 3:
            r["_flag"], r["_flag_cls"] = "⚠️ 편측", "bad"
    fairness_rows = _fmt_rows(fairness_raw, {"ts": _ts_fmt, "value_a": _money_fmt, "value_b": _money_fmt, "ratio": _num1})

    # ── 송금 경로별(C19) ──
    xfer_raw = queries.c19_xfer_by_via()
    xfer_chart = charts.bar_chart([r["via"] for r in xfer_raw], [r["total_amt"] or 0 for r in xfer_raw],
                                   value_fmt=_money_fmt, title="송금 경로별 총액") if xfer_raw else None
    xfer_rows = _fmt_rows(xfer_raw, {"n": _num1, "total_amt": _money_fmt, "total_fee": _money_fmt, "avg_amt": _money_fmt})

    # ── 수표 발행/입금(C20) ──
    check_raw = queries.c20_check_summary()
    check_rows = _fmt_rows(check_raw, {"issued_n": _num1, "issued_value": _money_fmt, "issued_fee": _money_fmt,
                                        "deposited_n": _num1, "deposited_value": _money_fmt,
                                        "outstanding_estimate": _money_fmt})

    sections = [
        *money_sections,
        {
            "heading": "상점 품목별 구매/판매(C16)",
            "chart_svg": shop_chart,
            "table_cols": ["shop", "item", "bought_qty", "bought_revenue", "sold_qty", "sold_payout"],
            "table_rows": shop_rows,
        },
        {
            "heading": "유저마켓 품목별 실적(C17)",
            "chart_svg": market_chart,
            "table_cols": ["item", "listings", "sold", "cancelled", "expired", "avg_price", "avg_sell_min"],
            "table_rows": market_rows,
        },
        {
            "heading": f"직거래 편측 탐지(C18) — 전체 {_num1(ov['trades'])}건 중 "
                       f"{_num1(ov['fully_priced'])}건 가치 100% 확인(상위 {len(fairness_rows)}건 표시)",
            "table_cols": ["ts", "player_a", "player_b", "value_a", "value_b", "ratio"],
            "table_rows": fairness_rows,
        },
        {
            "heading": "송금 경로별(C19)",
            "chart_svg": xfer_chart,
            "table_cols": ["via", "n", "total_amt", "total_fee", "avg_amt"],
            "table_rows": xfer_rows,
        },
        {
            "heading": "수표 발행/입금 요약(C20)",
            "table_cols": ["issued_n", "issued_value", "issued_fee", "deposited_n", "deposited_value", "outstanding_estimate"],
            "table_rows": check_rows,
        },
    ]
    return templates.TemplateResponse(request, "listing.html", {
        "request": request, "user": admin, "active": "economy", "page_title": "③ 경제",
        "page_intro": "<b>이 페이지가 하는 일</b>: 서버 화폐가 어디서 생기고(소스) 어디로 사라지는지(싱크) "
                      "사유별로 집계합니다. 소스만 계속 커지고 싱크가 못 따라가면 인플레(돈 가치 하락)로 이어지니, "
                      "판매·마켓·직거래·송금·수표까지 돈이 오가는 모든 경로의 균형을 보는 페이지예요.",
        "page_note": "C6 — 골드/캐시/잠수포인트 등 재화 종류별로 섹션이 분리되어 있습니다(서로 다른 "
                     "재화라 합산하면 안 됨, 2026-07-28 수정). 🟢초록 배지=화폐 회수(건강) · "
                     "🔴빨강 배지=화폐 발행 최대치(인플레 주의) — 배지는 재화별로 따로 매겨짐.<br>"
                     "<b>C16</b> shop=island(섬상점)/recommend(추천상점)/drill(드릴상점) 등 · "
                     "bought/sold=구매·되팔기 수량·금액.<br>"
                     "<b>C17</b> listings=등록건수 · sold/cancelled/expired=결과별 건수 · "
                     "avg_sell_min=등록부터 판매까지 평균 소요분(높으면 안 팔리고 오래 걸린다는 뜻).<br>"
                     "<b>C18</b> value_a/value_b=양쪽이 주고받은 아이템의 실제 가치 합(수표 액면가+물고기 시세만 "
                     "반영, 일반 아이템은 가격을 몰라 계산에서 제외) · ratio=더 비싼 쪽/싼 쪽 배율 — 높을수록 "
                     "한쪽이 손해보는 거래(사기·실수·우회증여 의심). 일반 아이템이 섞인 거래는 애초에 이 표에 안 나옴"
                     "(양쪽 다 100% 가치를 아는 거래만 표시).<br>"
                     "<b>C19</b> via=transfer_cmd(/송금, 수수료 10%) vs money_cmd(/돈 송금·보내기, 수수료 0%) — "
                     "money_cmd 총액이 크면 그만큼 수수료를 우회한 규모.<br>"
                     "<b>C20</b> outstanding_estimate=발행됐지만 아직 안 들어온 수표 액면 추정치(직거래로 계속 "
                     "돌아다닐 수 있어 정확한 유통량은 아니고 추세 참고용).",
        "sections": sections,
    })


# ── ④ 장비 ────────────────────────────────────────────────────────
@app.get("/equipment", response_class=HTMLResponse)
def equipment(request: Request):
    admin, redirect = guard(request)
    if redirect:
        return redirect
    perf = queries.c3_loadout_perf(min_catches=20)
    # ★avg_price는 "이 로드아웃 가격"이 아니라 "이 로드아웃으로 낚은 물고기의 평균 판매가"다(C3 쿼리
    # 정의) — high_rate가 높으면 avg_price도 같이 오르는 종속 관계라, 둘을 나눠 "가성비"라 부르면
    # 의미가 왜곡된다(2026-07-28 피드백으로 발견한 버그, 예전엔 이렇게 잘못 계산했었음). 그래서
    # 판정은 high_rate 단독 상위/하위로만 한다 — 산점도는 어디까지나 "가격대별로 고등급이 잘
    # 나오는지" 참고용 분포도.
    insights.flag_extremes(perf, "high_rate", good_label="👍 고등급 잘 나옴", bad_label="⚠️ 고등급 저조",
                            n=2, good="high")
    scatter_pts = [(r["avg_price"] or 0, r["high_rate"] or 0, f"{r['rod']}+{r['enh']}") for r in perf]
    scatter_colors = [r.get("_flag_cls") for r in perf]
    scatter_svg = charts.scatter_chart(
        scatter_pts, x_fmt=lambda v: f"{v:,.1f}원", y_fmt=lambda v: f"{v * 100:.1f}%",
        title="이 조합으로 낚은 물고기의 평균판매가(x) vs 고등급비율(y) — 점에 마우스를 올리면 조합명 표시",
        x_label="평균판매가(원)", y_label="고등급비율(%)", colors=scatter_colors,
    ) if scatter_pts else None
    perf_rows = _fmt_rows(perf, {"catches": _num1, "avg_price": _money_fmt, "high_rate": _pct1})

    zero = queries.c5_zero_purchase()
    for r in zero:
        if (r["n"] or 0) == 0:
            r["_flag"], r["_flag_cls"] = "⚠️ 구매 0건(사장 후보)", "bad"
    zero_rows = _fmt_rows(zero, {"n": _num1})

    sections = [
        {"heading": "로드아웃별 실적(20캐치 이상)", "chart_svg": scatter_svg,
         "table_cols": ["rod", "enh", "catches", "avg_price", "high_rate"], "table_rows": perf_rows},
        {"heading": "부품 구매 하위(0건 후보)", "table_cols": ["name", "n"], "table_rows": zero_rows},
    ]
    return templates.TemplateResponse(request, "listing.html", {
        "request": request, "user": admin, "active": "equipment", "page_title": "④ 장비",
        "page_intro": "<b>이 페이지가 하는 일</b>: 낚싯대+강화 조합별로 실제로 고등급이 잘 나오는지 비교합니다. "
                      "아래 산점도는 조합 하나당 점 하나 — <b>오른쪽</b>일수록 그 조합으로 낚은 물고기 값어치가 "
                      "높고, <b>위쪽</b>일수록 고등급(S/M/L/G)이 잘 나온 겁니다. 초록 점=고등급이 특히 잘 나오는 "
                      "조합, 빨강 점=유난히 안 나오는 조합(강화 확률이나 등급업 로직에 문제가 있을 수 있음).",
        "page_note": "avg_price=이 조합으로 낚은 물고기의 평균 판매가(로드아웃 가격 아님) · "
                     "high_rate=그 중 S/M/L/G 고등급 비율 · catches=표본수(20건 미만은 제외). "
                     "C3·C5 — 구매 실적 하위 품목은 하단 표.",
        "sections": sections,
    })


# ── ⑤ 생산 ────────────────────────────────────────────────────────
@app.get("/production", response_class=HTMLResponse)
def production(request: Request):
    admin, redirect = guard(request)
    if redirect:
        return redirect

    # ── 작물(C4) ──
    crops = queries.c4_crop_roi()
    crop_chart = charts.bar_chart([r["crop"] for r in crops[:15]], [r["qty_per_sec"] or 0 for r in crops[:15]],
                                   value_fmt=lambda v: f"{_num1(v)}/s", title="작물별 초당 산출량") if crops else None
    insights.flag_extremes(crops, "qty_per_sec", good_label="👍 생산성 최고", bad_label="⚠️ 생산성 최저", n=2, good="high")
    crop_rows = _fmt_rows(crops, {"harvests": _num1, "avg_qty": _num1, "avg_grow_s": _num1, "qty_per_sec": _num1})

    # ── 채집(C11) ──
    forage = queries.c11_forage_performance()
    forage_chart = charts.bar_chart([r["forage_type"] or "?" for r in forage], [(r["ok_rate"] or 0) * 100 for r in forage],
                                     value_fmt=lambda v: f"{v:.1f}%", title="채집물별 성공률") if forage else None
    insights.flag_extremes(forage, "ok_rate", good_label="👍 성공률 높음", bad_label="⚠️ 성공률 낮음", n=2, good="high")
    forage_rows = _fmt_rows(forage, {"n": _num1, "ok_rate": _pct1, "rare_rate": _pct1,
                                      "avg_qty": _num1, "avg_dur_s": _num1})

    # ── 통발(C12) ──
    traps = queries.c12_trap_performance()
    trap_chart = charts.bar_chart([r["region"] or "?" for r in traps], [(r["break_rate"] or 0) * 100 for r in traps],
                                   value_fmt=lambda v: f"{v:.1f}%", title="지역별 통발 파손율") if traps else None
    insights.flag_extremes(traps, "break_rate", bad_label="⚠️ 파손율 높음", n=2, min_rows=3, good="low")
    trap_rows = _fmt_rows(traps, {"placed": _num1, "collected": _num1, "broken": _num1,
                                   "avg_catch_per_collect": _num1, "avg_wait_s": _num1, "break_rate": _pct1})

    # ── 광질 — 드릴 티어(C13) ──
    drills = queries.c13_mining_by_tier()
    drill_chart = charts.bar_chart([r["tier"] or "?" for r in drills], [r["ore_per_flush"] or 0 for r in drills],
                                    value_fmt=lambda v: f"{_num1(v)}개/분", title="드릴 티어별 분당 채굴량") if drills else None
    insights.flag_extremes(drills, "ore_per_flush", good_label="👍 티어값 함", bad_label="⚠️ 티어값 부족", n=1, good="high")
    drill_rows = _fmt_rows(drills, {"flushes": _num1, "total_ore": _num1, "avg_chain": _num1,
                                     "total_xp": _num1, "ore_per_flush": _num1})

    # ── 광물 종류별 채굴량(C14, 드릴+섬광산 통합) ──
    ores = queries.c14_ore_breakdown()
    ore_chart = charts.bar_chart([r["ore"] for r in ores[:10]], [r["qty"] or 0 for r in ores[:10]],
                                  value_fmt=_num1, title="광물별 채굴량(상위 10)") if ores else None
    insights.flag_extremes(ores, "qty", good_label="🔥 최다 채굴", n=2, min_rows=4, good="high")
    ore_rows = _fmt_rows(ores, {"qty": _num1, "events": _num1})

    # ── 섬 광산 요약(C15) ──
    imine = queries.c15_island_mine_summary()
    # capped_rate 제거(2026-08-17) — 「채굴 한도에 걸린 비율」이라 설명했지만 그런 한도는 없었다.
    # 실체는 분당 200개 초과 시 켜지는 매크로 의심 진단 플래그였고, 해석이 거꾸로였다.
    imine_rows = _fmt_rows(imine, {"flushes": _num1, "total_ore": _num1, "total_xp": _num1})

    sections = [
        {"heading": "작물 ROI(C4)", "chart_svg": crop_chart,
         "table_cols": ["crop", "harvests", "avg_qty", "avg_grow_s", "qty_per_sec"], "table_rows": crop_rows},
        {"heading": "채집 성과(C11)", "chart_svg": forage_chart,
         "table_cols": ["forage_type", "n", "ok_rate", "rare_rate", "avg_qty", "avg_dur_s"], "table_rows": forage_rows},
        {"heading": "통발 지역별 실적(C12)", "chart_svg": trap_chart,
         "table_cols": ["region", "placed", "collected", "broken", "avg_catch_per_collect", "avg_wait_s", "break_rate"],
         "table_rows": trap_rows},
        {"heading": "드릴 티어별 채굴(C13)", "chart_svg": drill_chart,
         "table_cols": ["tier", "flushes", "total_ore", "avg_chain", "total_xp", "ore_per_flush"], "table_rows": drill_rows},
        {"heading": "광물별 채굴량(C14)", "chart_svg": ore_chart,
         "table_cols": ["ore", "qty", "events"], "table_rows": ore_rows},
        {"heading": "섬 광산 요약(C15)",
         "table_cols": ["flushes", "total_ore", "total_xp"], "table_rows": imine_rows},
    ]
    return templates.TemplateResponse(request, "listing.html", {
        "request": request, "user": admin, "active": "production", "page_title": "⑤ 생산",
        "page_intro": "<b>이 페이지가 하는 일</b>: 작물·채집·통발·드릴광질·섬광산 등 "
                      "\"시간을 들여 자원을 얻는\" 모든 활동의 효율을 비교합니다. 어떤 항목이 유독 "
                      "좋거나 나쁘면 그쪽 확률/산출량 밸런스를 다시 봐야 한다는 신호예요.",
        "page_note": "<b>작물</b> qty_per_sec=avg_qty÷avg_grow_s(시간당 산출, 높을수록 좋음).<br>"
                     "<b>채집</b> ok_rate=시도 대비 성공 비율 · rare_rate=성공 중 희귀 발견 비율.<br>"
                     "<b>통발</b> break_rate=설치 대비 파손 비율(높으면 내구도 확인 필요) · "
                     "avg_wait_s=회수까지 평균 대기시간.<br>"
                     "<b>드릴</b> ore_per_flush=분당(60초 집계 1건당) 채굴 개수.<br>"
                     "<b>섬 광산</b> total_ore=집계 구간의 광물 총량 · total_xp=광질 경험치 총량.",
        "sections": sections,
    })


# ── ⑥ 퀘스트 ───────────────────────────────────────────────────────
@app.get("/quests", response_class=HTMLResponse)
def quests(request: Request):
    admin, redirect = guard(request)
    if redirect:
        return redirect
    rows = queries.c2_quest_efficiency()
    chart_svg = charts.bar_chart([r["qid"] for r in rows[:15]], [r["money_per_sec"] or 0 for r in rows[:15]],
                                  value_fmt=lambda v: f"{_num1(v)}/s", title="퀘스트별 원/초(상위 15)") if rows else None
    insights.flag_extremes(rows, "money_per_sec", good_label="👍 혜자 퀘스트", bad_label="⚠️ 비효율 퀘스트",
                            n=2, good="high")
    table_rows = _fmt_rows(rows, {"n": _num1, "avg_money": _money_fmt, "avg_dur_s": _num1, "money_per_sec": _num1})
    sections = [{"heading": "퀘스트 원/분 랭킹(C2)", "chart_svg": chart_svg,
                 "table_cols": ["qid", "n", "avg_money", "avg_dur_s", "money_per_sec"], "table_rows": table_rows}]
    return templates.TemplateResponse(request, "listing.html", {
        "request": request, "user": admin, "active": "quests", "page_title": "⑥ 퀘스트",
        "page_intro": "<b>이 페이지가 하는 일</b>: 퀘스트별로 걸리는 시간 대비 보상이 얼마나 되는지 "
                      "줄 세워서 보여줍니다. 위쪽(👍)은 시간 대비 보상이 후한 \"혜자\" 퀘스트, "
                      "아래쪽(⚠️)은 들이는 시간에 비해 보상이 짠 퀘스트 — 밸런스 조정 후보입니다.",
        "page_note": "avg_money=평균 보상금 · avg_dur_s=평균 소요시간(초) · "
                     "money_per_sec=avg_money÷avg_dur_s(시간당 보상, 높을수록 혜자).",
        "sections": sections,
    })


# ── ⑦ 카지노 ───────────────────────────────────────────────────────
@app.get("/casino", response_class=HTMLResponse)
def casino(request: Request):
    admin, redirect = guard(request)
    if redirect:
        return redirect
    rows = queries.c8_casino_rtp()
    chart_svg = charts.bar_chart([r["game"] for r in rows], [(r["realized_rtp"] or 0) * 100 for r in rows],
                                  value_fmt=lambda v: f"{v:.1f}%", title="게임별 실현 RTP(%)") if rows else None
    # RTP 1.0 초과 = 플레이어가 순이익(하우스 손해, 밸런스 붕괴 위험) / 0.85 미만 = 하우스가 과도하게
    # 유리(플레이어 이탈 위험) / 그 사이 = 정상 범위 — 절대 기준 판정(2026-07-28 피드백).
    insights.flag_band(rows, "realized_rtp", good_range=(0.85, 1.0), good_label="✅ 정상 범위",
                        low_label="⚠️ 과도한 하우스이득", high_label="⚠️ 플레이어 순이익(하우스 손해)")
    table_rows = _fmt_rows(rows, {"total_bet": _money_fmt, "total_net": _money_fmt, "total_rake": _money_fmt,
                                   "rounds": _num1, "realized_rtp": _pct1})
    sections = [{"heading": "게임별 실현 RTP(C8)", "chart_svg": chart_svg,
                 "table_cols": ["game", "total_bet", "total_net", "total_rake", "rounds", "realized_rtp"],
                 "table_rows": table_rows}]
    return templates.TemplateResponse(request, "listing.html", {
        "request": request, "user": admin, "active": "casino", "page_title": "⑦ 카지노",
        "page_intro": "<b>이 페이지가 하는 일</b>: 카지노 게임별로 \"플레이어가 건 돈 대비 실제로 얼마를 "
                      "돌려받았는지\"(RTP)를 봅니다. RTP 100%면 본전, 그보다 낮으면 하우스(서버)가 유리, "
                      "높으면 플레이어가 유리 — 너무 낮으면 유저 이탈, 너무 높으면 서버 화폐가 새는 구멍이 됩니다.",
        "page_note": "total_net=라운드별 플레이어 순손익 합(양수=플레이어 순이익) · total_rake=하우스 수수료 총액 · "
                     "realized_rtp=1+(total_net÷total_bet), 1.0=본전. "
                     "정상 범위는 RTP 85~100%로 가정(하우스 소폭 유리) — 밸런스 목표치가 따로 있으면 조정 필요.",
        "sections": sections,
    })


# ── ⑧ RNG ─────────────────────────────────────────────────────────
@app.get("/rng", response_class=HTMLResponse)
def rng(request: Request):
    admin, redirect = guard(request)
    if redirect:
        return redirect
    fish = queries.c9_rng_fish()
    enh = queries.c9_rng_enhance()
    fish_svg = charts.line_chart(
        [(r["p_bucket"], r["realized_rate"]) for r in fish],
        value_fmt=lambda v: f"{v * 100:.1f}%", x_fmt=lambda v: f"{v * 100:.1f}%",
        title="점선(이론값)과 실선(실측)이 겹칠수록 정상",
        x_label="명목 확률 구간", y_label="실제 성공률", reference_diagonal=True,
    ) if fish else None
    enh_svg = charts.line_chart(
        [(r["p_bucket"], r["realized_rate"]) for r in enh],
        value_fmt=lambda v: f"{v * 100:.1f}%", x_fmt=lambda v: f"{v * 100:.1f}%",
        title="점선(이론값)과 실선(실측)이 겹칠수록 정상",
        x_label="명목 확률 구간", y_label="실제 성공률", reference_diagonal=True,
    ) if enh else None
    # 대각선(y=x)에서 크게 벗어난 구간 = 명목 확률과 실측이 안 맞는 이상치(RNG 버그 의심 지점).
    insights.flag_deviation(fish, "realized_rate", "p_bucket", label="⚠️ 명목과 괴리", n=2, threshold=0.05)
    insights.flag_deviation(enh, "realized_rate", "p_bucket", label="⚠️ 명목과 괴리", n=2, threshold=0.05)
    fish_rows = _fmt_rows(fish, {"p_bucket": _pct1, "n": _num1, "realized_rate": _pct1})
    enh_rows = _fmt_rows(enh, {"p_bucket": _pct1, "n": _num1, "realized_rate": _pct1})

    # C10 — "몇강에서 몇번 있었고 몇번 실패했고"(2026-07-28 요청): C9가 확률구간 기준이라면 이건
    # 실제 강화 단계(from) 기준 — 레벨업 페이지의 게이트/난이도 확인에 더 직접적으로 쓰인다.
    by_level = queries.c10_enhance_by_level()
    level_svg = charts.bar_chart(
        [f"{r['enh_from']}강" for r in by_level], [r["success_rate"] or 0 for r in by_level],
        value_fmt=lambda v: f"{v * 100:.1f}%", title="강화 단계별 성공률(실측)",
    ) if by_level else None
    # 실측 성공률이 평균 명목확률(avg_p_succ)에서 크게 벗어난 단계 = 확인 필요.
    insights.flag_deviation(by_level, "success_rate", "avg_p_succ", label="⚠️ 명목과 괴리", n=2, threshold=0.05)
    level_rows = _fmt_rows(by_level, {"n": _num1, "success": _num1, "fail": _num1,
                                       "avg_p_succ": _pct1, "success_rate": _pct1})

    sections = [
        {"heading": "낚시 등급업 RNG(C9)", "chart_svg": fish_svg,
         "table_cols": ["p_bucket", "n", "realized_rate"], "table_rows": fish_rows},
        {"heading": "강화 성공 RNG(C9)", "chart_svg": enh_svg,
         "table_cols": ["p_bucket", "n", "realized_rate"], "table_rows": enh_rows},
        {"heading": "강화 단계별(몇강) 시도/성공/실패(C10)", "chart_svg": level_svg,
         "table_cols": ["enh_from", "n", "success", "fail", "avg_p_succ", "success_rate"],
         "table_rows": level_rows},
    ]
    page_intro = (
        "<b>이 페이지가 하는 일</b>: 게임이 \"이번 시도는 65% 확률로 성공\"이라고 계산해놓고, "
        "실제로 그 65%짜리 시도들을 전부 모아봤을 때 <b>진짜로 65% 근처로 성공했는지</b> 검증합니다. "
        "만약 65%라고 약속해놓고 실제로는 40%밖에 성공 안 했다면 확률 계산에 버그가 있다는 뜻이에요.<br>"
        "그래프는 <b>같은 확률 구간(p_bucket)끼리 묶어서</b> 점선(이론상 이래야 함)과 실선(실제 결과)을 "
        "겹쳐 그린 것 — 두 선이 거의 포개지면 정상, 실선이 점선에서 크게 벗어나 있으면 그 구간이 의심스러운 겁니다."
    )
    return templates.TemplateResponse(request, "listing.html", {
        "request": request, "user": admin, "active": "rng", "page_title": "⑧ RNG 검증",
        "page_intro": page_intro,
        "page_note": "p_bucket=명목 확률을 5%p 단위로 묶은 구간 · n=그 구간 시도 건수 · "
                     "realized_rate=그 구간에서 실제로 성공(등급업/강화성공)한 비율. "
                     "5%p 이상 벗어난 구간은 표에 ⚠️ 배지로 표시.<br>"
                     "맨 아래 표(C10)는 확률구간이 아니라 <b>실제 강화 단계(enh_from=몇강에서 시도했는지)</b> "
                     "기준 — success/fail=그 단계에서의 성공/실패(유지+하락 합산) 건수, "
                     "avg_p_succ=그 단계 시도들의 평균 명목 성공확률, success_rate=실제 성공률.",
        "sections": sections,
    })


# ── ⑨ 유저 상세 ────────────────────────────────────────────────────
@app.get("/user", response_class=HTMLResponse)
def user_detail(request: Request, name: str = ""):
    admin, redirect = guard(request)
    if redirect:
        return redirect
    ctx = {"request": request, "user": admin, "active": "user", "name": name, "rows": [], "events": [], "error": "", "players": []}
    import sqlite3
    if not os.path.exists(queries.STATS_DB):
        ctx["error"] = "stats.db가 없습니다."
        return templates.TemplateResponse(request, "user.html", ctx)
    c = sqlite3.connect(queries.STATS_DB)
    c.row_factory = sqlite3.Row
    if not name:
        # 유저 상세는 정확한 닉네임을 알아야만 조회 가능했음 — 2026-07-29 피드백:
        # 처음 오면 아무도 못 고르니 최근 스냅샷 날짜의 플레이어 목록을 미리 보여준다(클릭해서 조회).
        latest = c.execute("SELECT MAX(date) d FROM player_snapshot").fetchone()
        if latest and latest["d"]:
            ctx["players"] = [dict(r) for r in c.execute(
                "SELECT name, level, total_fish, money FROM player_snapshot "
                "WHERE date=? AND name IS NOT NULL ORDER BY level DESC, total_fish DESC LIMIT 100",
                (latest["d"],))]
        c.close()
        return templates.TemplateResponse(request, "user.html", ctx)
    row = c.execute("SELECT uuid FROM player_snapshot WHERE name=? COLLATE NOCASE ORDER BY date DESC LIMIT 1",
                     (name,)).fetchone()
    if not row:
        ctx["error"] = f"유저를 찾을 수 없습니다: {name}"
        c.close()
        return templates.TemplateResponse(request, "user.html", ctx)
    uuid = row["uuid"]
    ctx["rows"] = [dict(r) for r in c.execute(
        "SELECT date,playtime_s,casts,catches,best_grade,money_in,money_out,quests_done,crafts,submits "
        "FROM day_player WHERE uuid=? ORDER BY date DESC LIMIT 7", (uuid,))]
    c.close()
    for f in queries._event_months():
        path = os.path.join(queries.DATA_DIR, f)
        try:
            ec = sqlite3.connect(path)
            ec.row_factory = sqlite3.Row
            for r in ec.execute("SELECT ts,type,ctx FROM ev WHERE uuid=? ORDER BY ts DESC LIMIT 30", (uuid,)):
                ctx["events"].append({
                    "time": time.strftime("%m-%d %H:%M", time.localtime(r["ts"] / 1000)),
                    "type": r["type"], "ctx": (r["ctx"] or "")[:120],
                })
            ec.close()
            if ctx["events"]:
                break
        except Exception:
            continue
    return templates.TemplateResponse(request, "user.html", ctx)


# ── ⑩ 커버리지 ─────────────────────────────────────────────────────
@app.get("/coverage", response_class=HTMLResponse)
def coverage(request: Request):
    admin, redirect = guard(request)
    if redirect:
        return redirect
    rows = queries.c7_usage(7)
    insights.flag_extremes(rows, "n", bad_label="⚠️ 이용률 저조(사각지대 후보)", n=3, min_rows=6, good="high")
    table_rows = _fmt_rows(rows, {"n": _num1, "players": _num1})
    sections = [{"heading": "최근 7일 이벤트 타입별 발생량(day_type)",
                 "table_cols": ["type", "n", "players"], "table_rows": table_rows}]
    return templates.TemplateResponse(request, "listing.html", {
        "request": request, "user": admin, "active": "coverage", "page_title": "⑩ 커버리지",
        "page_intro": "<b>이 페이지가 하는 일</b>: 어떤 기능이 최근 7일간 실제로 쓰이고 있는지 이벤트 "
                      "타입별로 셉니다. 건수가 유난히 적은 기능은 유저가 존재를 모르거나(홍보 부족), 접근이 "
                      "불편하거나, 이미 매력이 없는 콘텐츠일 수 있어요 — ⚠️ 배지가 그 후보들입니다.",
        "page_note": "n=최근 7일 발생 건수 · players=그 이벤트를 1번이라도 발생시킨 순유저 수. "
                     "상세 사각지대 판정(명령/GUI 대조)은 인게임 /통계 커버리지가 더 정확 — 이 페이지는 최근 7일 이벤트 타입 전수 목록.",
        "sections": sections,
    })


# ── ⑪ 통합 콘솔 (Phase 6, §10-6 — admin 역할 전용) ────────────────────
@app.get("/console", response_class=HTMLResponse)
def console_page(request: Request):
    admin, err = guard_admin(request)
    if err:
        return err
    csrf = _csrf_token(request)
    flash = request.session.pop("console_flash", None)
    recent = admin_actions.recent_audit_log(20)
    for r in recent:
        r["time"] = time.strftime("%m-%d %H:%M", time.localtime(r["ts"] / 1000))
    return templates.TemplateResponse(request, "console.html", {
        "request": request, "user": admin, "active": "console",
        "csrf": csrf, "catalog": admin_actions.ACTION_CATALOG, "recent": recent, "flash": flash,
        "rcon_enabled": bool(os.environ.get("RCON_PASSWORD")),
    })


@app.post("/console/action")
async def console_action(request: Request):
    admin, err = guard_admin(request)
    if err:
        return err
    form = await request.form()
    # §10-6 쓰기 액션 원칙② — CSRF 토큰 불일치는 무조건 거부(임의 요청 재생 방지).
    if form.get("csrf") != request.session.get("csrf"):
        return HTMLResponse(
            "<h1>403</h1><p>CSRF 토큰이 일치하지 않습니다 — 새로고침 후 다시 시도하세요.</p>",
            status_code=403)
    action = form.get("action", "")
    player = (form.get("player") or "").strip()
    reason = (form.get("reason") or "").strip()
    entry = admin_actions.ACTION_CATALOG.get(action)
    if not entry:
        # 카탈로그에 없는 action 값은 폼 조작으로만 만들 수 있음 — 원칙① 그대로 거부.
        request.session["console_flash"] = {"ok": False, "text": f"알 수 없는 액션: {action}"}
        return redirect("/console", status_code=303)
    try:
        result = admin_actions.run_action(action, player, reason)
        flash = {"ok": True, "text": f"{entry['label']} 실행 완료 — {result or '(응답 없음)'}"}
    except Exception as e:
        result = str(e)
        flash = {"ok": False, "text": f"{entry['label']} 실패 — {result}"}
    admin_actions.record(admin, action, player or "-", {"reason": reason}, result)
    request.session["console_flash"] = flash
    return redirect("/console")


# ── ⑫ 멤버십/환불 관리 — Discord admin 권한 + statsweb CSRF + 로컬 결제 API ──
@app.get("/membership", response_class=HTMLResponse)
async def membership_page(request: Request):
    admin, err = guard_admin(request)
    if err:
        return err
    error, rows, bank_orders = "", [], []
    try:
        rows = (await vip_billing.refunds()).get("rows", [])
        bank_orders = (await vip_billing.bank_transfer_orders()).get("rows", [])
    except vip_billing.VipBillingUnavailable as exc:
        error = str(exc)
    for row in rows:
        if row.get("created_at"):
            row["created_at"] = str(row["created_at"]).replace("T", " ").replace("Z", "")[:16]
    for row in bank_orders:
        for field in ("created_at", "transfer_deadline"):
            if row.get(field):
                row[field] = str(row[field]).replace("T", " ").replace("Z", "")[:16]
    return templates.TemplateResponse(request, "membership.html", {
        "request": request, "user": admin, "active": "membership", "csrf": _csrf_token(request),
        "rows": rows, "bank_orders": bank_orders, "error": error,
        "flash": request.session.pop("membership_flash", None),
    })


@app.post("/membership/refund/{refund_id}")
async def membership_refund(request: Request, refund_id: str):
    admin, err = guard_admin(request)
    if err:
        return err
    form = await request.form()
    if form.get("csrf") != request.session.get("csrf"):
        return HTMLResponse("<h1>403</h1><p>CSRF 토큰이 일치하지 않습니다.</p>", status_code=403)
    try:
        result = await vip_billing.decide_refund(refund_id, form.get("action", ""), admin["name"])
        request.session["membership_flash"] = {"ok": True, "text": result.get("message", "환불 요청을 처리했습니다.")}
    except (ValueError, vip_billing.VipBillingUnavailable) as exc:
        request.session["membership_flash"] = {"ok": False, "text": str(exc)}
    return redirect("/membership", status_code=303)


@app.post("/membership/bank-transfer/{order_id}")
async def membership_bank_transfer(request: Request, order_id: str):
    admin, err = guard_admin(request)
    if err:
        return err
    form = await request.form()
    if form.get("csrf") != request.session.get("csrf"):
        return HTMLResponse("<h1>403</h1><p>CSRF 토큰이 일치하지 않습니다.</p>", status_code=403)
    try:
        result = await vip_billing.decide_bank_transfer_order(order_id, form.get("action", ""), admin["name"])
        request.session["membership_flash"] = {"ok": True, "text": result.get("message", "입금 주문을 처리했습니다.")}
    except (ValueError, vip_billing.VipBillingUnavailable) as exc:
        request.session["membership_flash"] = {"ok": False, "text": str(exc)}
    return redirect("/membership", status_code=303)


@app.get("/playerdata", response_class=HTMLResponse)
def playerdata_view(request: Request, name: str = ""):
    admin, err = guard_admin(request)
    if err:
        return err
    import json as jsonlib
    import sqlite3
    ctx = {"request": request, "user": admin, "active": "console", "name": name, "json_text": "", "error": ""}
    if not PLAYERDATA_DIR:
        ctx["error"] = "PLAYERDATA_DIR가 설정되지 않았습니다(.env)."
    elif name:
        uuid = None
        if os.path.exists(queries.STATS_DB):
            c = sqlite3.connect(queries.STATS_DB)
            row = c.execute(
                "SELECT uuid FROM player_snapshot WHERE name=? COLLATE NOCASE ORDER BY date DESC LIMIT 1",
                (name,)).fetchone()
            c.close()
            uuid = row[0] if row else None
        if not uuid:
            ctx["error"] = f"유저를 찾을 수 없습니다(스냅샷에 없음): {name}"
        else:
            path = os.path.join(PLAYERDATA_DIR, f"{uuid}.json")
            if not os.path.exists(path):
                ctx["error"] = f"playerdata 파일이 없습니다: {uuid}.json"
            else:
                with open(path, encoding="utf-8") as f:
                    data = jsonlib.load(f)
                ctx["json_text"] = jsonlib.dumps(data, ensure_ascii=False, indent=2)
                ctx["uuid"] = uuid
    return templates.TemplateResponse(request, "playerdata.html", ctx)


@app.get("/banlist", response_class=HTMLResponse)
def banlist_view(request: Request):
    admin, err = guard_admin(request)
    if err:
        return err
    import json as jsonlib
    rows, error = [], ""
    if not BANNED_PLAYERS_FILE:
        error = "BANNED_PLAYERS_FILE이 설정되지 않았습니다(.env)."
    elif not os.path.exists(BANNED_PLAYERS_FILE):
        error = f"밴 목록 파일이 없습니다: {BANNED_PLAYERS_FILE}"
    else:
        with open(BANNED_PLAYERS_FILE, encoding="utf-8") as f:
            rows = jsonlib.load(f)
    return templates.TemplateResponse(request, "banlist.html", {
        "request": request, "user": admin, "active": "console", "rows": rows, "error": error,
    })


@app.get("/healthz")
def healthz():
    return {"ok": True}
