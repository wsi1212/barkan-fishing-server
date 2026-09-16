#!/usr/bin/env bash
# Geyser-Velocity asset deployer.
#
# Default/--restart-proxy: legacy full proxy restart, only at zero connections. Needed only
# for a changed Geyser extension JAR.
# --reload-geyser: atomically apply packs/mappings then tell the already-running maintenance
# proxy to execute `geyser reload`. Velocity itself stays up; Java players stay connected and
# Bedrock sessions reconnect to receive the new packs.
set -euo pipefail

NETWORK_ROOT=${BARKAN_NETWORK_ROOT:-/home/ubuntu/mc-network}
STAGING_DIR=${BARKAN_GEYSER_STAGING:-/home/ubuntu/mcserver/staging/geyser}
GEYSER_DIR=${BARKAN_GEYSER_DIR:-$NETWORK_ROOT/velocity/plugins/Geyser-Velocity}
STATUS_FILE=${BARKAN_MAINTENANCE_STATUS:-$NETWORK_ROOT/control/status.json}
BACKUP_DIR=${BARKAN_PROXY_BACKUPS:-/home/ubuntu/mcserver/backups/proxy-assets}
CONTROL_DIR=${BARKAN_MAINTENANCE_CONTROL_DIR:-$NETWORK_ROOT/control}

MODE=${1:---restart-proxy}
case "$MODE" in
  --reload-geyser|--restart-proxy) ;;
  *) echo "사용법: $0 [--reload-geyser|--restart-proxy]" >&2; exit 2 ;;
esac

if [ "$MODE" = "--reload-geyser" ]; then
  [ -d "$STAGING_DIR" ] || { echo "Geyser staging 없음"; exit 3; }
  reloadable=()
  while IFS= read -r asset; do reloadable+=("$asset"); done < <(find "$STAGING_DIR" -maxdepth 1 -type f \( -name '*.mcpack' -o -name '*.json' \) | sort)
  [ "${#reloadable[@]}" -gt 0 ] || { echo "리로드할 Geyser 팩·매핑 없음"; exit 3; }
  [ -d "$CONTROL_DIR" ] || { echo "프록시 제어 디렉터리 없음: $CONTROL_DIR" >&2; exit 5; }

  stamp=$(TZ=Asia/Seoul date +%Y%m%d-%H%M%S)
  rollback="$BACKUP_DIR/$stamp-reload-rollback"
  mkdir -p "$rollback"
  declare -a changed=()
  declare -a created=()

  rollback_assets() {
    local destination name
    for destination in "${changed[@]}"; do
      name=$(basename "$destination")
      cp -f "$rollback/$name" "$destination"
    done
    for destination in "${created[@]}"; do rm -f "$destination"; done
  }

  for src in "${reloadable[@]}"; do
    name=$(basename "$src")
    case "$name" in
      *.mcpack)
        destination="$GEYSER_DIR/packs/$name"
        unzip -p "$src" manifest.json | python3 -c 'import json,sys; json.load(sys.stdin)["header"]["uuid"]' >/dev/null ;;
      *.json)
        destination="$GEYSER_DIR/custom_mappings/$name"
        python3 -c 'import json,sys; json.load(open(sys.argv[1]))' "$src" >/dev/null ;;
    esac
    mkdir -p "$(dirname "$destination")"
    if [ -f "$destination" ]; then
      cp -f "$destination" "$rollback/$name"
      changed+=("$destination")
    else
      created+=("$destination")
    fi
    temporary="$destination.reload-$stamp"
    cp -f "$src" "$temporary"
    mv -f "$temporary" "$destination"
  done

  token="geyser-reload-${stamp}-$$"
  result="$CONTROL_DIR/geyser-reload.result"
  request="$CONTROL_DIR/geyser-reload.request"
  rm -f "$result"
  printf '%s\n' "$token" > "$request.tmp"
  mv -f "$request.tmp" "$request"

  for _wait in $(seq 1 45); do
    if [ -s "$result" ]; then
      response=$(cat "$result")
      if [ "$response" = "$token ok" ]; then
        rm -f "${reloadable[@]}"
        echo "Geyser 팩·매핑 ${#reloadable[@]}개 적용 + Geyser 리로드 완료"
        exit 0
      fi
      echo "Geyser 리로드 거부/실패: $response" >&2
      rollback_assets
      exit 6
    fi
    sleep 1
  done
  echo "Geyser 리로드 응답 시간 초과" >&2
  rollback_assets
  exit 6
fi

[ -d "$STAGING_DIR" ] || { echo "Geyser staging 없음"; exit 3; }
assets=()
while IFS= read -r asset; do assets+=("$asset"); done < <(find "$STAGING_DIR" -maxdepth 1 -type f \( -name '*.mcpack' -o -name '*.json' -o -name '*.jar' \) | sort)
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
