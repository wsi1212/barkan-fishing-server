#!/bin/bash
# stats-lab/pull.sh — prod(오라클)에서 텔레메트리 DB 안전 사본을 Mac으로 가져온다
# (stats-system-plan.md §10-2). WAL 라이브 파일 직접 scp는 금지 — 항상 sqlite3 backup API로
# 일관 사본을 뜬 뒤 옮긴다. stats.db는 서버가 매일 VACUUM INTO로 export/stats-latest.db를
# 만들어두므로 그걸 그대로 scp하면 된다(§9-2 ExportJob).
set -euo pipefail

SSH_KEY="$HOME/.ssh/oracle-mc.key"
HOST="ubuntu@168.107.8.107"
REMOTE_TELE="/home/ubuntu/mcserver/plugins/BlockShip/telemetry"
LOCAL_DATA="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/data"

# 받을 월 지정 가능: ./pull.sh 2026-07 2026-08  (생략 시 이번 달 + 지난 달)
if [ "$#" -gt 0 ]; then
  MONTHS=("$@")
else
  MONTHS=("$(date +%Y-%m)" "$(date -v-1m +%Y-%m 2>/dev/null || date -d 'last month' +%Y-%m)")
fi

mkdir -p "$LOCAL_DATA"

echo "[1/2] stats.db (export/stats-latest.db) 받는 중..."
scp -i "$SSH_KEY" "$HOST:$REMOTE_TELE/export/stats-latest.db" "$LOCAL_DATA/stats-latest.db"

echo "[2/2] 월별 events DB 받는 중: ${MONTHS[*]}"
for m in "${MONTHS[@]}"; do
  REMOTE_FILE="$REMOTE_TELE/events-$m.db"
  TMP_REMOTE="/tmp/ev-$m.db"
  ssh -i "$SSH_KEY" "$HOST" \
    "python3 -c \"import sqlite3,os; \
src='$REMOTE_FILE'; \
print('스킵(파일없음):', src) if not os.path.exists(src) else (lambda: (s:=sqlite3.connect(src), d:=sqlite3.connect('$TMP_REMOTE'), s.backup(d), d.close(), s.close()))()\""
  if ssh -i "$SSH_KEY" "$HOST" "test -f $TMP_REMOTE"; then
    scp -i "$SSH_KEY" "$HOST:$TMP_REMOTE" "$LOCAL_DATA/events-$m.db"
    ssh -i "$SSH_KEY" "$HOST" "rm -f $TMP_REMOTE"
    echo "  받음: events-$m.db"
  fi
done

echo "완료 — data/ 안 파일: $(ls "$LOCAL_DATA" | tr '\n' ' ')"
echo "사용: python3 queries.py c1   /   python3 report.py"
