#!/usr/bin/env bash
# minecraft-auth-check: Mojang/Microsoft 마인크래프트 인증 서비스 실시간 상태 판정
# 사용: check_auth.sh [--monitor] [--json] [--interval N] [--need N] [--max SEC]
#   (기본) 한 번 찔러 판정 출력. verdict=UP이면 exit 0, 아니면 exit 1
#   --monitor  복구될 때까지 폴링(연속 --need회 UP이면 종료). 백그라운드로 띄우기 좋음
#   --json     기계 판독용 한 줄 JSON
set -uo pipefail

MODE="check"; JSON=0; INTERVAL=120; NEED=3; MAX_SEC=21600
while [ $# -gt 0 ]; do
  case "${1:-}" in
    --monitor)  MODE="monitor" ;;
    --json)     JSON=1 ;;
    --interval) INTERVAL="${2:-120}"; shift ;;
    --need)     NEED="${2:-3}"; shift ;;
    --max)      MAX_SEC="${2:-21600}"; shift ;;
    -h|--help)  sed -n '2,6p' "$0"; exit 0 ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
  shift
done

# Notch의 UUID — sessionserver 프로필 조회용(아무 유효 UUID면 됨)
NOTCH="853c80ef3c3749fdaa49938b674adae6"
LOGIN="https://api.minecraftservices.com/launcher/login"
XBOX="https://api.minecraftservices.com/authentication/login_with_xbox"
SESS="https://sessionserver.mojang.com/session/minecraft/profile/$NOTCH"

# $1=method $2=url -> HTTP 코드 (연결 실패/타임아웃이면 000)
probe() {
  local code
  if [ "$1" = POST ]; then
    code=$(curl -s -X POST --connect-timeout 8 --max-time 15 -o /dev/null -w "%{http_code}" \
             -H "Content-Type: application/json" -d '{}' "$2" 2>/dev/null)
  else
    code=$(curl -s --connect-timeout 8 --max-time 15 -o /dev/null -w "%{http_code}" "$2" 2>/dev/null)
  fi
  echo "${code:-000}"
}

# 로그인 엔드포인트는 빈 바디 POST라 400/401이 "정상"(=살아서 요청 처리중). 5xx가 장애.
is_ok()   { case "$1" in 200|400|401|403|405) return 0 ;; *) return 1 ;; esac; }
is_down() { case "$1" in 500|502|503|504) return 0 ;; *) return 1 ;; esac; }

VERDICT=""; MSG=""
evaluate() { # $1=launcher $2=xbox $3=sess
  local L="$1" X="$2"
  if is_ok "$L" && is_ok "$X"; then
    VERDICT="UP";       MSG="Mojang 인증 정상 — 로그인 가능"
  elif is_down "$L" || is_down "$X"; then
    VERDICT="DOWN";     MSG="Mojang 서버측 장애(5xx) — 복구 대기만, 클라/서버 손댈 것 없음"
  elif [ "$L" = 000 ] && [ "$X" = 000 ]; then
    VERDICT="NETFAIL";  MSG="엔드포인트 연결 실패 — 로컬 네트워크/DNS/방화벽/프록시 확인"
  else
    VERDICT="DEGRADED"; MSG="일부 엔드포인트 이상(플래핑 가능) — 잠시 후 재확인 권장"
  fi
}

emit() { # $1=L $2=X $3=S
  if [ "$JSON" = 1 ]; then
    printf '{"verdict":"%s","launcher_login":"%s","login_with_xbox":"%s","sessionserver":"%s","message":"%s"}\n' \
      "$VERDICT" "$1" "$2" "$3" "$MSG"
  else
    echo "  launcher/login    : HTTP $1"
    echo "  login_with_xbox   : HTTP $2"
    echo "  sessionserver     : HTTP $3"
    echo "  -> [$VERDICT] $MSG"
  fi
}

if [ "$MODE" = check ]; then
  L=$(probe POST "$LOGIN"); X=$(probe POST "$XBOX"); S=$(probe GET "$SESS")
  evaluate "$L" "$X" "$S"; emit "$L" "$X" "$S"
  [ "$VERDICT" = UP ] && exit 0 || exit 1
fi

# --monitor: 연속 NEED회 UP이면 '안정 복구'로 종료. 순간 회복(플래핑)엔 속지 않음.
start=$(date +%s); streak=0; last=""
while [ $(( $(date +%s) - start )) -lt "$MAX_SEC" ]; do
  L=$(probe POST "$LOGIN"); X=$(probe POST "$XBOX"); S=$(probe GET "$SESS")
  evaluate "$L" "$X" "$S"; last="$VERDICT ($L/$X/$S)"
  if [ "$VERDICT" = UP ]; then
    streak=$((streak+1))
    if [ "$streak" -ge "$NEED" ]; then
      echo "✅ Mojang 인증 안정 복구 (연속 ${NEED}회 UP, $L/$X, $(date '+%H:%M %Z')) — 이제 로그인하세요."
      exit 0
    fi
  else
    streak=0
  fi
  sleep "$INTERVAL"
done
echo "⏱ 모니터 종료(상한 ${MAX_SEC}s) — 마지막 상태: $last. 계속 감시하려면 다시 실행."
exit 2
