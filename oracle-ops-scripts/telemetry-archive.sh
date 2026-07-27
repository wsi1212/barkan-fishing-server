#!/usr/bin/env bash
# =====================================================================
# 바르칸 prod 텔레메트리 월간 아카이브 (stats-system-plan.md §11)
#   대상 : ~/mcserver/plugins/BlockShip/telemetry/events-YYYY-MM.db (전월분)
#   방법 : sqlite3 backup API로 WAL-안전 사본 → gzip → Object Storage 버킷 mc-backups
#           telemetry/ 프리픽스 (offsite-backup.sh의 blockship/ tar와 별개 아카이브)
#   보존 : 로컬 3개월 / 버킷 12개월(이후 수동 정리) — 로컬은 "3개월 지난 것만" 삭제(당월/최근분 보호)
#   cron : 30 18 2 * * (매월 2일 03:30 KST, 기존 백업 시간대와 무충돌)
# =====================================================================
set -uo pipefail

OCI=~/oci-cli-venv/bin/oci
NS=ax4ljwis9hth
BUCKET=mc-backups
TELE_DIR=~/mcserver/plugins/BlockShip/telemetry
WEBHOOK_FILE=~/mcserver/scripts/discord-webhook.url
STATUS_FILE=~/mcserver/backups/.backup-status
LABEL="[바르칸 prod]"
KEEP_LOCAL_MONTHS=3   # 로컬 원본 보존 개월수 — 이보다 오래된 events-*.db만 삭제

notify(){  # $1=이모지 $2=메시지
  [ -s "$WEBHOOK_FILE" ] || return 0
  local url msg payload
  url=$(cat "$WEBHOOK_FILE")
  msg="$LABEL $1 $2"
  payload=$(python3 -c "import json,sys; print(json.dumps({'content':sys.argv[1]}))" "$msg")
  curl -sf -m 10 -H "Content-Type: application/json" -d "$payload" "$url" >/dev/null 2>&1 || true
}
fail(){ echo "FAIL: $1" >&2; notify "🔴" "텔레메트리 아카이브 실패: $1"; exit 1; }

# 전월 YYYY-MM (오늘이 매월 2일에 도는 걸 전제 — 그래도 날짜 자체로 안전하게 계산)
PREV_MONTH=$(date -u -d "$(date -u +%Y-%m-01) -1 day" +%Y-%m 2>/dev/null \
             || date -u -v-1m +%Y-%m 2>/dev/null)
[ -z "$PREV_MONTH" ] && fail "전월 계산 실패"

SRC="$TELE_DIR/events-$PREV_MONTH.db"
if [ ! -f "$SRC" ]; then
  echo "스킵: $SRC 없음 (이미 아카이브했거나 그 달에 텔레메트리가 없었음)"
  exit 0
fi

TMP="/tmp/events-$PREV_MONTH-archive.db"
GZ="$TMP.gz"
rm -f "$TMP" "$GZ"

# 1) WAL-안전 사본 (라이브 파일 직접 압축 금지)
python3 -c "
import sqlite3
s = sqlite3.connect('$SRC')
d = sqlite3.connect('$TMP')
s.backup(d)
d.close(); s.close()
" || fail "sqlite3 backup API 실패"
[ -s "$TMP" ] || fail "backup 결과가 비어있음"

# 2) gzip
gzip -f "$TMP" || fail "gzip 실패"
[ -s "$GZ" ] || fail "gzip 결과가 비어있음"
gzip -t "$GZ" || fail "gzip 무결성 검증 실패"
SIZE=$(du -h "$GZ" | cut -f1)

# 3) 업로드
REMOTE="telemetry/events-$PREV_MONTH.db.gz"
$OCI os object put --namespace "$NS" --bucket-name "$BUCKET" \
  --name "$REMOTE" --file "$GZ" --force --auth instance_principal \
  >/dev/null 2>&1 || fail "오브젝트 스토리지 업로드 실패"

# 4) 업로드 검증
$OCI os object head --namespace "$NS" --bucket-name "$BUCKET" \
  --name "$REMOTE" --auth instance_principal >/dev/null 2>&1 \
  || fail "업로드 검증 실패 (원격에 객체 없음)"

rm -f "$GZ"

# 5) 로컬 원본 정리 — KEEP_LOCAL_MONTHS개월보다 오래된 events-*.db만 삭제(당월/최근분 보호)
CUTOFF=$(date -u -d "-$KEEP_LOCAL_MONTHS month" +%Y-%m 2>/dev/null || date -u -v-${KEEP_LOCAL_MONTHS}m +%Y-%m 2>/dev/null)
removed=0
for f in "$TELE_DIR"/events-*.db; do
  [ -e "$f" ] || continue
  ym=$(basename "$f" .db | sed 's/^events-//')
  if [[ "$ym" < "$CUTOFF" ]]; then
    rm -f "$f"
    removed=$((removed+1))
    echo "로컬 정리: $f (아카이브 완료, ${KEEP_LOCAL_MONTHS}개월 초과)"
  fi
done

echo "🟢 텔레메트리 아카이브 events-$PREV_MONTH.db.gz ($SIZE, 로컬 ${removed}개 정리)" >> "$STATUS_FILE"
echo "OK: events-$PREV_MONTH.db.gz ($SIZE) uploaded to $BUCKET/$REMOTE, 로컬 ${removed}개 정리"
