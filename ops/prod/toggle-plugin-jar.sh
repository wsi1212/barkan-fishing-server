#!/usr/bin/env bash
# prod 플러그인 jar 활성/비활성 — stop → 교체 → start 를 한 몸으로 처리한다.
# 라이브 상태에서 jar을 건드리면 이후 처음 로드되는 클래스가 전부 CNFE가 되므로
# (2026-08-03 prod 사고) 반드시 서버를 멈춘 뒤에만 이름을 바꾼다.
#
# 사용: ./toggle-plugin-jar.sh enable|disable <jar파일명>
#   예: ./toggle-plugin-jar.sh enable BetterHud-2.0.0.jar
set -euo pipefail

ACTION="${1:?enable 또는 disable}"
JAR="${2:?jar 파일명 (예: BetterHud-2.0.0.jar)}"
PLUGINS="$HOME/mcserver/plugins"

case "$ACTION" in
  enable)  SRC="$PLUGINS/$JAR.disabled"; DST="$PLUGINS/$JAR" ;;
  disable) SRC="$PLUGINS/$JAR"; DST="$PLUGINS/$JAR.disabled" ;;
  *) echo "❌ action은 enable/disable"; exit 1 ;;
esac

[ -f "$SRC" ] || { echo "❌ 원본 없음: $SRC"; exit 1; }
[ -e "$DST" ] && { echo "❌ 목적지가 이미 있음: $DST"; exit 1; }

echo "[1] 서버 정지..."
sudo systemctl stop mcserver
for i in $(seq 1 60); do
  systemctl is-active --quiet mcserver || break
  sleep 1
done
if systemctl is-active --quiet mcserver; then
  echo "❌ 60초 안에 정지되지 않음 — 중단(jar 안 건드림)"; exit 1
fi
echo "    정지 확인됨"

echo "[2] jar 교체: $(basename "$SRC") → $(basename "$DST")"
mv "$SRC" "$DST"

echo "[3] 서버 기동..."
sudo systemctl start mcserver
echo "✅ 완료 — $ACTION $JAR"
