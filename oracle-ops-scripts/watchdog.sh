#!/usr/bin/env bash
# =====================================================================
# 바르칸 prod 외부 워치독 — 메인스레드 프리즈(데드락/GC지옥) 자동복구
#   systemd는 '프로세스 death'만 잡음. 이 워치독은 '살아있지만 얼어붙음'을 잡는다.
#   cron 2분마다 실행. RCON list 응답으로 메인스레드 생사 판정.
#   THRESHOLD회(기본4=약8분) 연속 무응답 → 프리즈 확정 → 재시작 + Discord 알림.
#   순간렉/저장/GC(수초~수십초)는 다음 체크 때 회복 → 카운터 리셋 → 재시작 안 함.
# env로 테스트 주입 가능: RCON_CMD / RESTART_CMD / GRACE / WEBHOOK_FILE
# =====================================================================
set -uo pipefail

DIR=~/mcserver/scripts
FAILS_FILE="$DIR/.watchdog_fails"
RESTARTS_FILE="$DIR/.watchdog_restarts"
CLOOP_MARK="$DIR/.watchdog_crashloop"
LABEL="[바르칸 prod]"

THRESHOLD=4          # 연속 실패 몇 회 = 프리즈 (2분 간격 → 약 8분)
WARN_AT=2            # 이 횟수에서 사전 경고 1회 (약 4분)
GRACE="${GRACE:-300}"          # 부팅/재시작 후 유예(초)
MAX_RESTARTS_HR=3              # 1시간 내 이 횟수 초과 재시작에도 무응답이면 크래시루프로 보고 중단
RCON_CMD="${RCON_CMD:-$DIR/rcon.py list}"
RESTART_CMD="${RESTART_CMD:-sudo systemctl restart mcserver}"
WEBHOOK_FILE="${WEBHOOK_FILE:-$DIR/discord-webhook.url}"

log(){ echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) $*"; }
notify(){ [ -s "$WEBHOOK_FILE" ] || return 0; local u m p; u=$(cat "$WEBHOOK_FILE"); m="$LABEL $1"
  p=$(python3 -c "import json,sys;print(json.dumps({'content':sys.argv[1]}))" "$m")
  curl -sf -m 10 -H 'Content-Type: application/json' -d "$p" "$u" >/dev/null 2>&1 || true; }

now=$(date +%s)

# --- 부팅 유예: 서버가 최근 GRACE초 내 시작됐으면 체크 skip ---
started_str=$(systemctl show mcserver -p ActiveEnterTimestamp --value 2>/dev/null || true)
started=0
[ -n "$started_str" ] && started=$(date -d "$started_str" +%s 2>/dev/null || echo 0)
if [ "$started" -gt 0 ]; then
  age=$((now - started))
  if [ "$age" -lt "$GRACE" ]; then
    echo 0 > "$FAILS_FILE"
    log "grace (uptime ${age}s < ${GRACE}s) — skip"
    exit 0
  fi
fi

# --- 헬스체크 ---
if eval "$RCON_CMD" >/dev/null 2>&1; then
  echo 0 > "$FAILS_FILE"
  rm -f "$CLOOP_MARK"                      # 회복됨 → 크래시루프 마커 해제
  log "OK"
  exit 0
fi

# --- 실패: 카운터 증가 ---
fails=$(cat "$FAILS_FILE" 2>/dev/null || echo 0); fails=$((fails+1))
echo "$fails" > "$FAILS_FILE"
log "FAIL ${fails}/${THRESHOLD}"

if [ "$fails" -lt "$THRESHOLD" ]; then
  [ "$fails" -eq "$WARN_AT" ] && notify "⚠️ 서버 무응답 감지 (${fails}/${THRESHOLD}, 약 $((WARN_AT*2))분). 지속되면 ${THRESHOLD}회(약 8분)에 자동 재시작합니다."
  exit 0
fi

# --- THRESHOLD 도달 = 프리즈 확정. 재시작 rate-limit 확인 ---
hour_ago=$((now - 3600))
if [ -f "$RESTARTS_FILE" ]; then
  awk -v t="$hour_ago" '$1>=t' "$RESTARTS_FILE" > "$RESTARTS_FILE.tmp" 2>/dev/null && mv "$RESTARTS_FILE.tmp" "$RESTARTS_FILE"
  recent_count=$(wc -l < "$RESTARTS_FILE")
else
  recent_count=0
fi

if [ "$recent_count" -ge "$MAX_RESTARTS_HR" ]; then
  log "CRASH-LOOP (${recent_count} restarts/hr) — 자동재시작 중단"
  if [ ! -f "$CLOOP_MARK" ]; then           # 에피소드당 알림 1회
    notify "🆘 서버가 1시간 내 ${recent_count}회 재시작에도 계속 무응답 = 크래시 루프. 자동복구 실패 — 수동 확인 필요!"
    touch "$CLOOP_MARK"
  fi
  exit 0
fi

# --- 재시작 실행 ---
notify "🔶 서버 ${THRESHOLD}회 연속(약 8분) 무응답 = 프리즈 판정 → 자동 재시작합니다."
echo "$now" >> "$RESTARTS_FILE"
echo 0 > "$FAILS_FILE"
log "RESTART trigger → $RESTART_CMD"
eval "$RESTART_CMD"
sleep 5
notify "🔁 재시작 명령 실행 완료. 부팅까지 1~2분 소요."
log "RESTARTED"
