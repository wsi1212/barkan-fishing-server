#!/usr/bin/env bash
# Geyser 를 Velocity 플러그인에서 standalone 프로세스로 옮긴다.
# ★이 스크립트가 유일한 «전원 끊김» 지점이다(Velocity 1회 재기동, 약 10초).
#   그 뒤로는 팩·매핑·확장·코어 전부 베드락만 끊긴다.
# 되돌리기: rollback.sh
set -euo pipefail

NET=${BARKAN_NETWORK_ROOT:-/home/ubuntu/mc-network}
DST="$NET/geyser"
PLUGIN="$NET/velocity/plugins/Geyser-Velocity.jar"
PARKED="$NET/velocity/plugins/.Geyser-Velocity.jar.parked"
UNIT=/etc/systemd/system/barkan-geyser.service

[ -s "$DST/Geyser-Standalone.jar" ] || { echo "prepare.sh 를 먼저 돌려라 — $DST/Geyser-Standalone.jar 없음" >&2; exit 2; }
[ -s "$DST/config.yml" ] || { echo "prepare.sh 를 먼저 돌려라 — config 없음" >&2; exit 2; }
[ -s "$DST/key.pem" ] || { echo "floodgate key 가 없다: $DST/key.pem" >&2; exit 2; }
[ -f "$UNIT" ] || { echo "systemd 유닛이 없다: $UNIT (install 단계 먼저)" >&2; exit 2; }

n=$(python3 - "$NET/control/status.json" <<'PY' 2>/dev/null || echo "?"
import json,sys
print(json.load(open(sys.argv[1],encoding="utf-8")).get("proxyPlayers","?"))
PY
)
echo "현재 프록시 접속자: ${n}명 — 이들은 약 10초 끊겼다 재접속한다."
read -r -p "진행하려면 CUTOVER 입력: " ok
[ "$ok" = "CUTOVER" ] || { echo "취소"; exit 1; }

echo "▶ Velocity 정지"
sudo systemctl stop barkan-velocity

echo "▶ Geyser 플러그인 격리(삭제 아님 — rollback 용)"
[ -f "$PLUGIN" ] && mv -f "$PLUGIN" "$PARKED"

echo "▶ Velocity 기동 (Java 전용 · UDP 19132 해제됨)"
sudo systemctl start barkan-velocity
for i in $(seq 1 30); do systemctl is-active --quiet barkan-velocity && break; sleep 2; done
systemctl is-active --quiet barkan-velocity || { echo "🔴 Velocity 기동 실패 — rollback.sh" >&2; exit 3; }

echo "▶ Geyser standalone 기동 (UDP 19132 인수)"
sudo systemctl daemon-reload
sudo systemctl enable --now barkan-geyser
for i in $(seq 1 30); do
  sudo ss -ulnp 2>/dev/null | grep -q ':19132' && break; sleep 2
done
if ! sudo ss -ulnp 2>/dev/null | grep -q ':19132'; then
  echo "🔴 UDP 19132 을 아무도 안 듣는다 — 베드락 접속 불가. rollback.sh" >&2; exit 4
fi

echo
echo "✅ 컷오버 완료"
echo "   Java   : Velocity 25565 (이제 Geyser 와 무관)"
echo "   Bedrock: Geyser standalone 19132 → 127.0.0.1:25565"
echo "   로그   : journalctl -u barkan-geyser -f"
echo "   ★베드락으로 실제 접속해 보고, 안 되면 즉시 rollback.sh"
