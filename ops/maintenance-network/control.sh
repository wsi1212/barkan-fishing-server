#!/usr/bin/env bash
# Local control helper. Install beside /home/ubuntu/mc-network/control on prod.
set -euo pipefail

ACTION=${1:?usage: control.sh <drain|resume|status|wait-drained|wait-idle>}
CONTROL_DIR=${BARKAN_MAINTENANCE_CONTROL_DIR:-/home/ubuntu/mc-network/control}
REQUEST_FILE="$CONTROL_DIR/request"
STATUS_FILE="$CONTROL_DIR/status.json"

write_request(){
  local value="$1" temporary="$CONTROL_DIR/request.$$"
  mkdir -p "$CONTROL_DIR"
  printf '%s\n' "$value" > "$temporary"
  mv -f "$temporary" "$REQUEST_FILE"
}
read_state(){
  python3 - "$STATUS_FILE" <<'PY'
import json, sys, time
data = json.load(open(sys.argv[1], encoding="utf-8"))
age = time.time() * 1000 - int(data.get("updatedEpochMs", 0))
if age > 5000:
    raise SystemExit("stale proxy status")
print(json.dumps(data, ensure_ascii=False, separators=(",", ":")))
PY
}
wait_for(){
  local wanted="$1" players_field="$2" state players
  for _wait in $(seq 1 90); do
    state=$(read_state 2>/dev/null || true)
    if [ -n "$state" ]; then
      players=$(python3 -c 'import json,sys; d=json.loads(sys.argv[1]); print(d.get(sys.argv[2],-1))' "$state" "$players_field")
      if [ "$(python3 -c 'import json,sys; print(json.loads(sys.argv[1]).get("state",""))' "$state")" = "$wanted" ] \
          && [ "$players" = "0" ]; then
        printf '%s\n' "$state"
        return 0
      fi
    fi
    sleep 1
  done
  echo "timeout waiting for $wanted" >&2
  return 1
}

case "$ACTION" in
  drain) write_request drain ;;
  resume) write_request resume ;;
  status) read_state ;;
  wait-drained) wait_for MAINTENANCE mainPlayers ;;
  wait-idle) wait_for IDLE waitingPlayers ;;
  *) echo "unknown action: $ACTION" >&2; exit 2 ;;
esac
