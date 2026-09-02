#!/usr/bin/env bash
# 바르칸 prod 06:00 KST 정기 점검.
# 공지·저장·상태 보고만 수행하며, prod를 중지/재시작하거나 staging을 적용하지 않는다.
set -uo pipefail

DIR="${MC_ROOT:-$HOME/mcserver}/scripts"
MC="${MC_ROOT:-$HOME/mcserver}"
LOG_FILE="${LOG_FILE:-$MC/backups/ops.log}"
WEBHOOK_FILE="${WEBHOOK_FILE:-$DIR/discord-webhook.url}"
LABEL="[바르칸 prod]"

log() {
  local m="$(date -u +%Y-%m-%dT%H:%M:%SZ) [maintenance] $*"
  echo "$m"
  echo "$m" >> "$LOG_FILE" 2>/dev/null || true
}
notify() {
  [ -s "$WEBHOOK_FILE" ] || return 0
  local url payload
  url=$(cat "$WEBHOOK_FILE")
  payload=$(python3 -c 'import json,sys; print(json.dumps({"content": sys.argv[1]}))' "$1")
  curl -sf -m 10 -H 'Content-Type: application/json' -d "$payload" "$url" >/dev/null 2>&1 || true
}
rcon() { "$DIR/rcon.py" "$1" >/dev/null 2>&1; }

out=$("$DIR/rcon.py" list 2>/dev/null || true)
n=$(printf '%s' "$out" | grep -oE 'are [0-9]+' | grep -oE '[0-9]+' | head -1 || true)
n=${n:-0}

if [ "$n" -gt 0 ] 2>/dev/null; then
  rcon "say [서버] 06:00 정기 점검을 시작합니다. 재시작 없이 저장과 상태만 확인합니다."
fi
rcon "save-all flush"

active=$(systemctl is-active mcserver 2>/dev/null || echo unknown)
started=$(systemctl show mcserver -p ExecMainStartTimestamp --value 2>/dev/null || echo unknown)
disk=$(df -P "$MC" | awk 'NR==2 {print $5}')
jar_count=$(find "$MC/staging" -maxdepth 1 -type f -name '*.jar' 2>/dev/null | wc -l | tr -d ' ')
json_count=$(find "$MC/staging/BlockShip" -maxdepth 1 -type f -name '*.json' 2>/dev/null | wc -l | tr -d ' ')
bh_count=$(find "$MC/staging/betterhud" -type f 2>/dev/null | wc -l | tr -d ' ')

log "재시작 없음 · 상태=$active · 접속=${n}명 · 디스크=$disk · staging jar=${jar_count}, json=${json_count}, betterhud=${bh_count} · 시작=$started"
msg="$LABEL 🌅 06:00 재시작 없는 정기 점검 완료
서버 상태: $active · 접속: ${n}명 · 디스크: $disk
staging 대기: JAR ${jar_count}개 · JSON ${json_count}개 · BetterHud ${bh_count}개
재시작·staging 적용 없음"
notify "$msg"
if [ "$n" -gt 0 ] 2>/dev/null; then
  rcon "say [서버] 06:00 정기 점검이 끝났습니다. 재시작 없이 정상 운영 중입니다."
fi
