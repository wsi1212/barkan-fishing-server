#!/usr/bin/env bash
# Install inactive unit definitions and the harmless BlockShip marker environment.
# This script never starts, stops, enables, or disables a service.
set -euo pipefail

NETWORK_ROOT=${BARKAN_NETWORK_ROOT:-/home/ubuntu/mc-network}
UNIT_SOURCE="$NETWORK_ROOT/systemd"
DROPIN_DIR=/etc/systemd/system/mcserver.service.d

for required in \
  "$UNIT_SOURCE/barkan-velocity.service" \
  "$UNIT_SOURCE/barkan-waiting.service" \
  "$UNIT_SOURCE/mcserver-velocity-backend.conf"; do
  [ -s "$required" ] || { echo "필수 unit 파일 없음: $required" >&2; exit 2; }
done

sudo -n install -m 0644 "$UNIT_SOURCE/barkan-velocity.service" \
  /etc/systemd/system/barkan-velocity.service
sudo -n install -m 0644 "$UNIT_SOURCE/barkan-waiting.service" \
  /etc/systemd/system/barkan-waiting.service
sudo -n install -d -m 0755 "$DROPIN_DIR"
sudo -n install -m 0644 "$UNIT_SOURCE/mcserver-velocity-backend.conf" \
  "$DROPIN_DIR/velocity-backend.conf"
sudo -n systemctl daemon-reload

echo "systemd 정의 설치 완료 (서비스 시작·enable·main 재시작 없음)"

