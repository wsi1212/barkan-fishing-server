#!/usr/bin/env bash
# =====================================================================
# 바르칸 prod jar 가드 — "가동 중 jar 교체" 자동 감지 + 자가치유
#
#   라이브 jar을 덮어쓰면 그 뒤 처음 로드되는 클래스가 전부 NoClassDefFoundError가
#   된다. 이미 로드된 기능은 멀쩡하니 즉시 안 터지고, 유저가 안 써본 기능부터
#   하나씩 죽는다 → 원인 추적이 지옥. 로그에 CNFE가 뜰 때까지 아무도 모른다.
#   (2026-08-03 실사고: 18:05 jar 교체 → 20:55 WeatherManager$WeatherChoice CNFE,
#    /칭호·계단앉기 등 전방위 고장. 사람이 알아챈 건 3시간 뒤였다.)
#
#   판정: plugins/*.jar 의 mtime > 서버 프로세스 시작시각  →  중간상태 확정.
#   조치: Discord 🔴 알림 + systemctl restart (jar을 정상 적용시켜 복구).
#         재시작은 30분에 1회로 제한(루프 방지). 접속자 유무와 무관하게 한다 —
#         중간상태를 방치하는 게 더 나쁘다.
#
#   ★훅(에이전트측)이 1차 방어고 이건 최종 방어다. 사람이 손으로 scp 하든,
#     훅 없는 도구가 하든, 배포 스크립트가 중간에 죽든 여기서 잡힌다.
#
#   env: PREVIEW=1 이면 알림·재시작 없이 판정만 출력 (테스트용)
#        GRACE / RESTART_CMD / WEBHOOK_FILE 주입 가능
# =====================================================================
set -uo pipefail

DIR=~/mcserver/scripts
PLUGINS="${PLUGINS:-$HOME/mcserver/plugins}"   # 테스트 주입 가능
LAST_FILE="$DIR/.jar_guard_last_restart"
LABEL="[바르칸 prod]"

GRACE="${GRACE:-90}"                 # 부팅 직후 유예(초) — 부팅 중 mtime 비교는 노이즈
COOLDOWN="${COOLDOWN:-1800}"         # 자동 재시작 최소 간격(초)
RESTART_CMD="${RESTART_CMD:-sudo systemctl restart mcserver}"
WEBHOOK_FILE="${WEBHOOK_FILE:-$DIR/discord-webhook.url}"
PREVIEW="${PREVIEW:-0}"

log(){ echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) [jar-guard] $*"; }
notify(){ [ "$PREVIEW" = "1" ] && { log "PREVIEW 알림: $1"; return 0; }
  [ -s "$WEBHOOK_FILE" ] || return 0; local u m p; u=$(cat "$WEBHOOK_FILE"); m="$LABEL $1"
  p=$(python3 -c "import json,sys;print(json.dumps({'content':sys.argv[1]}))" "$m")
  curl -sf -m 10 -H 'Content-Type: application/json' -d "$p" "$u" >/dev/null 2>&1 || true; }

now=$(date +%s)

# --- 서버 시작시각 ---
started_str=$(systemctl show mcserver -p ActiveEnterTimestamp --value 2>/dev/null || true)
started=0
[ -n "$started_str" ] && started=$(date -d "$started_str" +%s 2>/dev/null || echo 0)
if [ "$started" -le 0 ]; then log "시작시각 확인 불가 — skip"; exit 0; fi

# 서버가 안 돌면 판정 의미 없음 (systemd가 알아서 띄운다)
systemctl is-active --quiet mcserver || { log "mcserver 비활성 — skip"; exit 0; }

age=$((now - started))
if [ "$age" -lt "$GRACE" ]; then log "grace (uptime ${age}s < ${GRACE}s) — skip"; exit 0; fi

# --- 시작시각보다 새로운 jar 찾기 ---
newer=$(find "$PLUGINS" -maxdepth 1 -name '*.jar' -newermt "@$started" -printf '%f(%TH:%TM) ' 2>/dev/null)
if [ -z "${newer// /}" ]; then log "정상 — 시작시각($started_str) 이후 변경된 jar 없음"; exit 0; fi

log "⚠ 가동 중 교체된 jar 감지: $newer (uptime ${age}s)"

# --- 쿨다운 ---
last=0; [ -f "$LAST_FILE" ] && last=$(cat "$LAST_FILE" 2>/dev/null || echo 0)
if [ $((now - last)) -lt "$COOLDOWN" ]; then
  log "쿨다운 중($(( (COOLDOWN - (now - last)) / 60 ))분 남음) — 알림만"
  notify "🟠 가동 중 jar 교체가 또 감지됐다: \`$newer\`
쿨다운($((COOLDOWN/60))분)이라 자동 재시작은 건너뛴다. 배포 절차를 확인할 것 — jar만 올리고 재시작 안 한 상태는 그 자체가 고장이다."
  exit 0
fi

notify "🔴 **가동 중 jar 교체 감지 → 자동 재시작**
교체된 jar: \`$newer\`
서버 시작: $started_str (uptime $((age/60))분)

이 상태를 두면 그 뒤 처음 로드되는 클래스가 전부 NoClassDefFoundError가 나서 기능이 하나씩 죽는다. 지금 재시작해 정상 적용한다.
★jar을 올렸으면 **반드시 같은 작업으로 재시작**할 것 (\`~/deploy-blockship.sh\`) — 지연 배포는 \`~/stage-blockship.sh\`(staging/)를 쓸 것."

if [ "$PREVIEW" = "1" ]; then log "PREVIEW — 재시작 생략"; exit 0; fi

echo "$now" > "$LAST_FILE"
if $RESTART_CMD; then log "재시작 요청 완료"
else log "🔴 재시작 실패"; notify "🆘 jar 가드 재시작 실패 — 수동 개입 필요: \`sudo systemctl restart mcserver\`"; fi
