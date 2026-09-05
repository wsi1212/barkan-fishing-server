#!/usr/bin/env bash
# =====================================================================
# 바르칸 prod 데일리 유지보수 (cron 21:00 UTC = 06:00 KST)
#   ① 스테이징 자동배포: ~/mcserver/staging/ 의 jar/설정을 재시작 직전 적용
#      (낮에 올려두면 Mac 꺼져있어도 6시에 자동 반영)
#   ② 무조건 재시작(누수정리): 사전예고는 restart-warning.sh(30/10/5/1분 전, 별도 cron)가
#      이미 함 — 여기선 재시작 직전 즉시 알림 1회만 + save-all flush
#   ③ 데일리 리포트: 배포결과 + 백업 성공목록 + 헬스 스냅샷을 한 메시지로
#   ★실패 백업은 각 스크립트가 이미 즉시 개별 🔴 발송(여기 요약과 별개).
#
# 즉시 모드 (--now / NOW=1) — fetch-staging.sh 가 APPLY_NOW 마커를 보면 부른다.
#   06:00 을 기다리지 않고 지금 적용한다. 적용·검증 로직을 복제하지 않으려고
#   같은 스크립트에 모드를 붙였다 — validate-staged 게이트·리소스팩 교차검증·구 jar
#   백업이 전부 여기 있고, 사본을 만들면 한쪽만 고쳐지는 날이 온다.
#   정기 실행과 다른 점 네 가지:
#     ① staging 이 비어 있으면 재시작하지 않는다(정기는 누수정리 목적이라 무조건 재시작)
#     ② 예고 방송이 없었으므로 GRACE 초(기본 60) 를 주고 재시작
#     ③ 데일리 리포트가 아니라 배포 알림을 보내고, **.backup-status 를 지우지 않는다**
#        (지우면 그날 06:00 리포트가 "백업 성공 기록 없음" 으로 나온다)
#     ④ 부팅까지 확인하고 실패하면 롤백 방법과 함께 알린다(사람이 안 볼 시간대라서)
#   skip-once 마커는 정기 재시작용이라 즉시 모드에선 건드리지 않는다.
#
# env: PREVIEW=1(발송·배포·재시작 없이 메시지 출력) / DRY=1(재시작·배포 실제로 안 함)
#      NOW=1(즉시 모드) / GRACE=초(즉시 모드 예고 시간, 기본 60)
#      RESTART_CMD / STATUS_FILE / WEBHOOK_FILE / STAGING
# =====================================================================
set -uo pipefail

DIR=~/mcserver/scripts
STATUS_FILE=${STATUS_FILE:-$HOME/mcserver/backups/.backup-status}
WEBHOOK_FILE=${WEBHOOK_FILE:-$DIR/discord-webhook.url}
RESTART_CMD=${RESTART_CMD:-sudo systemctl restart mcserver}
STOP_CMD=${STOP_CMD:-sudo systemctl stop mcserver}
START_CMD=${START_CMD:-sudo systemctl start mcserver}
STAGING=${STAGING:-$HOME/mcserver/staging}
PLUGINS=${PLUGINS:-$HOME/mcserver/plugins}
JARBAK=${JARBAK:-$HOME/mcserver/backups/deployed-jars}
DRYRUN=0; [ "${PREVIEW:-0}" = "1" ] && DRYRUN=1; [ "${DRY:-0}" = "1" ] && DRYRUN=1
IMMEDIATE=${NOW:-0}
case "${1:-}" in --now|now) IMMEDIATE=1 ;; esac
GRACE=${GRACE:-60}
LABEL="[바르칸 prod]"
log(){ echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) [daily] $*"; }
notify(){ [ -s "$WEBHOOK_FILE" ] || return 0; local u p; u=$(cat "$WEBHOOK_FILE")
  p=$(python3 -c "import json,sys;print(json.dumps({'content':sys.argv[1]}))" "$1")
  curl -sf -m 10 -H 'Content-Type: application/json' -d "$p" "$u" >/dev/null 2>&1 || true; }
rcon(){ "$DIR/rcon.py" "$1" >/dev/null 2>&1; }
SKIP_MARK="$DIR/.skip-nightly-once"

# --- 로컬 백업 -------------------------------------------------------------
#   대용량 월드(main/islands)는 05:50 KST pre-restart-backup.sh 가 라이브에서
#   save-all flush 후 미리 만든다. 오늘 마커가 없을 때만 06:00 정지 창에서
#   폴백한다. 따라서 정상적인 재시작에는 139초의 월드 tar가 더해지지 않는다.
#   playerdata(BlockShip)는 종료 저장 직후가 가장 정확하고 약 4초뿐이므로 06:00
#   정지 창에서 계속 tar 한다.
#   ★오프사이트 3종(offsite-backup / offsite-worlds)은 여기 넣지 않는다.
#     OCI 업로드가 네트워크에 묶여 있어 다운타임이 예측 불가능해진다
#     (격주 본월드는 1.4GB 업로드). 그건 각자 cron 그대로 둔다.
#   ★백업이 어떻게 끝나든 서버는 반드시 다시 올린다(아래 trap).
BACKUP_GROUPS=${BACKUP_GROUPS:-"main islands"}
BACKUP_TIMEOUT=${BACKUP_TIMEOUT:-600}
bsec=""; boot_line=""; OFFSITE_BS_TAR=""; backup_note=""
OFFLOG=${OFFLOG:-$HOME/mcserver/backups/offsite.log}
BAKDIR=${BAKDIR:-$HOME/mcserver/backups}
PREBACKUP_MARK=${PREBACKUP_MARK:-$BAKDIR/.pre-restart-backup-ready}
PREBACKUP_LOCK=${PREBACKUP_LOCK:-$BAKDIR/.pre-restart-backup.lock}
prebackup_ready(){
  [ -s "$PREBACKUP_MARK" ] && grep -qx "$(TZ=Asia/Seoul date +%Y-%m-%d)" "$PREBACKUP_MARK"
}
# 05:50 작업이 예외적으로 아직 돌고 있으면 tar 중인 월드를 종료하지 않는다.
# 정상 실측은 약 139초라 이 대기는 생기지 않는다.
wait_for_prebackup(){
  if ! flock -n "$PREBACKUP_LOCK" -c true; then
    log "05:50 월드 백업 진행 중 — 완료 후 정기 재시작 계속"
    flock "$PREBACKUP_LOCK" -c true
  fi
}
# 백업 디렉터리에서 «방금 만들어진» tar 하나를 고른다. 최신 파일을 그냥 집으면
# 오늘 백업이 실패한 날 어제 tar 를 오늘 이름으로 올려버린다 — 조용한 거짓 백업.
fresh_tar(){ find "$BAKDIR" -maxdepth 1 -name "$1-*.tar.gz" -mmin -"${2:-60}" -print 2>/dev/null | sort | tail -1; }

# --- 오프사이트 업로드(기동 후) ---
#   2026-09-05: 04:00/05:30/05:45 KST 개별 cron 이던 오프사이트 3종을 여기로 흡수했다.
#   ★tar 를 다시 뜨지 않는다 — 정지 중에 만든 로컬 tar 를 그대로 올린다.
#     offsite-worlds.sh 의 월드 목록이 local-backup.sh 와 글자까지 같아서, 예전엔
#     같은 내용을 하루 두 번 압축하고 있었다(본월드 1.4GB × 2회).
#   ★업로드는 네트워크에 묶여 있어 정지 창에 넣지 않는다. 서버를 올린 뒤에 한다.
run_offsite_uploads(){
  local isl mn d
  if [ "$DRYRUN" = "1" ]; then log "DRY: would run offsite uploads"; return 0; fi
  # ① playerdata(BlockShip 폴더) — 매일. tar 는 정지 중에 떠 뒀다.
  if [ -n "$OFFSITE_BS_TAR" ]; then
    "$DIR/offsite-backup.sh" --upload-only "$OFFSITE_BS_TAR" >>"$OFFLOG" 2>&1 \
      || log "playerdata 오프사이트 업로드 실패"
  else
    log "playerdata 오프사이트 건너뜀 (정지 중 tar 없음)"
  fi
  # ② 섬 — 매일
  isl=$(fresh_tar localislands)
  if [ -n "$isl" ]; then
    "$DIR/offsite-worlds.sh" islands --upload-only "$isl" >>"$OFFLOG" 2>&1 \
      || log "섬 오프사이트 업로드 실패"
  else log "섬 오프사이트 건너뜀 (오늘 tar 없음)"; fi
  # ③ 본월드 — KST 1·15일만(격주). 1.4GB 라 매일 올리지 않는다.
  d=$(TZ=Asia/Seoul date +%d)
  case "$d" in 01|15)
    mn=$(fresh_tar localmain)
    if [ -n "$mn" ]; then
      "$DIR/offsite-worlds.sh" main --upload-only "$mn" >>"$OFFLOG" 2>&1 \
        || log "본월드 오프사이트 업로드 실패"
    else log "본월드 오프사이트 건너뜀 (오늘 tar 없음)"; fi
  ;; esac
  # ④ 레거시 playerdata-*.tar.gz 정리(옛 21:00 cron 이관 — 신규 생성은 없다)
  find "$BAKDIR" -maxdepth 1 -name 'playerdata-*.tar.gz' -mtime +30 -delete 2>/dev/null
}
run_local_backups(){   # $1 = down(정지 중) | live(서버 켜진 채 폴백)
  local where="$1" g rc
  for g in $BACKUP_GROUPS; do
    if [ "$DRYRUN" = "1" ]; then log "DRY: would back up $g ($where)"; continue; fi
    timeout "$BACKUP_TIMEOUT" "$DIR/local-backup.sh" "$g" >>"$BAKDIR/local.log" 2>&1
    rc=$?
    if [ "$rc" = "0" ]; then log "로컬 백업 $g 완료 ($where)"
    else
      log "로컬 백업 $g 실패 (rc=$rc, $where)"
      # rc!=0 은 local-backup.sh 가 이미 개별 🔴 를 보냈다. 단 timeout(124)은
      # 스크립트가 알릴 새도 없이 죽으므로 여기서만 알린다.
      [ "$rc" = "124" ] && notify "$LABEL 🔴 로컬 백업 $g 이 ${BACKUP_TIMEOUT}초를 넘겨 중단됐습니다(서버 기동은 그대로 진행)."
    fi
  done
}

# ★KST 기준(2026-08-17). 이 스팜립트는 21:00 UTC 에 돌고 그건 KST 다음 날 06:00 이다.
#   date -u 를 쓰는 동안 리포트 헤더가 «UTC 날짜에 KST 라밨»을 붙이는 자기모순이었다
#   (「데일리 리포트 (2026-08-16 · 06:00 KST)」이라 찍힌 시간이 실제로는 08-17 06:00 KST).
today=$(TZ=Asia/Seoul date +%Y-%m-%d)

# --- 오늘 밤만 스킵 요청 있으면: 배포/재시작/방송 전부 건너뜀(1회성, 자동 소모) ---
if [ "$IMMEDIATE" = "0" ] && [ -f "$SKIP_MARK" ]; then
  rm -f "$SKIP_MARK"
  if [ "${PREVIEW:-0}" = "1" ]; then echo "(스킵 마커 있음 — 오늘밤 재시작 생략됨)"; exit 0; fi
  # 재시작만 건너뛴다. 05:50 선행 백업이 성공했으면 같은 tar를 다시 뜨지 않는다.
  if prebackup_ready; then
    log "skip-once 마커로 오늘 재시작 생략 — 05:50 라이브 월드 백업 사용"
  else
    log "skip-once 마커로 오늘 재시작 생략 — 선행 백업 없음, 라이브로 수행"
    run_local_backups live
  fi
  notify "$LABEL ⏭️ 오늘 06:00 정기 재시작 — 요청에 의해 1회 스킵됨(내일부터 정상 진행). 로컬 백업은 서버를 켠 채 수행했습니다."
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
    [ -f "$PLUGINS/$bn" ] && cp -f "$PLUGINS/$bn" "$JARBAK/${bn}.bak-$(TZ=Asia/Seoul date +%Y%m%d-%H%M%S)"
    mv -f "$j" "$PLUGINS/$bn"; log "배포 jar 적용: $bn"
  else log "DRY: would deploy jar $bn"; fi
done
if [ -d "$STAGING/BlockShip" ] && [ -n "$(ls -A "$STAGING/BlockShip" 2>/dev/null)" ]; then
  # ★2026-08-01 사고 후 게이트: 예전엔 cp -rf 로 통째 복사했다가, NPC 1명짜리 부분
  #   npc.json이 138명짜리 라이브를 덮어 NPC/대화/퀘스트가 통째로 죽었다.
  #   validate-staged.py 가 파싱·항목수감소·스키마파손을 검사해 거부한다.
  #   거부된 파일은 staging-rejected/ 로 격리(다음날 조용히 재적용되지 않게) + 리포트에 표기.
  ok=0; rej=0; rejlist=""
  REJDIR="$STAGING-rejected/$(TZ=Asia/Seoul date +%Y%m%d-%H%M%S)"
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
# --- ①-3 Geyser 베드락 팩·매핑 스테이징 (재시작 «직전» 적용) ---
# ★라이브 폴더에 직접 넣으면 안 된다. Geyser 는 부팅 때 읽은 uuid·버전·해시·크기를
#   클라에 알려주고 바이트는 그때그때 디스크에서 흘려보낸다 → 가동 중에 파일을 갈면
#   알린 해시와 보낸 바이트가 어긋나 «커스텀 아이템이 전부 투명» 해진다(2026-09-04 실측).
#   그래서 반드시 여기서, 서버를 내리기 직전에 갈아 끼운다.
GEYDIR="$PLUGINS/Geyser-Spigot"
if [ -d "$STAGING/geyser" ] && [ -n "$(ls -A "$STAGING/geyser" 2>/dev/null)" ]; then
  gok=0; gbad=""
  for src in "$STAGING/geyser"/*.mcpack "$STAGING/geyser"/*.json; do
    [ -e "$src" ] || continue
    bn=$(basename "$src")
    case "$bn" in
      *.mcpack) dst="$GEYDIR/packs/$bn"
                unzip -p "$src" manifest.json 2>/dev/null | python3 -c 'import json,sys; json.load(sys.stdin)["header"]["uuid"]' >/dev/null 2>&1 \
                  || { gbad+="   ⛔ $bn — manifest.json 을 읽을 수 없음"$'\n'; continue; } ;;
      *.json)   dst="$GEYDIR/custom_mappings/$bn"
                python3 -c 'import json,sys; json.load(open(sys.argv[1]))' "$src" >/dev/null 2>&1 \
                  || { gbad+="   ⛔ $bn — JSON 파싱 실패"$'\n'; continue; } ;;
    esac
    if [ "$DRYRUN" = "0" ]; then
      mkdir -p "$(dirname "$dst")"
      [ -f "$dst" ] && cp -f "$dst" "$dst.bak-$(TZ=Asia/Seoul date +%Y%m%d-%H%M%S)"
      mv -f "$src" "$dst"; log "Geyser 적용: $bn"
    else log "DRY: would apply geyser $bn"; fi
    gok=$((gok+1))
  done
  [ "$gok" -gt 0 ] && deploy_lines+="🚀 Geyser 베드락 팩·매핑 ${gok}개 적용"$'\n'
  if [ -n "$gbad" ]; then
    deploy_lines+="🔴 Geyser 스테이징 거부(적용 안 함)"$'\n'"$gbad"
    notify "$LABEL 🔴 Geyser 스테이징 거부 — 깨진 팩이 올라갈 뻔했습니다.
$gbad"
  fi
fi
# --- ①-2 BetterHud 정의·자산 스테이징 (재시작 «전» 적용) ---
# jar/설정과 달리 BetterHud 자산은 재시작 후에 팩 재생성·공개배치·sha1 갱신이 더 필요하다.
# 그 후반부는 아래 재시작 뒤 --post 가 맡는다(2차 재시작까지 그 안에서).
BHSTAGE="$DIR/apply-betterhud-staging.sh"
if [ -x "$BHSTAGE" ]; then
  if bhline=$(DRY=$DRYRUN "$BHSTAGE" --pre 2>&1); then
    [ -n "$bhline" ] && deploy_lines+="$bhline"$'\n'
  else
    bhrc=$?
    # 3 = 스테이징 없음(정상). 그 외는 이미 스크립트가 Discord 로 알렸다.
    [ "$bhrc" = "3" ] || deploy_lines+="🔴 BetterHud 스테이징 실패(rc=$bhrc): $bhline"$'\n'
  fi
fi

[ -z "$deploy_lines" ] && deploy_summary="배포 없음" || deploy_summary=$(printf '%s' "$deploy_lines")

# ★즉시 모드는 "적용할 게 있어서" 불린 것이다. 비어 있으면 재시작할 이유가 없다 —
#   정기 재시작(누수정리)과 달리 여기서 서버를 내리면 순수 손해다.
if [ "$IMMEDIATE" = "1" ] && [ -z "$deploy_lines" ]; then
  log "즉시 모드인데 staging 이 비어 있다 — 재시작하지 않고 끝낸다"
  exit 0
fi

# --- 리소스팩 공개 파일과 server.properties SHA1 교차검증 ---
# `latest` asset을 교체하면 URL은 같고 파일만 바뀐다. 이 검증 없이 재시작하면
# require-resource-pack=true 환경에서 모든 접속자가 리소스팩 다운로드에 실패한다.
if [ "$DRYRUN" = "0" ] && ! "$DIR/resourcepack-guard.sh" --repair; then
  log "resource pack guard failed — restart cancelled"
  prebackup_ready || run_local_backups live
  notify "$LABEL 🔴 리소스팩 공개파일 검증 실패로 정기 재시작을 취소했습니다. 서버는 기존 상태를 유지하고, 로컬 백업은 켠 채 수행했습니다."
  exit 1
fi

# 05:50 백업이 예외적으로 아직 tar 중이면 먼저 끝낼 때까지 기다린다. 그래야
# 종료 과정이 라이브 tar와 겹치지 않고, 실패 시에도 아래 정지 중 폴백이 안전하다.
if [ "$IMMEDIATE" = "0" ] && [ "$DRYRUN" = "0" ]; then wait_for_prebackup; fi

# --- ② 재시작 예고 ---
#   정기: restart-warning.sh 가 30/10/5/1분 전 방송을 이미 했다 → 직전 1회만.
#   즉시: 예고가 아예 없었다 → GRACE 초를 주고 그 끝에 한 번 더.
if [ "$n" -gt 0 ] && [ "$DRYRUN" = "0" ]; then
  if [ "$IMMEDIATE" = "1" ]; then
    rcon "say [서버] 업데이트 적용으로 ${GRACE}초 후 재시작합니다. 곧 다시 들어올 수 있어요."
    sleep "$GRACE"
    rcon "say [서버] 지금 재시작합니다."
  else
    rcon "say [서버] 서버 재부팅합니다 (정기 점검). 약 3분 뒤 다시 접속해 주세요."
  fi
fi

# --- 저장 플러시 (서버 응답할 때) ---
[ "$n" -ge 0 ] && [ "$DRYRUN" = "0" ] && { rcon "save-all flush"; sleep 3; }

# --- 백업 성공 목록 ---
#   ★호출 시점이 중요하다. 로컬 백업이 재시작 창 안으로 들어갔으므로 STATUS_FILE 은
#     «기동 후»에 읽어야 오늘치가 들어온다. 미리 읽으면 매일 어제 것만 보고된다.
read_backups(){
  if [ -s "$STATUS_FILE" ]; then bcount=$(grep -c . "$STATUS_FILE"); backups=$(cat "$STATUS_FILE")
  else bcount=0; backups="⚠️ 성공 기록 없음 (전부 실패했거나 안 돎 — 실패 시 개별 🔴 확인)"; fi
}

# --- 지역 정합성 감사 (2026-08-27 신설) ---
#  지역 ID·참조가 어긋나면 로그도 경고도 없이 게임만 안 돈다 — BGM 무음, 잡을 수 없는 어종,
#  «이미 존재» 로 막히는 지역 생성. 라이브 데이터(권위)를 매일 한 번 훑어 리포트에 싣는다.
if ra=$("$DIR/region-audit.py" --data "$HOME/mcserver/plugins/BlockShip" 2>&1); then
  region_line="🗺️ 지역 감사 정상"
else
  region_line="🗺️ 지역 감사 🔴 $(printf '%s' "$ra" | grep -c 'ERROR ')건 — scripts/region-audit.py 로 확인"
fi
rw=$(printf '%s' "$ra" | grep 'WARN  ' | sed 's/^ *WARN  /   ⚠️ /')
[ -n "$rw" ] && region_line="$region_line
$rw"

# --- 헬스 스냅샷 ---
disk=$(df / | awk 'NR==2{print $5}')
np=$([ "$n" -ge 0 ] && echo "${n}명$([ "$n" -gt 0 ] && echo ' (예고 후 재시작)')" || echo "무응답")
started=$(date -d "$(systemctl show mcserver -p ActiveEnterTimestamp --value 2>/dev/null)" +%s 2>/dev/null || echo 0)
[ "$started" -gt 0 ] && upl="$(( ( $(date +%s) - started ) / 3600 ))h" || upl="?"

build_msg(){
if [ "$IMMEDIATE" = "1" ]; then
  msg="$LABEL 🚀 즉시 배포 ($(date -u -d '+9 hours' '+%Y-%m-%d %H:%M') KST)

$deploy_summary

💾 디스크 $disk · 🕐 MC업타임 $upl · 👥 접속 $np
※ Release 에 APPLY_NOW 마커가 있어 06:00 을 기다리지 않고 적용했습니다."
else
  msg="$LABEL 🌅 데일리 리포트 ($today · 06:00 KST)

🔄 정기 재시작 실행${bsec:+ · 정지 중 로컬 백업 ${bsec}초}${backup_note}
$deploy_summary

📦 백업 ${bcount}건 성공
$backups

💾 디스크 $disk · 🕐 MC업타임 $upl · 👥 접속 $np
$region_line${boot_line:+
$boot_line}"
fi
}

# --- PREVIEW: 출력만 ---
if [ "${PREVIEW:-0}" = "1" ]; then read_backups; build_msg; printf '%s\n' "$msg"; exit 0; fi

# 즉시 모드는 예전처럼 먼저 알리고 재시작한다(백업이 끼지 않아 기다릴 이유가 없다).
# ★즉시 배포는 .backup-status 를 비우지 않는다. 비우면 그날 06:00 데일리 리포트가
#   "백업 성공 기록 없음" 으로 나가고, 그게 진짜 백업 실패와 구분되지 않는다.
# 정기 리포트는 백업이 끝나야 내용이 채워지므로 기동 후로 내려갔다(아래).
if [ "$IMMEDIATE" = "1" ]; then read_backups; build_msg; notify "$msg"; log "즉시 배포 알림 발송"; fi

# --- 종료 직전 안내 kick ---
#   ★bukkit.yml 의 shutdown-message 는 «서버가 시작할 때 읽은» 값이라, 파일을 지금 고쳐도
#     다음 종료가 아니라 그 다음 종료부터 반영된다. 정기 점검 문구를 거기에만 두면
#     고친 날 아침에는 여전히 옛 문구로 튕긴다 — 그래서 여기서 직접 kick 한다.
#   ★/kick 의 사유는 평문이다. § 색코드를 넣으면 색이 아니라 글자로 찍힌다.
#   접속자가 없으면 "No entity was found" 가 나지만 rcon() 이 삼킨다(무해).
KICK_MSG="${KICK_MSG:-[정기 점검] 매일 새벽 6시 재시작입니다. 약 3분 뒤 다시 접속해 주세요!}"
if [ "$DRYRUN" = "0" ]; then rcon "kick @a $KICK_MSG"; sleep 1; fi

# --- ③ 재시작 (무조건) ---
#   정기: 정지 → (05:50 마커 없을 때만) 로컬 백업 → 기동.
#   즉시 모드는 백업과 무관하므로 예전 그대로 restart 한 방.
if [ "${DRY:-0}" = "1" ]; then
  log "DRY: would restart"
  prebackup_ready || run_local_backups down
  exit 0
fi
if [ "$IMMEDIATE" = "1" ]; then
  eval "$RESTART_CMD"
  log "restarted"
else
  # ★백업이 실패하든 timeout 이든 스크립트가 죽든, 서버는 반드시 다시 올라와야 한다.
  #   유닛에 Restart=no 가 걸려 있어 systemd 가 대신 올려주지 않는다.
  #   ★bash 의 시그널 트랩은 «핸들러를 돌고 하던 일을 계속»한다 — 그래서 핸들러가
  #     직접 exit 하지 않으면 SIGTERM 을 맞고도 백업을 계속 돌린다(그것도 이미
  #     기동시킨 라이브 월드 위에서). 반드시 올린 뒤 빠져나온다.
  _started=0
  _ensure_start(){ [ "$_started" = "1" ] && return 0; _started=1
    eval "$START_CMD"; log "기동(트랩 — 백업 도중 중단)"; }
  trap '_ensure_start; exit 1' INT TERM
  trap '_ensure_start' EXIT
  eval "$STOP_CMD"; log "stopped — 백업 창 시작"
  _b0=$(date +%s)
  if prebackup_ready; then
    backup_note=" · 05:50 라이브 월드 백업 사용"
    log "05:50 라이브 월드 백업 확인 — 정지 중 main/islands tar 생략"
  else
    log "05:50 라이브 월드 백업 없음/실패 — 정지 중 폴백"
    run_local_backups down
  fi
  # playerdata(BlockShip 폴더)는 «종료 저장 직후»가 가장 정확하다. tar 4초, 업로드는 기동 후.
  if [ "$DRYRUN" = "0" ]; then
    OFFSITE_BS_TAR=$("$DIR/offsite-backup.sh" --tar-only 2>>"$OFFLOG")
    if [ -s "$OFFSITE_BS_TAR" ]; then log "playerdata tar 생성: $(basename "$OFFSITE_BS_TAR")"
    else OFFSITE_BS_TAR=""; log "playerdata tar 실패"; fi
  fi
  _bsec=$(( $(date +%s) - _b0 ))
  if [ -z "$backup_note" ]; then
    bsec=$_bsec
    log "백업 창 종료 (${bsec}초)"
  else
    log "playerdata 백업 창 종료 (${_bsec}초)"
  fi
  _started=1; trap - EXIT INT TERM
  eval "$START_CMD"
  log "started"
fi

# --- BetterHud 후반부: 팩 재생성 → 공개배치 → CE sha1 → 마무리 재시작 ---
# 대기 중인 게 없으면 즉시 exit 3 으로 빠진다(평상시 비용 0). 안에서 부팅을 기다리므로
# 여기서 미리 기다릴 필요가 없다.
if [ -x "$BHSTAGE" ]; then
  "$BHSTAGE" --post || { bhrc=$?
    [ "$bhrc" = "3" ] || log "BetterHud post 실패(rc=$bhrc) — Discord 알림 확인"; }
fi

# --- 정기: 부팅 확인 → 데일리 리포트 ---
#   리포트가 여기로 내려온 이유는 백업 결과를 담아야 하기 때문이고, 이왕 기다리는 김에
#   부팅까지 확인한다. (프리즈 워치독 cron 이 꺼져 있는 동안엔 이게 유일한 기동 실패
#   감지 경로다. 예전 주석의 "워치독이 8분 안에 잡는다"는 지금 성립하지 않는다.)
if [ "$IMMEDIATE" = "0" ]; then
  boot_line="🔴 부팅 확인 실패 — RCON 무응답 (\`tail -50 ~/mcserver/logs/latest.log\`)"
  for i in $(seq 1 36); do
    if systemctl is-active --quiet mcserver && "$DIR/rcon.py" list >/dev/null 2>&1; then
      boot_line="✅ 부팅 확인 (${i}회 체크)"; break
    fi
    sleep 5
  done
  run_offsite_uploads
  read_backups
  build_msg
  notify "$msg"
  > "$STATUS_FILE"
  log "리포트 발송 (배포:$([ "$deploy_summary" = "배포 없음" ] && echo 없음 || echo 있음), 백업 ${bcount}건, 접속 ${np}, ${boot_line})"
  exit 0
fi

# 즉시 배포는 아무도 안 보고 있을 시간에 돌 수 있다 — 부팅까지 확인하고 실패면 알린다.
# (정기 06:00 은 이 확인을 하지 않는다. 프리즈 워치독이 8분 안에 잡는 경로가 이미 있고,
#  여기서 3분을 더 잡으면 뒤따르는 cron 과 겹친다.)
if [ "$IMMEDIATE" = "1" ]; then
  for i in $(seq 1 40); do
    if systemctl is-active --quiet mcserver && "$DIR/rcon.py" list >/dev/null 2>&1; then
      log "부팅 확인 완료 (${i}회 체크)"
      notify "$LABEL ✅ 즉시 배포 후 서버 정상 (부팅 확인 ${i}회)."
      exit 0
    fi
    sleep 5
  done
  log "재시작했지만 부팅 확인 실패"
  notify "$LABEL 🔴 **즉시 배포 후 부팅 확인 실패** — RCON 무응답.
로그: \`tail -50 ~/mcserver/logs/latest.log\`
롤백: \`~/mcserver/scripts/rollback-jar.sh list\` → \`rollback-jar.sh yes\`"
  exit 1
fi
