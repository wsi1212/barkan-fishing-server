#!/usr/bin/env bash
# =====================================================================
# 바르칸 prod 데일리 유지보수 (cron 21:00 UTC = 06:00 KST)
#   ① 스테이징 자동배포: ~/mcserver/staging/ 의 jar/설정을 재시작 직전 적용
#      (낮에 올려두면 Mac 꺼져있어도 6시에 자동 반영)
#   ② 무조건 재시작(누수정리): 사전예고는 restart-warning.sh(30/10/5/1분 전, 별도 cron)가
#      이미 함 — 여기선 재시작 직전 즉시 알림 1회만 + save-all flush
#   ③ 데일리 리포트: 배포결과 + 백업 성공목록 + 헬스 스냅샷을 한 메시지로
#   ★실패 백업은 각 스크립트가 이미 즉시 개별 🔴 발송(여기 요약과 별개).
# env: PREVIEW=1(발송·배포·재시작 없이 메시지 출력) / DRY=1(재시작·배포 실제로 안 함)
#      RESTART_CMD / STATUS_FILE / WEBHOOK_FILE / STAGING
# =====================================================================
set -uo pipefail
DIR=~/mcserver/scripts
STATUS_FILE=${STATUS_FILE:-$HOME/mcserver/backups/.backup-status}
WEBHOOK_FILE=${WEBHOOK_FILE:-$DIR/discord-webhook.url}
RESTART_CMD=${RESTART_CMD:-sudo systemctl restart mcserver}
STAGING=${STAGING:-$HOME/mcserver/staging}
PLUGINS=${PLUGINS:-$HOME/mcserver/plugins}
JARBAK=${JARBAK:-$HOME/mcserver/backups/deployed-jars}
DRYRUN=0; [ "${PREVIEW:-0}" = "1" ] && DRYRUN=1; [ "${DRY:-0}" = "1" ] && DRYRUN=1
LABEL="[바르칸 prod]"
log(){ echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) [daily] $*"; }
notify(){ [ -s "$WEBHOOK_FILE" ] || return 0; local u p; u=$(cat "$WEBHOOK_FILE")
  p=$(python3 -c "import json,sys;print(json.dumps({'content':sys.argv[1]}))" "$1")
  curl -sf -m 10 -H 'Content-Type: application/json' -d "$p" "$u" >/dev/null 2>&1 || true; }
rcon(){ "$DIR/rcon.py" "$1" >/dev/null 2>&1; }
SKIP_MARK="$DIR/.skip-nightly-once"

today=$(date -u +%Y-%m-%d)

# --- 오늘 밤만 스킵 요청 있으면: 배포/재시작/방송 전부 건너뜀(1회성, 자동 소모) ---
if [ -f "$SKIP_MARK" ]; then
  rm -f "$SKIP_MARK"
  if [ "${PREVIEW:-0}" = "1" ]; then echo "(스킵 마커 있음 — 오늘밤 재시작 생략됨)"; exit 0; fi
  notify "$LABEL ⏭️ 오늘 06:00 정기 재시작 — 요청에 의해 1회 스킵됨(내일부터 정상 진행)."
  log "skip-once 마커로 오늘 재시작 생략"
  exit 0
fi

# --- 접속자 수 ---
out=$("$DIR/rcon.py" list 2>/dev/null) && \
  n=$(printf '%s' "$out" | grep -oE 'are [0-9]+' | grep -oE '[0-9]+' | head -1) || n=-1
n=${n:-0}

# --- ① 스테이징 배포 감지(+적용) ---
shopt -s nullglob
deploy_lines=""
for j in "$STAGING"/*.jar; do
  bn=$(basename "$j")
  deploy_lines+="🚀 ${bn}"$'\n'
  if [ "$DRYRUN" = "0" ]; then
    mkdir -p "$JARBAK"
    [ -f "$PLUGINS/$bn" ] && cp -f "$PLUGINS/$bn" "$JARBAK/${bn}.bak-$(date -u +%Y%m%d-%H%M%S)"
    mv -f "$j" "$PLUGINS/$bn"; log "배포 jar 적용: $bn"
  else log "DRY: would deploy jar $bn"; fi
done
if [ -d "$STAGING/BlockShip" ] && [ -n "$(ls -A "$STAGING/BlockShip" 2>/dev/null)" ]; then
  # ★2026-08-01 사고 후 게이트: 예전엔 cp -rf 로 통째 복사했다가, NPC 1명짜리 부분
  #   npc.json이 138명짜리 라이브를 덮어 NPC/대화/퀘스트가 통째로 죽었다.
  #   validate-staged.py 가 파싱·항목수감소·스키마파손을 검사해 거부한다.
  #   거부된 파일은 staging-rejected/ 로 격리(다음날 조용히 재적용되지 않게) + 리포트에 표기.
  ok=0; rej=0; rejlist=""
  REJDIR="$STAGING-rejected/$(date -u +%Y%m%d-%H%M%S)"
  while IFS= read -r src; do
    rel="${src#$STAGING/BlockShip/}"
    case "$rel" in *.allow-shrink) continue;; esac
    dst="$PLUGINS/BlockShip/$rel"
    if reason=$(python3 "$DIR/validate-staged.py" "$src" "$dst" 2>&1); then
      if [ "$DRYRUN" = "0" ]; then mkdir -p "$(dirname "$dst")"; cp -f "$src" "$dst"; fi
      ok=$((ok+1))
    else
      rej=$((rej+1)); rejlist+="   ⛔ $rel — $reason"$'\n'
      if [ "$DRYRUN" = "0" ]; then mkdir -p "$REJDIR"; cp -f "$src" "$REJDIR/"; fi
      log "스테이징 거부: $rel — $reason"
    fi
  done < <(find "$STAGING/BlockShip" -type f)
  [ "$ok" -gt 0 ] && deploy_lines+="🚀 BlockShip 설정 ${ok}개 갱신"$'\n'
  if [ "$rej" -gt 0 ]; then
    deploy_lines+="🔴 BlockShip 설정 ${rej}개 거부(적용 안 함, staging-rejected/ 로 격리)"$'\n'"$rejlist"
    notify "$LABEL 🔴 스테이징 배포 거부 ${rej}건 — 부분 파일이 라이브를 덮으려 했습니다.
$rejlist"
  fi
  if [ "$DRYRUN" = "0" ]; then rm -rf "$STAGING/BlockShip"; log "배포 설정 적용 ${ok}개 / 거부 ${rej}개"
  else log "DRY: would deploy $ok, reject $rej"; fi
fi
[ -z "$deploy_lines" ] && deploy_summary="배포 없음" || deploy_summary=$(printf '%s' "$deploy_lines")

# --- ② 재시작 직전 즉시 알림 (사전예고 30/10/5/1분은 restart-warning.sh가 이미 방송함) ---
if [ "$n" -gt 0 ] && [ "$DRYRUN" = "0" ]; then
  rcon "say [서버] 서버 재부팅합니다 (정기 점검 06:00~06:10). 06:10 이후 다시 접속해 주세요."
fi

# --- 저장 플러시 (서버 응답할 때) ---
[ "$n" -ge 0 ] && [ "$DRYRUN" = "0" ] && { rcon "save-all flush"; sleep 3; }

# --- 백업 성공 목록 ---
if [ -s "$STATUS_FILE" ]; then bcount=$(grep -c . "$STATUS_FILE"); backups=$(cat "$STATUS_FILE")
else bcount=0; backups="⚠️ 성공 기록 없음 (전부 실패했거나 안 돎 — 실패 시 개별 🔴 확인)"; fi

# --- 헬스 스냅샷 ---
disk=$(df / | awk 'NR==2{print $5}')
np=$([ "$n" -ge 0 ] && echo "${n}명$([ "$n" -gt 0 ] && echo ' (예고 후 재시작)')" || echo "무응답")
started=$(date -d "$(systemctl show mcserver -p ActiveEnterTimestamp --value 2>/dev/null)" +%s 2>/dev/null || echo 0)
[ "$started" -gt 0 ] && upl="$(( ( $(date +%s) - started ) / 3600 ))h" || upl="?"

msg="$LABEL 🌅 데일리 리포트 ($today · 06:00 KST)

🔄 정기 재시작 실행
$deploy_summary

📦 백업 ${bcount}건 성공
$backups

💾 디스크 $disk · 🕐 MC업타임 $upl · 👥 접속 $np"

# --- PREVIEW: 출력만 ---
if [ "${PREVIEW:-0}" = "1" ]; then printf '%s\n' "$msg"; exit 0; fi

notify "$msg"
> "$STATUS_FILE"
log "리포트 발송 (배포:$([ "$deploy_summary" = "배포 없음" ] && echo 없음 || echo 있음), 백업 ${bcount}건, 접속 ${np})"

# --- ③ 재시작 (무조건) ---
if [ "${DRY:-0}" = "1" ]; then log "DRY: would restart"; exit 0; fi
eval "$RESTART_CMD"
log "restarted"
