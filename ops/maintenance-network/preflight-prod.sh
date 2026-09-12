#!/usr/bin/env bash
# Read-only checks for the one-time cutover. This script never changes services or files.
set -uo pipefail

NETWORK_ROOT=${BARKAN_NETWORK_ROOT:-/home/ubuntu/mc-network}
failed=0
check(){ if eval "$2"; then echo "✅ $1"; else echo "🔴 $1"; failed=1; fi; }

check "Java 25" "test -x /usr/lib/jvm/zulu25-ca-arm64/bin/java"
check "Velocity jar" "test -s '$NETWORK_ROOT/velocity/velocity.jar'"
check "Velocity plugin" "test -s '$NETWORK_ROOT/velocity/plugins/BarkanMaintenanceProxy.jar'"
check "Geyser-Velocity" "test -s '$NETWORK_ROOT/velocity/plugins/Geyser-Velocity.jar'"
check "Floodgate-Velocity" "test -s '$NETWORK_ROOT/velocity/plugins/floodgate-velocity.jar'"
check "forwarding secret" "test -s '$NETWORK_ROOT/velocity/forwarding.secret'"
check "waiting Paper" "test -s '$NETWORK_ROOT/waiting/paper.jar'"
check "waiting plugin" "test -s '$NETWORK_ROOT/waiting/plugins/BarkanWaitingRoom.jar'"
check "waiting EULA" "grep -qx 'eula=true' '$NETWORK_ROOT/waiting/eula.txt'"
check "main ship marker environment" "systemctl show mcserver -p Environment --value | grep -q 'BLOCKSHIP_SHIP_MARKER_DIR=/home/ubuntu/mc-network/shared/ship-entities'"
check "disk headroom >= 3 GiB" "test \$(df -Pk / | awk 'NR==2{print \$4}') -ge 3145728"

echo "현재 포트:"
ss -ltnp 2>/dev/null | grep -E ':(25565|25567|25568)\b' || true
echo "현재 서비스:"
systemctl is-active mcserver barkan-velocity barkan-waiting 2>/dev/null || true
exit "$failed"
