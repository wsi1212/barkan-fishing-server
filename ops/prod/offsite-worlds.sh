#!/usr/bin/env bash
# =====================================================================
# 바르칸 prod 월드 오프사이트 백업  →  Oracle Object Storage (mc-backups)
#   사용법: offsite-worlds.sh <islands|main>
#     islands : guild_world + island_world      (매일, 원격 5개 보관)
#     main    : world 계열 + flatroom + mine     (격주, 원격 2개 보관)
#   백업 전 tmux 세션 mc에 save-all flush 로 디스크 동기화 → 스냅샷 일관성 ↑
#   인증 instance principal (박스에 키 없음) / 실패·성공 Discord 알림
# =====================================================================
set -uo pipefail

GROUP="${1:-}"
OCI=~/oci-cli-venv/bin/oci
NS=ax4ljwis9hth
BUCKET=mc-backups
ROOT=~/mcserver
STAGE=~/mcserver/backups/offsite-stage
WEBHOOK_FILE=~/mcserver/scripts/discord-webhook.url
STATUS_FILE=~/mcserver/backups/.backup-status   # 성공 기록 누적 → 23:00 요약이 한 번에 발송
LABEL="[바르칸 prod]"
TMUX_SESSION=mc

case "$GROUP" in
  islands) WORLDS="guild_world island_world"
           PREFIX=islands; KEEP_REMOTE=5; KEEP_LOCAL=3; HUMAN="섬(개인·길드)";;
  main)    WORLDS="world world_nether world_the_end flatroom flatroom_nether flatroom_the_end mine"
           PREFIX=world; KEEP_REMOTE=2; KEEP_LOCAL=1; HUMAN="본월드(건축물)";;
  *) echo "usage: $0 <islands|main>" >&2; exit 2;;
esac

# ★KST 기준 파일명(2026-08-17) — offsite-backup.sh 와 같은 이유.
#   ★격주 본월드는 cron 이 «UTC 1·15일» 이라 KST 로는 1·15일 05:45 에 돈다. 이름을 KST 로
#     바꿔도 그 스케줄은 그대로다(cron 자체를 옮기지는 않았다).
TS=$(TZ=Asia/Seoul date +%Y%m%d-%H%M%S)
NAME=${PREFIX}-${TS}.tar.gz
LOCAL=$STAGE/$NAME
REMOTE=${PREFIX}/${NAME}

notify(){  # $1=이모지  $2=메시지
  [ -s "$WEBHOOK_FILE" ] || return 0
  local url msg payload
  url=$(cat "$WEBHOOK_FILE"); msg="$LABEL $1 $2"
  payload=$(python3 -c "import json,sys; print(json.dumps({'content':sys.argv[1]}))" "$msg")
  curl -sf -m 10 -H "Content-Type: application/json" -d "$payload" "$url" >/dev/null 2>&1 || true
}
fail(){ echo "FAIL: $1" >&2; notify "🔴" "$HUMAN 백업 실패: $1"; exit 1; }

mkdir -p "$STAGE"
cd "$ROOT"

# 존재하는 월드만 추림
LIST=""
for w in $WORLDS; do [ -d "$ROOT/$w" ] && LIST="$LIST $w"; done
[ -n "$LIST" ] || fail "백업할 월드 폴더가 하나도 없음 ($WORLDS)"

# 1) 서버에 저장 플러시 (tmux 세션 있으면)
if tmux has-session -t "$TMUX_SESSION" 2>/dev/null; then
  tmux send-keys -t "$TMUX_SESSION" "save-all flush" Enter 2>/dev/null || true
  sleep 6
fi

# 2) tar
tar --warning=no-file-changed -czf "$LOCAL" -C "$ROOT" $LIST 2>/dev/null
rc=$?
# tar rc: 0=성공, 1=읽는 중 파일 변경(라이브 서버 정상, 아카이브 유효), 2+=치명
[ "$rc" -ge 2 ] && fail "tar 치명 오류 (rc=$rc)"
[ -s "$LOCAL" ] || fail "tar 결과가 비어있음"
gzip -t "$LOCAL" 2>/dev/null || fail "아카이브 무결성 실패 (gzip -t)"
SIZE=$(du -h "$LOCAL" | cut -f1)

# 3) 업로드
$OCI os object put --namespace "$NS" --bucket-name "$BUCKET" \
  --name "$REMOTE" --file "$LOCAL" --force --auth instance_principal \
  >/dev/null 2>&1 || fail "오브젝트 스토리지 업로드 실패"

# 4) 업로드 검증
$OCI os object head --namespace "$NS" --bucket-name "$BUCKET" \
  --name "$REMOTE" --auth instance_principal >/dev/null 2>&1 \
  || fail "업로드 검증 실패 (원격에 객체 없음)"

# 5) 원격 정리 (최신 KEEP_REMOTE개만)
OLD=$($OCI os object list --namespace "$NS" --bucket-name "$BUCKET" \
  --prefix "${PREFIX}/" --auth instance_principal --all 2>/dev/null \
  | python3 -c "import sys,json
d=json.load(sys.stdin).get('data',[])
names=sorted(o['name'] for o in d)
[print(n) for n in names[:-$KEEP_REMOTE]]" 2>/dev/null)
for o in $OLD; do
  $OCI os object delete --namespace "$NS" --bucket-name "$BUCKET" \
    --name "$o" --force --auth instance_principal >/dev/null 2>&1
done

# 6) 로컬 staging 정리
ls -1t "$STAGE"/${PREFIX}-*.tar.gz 2>/dev/null | tail -n +$((KEEP_LOCAL+1)) | xargs -r rm -f

# 성공은 즉시 알림 안 하고 상태파일에 누적 (23:00 요약이 한 번에 발송). 실패만 즉시 개별 알림.
echo "🟢 ${HUMAN} 오프사이트 ($SIZE)" >> "$STATUS_FILE"
echo "OK: $NAME ($SIZE) -> $BUCKET/$REMOTE"
