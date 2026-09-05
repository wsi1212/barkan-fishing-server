#!/usr/bin/env bash
# =====================================================================
# 바르칸 prod 재시작 전 월드 백업 (cron 20:50 UTC = 05:50 KST)
#
# 정기 재시작의 접속 불가 시간을 줄이기 위해 큰 월드 tar 두 개를 서버가 켜진
# 상태에서 미리 만든다. 각 백업 전에 save-all flush를 수행하고 gzip -t까지 통과한
# 경우에만 오늘 날짜 마커를 남긴다. 06:00 유지보수는 그 마커가 있을 때에만 이
# 아카이브를 사용하며, 하나라도 실패하거나 끝나지 않았으면 기존처럼 정지 중
# 백업으로 폴백한다.
#
# playerdata(BlockShip)는 종료 저장 직후가 가장 정확하고 약 4초밖에 걸리지 않아
# 06:00 유지보수에 남긴다.
# =====================================================================
set -uo pipefail

DIR="$HOME/mcserver/scripts"
BAKDIR="$HOME/mcserver/backups"
LOCK="$BAKDIR/.pre-restart-backup.lock"
MARK="$BAKDIR/.pre-restart-backup-ready"
LOG="$BAKDIR/local.log"
TIMEOUT=${BACKUP_TIMEOUT:-600}
LABEL="[바르칸 prod]"
TODAY=$(TZ=Asia/Seoul date +%Y-%m-%d)

log(){ echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) [pre-restart-backup] $*" >>"$LOG"; }
notify(){
  local webhook payload
  webhook="$DIR/discord-webhook.url"
  [ -s "$webhook" ] || return 0
  payload=$(python3 -c "import json,sys; print(json.dumps({'content':sys.argv[1]}))" "$1")
  curl -sf -m 10 -H 'Content-Type: application/json' -d "$payload" "$(cat "$webhook")" >/dev/null 2>&1 || true
}
fail(){
  log "실패: $1"
  notify "$LABEL 🔴 05:50 재시작 전 월드 백업 실패: $1. 06:00에 정지 중 백업으로 자동 폴백합니다."
  exit 1
}

mkdir -p "$BAKDIR"
exec 9>"$LOCK"
if ! flock -n 9; then
  log "이미 실행 중 — 중복 실행 생략"
  exit 0
fi

# 마커가 오늘 것이라도 매일 새 tar를 검증해야 한다. 중간 실패 시에는 마커를
# 지워 06:00에 반드시 정지 중 폴백이 일어나게 한다.
rm -f "$MARK"
for group in main islands; do
  timeout "$TIMEOUT" "$DIR/local-backup.sh" "$group" >>"$LOG" 2>&1
  rc=$?
  [ "$rc" = "0" ] || {
    [ "$rc" = "124" ] && fail "$group 이 ${TIMEOUT}초 제한을 초과"
    fail "$group (rc=$rc)"
  }
  log "완료: $group (live)"
done

tmp="$MARK.$$.tmp"
printf '%s\n' "$TODAY" >"$tmp"
mv -f "$tmp" "$MARK"
log "완료: $TODAY 마커 생성 — 06:00은 월드 tar를 재사용"
