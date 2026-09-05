#!/usr/bin/env bash
# =====================================================================
# 바르칸 prod 오프사이트 백업
#   대상 : ~/mcserver/plugins/BlockShip (playerdata + 라이브 권위 JSON 전체)
#   대상지: Oracle Object Storage 버킷 mc-backups  (인스턴스와 분리된 고장영역)
#   인증 : instance principal (박스에 키 없음)
#   알림 : Discord webhook (성공/실패) — webhook 파일 없으면 조용히 skip
#   모드(2026-09-05 신설) — 06:00 유지보수 창 안에서 tar 와 업로드를 쪼개 쓴다:
#     --tar-only            tar 만 만들고 경로를 stdout 에 찍고 끝(정지 중에 부른다 — playerdata 는 종료 저장 직후가 가장 정확하다)
#     --upload-only <tar>   이미 있는 tar 를 업로드(기동 후에 부른다)
#   인자 없이 부르면 예전처럼 tar+업로드를 한 번에 한다.
# =====================================================================
set -uo pipefail

MODE=full; SRC_TAR=""
while [ $# -gt 0 ]; do
  case "$1" in
    --tar-only)    MODE=tar ;;
    --upload-only) MODE=upload; SRC_TAR="${2:-}"; shift ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
  shift
done

OCI=~/oci-cli-venv/bin/oci
NS=ax4ljwis9hth
BUCKET=mc-backups
SRC=~/mcserver/plugins/BlockShip
STAGE=~/mcserver/backups/offsite-stage
WEBHOOK_FILE=~/mcserver/scripts/discord-webhook.url
STATUS_FILE=~/mcserver/backups/.backup-status   # 성공 기록 누적 → 23:00 요약이 한 번에 발송
LABEL="[바르칸 prod]"
KEEP_REMOTE=30     # 원격 보관 개수 (일 1회면 30일)
KEEP_LOCAL=7       # 로컬 staging 보관 개수

# ★KST 기준 파일명(2026-08-17). 19:00 UTC = KST 다음 날 04:00 이라 date -u 로는 하루 빨랐다.
#   운영자·CLAUDE.md·디스코드 리포트가 전부 KST 로 말하므로 이름도 KST 로 맞춘다.
#   원격 보존은 개수 기반이고 이름이 여전히 단조증가하므로 영향 없다.
TS=$(TZ=Asia/Seoul date +%Y%m%d-%H%M%S)
NAME=blockship-$TS.tar.gz
LOCAL=$STAGE/$NAME
REMOTE=blockship/$NAME

notify(){  # $1=이모지  $2=메시지
  [ -s "$WEBHOOK_FILE" ] || return 0
  local url msg payload
  url=$(cat "$WEBHOOK_FILE")
  msg="$LABEL $1 $2"
  payload=$(python3 -c "import json,sys; print(json.dumps({'content':sys.argv[1]}))" "$msg")
  curl -sf -m 10 -H "Content-Type: application/json" -d "$payload" "$url" >/dev/null 2>&1 || true
}

fail(){ echo "FAIL: $1" >&2; notify "🔴" "백업 실패: $1"; exit 1; }

mkdir -p "$STAGE"

if [ "$MODE" = "upload" ]; then
  [ -n "$SRC_TAR" ] || fail "--upload-only 에 tar 경로가 없음"
  [ -s "$SRC_TAR" ] || fail "업로드할 tar 가 없음: $SRC_TAR"
  gzip -t "$SRC_TAR" 2>/dev/null || fail "아카이브 무결성 실패 (gzip -t): $SRC_TAR"
  LOCAL="$SRC_TAR"; NAME=$(basename "$LOCAL"); REMOTE=blockship/$NAME
  SIZE=$(du -h "$LOCAL" | cut -f1)
else
  # 1) tar 생성
  tar --warning=no-file-changed -czf "$LOCAL" -C "$(dirname "$SRC")" "$(basename "$SRC")" 2>/dev/null
  rc=$?
  # tar rc: 0=성공, 1=읽는 중 파일 변경(라이브 서버 정상, 아카이브 유효), 2+=치명
  [ "$rc" -ge 2 ] && fail "tar 치명 오류 (rc=$rc)"
  [ -s "$LOCAL" ] || fail "tar 결과가 비어있음"
  gzip -t "$LOCAL" 2>/dev/null || fail "아카이브 무결성 실패 (gzip -t)"
  SIZE=$(du -h "$LOCAL" | cut -f1)

  if [ "$MODE" = "tar" ]; then echo "$LOCAL"; exit 0; fi
fi

# 2) Object Storage 업로드
$OCI os object put --namespace "$NS" --bucket-name "$BUCKET" \
  --name "$REMOTE" --file "$LOCAL" --force --auth instance_principal \
  >/dev/null 2>&1 || fail "오브젝트 스토리지 업로드 실패"

# 3) 업로드 검증 (원격에 실제로 존재하는지 HEAD)
$OCI os object head --namespace "$NS" --bucket-name "$BUCKET" \
  --name "$REMOTE" --auth instance_principal >/dev/null 2>&1 \
  || fail "업로드 검증 실패 (원격에 객체 없음)"

# 4) 원격 오래된 것 정리 (최신 KEEP_REMOTE개만 유지)
OLD=$($OCI os object list --namespace "$NS" --bucket-name "$BUCKET" \
  --prefix "blockship/" --auth instance_principal --all 2>/dev/null \
  | python3 -c "import sys,json
d=json.load(sys.stdin).get('data',[])
names=sorted(o['name'] for o in d)
[print(n) for n in names[:-$KEEP_REMOTE]]" 2>/dev/null)
for o in $OLD; do
  $OCI os object delete --namespace "$NS" --bucket-name "$BUCKET" \
    --name "$o" --force --auth instance_principal >/dev/null 2>&1
done

# 5) 로컬 staging 정리 (최신 KEEP_LOCAL개만)
ls -1t "$STAGE"/blockship-*.tar.gz 2>/dev/null | tail -n +$((KEEP_LOCAL+1)) | xargs -r rm -f

# 성공은 즉시 알림 안 하고 상태파일에 누적 (23:00 요약이 한 번에 발송). 실패만 즉시 개별 알림.
echo "🟢 playerdata 오프사이트 ($SIZE)" >> "$STATUS_FILE"
echo "OK: $NAME ($SIZE) uploaded to $BUCKET/$REMOTE"
