#!/usr/bin/env bash
# Convert the existing local dev Paper into the backend of the prepared dev proxy network.
set -Eeuo pipefail

MAIN_ROOT=${BARKAN_DEV_MAIN_ROOT:-/Users/user/Library/Application Support/feather/player-server/servers/07de2d81-991a-47e2-b62d-06c0d1b5150a}
NETWORK_ROOT=${BARKAN_DEV_NETWORK_ROOT:-$MAIN_ROOT/dev-maintenance-network}
DEV_MC=${BARKAN_DEV_MC:-/Users/user/dev-mc.sh}
STAMP=$(date '+%Y%m%d-%H%M%S')
BACKUP_DIR="$NETWORK_ROOT/activation-backups/$STAMP"

for required in "$NETWORK_ROOT/bin/configure-backend.py" "$NETWORK_ROOT/bin/dev-network.sh" \
    "$NETWORK_ROOT/velocity/velocity.jar" "$NETWORK_ROOT/waiting/paper.jar" \
    "$MAIN_ROOT/server.properties" "$MAIN_ROOT/config/paper-global.yml" "$MAIN_ROOT/spigot.yml"; do
  [ -s "$required" ] || { echo "필수 파일 없음: $required" >&2; exit 2; }
done
if [ -e "$NETWORK_ROOT/enabled" ]; then
  "$NETWORK_ROOT/bin/dev-network.sh" start
  exit 0
fi

install -d -m 0700 "$BACKUP_DIR/main" "$BACKUP_DIR/geyser-jars"
cp -a "$MAIN_ROOT/server.properties" "$BACKUP_DIR/main/server.properties"
cp -a "$MAIN_ROOT/config/paper-global.yml" "$BACKUP_DIR/main/paper-global.yml"
cp -a "$MAIN_ROOT/spigot.yml" "$BACKUP_DIR/main/spigot.yml"

ACTIVATED=0
rollback(){
  local rc="${1:-$?}"
  [ "$ACTIVATED" = "1" ] && return 0
  trap - ERR INT TERM
  set +e
  "$NETWORK_ROOT/bin/dev-network.sh" stop
  cp -a "$BACKUP_DIR/main/server.properties" "$MAIN_ROOT/server.properties"
  cp -a "$BACKUP_DIR/main/paper-global.yml" "$MAIN_ROOT/config/paper-global.yml"
  cp -a "$BACKUP_DIR/main/spigot.yml" "$MAIN_ROOT/spigot.yml"
  for moved in "$BACKUP_DIR/geyser-jars"/*.jar; do
    [ -e "$moved" ] && mv -f "$moved" "$MAIN_ROOT/plugins/"
  done
  rm -f "$NETWORK_ROOT/enabled"
  "$DEV_MC" start
  echo "dev network 활성화 실패 — 기존 단일 dev 복원: $BACKUP_DIR" >&2
  exit "$rc"
}
trap 'rollback $?' ERR
trap 'rollback 130' INT TERM

"$DEV_MC" stop
"$NETWORK_ROOT/bin/configure-backend.py" \
  --root "$MAIN_ROOT" --port 25567 \
  --secret-file "$NETWORK_ROOT/velocity/forwarding.secret" --apply

shopt -s nullglob
geyser_jars=("$MAIN_ROOT"/plugins/Geyser-Spigot*.jar)
[ "${#geyser_jars[@]}" -gt 0 ] || { echo "Geyser-Spigot jar 없음" >&2; false; }
for geyser_jar in "${geyser_jars[@]}"; do
  mv -f "$geyser_jar" "$BACKUP_DIR/geyser-jars/"
done

touch "$NETWORK_ROOT/enabled"
"$NETWORK_ROOT/bin/dev-network.sh" start
ACTIVATED=1
trap - ERR INT TERM
echo "기존 dev를 Velocity 대기실 구조로 전환 완료. 백업: $BACKUP_DIR"
