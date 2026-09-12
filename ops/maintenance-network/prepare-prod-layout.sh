#!/usr/bin/env bash
# Provision new, inactive files for the one-time proxy cutover.
# It does not stop/start/enable any service and does not modify the live main Paper config.
set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "$0")" && pwd)
NETWORK_ROOT=${BARKAN_NETWORK_ROOT:-/home/ubuntu/mc-network}
MAIN_ROOT=${BARKAN_MAIN_ROOT:-/home/ubuntu/mcserver}
PROXY_JAR="$SCRIPT_DIR/proxy-plugin/build/libs/BarkanMaintenanceProxy.jar"
WAITING_JAR="$SCRIPT_DIR/waiting-plugin/build/libs/BarkanWaitingRoom.jar"
SHIP_EXTENSION=${BARKAN_SHIP_EXTENSION:-/tmp/BarkanShipGeyserExtension.jar}
VELOCITY_URL=https://fill-data.papermc.io/v1/objects/846411d2d0560fed0f23496ffb89681be528d2c0650ecdcf21724d2d7bd9c1ee/velocity-4.1.1-24.jar
VELOCITY_SHA256=846411d2d0560fed0f23496ffb89681be528d2c0650ecdcf21724d2d7bd9c1ee
GEYSER_URL=https://download.geysermc.org/v2/projects/geyser/versions/2.11.2/builds/1235/downloads/velocity
GEYSER_SHA256=1d6ab14770494c59e12cf019cc26356824725ffa298efd24e2104c6209b2a098
FLOODGATE_URL=https://download.geysermc.org/v2/projects/floodgate/versions/2.2.5/builds/140/downloads/velocity
FLOODGATE_SHA256=f5867ad79b90d38abcc72755a685428fbcf423b52c9830a39ffed5203de6936a

for required in "$PROXY_JAR" "$WAITING_JAR" "$SHIP_EXTENSION" "$MAIN_ROOT/paper.jar" \
    "$MAIN_ROOT/config/paper-global.yml" "$MAIN_ROOT/spigot.yml"; do
  [ -s "$required" ] || { echo "필수 파일 없음: $required" >&2; exit 2; }
done

install -d -m 0755 \
  "$NETWORK_ROOT/velocity/plugins/Geyser-Velocity/packs" \
  "$NETWORK_ROOT/velocity/plugins/Geyser-Velocity/custom_mappings" \
  "$NETWORK_ROOT/velocity/plugins/Geyser-Velocity/extensions" \
  "$NETWORK_ROOT/velocity/plugins/floodgate" \
  "$NETWORK_ROOT/waiting/plugins" "$NETWORK_ROOT/waiting/config" \
  "$NETWORK_ROOT/control" "$NETWORK_ROOT/shared/ship-entities" \
  "$NETWORK_ROOT/systemd"

download_verified(){
  local url="$1" expected="$2" destination="$3" temporary="$destination.download"
  curl -fL --retry 3 -o "$temporary" "$url"
  printf '%s  %s\n' "$expected" "$temporary" | sha256sum -c - >/dev/null
  mv -f "$temporary" "$destination"
}

download_verified "$VELOCITY_URL" "$VELOCITY_SHA256" "$NETWORK_ROOT/velocity/velocity.jar"
download_verified "$GEYSER_URL" "$GEYSER_SHA256" "$NETWORK_ROOT/velocity/plugins/Geyser-Velocity.jar"
download_verified "$FLOODGATE_URL" "$FLOODGATE_SHA256" "$NETWORK_ROOT/velocity/plugins/floodgate-velocity.jar"

install -m 0644 "$PROXY_JAR" "$NETWORK_ROOT/velocity/plugins/BarkanMaintenanceProxy.jar"
install -m 0644 "$WAITING_JAR" "$NETWORK_ROOT/waiting/plugins/BarkanWaitingRoom.jar"
install -m 0644 "$SHIP_EXTENSION" "$NETWORK_ROOT/velocity/plugins/Geyser-Velocity/extensions/BarkanShipGeyserExtension.jar"
install -m 0644 "$MAIN_ROOT/paper.jar" "$NETWORK_ROOT/waiting/paper.jar"
install -m 0644 "$SCRIPT_DIR/templates/velocity.toml" "$NETWORK_ROOT/velocity/velocity.toml"
install -m 0644 "$SCRIPT_DIR/templates/waiting-server.properties" "$NETWORK_ROOT/waiting/server.properties"
install -m 0644 "$MAIN_ROOT/config/paper-global.yml" "$NETWORK_ROOT/waiting/config/paper-global.yml"
install -m 0644 "$MAIN_ROOT/spigot.yml" "$NETWORK_ROOT/waiting/spigot.yml"
[ ! -f "$MAIN_ROOT/bukkit.yml" ] || install -m 0644 "$MAIN_ROOT/bukkit.yml" "$NETWORK_ROOT/waiting/bukkit.yml"
printf 'eula=true\n' > "$NETWORK_ROOT/waiting/eula.txt"

if [ ! -s "$NETWORK_ROOT/velocity/forwarding.secret" ]; then
  umask 077
  openssl rand -hex 32 > "$NETWORK_ROOT/velocity/forwarding.secret"
fi
printf 'resume\n' > "$NETWORK_ROOT/control/request"

MAIN_GEYSER="$MAIN_ROOT/plugins/Geyser-Spigot"
if [ -d "$MAIN_GEYSER" ]; then
  [ ! -f "$MAIN_GEYSER/config.yml" ] || install -m 0644 "$MAIN_GEYSER/config.yml" "$NETWORK_ROOT/velocity/plugins/Geyser-Velocity/config.yml"
  for asset_dir in packs custom_mappings; do
    if [ -d "$MAIN_GEYSER/$asset_dir" ]; then
      cp -a "$MAIN_GEYSER/$asset_dir/." "$NETWORK_ROOT/velocity/plugins/Geyser-Velocity/$asset_dir/"
    fi
  done
fi

MAIN_FLOODGATE="$MAIN_ROOT/plugins/floodgate"
if [ -d "$MAIN_FLOODGATE" ]; then
  [ ! -f "$MAIN_FLOODGATE/key.pem" ] || install -m 0600 "$MAIN_FLOODGATE/key.pem" "$NETWORK_ROOT/velocity/plugins/floodgate/key.pem"
  if [ -f "$MAIN_FLOODGATE/config.yml" ]; then
    install -m 0600 "$MAIN_FLOODGATE/config.yml" "$NETWORK_ROOT/velocity/plugins/floodgate/config.yml"
    perl -pi -e 's/^send-floodgate-data:\s*.*/send-floodgate-data: true/' "$NETWORK_ROOT/velocity/plugins/floodgate/config.yml"
  fi
fi

"$SCRIPT_DIR/configure-backend.py" \
  --root "$NETWORK_ROOT/waiting" --port 25568 \
  --secret-file "$NETWORK_ROOT/velocity/forwarding.secret" --apply

install -m 0644 "$SCRIPT_DIR/templates/barkan-velocity.service" "$NETWORK_ROOT/systemd/barkan-velocity.service"
install -m 0644 "$SCRIPT_DIR/templates/barkan-waiting.service" "$NETWORK_ROOT/systemd/barkan-waiting.service"
install -m 0644 "$SCRIPT_DIR/templates/mcserver-velocity-backend.conf" "$NETWORK_ROOT/systemd/mcserver-velocity-backend.conf"

echo "inactive prod layout 준비 완료: $NETWORK_ROOT"
echo "서비스 시작·enable, main 설정 변경, enabled 마커 생성은 하지 않았습니다."
