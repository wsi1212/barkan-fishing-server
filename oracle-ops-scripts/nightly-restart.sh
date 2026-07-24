#!/usr/bin/env bash
# =====================================================================
# 바르칸 prod 예방적 새벽 재시작 — 장시간 가동 누수(메모리·엔티티) 정리
#   접속자 0명일 때만 조용히 재시작. 1명이라도 있으면 skip(다음 밤).
#   RCON 무응답이면 skip(프리즈는 워치독 담당).
# env: DRY=1(재시작 안 함) / RESTART_CMD / WEBHOOK_FILE
# =====================================================================
set -uo pipefail
DIR=~/mcserver/scripts
WEBHOOK_FILE="${WEBHOOK_FILE:-$DIR/discord-webhook.url}"
RESTART_CMD="${RESTART_CMD:-sudo systemctl restart mcserver}"
LABEL="[바르칸 prod]"
log(){ echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) [nightly] $*"; }
notify(){ [ -s "$WEBHOOK_FILE" ] || return 0; local u m p; u=$(cat "$WEBHOOK_FILE"); m="$LABEL $1"
  p=$(python3 -c "import json,sys;print(json.dumps({'content':sys.argv[1]}))" "$m")
  curl -sf -m 10 -H 'Content-Type: application/json' -d "$p" "$u" >/dev/null 2>&1 || true; }

out=$("$DIR/rcon.py" list 2>/dev/null) || { log "RCON 무응답 — skip (워치독 담당)"; exit 0; }
n=$(printf '%s' "$out" | grep -oE 'are [0-9]+' | grep -oE '[0-9]+' | head -1); n=${n:-0}
if [ "$n" -gt 0 ]; then
  log "${n}명 접속중 — 예방 재시작 skip"
  exit 0
fi
log "0명 — 예방 재시작 진행"
if [ "${DRY:-0}" = "1" ]; then log "DRY: would restart"; exit 0; fi
notify "🌙 정기 예방 재시작 (접속자 0명, 메모리·엔티티 정리). 1~2분 후 복귀합니다."
eval "$RESTART_CMD"
log "restarted"
