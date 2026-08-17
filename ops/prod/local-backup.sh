#!/usr/bin/env bash
# =====================================================================
# 바르칸 prod 로컬(인스턴스 내부) 월드 백업  →  ~/mcserver/backups/
#   사용법: local-backup.sh <main|islands>
#     main    : world 계열 + flatroom + mine   (매일, 로컬 3개 보관)
#     islands : guild_world + island_world       (매일, 로컬 7개 보관)
#   오프사이트와 별개의 "빠른 되돌리기용" 로컬 사본. 파일명 접두어 local* 로
#   기존/오프사이트 백업과 glob 충돌 방지. 백업 전 save-all flush.
#   실패 시 Discord 알림(webhook 있으면).
# =====================================================================
set -uo pipefail

GROUP="${1:-}"
ROOT=~/mcserver
STAGE=~/mcserver/backups
WEBHOOK_FILE=~/mcserver/scripts/discord-webhook.url
STATUS_FILE=~/mcserver/backups/.backup-status   # 성공 기록 누적 → 23:00 요약이 한 번에 발송
LABEL="[바르칸 prod]"
TMUX_SESSION=mc

case "$GROUP" in
  main)    WORLDS="world world_nether world_the_end flatroom flatroom_nether flatroom_the_end mine"
           PREFIX=localmain;    KEEP=3; HUMAN="본월드(로컬)";;
  islands) WORLDS="guild_world island_world"
           PREFIX=localislands; KEEP=7; HUMAN="섬(로컬)";;
  *) echo "usage: $0 <main|islands>" >&2; exit 2;;
esac

# ★파일명은 KST 기준이다(2026-08-17 변경). 박스는 Etc/UTC 이고 이 백업은 20:00 UTC 에 도는데,
#   그건 KST 로 «다음 날 05:00» 이다. date -u 를 쓰던 동안에는 파일명이 실제 내용보다 하루
#   빨랐다 — 실측: localmain-20260815.tar.gz 의 생성 시각이 2026-08-15 20:01 UTC(=KST 08-16 05:01).
#   장애 때 「어제 백업」을 찾는 사람은 KST 로 생각하므로 하루를 헛짚게 된다.
#   보존 로직은 ls -1t(mtime 기준)라 파일명 변경에 영향받지 않는다. 기존 파일명은 그대로 둔다.
TS=$(TZ=Asia/Seoul date +%Y%m%d)
NAME=${PREFIX}-${TS}.tar.gz
LOCAL=$STAGE/$NAME

notify(){  # $1=이모지  $2=메시지
  [ -s "$WEBHOOK_FILE" ] || return 0
  local url msg payload
  url=$(cat "$WEBHOOK_FILE"); msg="$LABEL $1 $2"
  payload=$(python3 -c "import json,sys; print(json.dumps({'content':sys.argv[1]}))" "$msg")
  curl -sf -m 10 -H "Content-Type: application/json" -d "$payload" "$url" >/dev/null 2>&1 || true
}
fail(){ echo "FAIL: $1" >&2; notify "🔴" "$HUMAN 백업 실패: $1"; exit 1; }

mkdir -p "$STAGE"; cd "$ROOT"

# 존재하는 월드만
LIST=""; for w in $WORLDS; do [ -d "$ROOT/$w" ] && LIST="$LIST $w"; done
[ -n "$LIST" ] || fail "백업할 월드 폴더 없음 ($WORLDS)"

# 저장 플러시
if tmux has-session -t "$TMUX_SESSION" 2>/dev/null; then
  tmux send-keys -t "$TMUX_SESSION" "save-all flush" Enter 2>/dev/null || true
  sleep 6
fi

# tar (하루 1회 → 같은 날 재실행 시 덮어씀)
tar --warning=no-file-changed -czf "$LOCAL" -C "$ROOT" $LIST 2>/dev/null
rc=$?
# tar rc: 0=성공, 1=읽는 중 파일 변경(라이브 서버 정상, 아카이브 유효), 2+=치명
[ "$rc" -ge 2 ] && fail "tar 치명 오류 (rc=$rc)"
[ -s "$LOCAL" ] || fail "tar 결과가 비어있음"
gzip -t "$LOCAL" 2>/dev/null || fail "아카이브 무결성 실패 (gzip -t)"

# 보관 개수 초과분 삭제 (최신 KEEP개만)
ls -1t "$STAGE"/${PREFIX}-*.tar.gz 2>/dev/null | tail -n +$((KEEP+1)) | xargs -r rm -f

# 성공은 상태파일에 누적 (23:00 요약이 한 번에 발송). 실패만 즉시 개별 알림.
echo "🟢 ${HUMAN} ($(du -h "$LOCAL"|cut -f1))" >> "$STATUS_FILE"
echo "OK: $NAME ($(du -h "$LOCAL"|cut -f1)) local, keep $KEEP"
