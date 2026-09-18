#!/usr/bin/env bash
# 컷오버 되돌리기 — Geyser 를 다시 Velocity 플러그인으로. Velocity 1회 재기동(전원 끊김).
set -euo pipefail
NET=${BARKAN_NETWORK_ROOT:-/home/ubuntu/mc-network}
PLUGIN="$NET/velocity/plugins/Geyser-Velocity.jar"
PARKED="$NET/velocity/plugins/.Geyser-Velocity.jar.parked"

echo "▶ Geyser standalone 정지"
sudo systemctl disable --now barkan-geyser 2>/dev/null || true

echo "▶ 플러그인 복귀"
[ -f "$PARKED" ] && mv -f "$PARKED" "$PLUGIN"
[ -s "$PLUGIN" ] || { echo "🔴 Geyser-Velocity.jar 을 못 찾는다 — 수동 복구 필요" >&2; exit 2; }

echo "▶ Velocity 재기동"
sudo systemctl restart barkan-velocity
for i in $(seq 1 30); do systemctl is-active --quiet barkan-velocity && break; sleep 2; done
systemctl is-active --quiet barkan-velocity && echo "✅ 롤백 완료(플러그인 모드)" || { echo "🔴 Velocity 기동 실패" >&2; exit 3; }
