#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# dev 안전망 (cron */5)
#
# mcdev-up.sh 의 타이머 데몬은 프로세스다 — 죽으면 dev가 영원히 돌아간다.
# 군 복무 중에 잊힌 dev가 prod와 자원 경쟁을 몇 주 하는 게 최악의 시나리오라
# cron 으로 시한을 한 번 더 강제한다. 타이머와 독립적으로 동작한다.
#
# 설치:
#   */5 * * * * flock -n ~/mcdev/.reaper.lock ~/mcserver/scripts/mcdev-reaper.sh
# ─────────────────────────────────────────────────────────────────────────────
set -uo pipefail
cd "$(dirname "$0")" && source ./mcdev-lib.sh

GRACE_MIN="${MCDEV_ORPHAN_GRACE:-15}"   # 시한 파일 없는 고아 dev 를 봐주는 시간

dev_running || exit 0

NOW=$(date +%s)
REASON=""

if [[ -f "$DEADLINE_FILE" ]]; then
  DEADLINE=$(<"$DEADLINE_FILE")
  if [[ "$DEADLINE" =~ ^[0-9]+$ ]] && [[ $NOW -gt $DEADLINE ]]; then
    OVER=$(( (NOW - DEADLINE) / 60 ))
    # 타이머가 살아있고 방금 지난 거면 타이머가 처리하도록 2분 봐준다
    if [[ $OVER -ge 2 ]]; then
      REASON="시한을 ${OVER}분 초과했는데 살아있다 (타이머 데몬이 죽은 듯)"
    fi
  fi
else
  # 시한 파일이 없는데 돌고 있다 = 누가 손으로 띄웠거나 파일이 날아갔다
  START=$(stat -c %Y "$MCDEV_ROOT/logs/latest.log" 2>/dev/null || echo "$NOW")
  UP=$(( (NOW - START) / 60 ))
  REASON="시한 파일 없이 돌고 있다 (${UP}분 경과, 유예 ${GRACE_MIN}분)"
  [[ $UP -lt $GRACE_MIN ]] && REASON=""
fi

[[ -z "$REASON" ]] && exit 0

log "리퍼 발동: $REASON"
dev_rcon "say §c[dev] 안전망에 의해 종료" >/dev/null
dev_rcon "save-all flush" >/dev/null; sleep 5
dev_rcon "stop" >/dev/null
for _ in $(seq 1 45); do dev_java_running || break; sleep 2; done
if dev_java_running; then
  log "리퍼: stop 실패 — 강제 종료"
  dev_java_kill
fi
tmux kill-session -t "$MCDEV_TMUX" 2>/dev/null
rm -f "$DEADLINE_FILE" "$TIMER_PID_FILE" "$JAVA_PID_FILE"
log "리퍼: dev 종료 완료"
notify "🧹 **dev 강제 종료 (안전망)** — $REASON"
