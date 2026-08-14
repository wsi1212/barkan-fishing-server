#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# GitHub Release → ~/mcserver/staging/  (오라클에서 cron 으로 당겨온다)
#
# 방향이 핵심이다: 폰에서 오라클로 "밀어넣는" 게 아니라 오라클이 "당겨온다".
# 그래서 폰에 SSH 키가 없어도, 맥이 꺼져 있어도 배포가 돈다.
# (리소스팩이 이미 이 구조다 — GitHub Release URL 을 server.properties 가 가리킨다)
#
# 승격 게이트: Actions 워크플로는 **수동 promote 일 때만** Release 를 만든다.
# 그래서 "최신 Release 가 존재한다" = "사람이 승격을 눌렀다" 가 성립한다.
# push 마다 Release 가 생기게 바꾸면 이 전제가 깨지므로 절대 그렇게 하지 말 것.
#
# 흐름:  Release 조회 → 이미 받은 태그면 종료 → 다운로드 → 무결성 검증
#        → ~/mcserver/staging/ 배치 → Discord 알림
#        → 06:00 nightly-restart.sh 가 적용 + 구 jar 백업
#
# ★plugins/ 루트에는 절대 쓰지 않는다. staging 까지만이 이 스크립트의 권한이다.
#
# 설치:
#   crontab:  */15 * * * * flock -n ~/mcserver/.fetch.lock ~/mcserver/scripts/fetch-staging.sh
#   토큰:     ~/mcserver/.github-token  (fine-grained PAT, contents:read, chmod 600)
# ─────────────────────────────────────────────────────────────────────────────
set -uo pipefail

REPO="${BLOCKSHIP_REPO:-wsi1212/blockship-plugin}"  # 2026-08-14 실측 확인 (private)
MC_ROOT="${MC_ROOT:-$HOME/mcserver}"
STAGING="$MC_ROOT/staging"
STATE_FILE="$MC_ROOT/.fetch-staging-state"
TOKEN_FILE="${GITHUB_TOKEN_FILE:-$MC_ROOT/.github-token}"
WEBHOOK_FILE="$MC_ROOT/scripts/discord-webhook.url"
LOG_FILE="${FETCH_LOG:-$MC_ROOT/scripts/ops.log}"
ASSET_GLOB="${ASSET_GLOB:-BlockShip-*.jar}"

DRY=0; FORCE=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run) DRY=1; shift ;;
    --force)   FORCE=1; shift ;;
    -h|--help) sed -n '2,26p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "알 수 없는 인자: $1" >&2; exit 2 ;;
  esac
done

log() {
  local m="[$(date '+%Y-%m-%d %H:%M:%S')] [fetch-staging] $*"
  echo "$m"; echo "$m" >> "$LOG_FILE" 2>/dev/null || true
}
notify() {
  [[ -f "$WEBHOOK_FILE" ]] || return 0
  local url; url=$(<"$WEBHOOK_FILE"); [[ -n "$url" ]] || return 0
  curl -fsS --max-time 15 -H 'Content-Type: application/json' \
    -d "$(python3 -c 'import json,sys;print(json.dumps({"content":sys.argv[1]}))' "$1")" \
    "$url" >/dev/null 2>&1 || true
}
die() { log "✗ $*"; notify "🔴 **staging fetch 실패** — $*"; exit 1; }

# jar 무결성 — 깨진 다운로드가 staging 에 들어가면 06:00 에 그대로 적용된다.
# 유효한 zip 인지 + 플러그인 기술자가 있는지까지 본다.
validate_jar() {
  local jar="$1"
  [[ -s "$jar" ]]                         || { log "  검증 실패: 빈 파일"; return 1; }
  unzip -t "$jar" >/dev/null 2>&1         || { log "  검증 실패: 손상된 zip"; return 1; }
  # ★`unzip -l` 은 크기·날짜가 앞에 붙은 표 형식이라 경계 매칭이 어긋난다
  #   (정상 jar 를 전부 거부하는 버그를 실측으로 물었다). -Z1 은 이름만 한 줄씩 낸다.
  # ★★그리고 파이프로 `grep -q` 에 넘기면 안 된다. grep -q 는 첫 매칭에서 즉시 끝나고,
  #   그러면 아직 쓰는 중인 unzip 이 SIGPIPE 로 죽어 rc=141 이 된다. 이 스크립트는
  #   `set -o pipefail` 이라 **매칭에 성공했는데도 파이프라인이 실패로 잡힌다.**
  #   → 정상 jar 를 100% 거부한다. 2026-08-14 첫 실제 배포에서 물었다(prod 실측 rc=141).
  #   엔트리가 적은 합성 jar 로 시험하면 unzip 이 파이프 버퍼에 다 쓰고 끝나 SIGPIPE 가
  #   안 나므로 통과한다 — 그래서 앞선 6케이스 검증을 빠져나갔다. 목록을 먼저 담아서 본다.
  local names
  names=$(unzip -Z1 "$jar" 2>/dev/null) \
                                          || { log "  검증 실패: 항목 목록을 읽을 수 없다"; return 1; }
  grep -qE '^(plugin|paper-plugin)\.yml$' <<<"$names" \
                                          || { log "  검증 실패: plugin.yml 없음 (플러그인 jar 가 아니다)"; return 1; }
  return 0
}

[[ -d "$MC_ROOT" ]] || die "mcserver 트리 없음: $MC_ROOT"
[[ -f "$TOKEN_FILE" ]] || die "GitHub 토큰 없음: $TOKEN_FILE (fine-grained PAT, contents:read)"
TOKEN=$(<"$TOKEN_FILE")
[[ -n "$TOKEN" ]] || die "토큰 파일이 비어있다"

API="https://api.github.com/repos/$REPO"
HDR=(-H "Authorization: Bearer $TOKEN" -H "Accept: application/vnd.github+json" \
     -H "X-GitHub-Api-Version: 2022-11-28")

# ★상태코드를 봐야 한다. 전에는 실패를 뭉개서 "Release 조회 실패" 하나로 냈는데,
#   그러면 **아직 promote 안 한 정상 상태**(404, releases 0개)와 **토큰 만료·권한 부족**(401/403)이
#   같은 빨간 알림으로 나온다. cron 이 15분마다 도니까 첫 promote 전에는 하루 96번 오탐이 되고,
#   그 노이즈에 묻혀 진짜 토큰 만료를 놓친다 — 무인운영에서 제일 위험한 실패 방식이다.
#   2026-08-14 실측으로 갈랐다: repo 200 / releases/latest 404 / releases 0개.
# trap 은 쓰지 않는다 — 아래 다운로드 구간이 자기 trap 으로 EXIT 를 덮어써서 이 파일이 남는다.
HTTP_BODY=$(mktemp)
CODE=$(curl -sS --max-time 60 -o "$HTTP_BODY" -w '%{http_code}' "${HDR[@]}" "$API/releases/latest" 2>/dev/null || echo 000)
RESP=""
[[ "$CODE" == 200 ]] && RESP=$(<"$HTTP_BODY")
rm -f "$HTTP_BODY"
case "$CODE" in
  200) : ;;
  404) log "아직 Release 가 없다 (promote 전 정상 상태) — 할 일 없음"; exit 0 ;;
  401) die "토큰 인증 실패 (401) — PAT 만료·오타 의심: $TOKEN_FILE" ;;
  403) die "권한 부족 또는 rate limit (403) — PAT 의 Contents:read 와 대상 repo 확인: $REPO" ;;
  000) die "GitHub API 에 닿지 못했다 (네트워크·DNS)" ;;
  *)   die "Release 조회 예상 밖 응답 HTTP $CODE ($REPO)" ;;
esac

read -r TAG ASSET_ID ASSET_NAME ASSET_SIZE <<<"$(python3 - "$ASSET_GLOB" <<PY
import json, sys, fnmatch
d = json.loads('''$RESP''')
if d.get('draft') or d.get('prerelease'):
    sys.exit('draft/prerelease 는 건너뛴다')
for a in d.get('assets', []):
    if fnmatch.fnmatch(a['name'], sys.argv[1]):
        print(d['tag_name'], a['id'], a['name'], a['size']); break
else:
    sys.exit('일치하는 자산이 없다')
PY
)" || die "Release 파싱: $(python3 -c "
import json;d=json.loads('''$RESP''');print(d.get('tag_name','?'),'draft' if d.get('draft') else '','prerelease' if d.get('prerelease') else '')" 2>/dev/null)"

log "최신 Release: $TAG ($ASSET_NAME, $((ASSET_SIZE / 1024))KB)"

LAST=$(cat "$STATE_FILE" 2>/dev/null || echo "")
if [[ "$LAST" == "$TAG" && $FORCE -eq 0 ]]; then
  # 조용히 끝낸다 — cron 이 15분마다 도니 여기서 알림을 보내면 노이즈가 된다
  exit 0
fi

log "새 승격 감지: ${LAST:-<없음>} → $TAG"
[[ $DRY -eq 1 ]] && { log "(dry-run — 여기서 멈춘다)"; exit 0; }

mkdir -p "$STAGING"
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT

curl -fsSL --max-time 300 \
  -H "Authorization: Bearer $TOKEN" -H "Accept: application/octet-stream" \
  -o "$TMP/$ASSET_NAME" "$API/releases/assets/$ASSET_ID" \
  || die "다운로드 실패: $ASSET_NAME"

GOT=$(stat -c %s "$TMP/$ASSET_NAME")
[[ "$GOT" == "$ASSET_SIZE" ]] || die "크기 불일치 (기대 $ASSET_SIZE / 실제 $GOT)"
validate_jar "$TMP/$ASSET_NAME" || die "무결성 검증 실패 — staging 에 넣지 않는다"
log "검증 통과 (zip 정상 + plugin.yml 존재)"

# 디스크 확인 — disk-guard 는 92% 에서 백업부터 지운다
USED=$(df --output=pcent "$MC_ROOT" | tail -1 | tr -dc '0-9')
[[ "$USED" -ge 88 ]] && die "디스크 ${USED}% — staging 배치 중단"

# 구 staging jar 는 치운다 (nightly 가 여러 개를 만나면 어느 걸 쓸지 모호해진다)
rm -f "$STAGING"/BlockShip-*.jar
mv "$TMP/$ASSET_NAME" "$STAGING/"
echo "$TAG" > "$STATE_FILE"

log "staging 배치 완료: $STAGING/$ASSET_NAME"
notify "📦 **staging 에 새 jar** — \`$ASSET_NAME\` (\`$TAG\`)
06:00 데일리 유지보수가 적용한다.
검증하려면: \`mcdev-up.sh --jar $STAGING/$ASSET_NAME\`
취소하려면 적용 전에: \`rm $STAGING/$ASSET_NAME\`"
exit 0
