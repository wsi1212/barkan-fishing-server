#!/usr/bin/env bash
# Apply Geyser-Velocity assets only while the proxy has zero connected players.
# This is intentionally separate from main Paper's nightly restart: restarting Velocity would
# disconnect every Java and Bedrock client, defeating the waiting-room design.
set -euo pipefail

NETWORK_ROOT=${BARKAN_NETWORK_ROOT:-/home/ubuntu/mc-network}
STAGING_DIR=${BARKAN_GEYSER_STAGING:-/home/ubuntu/mcserver/staging/geyser}
GEYSER_DIR=${BARKAN_GEYSER_DIR:-$NETWORK_ROOT/velocity/plugins/Geyser-Velocity}
STATUS_FILE=${BARKAN_MAINTENANCE_STATUS:-$NETWORK_ROOT/control/status.json}
BACKUP_DIR=${BARKAN_PROXY_BACKUPS:-/home/ubuntu/mcserver/backups/proxy-assets}

[ -d "$STAGING_DIR" ] || { echo "Geyser staging 없음"; exit 3; }
mapfile -t assets < <(find "$STAGING_DIR" -maxdepth 1 -type f \( -name '*.mcpack' -o -name '*.json' -o -name '*.jar' \) | sort)
[ "${#assets[@]}" -gt 0 ] || { echo "Geyser staging 없음"; exit 3; }

players=$(python3 - "$STATUS_FILE" <<'PY'
import json, sys, time
d = json.load(open(sys.argv[1], encoding="utf-8"))
if time.time() * 1000 - int(d.get("updatedEpochMs", 0)) > 5000:
    raise SystemExit("proxy status is stale")
print(int(d.get("proxyPlayers", -1)))
PY
)
[ "$players" = "0" ] || { echo "접속자 ${players}명 — 프록시 자산 적용 취소" >&2; exit 4; }
systemctl is-active --quiet barkan-velocity || { echo "Velocity 비활성" >&2; exit 5; }

stamp=$(TZ=Asia/Seoul date +%Y%m%d-%H%M%S)
mkdir -p "$BACKUP_DIR/$stamp"
sudo systemctl stop barkan-velocity
start_needed=1
ensure_start(){
  [ "$start_needed" = "1" ] || return 0
  start_needed=0
  sudo systemctl start barkan-velocity
}
trap ensure_start EXIT INT TERM

for src in "${assets[@]}"; do
  name=$(basename "$src")
  case "$name" in
    *.mcpack) destination="$GEYSER_DIR/packs/$name"
      unzip -p "$src" manifest.json | python3 -c 'import json,sys; json.load(sys.stdin)["header"]["uuid"]' >/dev/null ;;
    *.json) destination="$GEYSER_DIR/custom_mappings/$name"
      python3 -c 'import json,sys; json.load(open(sys.argv[1]))' "$src" >/dev/null ;;
    *.jar) destination="$GEYSER_DIR/extensions/$name"
      unzip -p "$src" extension.yml | grep -Eq '^id:[[:space:]]*[^[:space:]]+' ;;
    *) continue ;;
  esac
  mkdir -p "$(dirname "$destination")"
  [ ! -f "$destination" ] || cp -f "$destination" "$BACKUP_DIR/$stamp/$name"
  mv -f "$src" "$destination"
  echo "적용: $name"
done

ensure_start
trap - EXIT INT TERM
for _wait in $(seq 1 30); do
  if systemctl is-active --quiet barkan-velocity \
      && python3 - "$STATUS_FILE" <<'PY' >/dev/null 2>&1
import json, sys, time
d=json.load(open(sys.argv[1], encoding="utf-8"))
assert time.time()*1000-int(d["updatedEpochMs"]) < 5000
PY
  then
    echo "Velocity/Geyser 재기동 확인"
    exit 0
  fi
  sleep 2
done
echo "Velocity 재기동 확인 실패" >&2
exit 1
