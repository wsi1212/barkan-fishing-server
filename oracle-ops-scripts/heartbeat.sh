#!/usr/bin/env bash
# =====================================================================
# 바르칸 prod 데드맨 스위치 하트비트 — 박스 밖(healthchecks.io)으로 생존신호.
#   MC 리스너(25565)가 살아있을 때만 healthchecks.io에 핑.
#   → 박스다운/네트워크끊김/cron정지/서버다운이면 핑이 끊김
#     → healthchecks.io가 침묵을 감지해 '박스 밖에서' 디스코드 알림.
#   우리가 만든 온-박스 자동화가 전부 죽어도 이 감시는 살아남는다(외부).
#   핑 URL은 ~/mcserver/scripts/hc-ping.url 에 저장(없으면 조용히 종료).
# =====================================================================
set -uo pipefail
URL_FILE=~/mcserver/scripts/hc-ping.url
[ -s "$URL_FILE" ] || exit 0
url=$(cat "$URL_FILE")

# MC 리스너 생존 확인 (프리즈여도 포트는 열려있음=박스생존 신호로 충분;
#  완전 다운/크래시루프면 포트 닫힘 → 핑 안 감 → 외부 침묵감지)
if timeout 5 bash -c 'exec 3<>/dev/tcp/127.0.0.1/25565' 2>/dev/null; then
  curl -fsS -m 10 --retry 2 "$url" >/dev/null 2>&1 || true
fi
