#!/usr/bin/env bash
# =====================================================================
# 바르칸 prod 데일리 리포트 + 예방적 새벽 재시작 (cron 21:00 UTC = 06:00 KST)
#   그날 모든 백업(19:00~20:45)이 끝난 뒤 실행 → 하루치를 한 메시지로 통합 발송:
#     · 예방 재시작 결과(0명이면 실행, 접속중이면 skip)
#     · 백업 성공 목록(.backup-status 누적분)
#     · 헬스 스냅샷(디스크·MC업타임·접속자)
#   ★실패 백업은 각 스크립트가 이미 즉시 개별 🔴 발송(여기 요약과 별개).
# env: DRY=1(재시작 안 함) / RESTART_CMD / STATUS_FILE / WEBHOOK_FILE
# =====================================================================
set -uo pipefail
DIR=~/mcserver/scripts
STATUS_FILE=${STATUS_FILE:-$HOME/mcserver/backups/.backup-status}
WEBHOOK_FILE=${WEBHOOK_FILE:-$DIR/discord-webhook.url}
RESTART_CMD=${RESTART_CMD:-sudo systemctl restart mcserver}
LABEL="[바르칸 prod]"
log(){ echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) [daily] $*"; }
notify(){ [ -s "$WEBHOOK_FILE" ] || return 0; local u p; u=$(cat "$WEBHOOK_FILE")
  p=$(python3 -c "import json,sys;print(json.dumps({'content':sys.argv[1]}))" "$1")
  curl -sf -m 10 -H 'Content-Type: application/json' -d "$p" "$u" >/dev/null 2>&1 || true; }

today=$(date -u +%Y-%m-%d)

# --- 접속자 수 (RCON) ---
out=$("$DIR/rcon.py" list 2>/dev/null); rc=$?
if [ $rc -eq 0 ]; then
  n=$(printf '%s' "$out" | grep -oE 'are [0-9]+' | grep -oE '[0-9]+' | head -1); n=${n:-0}
else
  n=-1
fi

# --- 재시작 결정 ---
do_restart=0
if   [ "$n" -eq 0 ]; then restart_line="🔄 예방 재시작: 실행 (접속 0명)"; do_restart=1
elif [ "$n" -gt 0 ]; then restart_line="⏭️ 예방 재시작: 건너뜀 (${n}명 접속중)"
else                      restart_line="⚠️ 예방 재시작: 건너뜀 (RCON 무응답 — 워치독 담당)"
fi

# --- 백업 성공 목록 ---
if [ -s "$STATUS_FILE" ]; then
  bcount=$(grep -c . "$STATUS_FILE"); backups=$(cat "$STATUS_FILE")
else
  bcount=0; backups="⚠️ 성공 기록 없음 (전부 실패했거나 안 돎 — 실패 시 개별 🔴 확인)"
fi

# --- 헬스 스냅샷 ---
disk=$(df / | awk 'NR==2{print $5}')
np=$([ "$n" -ge 0 ] && echo "${n}명" || echo "무응답")
started=$(date -d "$(systemctl show mcserver -p ActiveEnterTimestamp --value 2>/dev/null)" +%s 2>/dev/null || echo 0)
if [ "$started" -gt 0 ]; then uph=$(( ( $(date +%s) - started ) / 3600 )); upl="${uph}h"; else upl="?"; fi

msg="$LABEL 🌅 데일리 리포트 ($today · 06:00 KST)

$restart_line

📦 백업 ${bcount}건 성공
$backups

💾 디스크 $disk · 🕐 MC업타임 $upl · 👥 접속 $np"

# PREVIEW=1 : 발송·재시작·파일비움 없이 메시지만 출력 (테스트용)
if [ "${PREVIEW:-0}" = "1" ]; then printf '%s\n' "$msg"; exit 0; fi

notify "$msg"
> "$STATUS_FILE"                       # 리포트 후 비움
log "리포트 발송 (백업 ${bcount}건, 접속 ${np})"

# --- 예방 재시작 실행 ---
if [ "$do_restart" = "1" ]; then
  if [ "${DRY:-0}" = "1" ]; then log "DRY: would restart"; exit 0; fi
  eval "$RESTART_CMD"
  log "restarted"
fi
