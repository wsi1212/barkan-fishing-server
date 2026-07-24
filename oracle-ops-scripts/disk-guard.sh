#!/usr/bin/env bash
# =====================================================================
# 바르칸 prod 디스크 가드레일 — 디스크 풀로 인한 서버 크래시 방지
#   매시간 사용률 체크:
#     85% 이상 → Discord 경고 (에피소드당 1회)
#     92% 이상 → 오래된 로컬 백업 자동 삭제로 88% 아래까지 확보 + 알림
#   ★라이브 데이터는 절대 안 건드림. 삭제 대상 = 로컬 백업 tar뿐(오프사이트는 무사).
# env: USAGE=<숫자>(테스트용 강제 사용률) / DRY=1(삭제 안 함) / WEBHOOK_FILE
# =====================================================================
set -uo pipefail
DIR=~/mcserver/scripts
BK=~/mcserver/backups
WEBHOOK_FILE="${WEBHOOK_FILE:-$DIR/discord-webhook.url}"
LABEL="[바르칸 prod]"
WARN=85; CRIT=92; TARGET=88
MARK="$DIR/.diskguard_warned"
log(){ echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) [diskguard] $*"; }
notify(){ [ -s "$WEBHOOK_FILE" ] || return 0; local u m p; u=$(cat "$WEBHOOK_FILE"); m="$LABEL $1"
  p=$(python3 -c "import json,sys;print(json.dumps({'content':sys.argv[1]}))" "$m")
  curl -sf -m 10 -H 'Content-Type: application/json' -d "$p" "$u" >/dev/null 2>&1 || true; }
cur(){ echo "${USAGE:-$(df / | awk 'NR==2{print $5}' | tr -d %)}"; }

usage=$(cur)
log "disk ${usage}%"

if [ "$usage" -ge "$CRIT" ]; then
  notify "🔴 디스크 ${usage}% 위험 — 오래된 로컬 백업 자동 삭제로 공간 확보 시도."
  deleted=""
  while [ "$(cur)" -ge "$TARGET" ]; do
    # 오래된 것부터: localmain(큼) 2개 이상일 때 초과분 → 없으면 localislands 초과분
    cand=$(ls -1t "$BK"/localmain-*.tar.gz 2>/dev/null | tail -n +2 | tail -1)
    [ -z "$cand" ] && cand=$(ls -1t "$BK"/localislands-*.tar.gz 2>/dev/null | tail -n +2 | tail -1)
    [ -z "$cand" ] && { log "더 삭제할 로컬 백업 없음 — 확보 한계"; break; }
    if [ "${DRY:-0}" = "1" ]; then log "DRY: would delete $(basename "$cand")"; deleted="$deleted $(basename "$cand")"; break; fi
    rm -f "$cand"; log "삭제: $(basename "$cand")"; deleted="$deleted $(basename "$cand")"
  done
  notify "🧹 정리 완료 → 디스크 $(cur)%. 삭제:${deleted:- 없음}"
  touch "$MARK"
elif [ "$usage" -ge "$WARN" ]; then
  if [ ! -f "$MARK" ]; then
    notify "⚠️ 디스크 ${usage}% — 주의. ${CRIT}% 도달 시 오래된 로컬 백업을 자동 정리합니다."
    touch "$MARK"
  fi
  log "warn (marker set)"
else
  rm -f "$MARK"   # 정상 복귀 → 경고 재무장
fi
