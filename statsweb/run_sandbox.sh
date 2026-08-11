#!/bin/bash
# statsweb 로컬 샌드박스 실행 — 가짜 데이터로 전 페이지를 Discord 로그인 없이 바로 열람.
# prod(.env)와 완전히 격리(별도 세션시크릿·별도 포트·별도 데이터 디렉토리) — prod 설정을 안 건드림.
set -e
cd "$(dirname "$0")"

DATA_DIR="../stats-lab/sandbox-data"
if [ ! -d "$DATA_DIR" ]; then
  echo "샌드박스 데이터가 없어 먼저 생성합니다..."
  (cd ../stats-lab && python3 seed_sandbox.py)
fi

if [ ! -d venv ]; then
  echo "venv가 없어 먼저 만듭니다..."
  python3 -m venv venv
  venv/bin/pip install -q -r requirements.txt
fi

export STATSLAB_DATA_DIR="$(cd "$DATA_DIR" && pwd)"
export SANDBOX_MODE=1
export SESSION_SECRET=sandbox-only-insecure
export BASE_PATH=
export DISCORD_CLIENT_ID=sandbox
export DISCORD_CLIENT_SECRET=sandbox
export DISCORD_REDIRECT_URI=http://127.0.0.1:8090/callback

# Phase 6(§10-6) 콘솔 데모용 — RCON_PASSWORD를 절대 여기서 설정하지 않는다(비워두면
# rcon_client.RconDisabled로 안전하게 막힘). 진짜 프로덕션 서버에 실수로 명령이 나가는 걸
# 원천 차단하는 샌드박스의 핵심 안전장치 — 지우거나 값 채우지 말 것.
export RCON_PASSWORD=
export PLAYERDATA_DIR="$(cd ../stats-lab/sandbox-fixtures/playerdata && pwd)"
export BANNED_PLAYERS_FILE="$(cd ../stats-lab/sandbox-fixtures && pwd)/banned-players.json"

echo "샌드박스 서버 실행: http://127.0.0.1:8090 (Ctrl+C로 종료)"
venv/bin/uvicorn app:app --reload --port 8090
