#!/usr/bin/env bash
# =====================================================================
# 바르칸 prod 오프사이트 백업
#   대상 : ~/mcserver/plugins/BlockShip (playerdata + 라이브 권위 JSON 전체)
#   대상지: Oracle Object Storage 버킷 mc-backups  (인스턴스와 분리된 고장영역)
#   인증 : instance principal (박스에 키 없음)
#   알림 : Discord webhook (성공/실패) — webhook 파일 없으면 조용히 skip
# 재시작 없이 안전하게 매일 실행. cron에서 호출.
# =====================================================================
set -uo pipefail

OCI=~/oci-cli-venv/bin/oci
NS=ax4ljwis9hth
BUCKET=mc-backups
SRC=~/mcserver/plugins/BlockShip
STAGE=~/mcserver/backups/offsite-stage
WEBHOOK_FILE=~/mcserver/scripts/discord-webhook.url
LABEL="[바르칸 prod]"
KEEP_REMOTE=30     # 원격 보관 개수 (일 1회면 30일)
KEEP_LOCAL=7       # 로컬 staging 보관 개수

TS=$(date -u +%Y%m%d-%H%M%S)
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

# 1) tar 생성
tar --warning=no-file-changed -czf "$LOCAL" -C "$(dirname "$SRC")" "$(basename "$SRC")" 2>/dev/null
rc=$?
# tar rc: 0=성공, 1=읽는 중 파일 변경(라이브 서버 정상, 아카이브 유효), 2+=치명
[ "$rc" -ge 2 ] && fail "tar 치명 오류 (rc=$rc)"
[ -s "$LOCAL" ] || fail "tar 결과가 비어있음"
gzip -t "$LOCAL" 2>/dev/null || fail "아카이브 무결성 실패 (gzip -t)"
SIZE=$(du -h "$LOCAL" | cut -f1)

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

notify "🟢" "백업 완료: $NAME ($SIZE) → Object Storage (원격 ${KEEP_REMOTE}개 보관)"
echo "OK: $NAME ($SIZE) uploaded to $BUCKET/$REMOTE"
