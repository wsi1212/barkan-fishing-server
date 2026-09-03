#!/usr/bin/env bash
# =====================================================================
# 바르칸 prod 데일리 재시작(06:00 KST) 사전예고 — 30/10/5/1분 전 각각 cron으로 호출.
#   접속자 0명이면 조용히 스킵(빈 서버에 방송 불필요). RCON 무응답이면도 스킵(워치독 담당).
# 사용법: restart-warning.sh <30|10|5|1>
# =====================================================================
set -uo pipefail
DIR=~/mcserver/scripts
MINUTES="${1:?usage: restart-warning.sh <30|10|5|1>}"

# 오늘 밤 스킵 마커 있으면 예고 방송 자체를 안 함(실제 재시작 없을 거라 방송이 거짓말이 됨).
# 마커 삭제(소모)는 nightly-restart.sh(06:00, 제일 마지막)가 담당 — 여기선 확인만.
[ -f "$DIR/.skip-nightly-once" ] && exit 0

out=$("$DIR/rcon.py" list 2>/dev/null) || exit 0
n=$(printf '%s' "$out" | grep -oE 'are [0-9]+' | grep -oE '[0-9]+' | head -1); n=${n:-0}
[ "$n" -eq 0 ] && exit 0

"$DIR/rcon.py" "say [서버] 서버 재부팅까지 ${MINUTES}분 남았습니다 (정기 점검 06:00~06:10). 안전한 곳으로 이동해 주세요." >/dev/null 2>&1
