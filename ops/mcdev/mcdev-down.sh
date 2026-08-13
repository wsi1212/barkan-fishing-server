#!/usr/bin/env bash
# dev 즉시 내리기. 폰에서 한 줄로 끝나게 짧게 유지한다.
set -uo pipefail
cd "$(dirname "$0")" && source ./mcdev-lib.sh

if [[ -f "$TIMER_PID_FILE" ]]; then
  kill "$(<"$TIMER_PID_FILE")" 2>/dev/null && log "타이머 데몬 정지"
  rm -f "$TIMER_PID_FILE"
fi

if ! dev_running; then
  log "dev는 이미 내려가 있다"
  rm -f "$DEADLINE_FILE"
  # tmux 세션 껍데기만 남은 경우 정리
  tmux kill-session -t "$MCDEV_TMUX" 2>/dev/null && log "빈 tmux 세션 정리"
  exit 0
fi

log "dev 종료 (save-all flush → stop)"
dev_rcon "say §c[dev] 수동 종료" >/dev/null
dev_rcon "save-all flush" >/dev/null; sleep 5
dev_rcon "stop" >/dev/null

for _ in $(seq 1 60); do dev_java_running || break; sleep 2; done
if dev_java_running; then
  log "⚠ stop 이 안 먹었다 — 강제 종료"
  dev_java_kill
  sleep 3
fi
tmux kill-session -t "$MCDEV_TMUX" 2>/dev/null
rm -f "$DEADLINE_FILE" "$JAVA_PID_FILE"
log "dev 종료 완료"
notify "⚫ **dev 종료** (수동)"
