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
import os
import sys
import time

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

STATS_LAB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "stats-lab")
sys.path.insert(0, os.path.abspath(STATS_LAB_DIR))
import queries  # noqa: E402  (stats-lab/queries.py — 웹·CLI 공유 쿼리 모듈)
import charts  # noqa: E402

data_dir_override = os.environ.get("STATSLAB_DATA_DIR")
if data_dir_override:
    queries.set_data_dir(data_dir_override)

import auth  # noqa: E402

app = FastAPI(title="바르칸 통계")
app.add_middleware(SessionMiddleware, secret_key=os.environ.get("SESSION_SECRET", "dev-only-insecure-key"))

templates = Jinja2Templates(directory=os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates"))


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


def _money_fmt(v):
    return f"{v:,.0f}원"


# ── 인증 ─────────────────────────────────────────────────────────
@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request, error: str = ""):
    if request.session.get("admin"):
        return RedirectResponse("/")
    return templates.TemplateResponse(request, "login.html", {"request": request, "error": error})


@app.get("/login/discord")
def login_discord(request: Request):
    state = auth.new_state()
    request.session["oauth_state"] = state
    return RedirectResponse(auth.build_authorize_url(state))


@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login")


@app.get("/callback")
async def callback(request: Request, code: str = "", state: str = "", error: str = ""):
    if error:
        return RedirectResponse(f"/login?error={error}")
    if state != request.session.get("oauth_state"):
        return RedirectResponse("/login?error=state_mismatch")
    token = await auth.exchange_code(code)
    if not token:
        return RedirectResponse("/login?error=token_exchange_failed")
    user = await auth.fetch_discord_user(token)
    if not user:
        return RedirectResponse("/login?error=user_fetch_failed")
    admin = auth.resolve_admin(user.get("id"))
    if not admin:
        return RedirectResponse("/login?error=not_an_admin")
    request.session["admin"] = admin
    return RedirectResponse("/")


def guard(request: Request):
    admin = _require_admin(request)
    if not admin:
        return None, RedirectResponse("/login")
    return admin, None


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

    ordered = sorted(rows, key=lambda r: r["date"])
    players_chart = charts.bar_chart([r["date"][5:] for r in ordered], [r["players"] for r in ordered],
                                      value_fmt=lambda v: f"{v:.0f}", title=None)
    net_chart = charts.bar_chart([r["date"][5:] for r in ordered],
                                  [(r["money_in"] or 0) - (r["money_out"] or 0) for r in ordered],
                                  value_fmt=_money_fmt, title=None)
    health = queries.collection_health()
    return templates.TemplateResponse(request, "home.html", {
        "request": request, "user": admin, "active": "home", "days": days,
        "today": today, "today_playtime_h": today_playtime_h,
        "today_net_str": _money_fmt(today_net), "today_casino_str": _money_fmt(today_casino),
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
        "page_note": f"목표 앵커(intended-curve.json): {intended.get('anchors', '없음')}",
        "sections": sections,
    })


# ── ③ 경제 ────────────────────────────────────────────────────────
@app.get("/economy", response_class=HTMLResponse)
def economy(request: Request):
    admin, redirect = guard(request)
    if redirect:
        return redirect
    rows = queries.c6_inflation()
    chart_svg = charts.bar_chart([r["reason"] or "(없음)" for r in rows[:15]],
                                  [(r["sourced"] or 0) + (r["sunk"] or 0) for r in rows[:15]],
                                  value_fmt=_money_fmt, title="reason별 순액(상위 15)") if rows else None
    sections = [{
        "heading": "money.txn reason별 순액",
        "chart_svg": chart_svg,
        "table_cols": ["reason", "sourced", "sunk", "n"],
        "table_rows": rows,
    }]
    return templates.TemplateResponse(request, "listing.html", {
        "request": request, "user": admin, "active": "economy", "page_title": "③ 경제",
        "page_note": "C6 — 일별 순발행/자산분포는 player_snapshot 누적 시 확장 예정.",
        "sections": sections,
    })


# ── ④ 장비 ────────────────────────────────────────────────────────
@app.get("/equipment", response_class=HTMLResponse)
def equipment(request: Request):
    admin, redirect = guard(request)
    if redirect:
        return redirect
    perf = queries.c3_loadout_perf(min_catches=20)
    scatter_pts = [(r["avg_price"] or 0, r["high_rate"] or 0, f"{r['rod']}+{r['enh']}") for r in perf]
    scatter_svg = charts.scatter_chart(scatter_pts, x_fmt=lambda v: f"{v:,.0f}원", y_fmt=lambda v: f"{v:.0%}",
                                        title="평균판매가(x) vs 고등급비율(y)") if scatter_pts else None
    zero = queries.c5_zero_purchase()
    sections = [
        {"heading": "로드아웃별 실적(20캐치 이상)", "chart_svg": scatter_svg,
         "table_cols": ["rod", "enh", "catches", "avg_price", "high_rate"], "table_rows": perf},
        {"heading": "부품 구매 하위(0건 후보)", "table_cols": ["name", "n"], "table_rows": zero},
    ]
    return templates.TemplateResponse(request, "listing.html", {
        "request": request, "user": admin, "active": "equipment", "page_title": "④ 장비",
        "page_note": "C3·C5 — 가격 대비 실측 성능, 구매 실적 하위 품목.",
        "sections": sections,
    })


# ── ⑤ 생산 ────────────────────────────────────────────────────────
@app.get("/production", response_class=HTMLResponse)
def production(request: Request):
    admin, redirect = guard(request)
    if redirect:
        return redirect
    crops = queries.c4_crop_roi()
    chart_svg = charts.bar_chart([r["crop"] for r in crops[:15]], [r["qty_per_sec"] or 0 for r in crops[:15]],
                                  value_fmt=lambda v: f"{v:.3f}/s", title="작물별 초당 산출량") if crops else None
    sections = [{"heading": "작물 ROI(C4)", "chart_svg": chart_svg,
                 "table_cols": ["crop", "harvests", "avg_qty", "avg_grow_s", "qty_per_sec"], "table_rows": crops}]
    return templates.TemplateResponse(request, "listing.html", {
        "request": request, "user": admin, "active": "production", "page_title": "⑤ 생산",
        "page_note": "채집/통발/광질 세부는 이벤트 누적 후 확장(현재 crop.harvest 기반 C4만).",
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
                                  value_fmt=lambda v: f"{v:.1f}/s", title="퀘스트별 원/초(상위 15)") if rows else None
    sections = [{"heading": "퀘스트 원/분 랭킹(C2)", "chart_svg": chart_svg,
                 "table_cols": ["qid", "n", "avg_money", "avg_dur_s", "money_per_sec"], "table_rows": rows}]
    return templates.TemplateResponse(request, "listing.html", {
        "request": request, "user": admin, "active": "quests", "page_title": "⑥ 퀘스트",
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
    sections = [{"heading": "게임별 실현 RTP(C8)", "chart_svg": chart_svg,
                 "table_cols": ["game", "total_bet", "total_net", "total_rake", "rounds", "realized_rtp"], "table_rows": rows}]
    return templates.TemplateResponse(request, "listing.html", {
        "request": request, "user": admin, "active": "casino", "page_title": "⑦ 카지노",
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
    fish_svg = charts.line_chart([(r["p_bucket"], r["realized_rate"]) for r in fish],
                                  value_fmt=lambda v: f"{v:.0%}", x_fmt=lambda v: f"{v:.2f}",
                                  title="등급업 명목p(x) vs 실측률(y)") if fish else None
    enh_svg = charts.line_chart([(r["p_bucket"], r["realized_rate"]) for r in enh],
                                 value_fmt=lambda v: f"{v:.0%}", x_fmt=lambda v: f"{v:.2f}",
                                 title="강화 명목p_succ(x) vs 실측률(y)") if enh else None
    sections = [
        {"heading": "낚시 등급업 RNG(C9)", "chart_svg": fish_svg,
         "table_cols": ["p_bucket", "n", "realized_rate"], "table_rows": fish},
        {"heading": "강화 성공 RNG(C9)", "chart_svg": enh_svg,
         "table_cols": ["p_bucket", "n", "realized_rate"], "table_rows": enh},
    ]
    return templates.TemplateResponse(request, "listing.html", {
        "request": request, "user": admin, "active": "rng", "page_title": "⑧ RNG 검증",
        "page_note": "대각선(y=x)에 가까울수록 명목 확률과 실측이 일치.",
        "sections": sections,
    })


# ── ⑨ 유저 상세 ────────────────────────────────────────────────────
@app.get("/user", response_class=HTMLResponse)
def user_detail(request: Request, name: str = ""):
    admin, redirect = guard(request)
    if redirect:
        return redirect
    ctx = {"request": request, "user": admin, "active": "user", "name": name, "rows": [], "events": [], "error": ""}
    if not name:
        return templates.TemplateResponse(request, "user.html", ctx)
    import sqlite3
    if not os.path.exists(queries.STATS_DB):
        ctx["error"] = "stats.db가 없습니다."
        return templates.TemplateResponse(request, "user.html", ctx)
    c = sqlite3.connect(queries.STATS_DB)
    c.row_factory = sqlite3.Row
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
    sections = [{"heading": "최근 7일 이벤트 타입별 발생량(day_type)",
                 "table_cols": ["type", "n", "players"], "table_rows": rows}]
    return templates.TemplateResponse(request, "listing.html", {
        "request": request, "user": admin, "active": "coverage", "page_title": "⑩ 커버리지",
        "page_note": "상세 사각지대 판정(명령/GUI 대조)은 인게임 /통계 커버리지가 더 정확 — 이 페이지는 최근 7일 이벤트 타입 전수 목록.",
        "sections": sections,
    })


@app.get("/healthz")
def healthz():
    return {"ok": True}
