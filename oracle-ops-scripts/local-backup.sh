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
LABEL="[바르칸 prod]"
TMUX_SESSION=mc

case "$GROUP" in
  main)    WORLDS="world world_nether world_the_end flatroom flatroom_nether flatroom_the_end mine"
           PREFIX=localmain;    KEEP=3; HUMAN="본월드(로컬)";;
  islands) WORLDS="guild_world island_world"
           PREFIX=localislands; KEEP=7; HUMAN="섬(로컬)";;
  *) echo "usage: $0 <main|islands>" >&2; exit 2;;
esac

TS=$(date -u +%Y%m%d)
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

echo "OK: $NAME ($(du -h "$LOCAL"|cut -f1)) local, keep $KEEP"
