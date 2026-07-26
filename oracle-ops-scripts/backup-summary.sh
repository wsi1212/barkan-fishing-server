#!/usr/bin/env bash
# =====================================================================
# 바르칸 prod 백업 요약 — 하루치 백업 성공을 한 번에 묶어 Discord 발송.
#   각 백업 스크립트는 성공 시 상태파일에 한 줄만 누적(즉시 알림 X).
#   이 스크립트가 cron 23:00 UTC(=08:00 KST, 모든 백업 후)에 한 번 요약 발송 → 상태파일 비움.
#   ★실패는 각 백업이 즉시 개별 🔴 알림(요약 대상 아님) — 중요 신호는 실시간 유지.
# env: STATUS_FILE / WEBHOOK_FILE (테스트용)
# =====================================================================
set -uo pipefail
DIR=~/mcserver/scripts
STATUS_FILE=${STATUS_FILE:-$HOME/mcserver/backups/.backup-status}
WEBHOOK_FILE=${WEBHOOK_FILE:-$DIR/discord-webhook.url}
LABEL="[바르칸 prod]"

notify(){  # $1=전체 메시지(멀티라인 가능)
  [ -s "$WEBHOOK_FILE" ] || return 0
  local u p; u=$(cat "$WEBHOOK_FILE")
  p=$(python3 -c "import json,sys; print(json.dumps({'content':sys.argv[1]}))" "$1")
  curl -sf -m 10 -H 'Content-Type: application/json' -d "$p" "$u" >/dev/null 2>&1 || true
}

if [ ! -s "$STATUS_FILE" ]; then
  echo "$(date -u +%H:%M) 성공 기록 없음 — 요약 생략"
  exit 0
fi

count=$(grep -c . "$STATUS_FILE")
body=$(cat "$STATUS_FILE")
today=$(date -u +%Y-%m-%d)
msg="$LABEL 📦 백업 요약 ($today · ${count}건 성공)
$body"

notify "$msg"
> "$STATUS_FILE"          # 발송 후 비움
echo "$(date -u +%H:%M) 요약 발송 완료 (${count}건)"
