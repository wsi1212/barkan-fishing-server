#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# BlockShip jar 롤백 — 폰에서 한 줄로
#
#   ~/mcserver/scripts/rollback-jar.sh --list        후보 보기 (안전, 아무것도 안 바꿈)
#   ~/mcserver/scripts/rollback-jar.sh --dry-run     무엇을 할지만 보기
#   ~/mcserver/scripts/rollback-jar.sh --yes         직전 백업으로 되돌리고 재시작
#   ~/mcserver/scripts/rollback-jar.sh --yes --to <파일명>   특정 백업으로
#
# 왜 스크립트인가: 손으로 하면 5단계고, 그중 staging 비우기를 빼먹으면
# **다음날 06:00 데일리 유지보수가 깨진 jar 를 다시 적용한다.** 스트레스 상황에서
# 폰 키보드로 순서를 정확히 지키는 건 설계 결함이라 한 줄로 묶었다.
#
# ★ 진짜 실행은 --yes 를 요구한다. 오타로 라이브가 재시작되지 않게.
# ─────────────────────────────────────────────────────────────────────────────
set -uo pipefail

MC_ROOT="${MC_ROOT:-$HOME/mcserver}"
PLUGINS="$MC_ROOT/plugins"
BACKUPS="$MC_ROOT/backups/deployed-jars"
STAGING="$MC_ROOT/staging"
LIVE="$PLUGINS/BlockShip-1.0.0-SNAPSHOT.jar"
BROKEN_DIR="$MC_ROOT/backups/broken-jars"
WEBHOOK_FILE="$MC_ROOT/scripts/discord-webhook.url"
LOG_FILE="$MC_ROOT/scripts/ops.log"

LIST=0; DRY=0; YES=0; TARGET=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --list)    LIST=1; shift ;;
    --dry-run) DRY=1; shift ;;
    --yes)     YES=1; shift ;;
    --to)      TARGET="${2:-}"; shift 2 ;;
    -h|--help) sed -n '2,17p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "알 수 없는 인자: $1" >&2; exit 2 ;;
  esac
done

log() {
  local m="[$(date '+%Y-%m-%d %H:%M:%S')] [rollback] $*"
  echo "$m"; echo "$m" >> "$LOG_FILE" 2>/dev/null || true
}
notify() {
  [[ -f "$WEBHOOK_FILE" ]] || return 0
  local url; url=$(<"$WEBHOOK_FILE"); [[ -n "$url" ]] || return 0
  curl -fsS --max-time 15 -H 'Content-Type: application/json' \
    -d "$(python3 -c 'import json,sys;print(json.dumps({"content":sys.argv[1]}))' "$1")" \
    "$url" >/dev/null 2>&1 || true
}
die() { log "✗ $*"; exit 1; }

# jar 이 온전한지 — 깨진 백업으로 되돌리면 상황이 더 나빠진다.
# ★`unzip -Z1 | grep -q` 로 파이프 연결 금지: grep -q 가 먼저 끝나 unzip 이 SIGPIPE(141)로
#   죽고 pipefail 이 성공을 실패로 뒤집는다(2026-08-14 fetch-staging 에서 실측). 담아서 본다.
valid_jar() {
  local jar="$1" names
  [[ -s "$jar" ]] || return 1
  unzip -t "$jar" >/dev/null 2>&1 || return 1
  names=$(unzip -Z1 "$jar" 2>/dev/null) || return 1
  grep -qE '^(plugin|paper-plugin)\.yml$' <<<"$names"
}

[[ -d "$BACKUPS" ]] || die "백업 디렉터리가 없다: $BACKUPS"

# 후보 = deployed-jars 안의 BlockShip 계열, 최신순
mapfile_compat() {  # macOS bash 3.2 에도 없고 여기는 Ubuntu 지만 이식성 위해 while read
  CANDIDATES=()
  while IFS= read -r f; do [[ -n "$f" ]] && CANDIDATES+=("$f"); done < <(
    ls -1t "$BACKUPS" 2>/dev/null | grep -E '^BlockShip.*\.jar' || true
  )
}
mapfile_compat

if [[ "$LIST" == 1 ]]; then
  echo "현재 라이브:"
  if [[ -f "$LIVE" ]]; then
    printf '  %s  %s  %s\n' "$(stat -c %y "$LIVE" | cut -d. -f1)" \
      "$(stat -c %s "$LIVE")" "$(basename "$LIVE")"
    echo "  sha256: $(sha256sum "$LIVE" | cut -c1-16)"
  else
    echo "  (없음!)"
  fi
  echo "되돌릴 수 있는 백업 (최신순):"
  if [[ ${#CANDIDATES[@]} -eq 0 ]]; then echo "  (없음)"; fi
  for f in "${CANDIDATES[@]}"; do
    ok=$(valid_jar "$BACKUPS/$f" && echo "정상" || echo "★손상")
    printf '  %s  %10s  %s  [%s]\n' \
      "$(stat -c %y "$BACKUPS/$f" | cut -d. -f1)" "$(stat -c %s "$BACKUPS/$f")" "$f" "$ok"
  done
  echo "staging 대기중 (롤백 시 함께 비운다 — 안 비우면 06:00 에 재적용):"
  ls -1 "$STAGING"/BlockShip-*.jar 2>/dev/null | sed 's|^|  |' || echo "  (없음)"
  exit 0
fi

# 되돌릴 대상 결정
if [[ -n "$TARGET" ]]; then
  SRC="$BACKUPS/$TARGET"
  [[ -f "$SRC" ]] || die "그런 백업이 없다: $TARGET  (--list 로 확인)"
else
  [[ ${#CANDIDATES[@]} -gt 0 ]] || die "되돌릴 백업이 없다 ($BACKUPS)"
  SRC="$BACKUPS/${CANDIDATES[0]}"
fi

valid_jar "$SRC" || die "되돌릴 jar 이 손상됐다: $(basename "$SRC") — 다른 것을 --to 로 지정할 것"

log "대상: $(basename "$SRC")  ($(stat -c %s "$SRC") bytes)"
if [[ -f "$LIVE" ]]; then
  log "현재: $(sha256sum "$LIVE" | cut -c1-16)…  →  되돌림: $(sha256sum "$SRC" | cut -c1-16)…"
  if [[ "$(sha256sum "$LIVE" | cut -d' ' -f1)" == "$(sha256sum "$SRC" | cut -d' ' -f1)" ]]; then
    log "⚠ 라이브와 내용이 같다 — 롤백해도 달라지는 게 없다. --list 로 다른 백업을 고를 것"
  fi
fi
STAGED=$(ls -1 "$STAGING"/BlockShip-*.jar 2>/dev/null | wc -l)
log "staging 에 대기중: ${STAGED}건 (함께 비운다)"

if [[ "$DRY" == 1 || "$YES" != 1 ]]; then
  [[ "$YES" != 1 && "$DRY" != 1 ]] && log "※ 실제로 실행하려면 --yes 를 붙일 것 (라이브가 재시작된다)"
  log "(여기서 멈춘다 — 아무것도 바꾸지 않았다)"
  exit 0
fi

# ── 실제 롤백 ────────────────────────────────────────────────────────────────
mkdir -p "$BROKEN_DIR"
if [[ -f "$LIVE" ]]; then
  KEEP="$BROKEN_DIR/BlockShip-broken-$(date +%Y%m%d-%H%M%S).jar"
  cp -p "$LIVE" "$KEEP" || die "현재 jar 보존 실패 — 중단 (아무것도 안 바꿨다)"
  log "현재 jar 보존: $(basename "$KEEP")"
fi
cp -p "$SRC" "$LIVE" || die "jar 교체 실패"
log "교체 완료: $(basename "$SRC") → $(basename "$LIVE")"

# ★이걸 빼먹으면 다음날 06:00 에 같은 jar 가 다시 적용된다
if [[ "$STAGED" -gt 0 ]]; then
  rm -f "$STAGING"/BlockShip-*.jar && log "staging 비움 (${STAGED}건) — 06:00 재적용 차단"
fi
# 승격 상태도 되돌린다. 안 그러면 fetch-staging 이 "이미 받았다"고 판단해 다시 안 받는다
rm -f "$MC_ROOT/.fetch-staging-state" 2>/dev/null && log "fetch-staging 상태 초기화"

log "재시작…"
sudo systemctl restart mcserver || die "재시작 실패 — 수동으로 sudo systemctl restart mcserver"

for i in $(seq 1 40); do
  if systemctl is-active --quiet mcserver && "$MC_ROOT/scripts/rcon.py" list >/dev/null 2>&1; then
    log "✅ 롤백 완료 — 서버 정상 (${i}회 체크)"
    notify "♻️ **롤백 완료** — \`$(basename "$SRC")\` 적용, staging ${STAGED}건 비움. 서버 정상."
    exit 0
  fi
  sleep 5
done
log "⚠ 재시작했지만 부팅 확인 실패 — 로그 확인: tail -50 $MC_ROOT/logs/latest.log"
notify "🔴 **롤백 후 부팅 확인 실패** — \`$(basename "$SRC")\` 적용했으나 RCON 무응답. 로그 확인 필요."
exit 1
