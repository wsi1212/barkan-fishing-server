#!/bin/bash
# BarkanWorldWarp dev 적용 — 정지 → jar 교체 → 기동을 한 몸으로 처리한다.
set -euo pipefail

JAR="${1:?사용: $0 <BarkanWorldWarp.jar>}"
[ -f "$JAR" ] || { echo "❌ jar 없음: $JAR"; exit 1; }

DEV_SERVER="/Users/user/Library/Application Support/feather/player-server/servers/07de2d81-991a-47e2-b62d-06c0d1b5150a"
TARGET="$DEV_SERVER/plugins/BarkanWorldWarp.jar"
WAS_UP=0

if pgrep -f 'paper-1\.21\..*\.jar' >/dev/null 2>&1; then
  WAS_UP=1
  "$HOME/dev-mc.sh" stop
fi

cp "$TARGET" "/tmp/BarkanWorldWarp.jar.before-op-guard"
cp "$JAR" "$TARGET"

if [ "$WAS_UP" -eq 1 ]; then
  "$HOME/dev-mc.sh" start
else
  echo "✅ jar 교체 완료 — dev 서버가 꺼져 있어 다음 기동 때 적용됩니다."
fi
