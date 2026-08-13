#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# dev에 prod 반영 (시딩/갱신)
#
# 맥 dev가 망가진 원인은 "드리프트"였다 — Citizens NPC가 12명 적어서 튜토 검증이
# 불가했다. 그래서 dev는 매번 prod에서 부어 만든다. 드리프트할 시간을 주지 않는다.
#
# 사용법:
#   mcdev-sync.sh                     # 메인 월드 3종 + 플러그인 전체
#   mcdev-sync.sh --worlds all        # 섬·길드섬·광산까지 전부 (디스크 주의)
#   mcdev-sync.sh --no-worlds         # 플러그인/설정만 갱신 (빠름, JSON 작업용)
#   mcdev-sync.sh --dry-run
# ─────────────────────────────────────────────────────────────────────────────
set -uo pipefail
cd "$(dirname "$0")" && source ./mcdev-lib.sh

WORLDS="world world_nether world_the_end"
COPY_WORLDS=1
DRY=0
EXCLUDE_PLUGINS=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --worlds)
      if [[ "$2" == "all" ]]; then
        WORLDS="world world_nether world_the_end guild_world island_world afk_world flatroom mine"
      else WORLDS="$2"; fi
      shift 2 ;;
    --no-worlds)      COPY_WORLDS=0; shift ;;
    --exclude-plugin) EXCLUDE_PLUGINS+=("$2"); shift 2 ;;
    --dry-run)        DRY=1; shift ;;
    -h|--help)        sed -n '2,18p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) die "알 수 없는 인자: $1" ;;
  esac
done

RSYNC_OPTS=(-a --delete --info=stats2)
[[ $DRY -eq 1 ]] && RSYNC_OPTS+=(--dry-run)

log "═══ dev 반영 시작 ═══"
[[ -d "$PROD_ROOT" ]] || die "prod 트리 없음: $PROD_ROOT"
dev_running && die "dev가 돌고 있다. 먼저 mcdev-down.sh 로 내릴 것."

# ── 디스크 가드 ──────────────────────────────────────────────────────────────
# ★disk-guard.sh 는 85%에서 경고하고 92%에서 "가장 오래된 로컬 백업부터 삭제"한다.
#   dev 월드 복사로 디스크를 밀어올리면 DR 백업이 지워진다. 그건 절대 안 된다.
USED=$(disk_used_pct "$HOME")
log "현재 디스크 사용률: ${USED}%"
if [[ "$USED" -ge "$DISK_CEIL_PCT" ]]; then
  die "디스크 ${USED}% ≥ ${DISK_CEIL_PCT}% — 반영 거부. dev가 백업을 밀어낼 위험이 있다."
fi

if [[ $COPY_WORLDS -eq 1 ]]; then
  NEED=0
  for w in $WORLDS; do
    [[ -d "$PROD_ROOT/$w" ]] || continue
    NEED=$(( NEED + $(du -sm "$PROD_ROOT/$w" 2>/dev/null | cut -f1) ))
  done
  AVAIL=$(df -BM --output=avail "$HOME" | tail -1 | tr -dc '0-9')
  log "월드 복사 필요 ${NEED}MB / 가용 ${AVAIL}MB"
  # 여유 2배는 남긴다 (백업 cron이 tar 만들 공간)
  if [[ $NEED -gt 0 && $(( NEED * 2 )) -gt $AVAIL ]]; then
    die "여유 부족 — 필요 ${NEED}MB의 2배를 확보할 수 없다. --no-worlds 나 월드 축소를 쓸 것."
  fi
fi

mkdir -p "$MCDEV_ROOT"

# ── prod 저장 플러시 ────────────────────────────────────────────────────────
# 라이브 파일을 읽는 중 바뀌면 복사본이 찢어진다. 백업 스크립트들과 같은 방식.
if prod_running; then
  log "prod save-all flush"
  if [[ -x "$PROD_ROOT/scripts/rcon.py" ]]; then
    "$PROD_ROOT/scripts/rcon.py" save-all flush >/dev/null 2>&1 \
      || tmux send-keys -t mc 'save-all flush' Enter 2>/dev/null || true
  else
    tmux send-keys -t mc 'save-all flush' Enter 2>/dev/null || true
  fi
  sleep 8
else
  log "⚠ prod가 안 돌고 있다 — 플러시 없이 파일 그대로 복사한다"
fi

# ── Paper jar ───────────────────────────────────────────────────────────────
PROD_PAPER=$(find "$PROD_ROOT" -maxdepth 1 -name 'paper-*.jar' | sort | tail -1)
[[ -n "$PROD_PAPER" ]] || die "prod Paper jar를 못 찾음"
if [[ $DRY -eq 0 ]]; then
  cp "$PROD_PAPER" "$MCDEV_ROOT/mcdev-paper.jar"
  echo "eula=true" > "$MCDEV_ROOT/eula.txt"
fi
log "Paper: $(basename "$PROD_PAPER")"

# ── 플러그인 ────────────────────────────────────────────────────────────────
# jar + 데이터 전부. Citizens saves.yml(NPC 157명)·BlockShip JSON·playerdata 가
# 여기 들어오는 게 이 스크립트의 존재 이유다.
PLUGIN_OPTS=("${RSYNC_OPTS[@]}")
for ex in ${EXCLUDE_PLUGINS[@]+"${EXCLUDE_PLUGINS[@]}"}; do
  PLUGIN_OPTS+=(--exclude "$ex")
  log "제외: $ex"
done
log "플러그인 동기화"
rsync "${PLUGIN_OPTS[@]}" "$PROD_ROOT/plugins/" "$MCDEV_ROOT/plugins/" 2>&1 | tail -4

# ── 월드 ────────────────────────────────────────────────────────────────────
if [[ $COPY_WORLDS -eq 1 ]]; then
  for w in $WORLDS; do
    if [[ ! -d "$PROD_ROOT/$w" ]]; then log "  (없음, 건너뜀) $w"; continue; fi
    log "월드 동기화: $w"
    # session.lock 은 가져가면 안 된다 — 새 인스턴스가 남의 락을 물고 죽는다
    rsync "${RSYNC_OPTS[@]}" --exclude 'session.lock' \
      "$PROD_ROOT/$w/" "$MCDEV_ROOT/$w/" 2>&1 | tail -3
  done
else
  log "월드 복사 생략 (--no-worlds)"
fi

# ── OP 명단 ─────────────────────────────────────────────────────────────────
[[ -f "$PROD_ROOT/ops.json" && $DRY -eq 0 ]] && cp "$PROD_ROOT/ops.json" "$MCDEV_ROOT/"

# ── server.properties ───────────────────────────────────────────────────────
# prod 것을 베이스로 쓰고 필요한 키만 덮는다. 리소스팩 URL·SHA1·난이도 등을
# 그대로 물려받아야 텍스처 검증이 의미가 있다.
if [[ $DRY -eq 0 ]]; then
  RCON_PW="dev$(head -c 12 /dev/urandom | base64 | tr -dc 'A-Za-z0-9')"
  echo "$RCON_PW" > "$RCON_PW_FILE"; chmod 600 "$RCON_PW_FILE"

  python3 - "$PROD_ROOT/server.properties" "$MCDEV_ROOT/server.properties" \
           "$MCDEV_GAME_PORT" "$MCDEV_RCON_PORT" "$RCON_PW" <<'PY'
import sys
src, dst, port, rport, rpw = sys.argv[1:6]
# ★online-mode=true 유지가 핵심. offline 이면 UUID 가 달라져서 prod playerdata 가
#   안 붙는다 → 레벨·돈·장비가 전부 초기화된 상태로 "검증"하게 된다.
override = {
    'server-port': port,
    'rcon.port': rport,
    'rcon.password': rpw,
    'enable-rcon': 'true',
    'online-mode': 'true',
    'white-list': 'true',
    'enforce-whitelist': 'true',
    'view-distance': '6',
    'simulation-distance': '5',
    'max-players': '3',
    'motd': '\\u00a7bBARKAN DEV \\u00a77(1h auto-stop)',
    'query.port': port,
}
lines, seen = [], set()
try:
    for ln in open(src, encoding='utf-8', errors='replace'):
        s = ln.strip()
        if s and not s.startswith('#') and '=' in s:
            k = s.split('=', 1)[0]
            if k in override:
                lines.append(f'{k}={override[k]}\n'); seen.add(k); continue
        lines.append(ln)
except FileNotFoundError:
    pass
for k, v in override.items():
    if k not in seen:
        lines.append(f'{k}={v}\n')
open(dst, 'w', encoding='utf-8').writelines(lines)
print('server.properties 작성 완료')
PY
fi

# ── 안전장치 확인 ────────────────────────────────────────────────────────────
# systemd 유닛이 dev를 물고 있으면 Restart=always 로 되살아난다. 절대 금지.
if systemctl list-unit-files 2>/dev/null | grep -q 'mcdev'; then
  log "⚠⚠ mcdev systemd 유닛이 존재한다 — dev는 절대 systemd 로 관리하지 말 것"
fi

SIZE=$(du -sh "$MCDEV_ROOT" 2>/dev/null | cut -f1)
log "═══ 반영 완료 (dev 트리 $SIZE) ═══"
[[ $DRY -eq 1 ]] && log "(dry-run 이었음)"
exit 0
