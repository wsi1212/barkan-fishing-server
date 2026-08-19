#!/usr/bin/env bash
# Apply a mobile resource-pack promotion with a short warning and a full restart.
set -euo pipefail

MC_ROOT="${MC_ROOT:-$HOME/mcserver}"
SCRIPT_DIR="$MC_ROOT/scripts"
WEBHOOK_FILE="$SCRIPT_DIR/discord-webhook.url"
GRACE="${GRACE:-60}"
RELEASE="${RESOURCEPACK_RELEASE:-mobile resource pack}"

notify() {
  [[ -s "$WEBHOOK_FILE" ]] || return 0
  local url
  url=$(<"$WEBHOOK_FILE")
  curl -fsS --max-time 15 -H 'Content-Type: application/json' \
    -d "$(python3 -c 'import json,sys;print(json.dumps({"content":sys.argv[1]}))' "$1")" \
    "$url" >/dev/null 2>&1 || true
}

rcon() {
  "$SCRIPT_DIR/rcon.py" "$1" >/dev/null 2>&1
}

"$SCRIPT_DIR/resourcepack-guard.sh" --check

players=0
if out=$("$SCRIPT_DIR/rcon.py" list 2>/dev/null); then
  players=$(printf '%s' "$out" | grep -oE 'are [0-9]+' | grep -oE '[0-9]+' | head -1 || true)
fi
players=${players:-0}

if [[ "$players" =~ ^[0-9]+$ && "$players" -gt 0 ]]; then
  rcon "say [서버] 리소스팩 업데이트로 ${GRACE}초 후 재시작합니다." || true
  sleep "$GRACE"
  rcon "say [서버] 지금 재시작합니다." || true
fi

rcon "save-all flush" || true
sleep 3
sudo systemctl restart mcserver

for i in $(seq 1 40); do
  if systemctl is-active --quiet mcserver && "$SCRIPT_DIR/rcon.py" list >/dev/null 2>&1; then
    notify "✅ **모바일 리소스팩 적용 완료** — \`$RELEASE\` (부팅 확인 ${i}회)"
    echo "resourcepack restart: OK ($RELEASE)"
    exit 0
  fi
  sleep 5
done

notify "🔴 **모바일 리소스팩 적용 후 부팅 확인 실패** — \`$RELEASE\`"
echo "resourcepack restart: boot check failed" >&2
exit 1
