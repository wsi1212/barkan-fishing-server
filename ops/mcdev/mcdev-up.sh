#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# dev 켜기 (+ 자동 종료 예약)
#
# 기본 60분 뒤 자동으로 내려간다. 켜둔 걸 잊어도 prod와 자원 경쟁을 오래 하지 않는다.
# 안전망은 2중: ① 이 스크립트가 띄우는 타이머 데몬 ② mcdev-reaper.sh (cron)
#
# 사용법:
#   mcdev-up.sh                                     # 현재 dev 플러그인 그대로 60분
#   mcdev-up.sh --jar ~/mcserver/staging/BlockShip-*.jar   # 후보 jar 검증 ★핵심 용도
#   mcdev-up.sh --minutes 30
#   mcdev-up.sh --minutes 90                        # 이미 켜져 있으면 시한만 연장
# ─────────────────────────────────────────────────────────────────────────────
set -uo pipefail
cd "$(dirname "$0")" && source ./mcdev-lib.sh

# ── 타이머 데몬 모드 (내부용, setsid 로 자기 자신을 재호출) ──────────────────
if [[ "${1:-}" == "--timer-daemon" ]]; then
  DEADLINE="$2"
  # ★자기 PID 를 직접 기록한다. 호출측의 $! 는 setsid 중간 프로세스를 가리킬 수 있어
  #   그걸 kill 해도 데몬이 안 죽는다.
  echo $$ > "$TIMER_PID_FILE"
  warned10=0; warned5=0; warned1=0
  # ★시한이 임계값보다 짧으면 그 경고는 애초에 보내지 않는다.
  #   안 그러면 --minutes 2 에서 "5분 후 종료" → "10분 후 종료" 순으로 거짓말을 한다(실측).
  LEFT0=$(( DEADLINE - $(date +%s) ))
  [[ $LEFT0 -le 600 ]] && warned10=1
  [[ $LEFT0 -le 300 ]] && warned5=1
  [[ $LEFT0 -le 60  ]] && warned1=1
  while :; do
    dev_running || { log "타이머: dev가 이미 내려갔다 — 타이머 종료"; exit 0; }
    # 시한이 밖에서 연장되면 즉시 반영
    [[ -f "$DEADLINE_FILE" ]] && DEADLINE=$(<"$DEADLINE_FILE")
    LEFT=$(( DEADLINE - $(date +%s) ))
    if   [[ $LEFT -le 0 ]]; then break
    elif [[ $LEFT -le 60   && $warned1 -eq 0 ]]; then dev_rcon "say §c[dev] 1분 후 자동 종료" >/dev/null; warned1=1
    elif [[ $LEFT -le 300  && $warned5 -eq 0 ]]; then dev_rcon "say §e[dev] 5분 후 자동 종료" >/dev/null; warned5=1
    elif [[ $LEFT -le 600  && $warned10 -eq 0 ]]; then dev_rcon "say §7[dev] 10분 후 자동 종료" >/dev/null; warned10=1
    fi
    sleep 15
  done
  log "타이머: 시한 만료 → dev 종료"
  dev_rcon "save-all flush" >/dev/null; sleep 5
  dev_rcon "stop" >/dev/null
  for _ in $(seq 1 60); do dev_java_running || break; sleep 2; done
  if dev_java_running; then
    log "타이머: stop 이 안 먹었다 — 강제 종료"
    dev_java_kill
  fi
  tmux kill-session -t "$MCDEV_TMUX" 2>/dev/null
  rm -f "$DEADLINE_FILE" "$TIMER_PID_FILE" "$JAVA_PID_FILE"
  log "dev 자동 종료 완료"
  notify "🌙 **dev 자동 종료** (시한 만료)"
  exit 0
fi

MINUTES="$MCDEV_MINUTES_DEFAULT"
CAND_JAR=""
SKIP_GUARDS="${MCDEV_SKIP_GUARDS:-0}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --jar)       CAND_JAR="$2"; shift 2 ;;
    --minutes)   MINUTES="$2"; shift 2 ;;
    --heap)      MCDEV_HEAP="$2"; shift 2 ;;
    --no-guards) SKIP_GUARDS=1; shift ;;
    -h|--help)   sed -n '2,16p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) die "알 수 없는 인자: $1" ;;
  esac
done

[[ "$MINUTES" =~ ^[0-9]+$ ]] || die "--minutes 는 숫자여야 한다: $MINUTES"

# ── 이미 켜져 있으면 시한 연장만 ────────────────────────────────────────────
if dev_running; then
  NEW=$(( $(date +%s) + MINUTES * 60 ))
  echo "$NEW" > "$DEADLINE_FILE"
  log "dev는 이미 돌고 있다 — 시한을 ${MINUTES}분으로 갱신 (종료 예정 $(date -d "@$NEW" '+%H:%M'))"
  dev_rcon "say §a[dev] 종료 시한이 $(date -d "@$NEW" '+%H:%M') 로 연장됨" >/dev/null
  exit 0
fi

log "═══ dev 시작 ═══"
[[ -f "$MCDEV_ROOT/mcdev-paper.jar" ]] || die "dev가 아직 시딩되지 않았다 — mcdev-sync.sh 를 먼저 돌릴 것"

# ── 가드 ────────────────────────────────────────────────────────────────────
if [[ "$SKIP_GUARDS" != "1" ]]; then
  # ★prod 가 죽어있으면 dev 를 켤 때가 아니다. prod 를 고칠 때다.
  if ! prod_running; then
    die "prod가 돌지 않는다 — dev보다 prod가 먼저다. (의도한 거면 --no-guards)"
  fi
  # ★메모리: prod 힙 16G + JVM 오버헤드에 dev 를 얹다 OOM 이 나면 죽는 건 prod 다.
  MEM=$(mem_available_mb)
  log "MemAvailable ${MEM}MB (문턱 ${MEM_FLOOR_MB}MB)"
  if [[ "$MEM" -lt "$MEM_FLOOR_MB" ]]; then
    die "메모리 부족 — 시작 거부. prod 힙을 12G로 내리거나(start.sh, 2026-07-07에 12G→16G 올린 것) --heap 을 줄일 것."
  fi
  USED=$(disk_used_pct "$HOME")
  [[ "$USED" -ge 88 ]] && die "디스크 ${USED}% — 시작 거부 (disk-guard가 백업을 지우기 시작한다)"
fi

# ── 후보 jar 투입 ───────────────────────────────────────────────────────────
if [[ -n "$CAND_JAR" ]]; then
  # glob 이 넘어올 수 있으니 첫 매치를 쓴다
  RESOLVED=$(ls -1 $CAND_JAR 2>/dev/null | head -1)
  [[ -n "$RESOLVED" && -f "$RESOLVED" ]] || die "jar 없음: $CAND_JAR"
  rm -f "$MCDEV_ROOT"/plugins/BlockShip-*.jar
  cp "$RESOLVED" "$MCDEV_ROOT/plugins/"
  log "후보 jar 투입: $(basename "$RESOLVED") ($(du -h "$RESOLVED" | cut -f1))"
fi

# ── 포트 확인 ───────────────────────────────────────────────────────────────
# OCI Security List 는 박스 안에서 알 수 없다. iptables 만 확인하고 안내한다.
if command -v iptables >/dev/null && sudo -n true 2>/dev/null; then
  if ! sudo -n iptables -C INPUT -p tcp --dport "$MCDEV_GAME_PORT" -j ACCEPT 2>/dev/null; then
    log "⚠ iptables에 ${MCDEV_GAME_PORT} 허용 규칙이 없다. 폰에서 접속하려면:"
    log "    sudo iptables -I INPUT -p tcp --dport $MCDEV_GAME_PORT -j ACCEPT"
    log "    그리고 OCI 콘솔 Security List 에 ${MCDEV_GAME_PORT}/tcp 인그레스 추가"
  fi
else
  log "ⓘ iptables 확인 생략 (sudo 무암호 아님) — ${MCDEV_GAME_PORT} 개방 여부는 직접 확인"
fi

# ── 기동 ────────────────────────────────────────────────────────────────────
rm -f "$MCDEV_ROOT"/*/session.lock 2>/dev/null
mkdir -p "$MCDEV_ROOT/logs"
: > "$MCDEV_ROOT/logs/latest.log" 2>/dev/null || true

log "tmux 세션 '$MCDEV_TMUX' 기동 (heap $MCDEV_HEAP, ${MINUTES}분 후 자동 종료)"
# JVM PID 를 파일로 남긴다 — 프로세스 판정을 pgrep -f 문자열매칭에 의존하지 않기 위해.
rm -f "$JAVA_PID_FILE"
tmux new-session -d -s "$MCDEV_TMUX" -c "$MCDEV_ROOT" \
  "java -Xms1G -Xmx$MCDEV_HEAP -XX:+UseG1GC -jar mcdev-paper.jar --nogui & \
   echo \$! > '$JAVA_PID_FILE'; wait"

BOOTED=0
for i in $(seq 1 180); do
  if grep -q 'Done (' "$MCDEV_ROOT/logs/latest.log" 2>/dev/null; then BOOTED=1; log "부팅 완료 (${i}s)"; break; fi
  tmux has-session -t "$MCDEV_TMUX" 2>/dev/null || { log "✗ 세션이 죽었다"; break; }
  sleep 1
done

if [[ $BOOTED -eq 0 ]]; then
  log "✗ 180s 안에 부팅되지 않았다. 로그 확인: $MCDEV_ROOT/logs/latest.log"
  tail -20 "$MCDEV_ROOT/logs/latest.log" 2>/dev/null
  notify "🔴 **dev 부팅 실패** — 로그 확인 필요"
  exit 1
fi

# ── 부팅 직후 점검 ──────────────────────────────────────────────────────────
if grep -qE 'NoClassDefFoundError|Error occurred while enabling' "$MCDEV_ROOT/logs/latest.log"; then
  log "⚠⚠ 부팅 로그에 치명 예외가 있다 — 이 jar 를 prod 로 보내지 말 것"
  grep -m5 -E 'NoClassDefFoundError|Error occurred while enabling' "$MCDEV_ROOT/logs/latest.log"
  notify "🔴 **dev 부팅 로그에 치명 예외** — 이 jar 는 승격 금지"
fi

# 화이트리스트는 부팅 후 rcon 으로. 이름만 주면 Paper 가 UUID 를 조회해 준다.
sleep 2
for who in ${MCDEV_WHITELIST//,/ }; do
  dev_rcon "whitelist add $who" >/dev/null && log "화이트리스트 추가: $who"
done
dev_rcon "whitelist on" >/dev/null

# ── 시한 등록 + 타이머 데몬 ─────────────────────────────────────────────────
DEADLINE=$(( $(date +%s) + MINUTES * 60 ))
echo "$DEADLINE" > "$DEADLINE_FILE"
# ★stdout 을 로그로 보내면 log() 의 echo 와 겹쳐 모든 줄이 두 번 찍힌다(실측).
#   log() 가 이미 파일에 쓰므로 stdout 은 버리고, 예기치 못한 stderr 만 남긴다.
setsid nohup "$PWD/$(basename "$0")" --timer-daemon "$DEADLINE" \
  >/dev/null 2>>"$LOG_FILE" < /dev/null &
# PID 는 데몬이 스스로 TIMER_PID_FILE 에 쓴다 (위 --timer-daemon 분기 참조)

STOP_AT=$(date -d "@$DEADLINE" '+%H:%M')
IP=$(curl -fsS --max-time 8 https://checkip.amazonaws.com 2>/dev/null | tr -d '\n')
log "═══ dev 준비 완료 — ${IP:-<서버IP>}:${MCDEV_GAME_PORT} · ${STOP_AT} 자동 종료 ═══"
notify "🟢 **dev 켜짐** — \`${IP:-서버IP}:${MCDEV_GAME_PORT}\`
자동 종료: **${STOP_AT}** (${MINUTES}분)
$( [[ -n "$CAND_JAR" ]] && echo "검증 대상: \`$(basename "$RESOLVED")\`" )
연장: \`mcdev-up.sh --minutes 90\` · 즉시 종료: \`mcdev-down.sh\`"
exit 0
