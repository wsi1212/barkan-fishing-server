#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# staging/ 의 jar 을 **지금 즉시** 적용하고 재시작한다.
#
# 평소 배포는 06:00 데일리 유지보수(nightly-restart.sh)가 한다. 이 스크립트는
# 베타 기간처럼 "고치자마자 봐야 하는" 때만 쓰는 지름길이다.
# 호출 경로는 둘:
#   ① fetch-staging.sh 가 태그가 now-* 인 Release 를 받았을 때 자동으로
#   ② 사람이 직접 (~/mcserver/scripts/apply-staged.sh)
#
# ★nightly 와 같은 규칙을 쓴다 — 구 jar 백업 → 교체 → 예고 → flush → 재시작.
#   다르게 굴면 두 경로가 서로 다른 상태를 만든다. 여기서 추가된 건 **부팅 확인**뿐이다
#   (06:00 은 사람이 자는 시간이라 확인이 의미 없지만, 즉시 배포는 지금 보고 있다).
#
# ★staging 을 비우고 적용한다 — 안 비우면 다음날 06:00 에 같은 jar 이 또 적용된다.
#   (rollback-jar.sh 가 staging 을 비우는 것과 같은 이유)
#
# 사용:
#   apply-staged.sh              적용 + 재시작
#   apply-staged.sh --dry-run    무엇을 할지만 출력
#   apply-staged.sh --wait 90    재시작 예고 후 대기 시간(초, 기본 60 · 접속자 0명이면 무시)
# ─────────────────────────────────────────────────────────────────────────────
set -uo pipefail

MC_ROOT="${MC_ROOT:-$HOME/mcserver}"
DIR="$MC_ROOT/scripts"
STAGING="${STAGING:-$MC_ROOT/staging}"
PLUGINS="${PLUGINS:-$MC_ROOT/plugins}"
JARBAK="${JARBAK:-$MC_ROOT/backups/deployed-jars}"
WEBHOOK_FILE="${WEBHOOK_FILE:-$DIR/discord-webhook.url}"
LOG_FILE="${APPLY_LOG:-$MC_ROOT/backups/ops.log}"   # ★운영 로그는 backups/ 에 모인다
RESTART_CMD="${RESTART_CMD:-sudo systemctl restart mcserver}"
WAIT_SEC="${WAIT_SEC:-60}"
BOOT_TIMEOUT="${BOOT_TIMEOUT:-180}"

DRY=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run) DRY=1; shift ;;
    --wait) WAIT_SEC="${2:-60}"; shift 2 ;;
    -h|--help) sed -n '2,22p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "알 수 없는 인자: $1" >&2; exit 2 ;;
  esac
done

log() { local m="[$(date '+%Y-%m-%d %H:%M:%S')] [apply-staged] $*"; echo "$m"; echo "$m" >> "$LOG_FILE" 2>/dev/null || true; }
notify() {
  [[ -s "$WEBHOOK_FILE" ]] || return 0
  local u; u=$(<"$WEBHOOK_FILE")
  curl -fsS --max-time 15 -H 'Content-Type: application/json' \
    -d "$(python3 -c 'import json,sys;print(json.dumps({"content":sys.argv[1]}))' "$1")" \
    "$u" >/dev/null 2>&1 || true
}
rcon() { "$DIR/rcon.py" "$@" 2>/dev/null; }

shopt -s nullglob
JARS=("$STAGING"/BlockShip-*.jar)
if [[ ${#JARS[@]} -eq 0 ]]; then
  log "staging 에 jar 이 없다 — 할 일 없음"; exit 0
fi
if [[ ${#JARS[@]} -gt 1 ]]; then
  # fetch-staging.sh 가 넣기 전에 구 jar 을 지우므로 정상적으로는 안 생긴다.
  log "✗ staging 에 jar 이 ${#JARS[@]}개다 — 어느 걸 쓸지 모호하니 중단한다"
  notify "🔴 **즉시 배포 중단** — staging 에 jar 이 ${#JARS[@]}개다. 수동 정리 필요."
  exit 1
fi
JAR="${JARS[0]}"; BN=$(basename "$JAR")

# 접속자 수 (-1 = 서버 무응답)
n=-1
if out=$(rcon list); then
  n=$(printf '%s' "$out" | grep -oE 'are [0-9]+' | grep -oE '[0-9]+' | head -1)
  n=${n:-0}
fi

log "적용 대상: $BN (접속 ${n}명)"
if [[ $DRY -eq 1 ]]; then
  log "DRY: 구 jar 백업 → 교체 → $([[ $n -gt 0 ]] && echo "${WAIT_SEC}초 예고 → ")재시작"
  exit 0
fi

# ── 접속자가 있으면 예고하고 기다린다 ────────────────────────────────
# 06:00 재시작은 restart-warning.sh 가 30/10/5/1분 전에 방송하지만, 즉시 배포는
# 예고할 시간이 없다. 그래도 통보 없이 끊으면 안 되니 짧게라도 센다.
if [[ $n -gt 0 ]]; then
  rcon "say [서버] 긴급 업데이트 적용으로 ${WAIT_SEC}초 후 재시작합니다. 잠시 후 다시 접속해 주세요." >/dev/null
  log "접속자 ${n}명 — ${WAIT_SEC}초 예고 후 재시작"
  sleep "$WAIT_SEC"
fi

# ── 구 jar 백업 → 교체 (nightly 와 같은 규칙) ────────────────────────
mkdir -p "$JARBAK"
STAMP=$(date -u +%Y%m%d-%H%M%S)
if [[ -f "$PLUGINS/$BN" ]]; then
  cp -f "$PLUGINS/$BN" "$JARBAK/${BN}.bak-$STAMP" || { log "✗ 구 jar 백업 실패 — 중단"; notify "🔴 **즉시 배포 중단** — 구 jar 백업 실패"; exit 1; }
  log "구 jar 백업: $JARBAK/${BN}.bak-$STAMP"
fi
mv -f "$JAR" "$PLUGINS/$BN" || { log "✗ jar 교체 실패"; notify "🔴 **즉시 배포 실패** — jar 교체 실패"; exit 1; }
log "jar 교체 완료: $PLUGINS/$BN"

# ── 저장 플러시 후 재시작 ─────────────────────────────────────────────
[[ $n -ge 0 ]] && { rcon "save-all flush" >/dev/null; sleep 3; }
log "재시작"
eval "$RESTART_CMD"

# ── 부팅 확인 — 즉시 배포는 지금 보고 있으니 여기서 결과를 낸다 ──────
# rcon 이 응답하면 서버가 살아난 것이다. 안 살아나면 롤백해야 한다.
deadline=$(( $(date +%s) + BOOT_TIMEOUT ))
until rcon list >/dev/null 2>&1; do
  if [[ $(date +%s) -ge $deadline ]]; then
    log "✗ ${BOOT_TIMEOUT}초 안에 부팅되지 않았다"
    notify "🔴 **즉시 배포 후 서버가 안 올라온다** — \`$BN\`
${BOOT_TIMEOUT}초 무응답. 로그: \`tail -100 ~/mcserver/logs/latest.log\`
되돌리려면: \`~/mcserver/scripts/rollback-jar.sh yes\`"
    exit 1
  fi
  sleep 5
done

log "부팅 확인 — 즉시 배포 완료"
notify "⚡ **즉시 배포 완료** — \`$BN\`
서버가 다시 올라온 것까지 확인했다. (구 jar 백업: \`${BN}.bak-$STAMP\`)
문제 있으면: \`~/mcserver/scripts/rollback-jar.sh yes\`"
exit 0
