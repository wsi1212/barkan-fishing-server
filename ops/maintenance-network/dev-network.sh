#!/usr/bin/env bash
# Manage the local dev Velocity + waiting Paper + existing main Paper topology.
set -euo pipefail

MAIN_ROOT=${BARKAN_DEV_MAIN_ROOT:-/Users/user/Library/Application Support/feather/player-server/servers/07de2d81-991a-47e2-b62d-06c0d1b5150a}
NETWORK_ROOT=${BARKAN_DEV_NETWORK_ROOT:-$MAIN_ROOT/dev-maintenance-network}
CONTROL_DIR="$NETWORK_ROOT/control"
LOG_DIR="$NETWORK_ROOT/logs"
CONTROL="$NETWORK_ROOT/bin/control.sh"
DEV_MC=${BARKAN_DEV_MC:-/Users/user/dev-mc.sh}
WAITING_SESSION=barkan-dev-waiting
VELOCITY_SESSION=barkan-dev-velocity
SUPERVISOR_SESSION=barkan-dev-supervisor

# control.sh defaults to the production path. Keep every dev invocation pinned to
# this isolated control directory, including nested restart/supervisor calls.
export BARKAN_MAINTENANCE_CONTROL_DIR="$CONTROL_DIR"

find_java(){
  local selected="" selected_version=0 candidate version
  for candidate in "/Users/user/Library/Application Support/minecraft/jre/"zulu*/Contents/Home/bin/java; do
    [ -x "$candidate" ] || continue
    version=$("$candidate" -version 2>&1 | head -1 | grep -oE '"[0-9]+' | tr -d '"')
    [ -n "$version" ] || continue
    if [ "$version" -ge 21 ] && [ "$version" -gt "$selected_version" ]; then
      selected="$candidate"; selected_version="$version"
    fi
  done
  [ -n "$selected" ] || return 1
  printf '%s\n' "$selected"
}

JAVA=${BARKAN_DEV_JAVA:-$(find_java)}
install -d "$LOG_DIR" "$CONTROL_DIR"

listening_tcp(){ lsof -nP -iTCP:"$1" -sTCP:LISTEN >/dev/null 2>&1; }
listening_udp(){ lsof -nP -iUDP:"$1" >/dev/null 2>&1; }
pid_alive(){ [ -s "$1" ] && kill -0 "$(cat "$1")" 2>/dev/null; }

wait_for_log(){
  local file="$1" pattern="$2" seconds="$3"
  for _wait in $(seq 1 "$seconds"); do
    grep -q "$pattern" "$file" 2>/dev/null && return 0
    sleep 1
  done
  echo "기동 타임아웃: $file" >&2
  return 1
}

start_waiting(){
  listening_tcp 25568 && return 0
  : > "$LOG_DIR/waiting.log"
  tmux kill-session -t "$WAITING_SESSION" >/dev/null 2>&1 || true
  local command
  printf -v command 'echo $$ > %q; exec %q -Dterminal.jline=false -Dterminal.ansi=false -Xms256M -Xmx512M -XX:+UseG1GC -jar paper.jar --nogui > %q 2>&1' \
    "$NETWORK_ROOT/waiting.pid" "$JAVA" "$LOG_DIR/waiting.log"
  tmux new-session -d -s "$WAITING_SESSION" -c "$NETWORK_ROOT/waiting" "$command"
  wait_for_log "$LOG_DIR/waiting.log" 'Done (' 90
}

start_velocity(){
  if listening_tcp 25565; then
    if pid_alive "$NETWORK_ROOT/velocity.pid"; then
      return 0
    fi
    echo "Velocity 포트 25565를 다른 프로세스가 사용 중" >&2
    return 1
  fi
  : > "$LOG_DIR/velocity.log"
  tmux kill-session -t "$VELOCITY_SESSION" >/dev/null 2>&1 || true
  local command
  printf -v command 'echo $$ > %q; exec env BARKAN_MAINTENANCE_CONTROL_DIR=%q BARKAN_SHIP_MARKER_DIR=%q BARKAN_MAIN_SERVER=main BARKAN_WAITING_SERVER=waiting BARKAN_MAINTENANCE_TEST_COMMANDS=true %q -Dterminal.jline=false -Dterminal.ansi=false -Xms256M -Xmx768M -XX:+UseG1GC -jar velocity.jar > %q 2>&1' \
    "$NETWORK_ROOT/velocity.pid" "$CONTROL_DIR" "$NETWORK_ROOT/shared/ship-entities" \
    "$JAVA" "$LOG_DIR/velocity.log"
  tmux new-session -d -s "$VELOCITY_SESSION" -c "$NETWORK_ROOT/velocity" "$command"
  for _wait in $(seq 1 60); do
    listening_tcp 25565 && listening_udp 19132 && "$CONTROL" status >/dev/null 2>&1 && return 0
    sleep 1
  done
  echo "Velocity 기동 실패: $LOG_DIR/velocity.log" >&2
  return 1
}

start_supervisor(){
  pid_alive "$NETWORK_ROOT/supervisor.pid" && return 0
  rm -f "$CONTROL_DIR/dev-action"
  tmux kill-session -t "$SUPERVISOR_SESSION" >/dev/null 2>&1 || true
  local command
  printf -v command 'echo $$ > %q; exec %q supervise > %q 2>&1' \
    "$NETWORK_ROOT/supervisor.pid" "$0" "$LOG_DIR/supervisor.log"
  tmux new-session -d -s "$SUPERVISOR_SESSION" "$command"
}

stop_pid(){
  local file="$1" pid
  pid_alive "$file" || { rm -f "$file"; return 0; }
  pid=$(cat "$file")
  kill "$pid" 2>/dev/null || true
  for _wait in $(seq 1 30); do
    kill -0 "$pid" 2>/dev/null || { rm -f "$file"; return 0; }
    sleep 1
  done
  echo "프로세스 종료 지연: $pid ($file)" >&2
  return 1
}

wait_main_reachable(){
  for _wait in $(seq 1 90); do
    if python3 - "$CONTROL_DIR/status.json" <<'PY'
import json, sys, time
try:
    data = json.load(open(sys.argv[1], encoding="utf-8"))
    fresh = time.time() * 1000 - int(data.get("updatedEpochMs", 0)) < 5000
    raise SystemExit(0 if fresh and data.get("mainReachable") is True else 1)
except Exception:
    raise SystemExit(1)
PY
    then return 0; fi
    sleep 1
  done
  return 1
}

restart_backend(){
  "$CONTROL" drain
  "$CONTROL" wait-drained >/dev/null
  "$DEV_MC" restart
  wait_main_reachable
  "$CONTROL" resume
  "$CONTROL" wait-idle >/dev/null
  echo "dev Paper 재시작·자동 복귀 완료"
}

supervise(){
  while true; do
    if [ -s "$CONTROL_DIR/dev-action" ]; then
      action=$(tr -d '\r\n' < "$CONTROL_DIR/dev-action")
      rm -f "$CONTROL_DIR/dev-action"
      case "$action" in
        restart)
          if restart_backend; then
            printf '%s restart OK\n' "$(date '+%Y-%m-%dT%H:%M:%S%z')" > "$CONTROL_DIR/dev-last-result"
          else
            printf '%s restart FAILED — users remain in waiting\n' "$(date '+%Y-%m-%dT%H:%M:%S%z')" \
              > "$CONTROL_DIR/dev-last-result"
          fi
          ;;
      esac
    fi
    sleep 0.5
  done
}

start_all(){
  for required in "$NETWORK_ROOT/velocity/velocity.jar" "$NETWORK_ROOT/waiting/paper.jar" "$CONTROL"; do
    [ -s "$required" ] || { echo "dev network 미설치: $required" >&2; exit 2; }
  done
  start_waiting
  start_velocity
  "$DEV_MC" start
  wait_main_reachable
  "$CONTROL" resume
  start_supervisor
  echo "dev network 준비 완료 — Java localhost:25565 / Bedrock UDP 19132"
}

stop_all(){
  "$DEV_MC" stop || true
  stop_pid "$NETWORK_ROOT/supervisor.pid" || true
  stop_pid "$NETWORK_ROOT/velocity.pid" || true
  stop_pid "$NETWORK_ROOT/waiting.pid" || true
  tmux kill-session -t "$SUPERVISOR_SESSION" >/dev/null 2>&1 || true
  tmux kill-session -t "$VELOCITY_SESSION" >/dev/null 2>&1 || true
  tmux kill-session -t "$WAITING_SESSION" >/dev/null 2>&1 || true
}

status(){
  printf 'main='; listening_tcp 25567 && echo active || echo inactive
  printf 'velocity='; listening_tcp 25565 && echo active || echo inactive
  printf 'waiting='; listening_tcp 25568 && echo active || echo inactive
  printf 'bedrock='; listening_udp 19132 && echo active || echo inactive
  "$CONTROL" status 2>/dev/null || true
  [ ! -s "$CONTROL_DIR/dev-last-result" ] || cat "$CONTROL_DIR/dev-last-result"
}

case "${1:-}" in
  start) start_all ;;
  stop) stop_all ;;
  restart-backend) restart_backend ;;
  drain) "$CONTROL" drain ;;
  resume) "$CONTROL" resume ;;
  status) status ;;
  supervise) supervise ;;
  *) echo "usage: dev-network.sh <start|stop|restart-backend|drain|resume|status>" >&2; exit 2 ;;
esac
