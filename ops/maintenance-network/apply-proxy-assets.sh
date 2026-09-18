#!/usr/bin/env bash
# Geyser-Velocity asset deployer.
#
# Default/--restart-proxy: legacy full proxy restart, only at zero connections. Needed only
# for a changed Geyser extension JAR.
# --reload-geyser: atomically apply packs/mappings then tell the already-running maintenance
# proxy to execute `geyser reload`. Velocity itself stays up; Java players stay connected and
# Bedrock sessions reconnect to receive the new packs.
set -euo pipefail

# --reload-geyser : Velocity 를 재기동하지 않고 팩·매핑만 바꾼 뒤 `geyser reload` 를 요청한다.
#   Java 세션은 손대지 않고 Bedrock 세션만 새 팩을 받으러 재접속한다. 확장 JAR(extensions/*.jar)
#   은 JVM 재기동이 있어야 로드되므로 이 모드에서는 건드리지 않고 staging 에 남긴다.
#   ★이 모드가 없어서 nightly-restart 가 넘기던 --reload-geyser 인자가 통째로 무시됐고,
#     대신 «프록시 무접속» 을 요구하는 전면 재기동 경로만 돌았다. 그런데 이 스크립트가 불리는
#     시점은 «대기실 전환 직후» — 모든 접속자가 프록시에 매달려 있어 proxyPlayers 가 0 일 수
#     없는 순간이라, 베드락 자산이 구조적으로 영원히 적용되지 않았다(2026-09-19, 2일 적체).
RELOAD_ONLY=0
for arg in "$@"; do
  case "$arg" in
    --reload-geyser) RELOAD_ONLY=1 ;;
    --full-restart) RELOAD_ONLY=0 ;;
    *) echo "usage: $0 [--reload-geyser|--full-restart]" >&2; exit 2 ;;
  esac
done

NETWORK_ROOT=${BARKAN_NETWORK_ROOT:-/home/ubuntu/mc-network}
STAGING_DIR=${BARKAN_GEYSER_STAGING:-/home/ubuntu/mcserver/staging/geyser}
GEYSER_DIR=${BARKAN_GEYSER_DIR:-$NETWORK_ROOT/velocity/plugins/Geyser-Velocity}
STATUS_FILE=${BARKAN_MAINTENANCE_STATUS:-$NETWORK_ROOT/control/status.json}
BACKUP_DIR=${BARKAN_PROXY_BACKUPS:-/home/ubuntu/mcserver/backups/proxy-assets}
CONTROL_DIR=${BARKAN_MAINTENANCE_CONTROL_DIR:-$NETWORK_ROOT/control}
RELOAD_REQUEST="$CONTROL_DIR/geyser-reload.request"
RELOAD_RESULT="$CONTROL_DIR/geyser-reload.result"
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
# 전면 재기동 모드에서만 «무접속» 을 요구한다 — 그 경로는 Java 까지 전부 끊기 때문이다.
# 리로드 모드는 Java 세션을 건드리지 않으므로 접속자 수와 무관하게 진행한다.
if [ "$RELOAD_ONLY" = "0" ]; then
  [ "$players" = "0" ] || { echo "접속자 ${players}명 — 프록시 자산 적용 취소" >&2; exit 4; }
fi
systemctl is-active --quiet barkan-velocity || { echo "Velocity 비활성" >&2; exit 5; }

stamp=$(TZ=Asia/Seoul date +%Y%m%d-%H%M%S)
mkdir -p "$BACKUP_DIR/$stamp"
if [ "$RELOAD_ONLY" = "0" ]; then
  sudo systemctl stop barkan-velocity
fi
start_needed=$([ "$RELOAD_ONLY" = "0" ] && echo 1 || echo 0)
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
    *.jar)
      # 확장은 JVM 재기동이 있어야 로드된다. 리로드 모드에서는 남겨 두고 다음 전면 창에 맡긴다.
      if [ "$RELOAD_ONLY" = "1" ]; then echo "보류(확장, JVM 재기동 필요): $name"; continue; fi
      destination="$GEYSER_DIR/extensions/$name"
      unzip -p "$src" extension.yml | grep -Eq '^id:[[:space:]]*[^[:space:]]+' ;;
    *) continue ;;
  esac
  mkdir -p "$(dirname "$destination")"
  [ ! -f "$destination" ] || cp -f "$destination" "$BACKUP_DIR/$stamp/$name"
  mv -f "$src" "$destination"
  echo "적용: $name"
done

if [ "$RELOAD_ONLY" = "1" ]; then
  trap - EXIT INT TERM
  # 프록시 플러그인(BarkanMaintenanceProxy)이 이 파일을 보고 콘솔로 `geyser reload` 를 실행하고
  # 같은 토큰을 result 에 적는다. 토큰이 있어야 «옛 결과»를 새 요청의 성공으로 오인하지 않는다.
  mkdir -p "$CONTROL_DIR"
  token="bh-$(date -u +%Y%m%d%H%M%S)-$$"
  rm -f "$RELOAD_RESULT"
  printf '%s\n' "$token" > "$RELOAD_REQUEST"
  for _w in $(seq 1 60); do
    if [ -f "$RELOAD_RESULT" ] && grep -q "^$token " "$RELOAD_RESULT" 2>/dev/null; then
      state=$(awk -v t="$token" '$1==t{print $2}' "$RELOAD_RESULT" | head -1)
      case "$state" in
        ok) echo "Geyser 리로드 완료(베드락만 재접속)"; exit 0 ;;
        busy) echo "Geyser 리로드가 이미 진행 중" >&2; exit 6 ;;
        unavailable) echo "Geyser 명령 없음 — 프록시 플러그인/Geyser 확인" >&2; exit 7 ;;
        *) echo "Geyser 리로드 실패($state)" >&2; exit 8 ;;
      esac
    fi
    sleep 2
  done
  echo "Geyser 리로드 응답 없음 — 프록시 플러그인이 옛 버전일 수 있다(geyser-reload 미지원)" >&2
  exit 9
fi

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
