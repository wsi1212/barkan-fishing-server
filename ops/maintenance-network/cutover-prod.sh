#!/usr/bin/env bash
# One-time public entry-point cutover. Run only inside an already planned outage,
# after mcserver has fully stopped and the staged BlockShip jar/scripts were applied.
# This file intentionally never stops a running mcserver by itself.
set -Eeuo pipefail

NETWORK_ROOT=${BARKAN_NETWORK_ROOT:-/home/ubuntu/mc-network}
MAIN_ROOT=${BARKAN_MAIN_ROOT:-/home/ubuntu/mcserver}
CONTROL_DIR="$NETWORK_ROOT/control"
BACKUP_ROOT="$NETWORK_ROOT/cutover-backups"
CONFIRM=${BARKAN_PROXY_CUTOVER_CONFIRM:-}
DROPIN_DIR=/etc/systemd/system/mcserver.service.d
OLD_GATE_DROPIN="$DROPIN_DIR/maintenance-gate.conf"
NEW_BACKEND_DROPIN="$DROPIN_DIR/velocity-backend.conf"
GATE_SERVICE=barkan-maintenance-gate.service
GATE_CONTROL="$MAIN_ROOT/scripts/maintenance-gate-control.sh"
STAMP=$(TZ=Asia/Seoul date +%Y%m%d-%H%M%S)
BACKUP_DIR="$BACKUP_ROOT/$STAMP"

if [ "$CONFIRM" != "BARKAN_PROXY_25565" ]; then
  echo "거부: BARKAN_PROXY_CUTOVER_CONFIRM=BARKAN_PROXY_25565 가 필요합니다." >&2
  exit 2
fi
if systemctl is-active --quiet mcserver; then
  echo "거부: mcserver가 active입니다. 이 스크립트는 서버를 직접 내리지 않습니다." >&2
  exit 2
fi
if [ -e "$NETWORK_ROOT/enabled" ]; then
  echo "거부: 프록시 네트워크가 이미 활성화되어 있습니다." >&2
  exit 2
fi

for required in \
  "$NETWORK_ROOT/bin/configure-backend.py" \
  "$NETWORK_ROOT/bin/install-systemd.sh" \
  "$NETWORK_ROOT/velocity/velocity.jar" \
  "$NETWORK_ROOT/velocity/plugins/BarkanMaintenanceProxy.jar" \
  "$NETWORK_ROOT/velocity/plugins/Geyser-Velocity.jar" \
  "$NETWORK_ROOT/velocity/plugins/floodgate-velocity.jar" \
  "$NETWORK_ROOT/velocity/plugins/floodgate/key.pem" \
  "$NETWORK_ROOT/velocity/forwarding.secret" \
  "$NETWORK_ROOT/waiting/paper.jar" \
  "$NETWORK_ROOT/waiting/plugins/BarkanWaitingRoom.jar" \
  "$MAIN_ROOT/server.properties" \
  "$MAIN_ROOT/config/paper-global.yml" \
  "$MAIN_ROOT/spigot.yml" \
  "$MAIN_ROOT/scripts/nightly-restart.sh" \
  "$MAIN_ROOT/scripts/restart-warning.sh"; do
  [ -s "$required" ] || { echo "필수 파일 없음: $required" >&2; exit 2; }
done

grep -q 'MAINT_ENABLED_FILE' "$MAIN_ROOT/scripts/nightly-restart.sh" || {
  echo "거부: 대기실 대응 nightly-restart.sh가 아직 설치되지 않았습니다." >&2; exit 2; }
grep -q 'mc-network/enabled' "$MAIN_ROOT/scripts/restart-warning.sh" || {
  echo "거부: 대기실 대응 restart-warning.sh가 아직 설치되지 않았습니다." >&2; exit 2; }
unzip -Z1 "$MAIN_ROOT/plugins/BlockShip-1.0.0-SNAPSHOT.jar" 2>/dev/null \
  | awk '$0 == "com/blockship/ship/BedrockShipMarkerStore.class" { found=1 } END { exit !found }' || {
    echo "거부: live BlockShip jar에 BedrockShipMarkerStore가 없습니다." >&2; exit 2; }

port_is_listening(){
  local protocol="$1" port="$2"
  if [ "$protocol" = tcp ]; then
    ss -ltnH | awk '{print $4}' | grep -Eq "(^|:)${port}$"
  else
    ss -lunH | awk '{print $4}' | grep -Eq "(^|:)${port}$"
  fi
}
for port in 25565 25567 25568; do
  if port_is_listening tcp "$port"; then
    echo "거부: TCP $port 사용 중" >&2
    exit 2
  fi
done
if port_is_listening udp 19132; then
  echo "거부: UDP 19132 사용 중 (main/Geyser가 완전히 종료됐는지 확인)" >&2
  exit 2
fi

install -d -m 0700 "$BACKUP_DIR/main" "$BACKUP_DIR/systemd" "$BACKUP_DIR/geyser-jars"
cp -a "$MAIN_ROOT/server.properties" "$BACKUP_DIR/main/server.properties"
cp -a "$MAIN_ROOT/config/paper-global.yml" "$BACKUP_DIR/main/paper-global.yml"
cp -a "$MAIN_ROOT/spigot.yml" "$BACKUP_DIR/main/spigot.yml"
[ ! -f "$OLD_GATE_DROPIN" ] || sudo -n cp -a "$OLD_GATE_DROPIN" "$BACKUP_DIR/systemd/maintenance-gate.conf"

GATE_WAS_ACTIVE=0
GATE_WAS_ENABLED=0
systemctl is-active --quiet "$GATE_SERVICE" && GATE_WAS_ACTIVE=1 || true
systemctl is-enabled --quiet "$GATE_SERVICE" && GATE_WAS_ENABLED=1 || true
CUTOVER_COMPLETE=0

rollback(){
  local rc=$?
  [ "$CUTOVER_COMPLETE" = "1" ] && return 0
  trap - ERR
  set +e
  echo "cutover 실패 — 기존 단일 Paper 진입점으로 롤백합니다." >&2
  rm -f "$NETWORK_ROOT/enabled"
  sudo -n systemctl disable --now barkan-velocity.service barkan-waiting.service >/dev/null 2>&1
  cp -a "$BACKUP_DIR/main/server.properties" "$MAIN_ROOT/server.properties"
  cp -a "$BACKUP_DIR/main/paper-global.yml" "$MAIN_ROOT/config/paper-global.yml"
  cp -a "$BACKUP_DIR/main/spigot.yml" "$MAIN_ROOT/spigot.yml"
  for moved in "$BACKUP_DIR/geyser-jars"/*.jar; do
    [ -e "$moved" ] && mv -f "$moved" "$MAIN_ROOT/plugins/"
  done
  sudo -n rm -f "$NEW_BACKEND_DROPIN"
  if [ -f "$BACKUP_DIR/systemd/maintenance-gate.conf" ]; then
    sudo -n install -m 0644 "$BACKUP_DIR/systemd/maintenance-gate.conf" "$OLD_GATE_DROPIN"
  fi
  sudo -n systemctl daemon-reload
  [ "$GATE_WAS_ENABLED" = "1" ] && sudo -n systemctl enable "$GATE_SERVICE" >/dev/null 2>&1
  [ "$GATE_WAS_ACTIVE" = "1" ] && sudo -n systemctl start "$GATE_SERVICE"
  sudo -n systemctl start mcserver
  echo "롤백 기동 요청 완료. 백업: $BACKUP_DIR" >&2
  exit "$rc"
}
trap rollback ERR

"$NETWORK_ROOT/bin/install-systemd.sh"
"$NETWORK_ROOT/bin/configure-backend.py" \
  --root "$MAIN_ROOT" --port 25567 \
  --secret-file "$NETWORK_ROOT/velocity/forwarding.secret" --apply

shopt -s nullglob
geyser_jars=("$MAIN_ROOT"/plugins/Geyser-Spigot*.jar)
[ "${#geyser_jars[@]}" -gt 0 ] || { echo "Geyser-Spigot jar 없음" >&2; false; }
for geyser_jar in "${geyser_jars[@]}"; do
  mv -f "$geyser_jar" "$BACKUP_DIR/geyser-jars/"
done

# mcserver stop drop-in may have armed the old TCP disconnect responder.
sudo -n "$GATE_CONTROL" disable
sudo -n systemctl disable --now "$GATE_SERVICE"
sudo -n rm -f "$OLD_GATE_DROPIN"
sudo -n systemctl daemon-reload

printf 'resume\n' > "$CONTROL_DIR/request"
sudo -n systemctl enable barkan-waiting.service barkan-velocity.service
sudo -n systemctl start barkan-waiting.service
for _wait in $(seq 1 60); do
  systemctl is-active --quiet barkan-waiting.service && port_is_listening tcp 25568 && break
  sleep 1
done
systemctl is-active --quiet barkan-waiting.service && port_is_listening tcp 25568

sudo -n systemctl start barkan-velocity.service
for _wait in $(seq 1 60); do
  if systemctl is-active --quiet barkan-velocity.service \
      && port_is_listening tcp 25565 && port_is_listening udp 19132 \
      && "$NETWORK_ROOT/bin/control.sh" status >/dev/null 2>&1; then
    break
  fi
  sleep 1
done
systemctl is-active --quiet barkan-velocity.service
port_is_listening tcp 25565
port_is_listening udp 19132
"$NETWORK_ROOT/bin/control.sh" status >/dev/null

sudo -n systemctl start mcserver
for _wait in $(seq 1 60); do
  if systemctl is-active --quiet mcserver && "$MAIN_ROOT/scripts/rcon.py" list >/dev/null 2>&1; then
    break
  fi
  sleep 5
done
systemctl is-active --quiet mcserver
"$MAIN_ROOT/scripts/rcon.py" list >/dev/null

for _wait in $(seq 1 90); do
  if python3 - "$CONTROL_DIR/status.json" <<'PY'
import json, sys, time
data = json.load(open(sys.argv[1], encoding="utf-8"))
fresh = time.time() * 1000 - int(data.get("updatedEpochMs", 0)) < 5000
raise SystemExit(0 if fresh and data.get("state") == "IDLE" and data.get("mainReachable") is True else 1)
PY
  then
    break
  fi
  sleep 1
done
python3 - "$CONTROL_DIR/status.json" <<'PY'
import json, sys, time
data = json.load(open(sys.argv[1], encoding="utf-8"))
fresh = time.time() * 1000 - int(data.get("updatedEpochMs", 0)) < 5000
raise SystemExit(0 if fresh and data.get("state") == "IDLE" and data.get("mainReachable") is True else 1)
PY

touch "$NETWORK_ROOT/enabled"
CUTOVER_COMPLETE=1
trap - ERR
echo "Velocity 대기실 네트워크 최초 전환 완료. 백업: $BACKUP_DIR"
