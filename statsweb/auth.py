"""
auth.py — Discord OAuth2 로그인 (stats-system-plan.md §10-5).

플로우: /login → Discord authorize URL로 리다이렉트 → 사용자 승인 → /callback?code=...
→ 코드를 토큰으로 교환 → /users/@me로 유저 정보 조회 → admins.json(discord_id→{name,role})에
있으면 세션에 담고 홈으로, 없으면 거부 페이지.

비밀번호 저장·회원가입·재설정 플로우가 통째로 없다 — 신원 확인은 전부 Discord가 대신하고,
우리는 "이 Discord ID가 admins.json에 있는가"만 본다. 어드민 추가/회수는 그 파일 한 줄 편집.
"""
import json
import logging
import os
import secrets
from urllib.parse import urlencode

import httpx

logger = logging.getLogger("statsweb.auth")

DISCORD_API = "https://discord.com/api"
AUTHORIZE_URL = f"{DISCORD_API}/oauth2/authorize"
TOKEN_URL = f"{DISCORD_API}/oauth2/token"
ME_URL = f"{DISCORD_API}/users/@me"

ADMINS_FILE = os.environ.get("STATSWEB_ADMINS_FILE", os.path.join(os.path.dirname(os.path.abspath(__file__)), "admins.json"))


def _config():
    client_id = os.environ.get("DISCORD_CLIENT_ID", "")
    client_secret = os.environ.get("DISCORD_CLIENT_SECRET", "")
    redirect_uri = os.environ.get("DISCORD_REDIRECT_URI", "http://127.0.0.1:8080/callback")
    return client_id, client_secret, redirect_uri


def load_admins():
    """admins.json: {"discord_id": {"name": "닉네임", "role": "viewer"|"admin"}}."""
    if not os.path.exists(ADMINS_FILE):
        return {}
    with open(ADMINS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def build_authorize_url(state):
    client_id, _, redirect_uri = _config()
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "identify",
        "state": state,
    }
    return f"{AUTHORIZE_URL}?{urlencode(params)}"


def new_state():
    return secrets.token_urlsafe(24)


async def exchange_code(code):
    """authorization code → access token. 실패 시 None."""
    client_id, client_secret, redirect_uri = _config()
    data = {
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri,
    }
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(TOKEN_URL, data=data, headers={"Content-Type": "application/x-www-form-urlencoded"})
    except httpx.HTTPError as exc:
        logger.warning("Discord OAuth token exchange request failed: %s", type(exc).__name__)
        return None

    if r.status_code != 200:
        # Discord's response distinguishes invalid_client, invalid_grant and
        # redirect_uri mismatches. Log only the safe diagnostic fields; never
        # write the authorization code, client secret, or response body.
        try:
            payload = r.json()
        except ValueError:
            payload = {}
        logger.warning(
            "Discord OAuth token exchange rejected: status=%s error=%s description=%s redirect_uri=%s",
            r.status_code,
            payload.get("error", "unknown"),
            payload.get("error_description", ""),
            redirect_uri,
        )
        return None

    try:
        access_token = r.json().get("access_token")
    except ValueError:
        logger.warning("Discord OAuth token exchange returned invalid JSON: status=%s", r.status_code)
        return None
    if not access_token:
        logger.warning("Discord OAuth token exchange returned no access token: status=%s", r.status_code)
    return access_token


async def fetch_discord_user(access_token):
    """access token → {id, username, ...}. 실패 시 None."""
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(ME_URL, headers={"Authorization": f"Bearer {access_token}"})
        if r.status_code != 200:
            return None
        return r.json()


def resolve_admin(discord_id):
    """discord_id가 admins.json에 있으면 {name, role, discord_id} 반환, 없으면 None."""
    admins = load_admins()
    entry = admins.get(str(discord_id))
    if entry is None:
        return None
    return {"discord_id": str(discord_id), "name": entry.get("name", ""), "role": entry.get("role", "viewer")}
