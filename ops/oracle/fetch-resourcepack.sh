#!/usr/bin/env bash
# GitHub mobile-promoted resource pack -> prod server.properties.
# The phone never needs SSH access: prod pulls an explicitly promoted Release.
# This script never restarts prod. APPLY_NOW is intentionally ignored.
set -uo pipefail

REPO="${RESOURCEPACK_REPO:-wsi1212/minecraft-fish-resource-pack}"
MC_ROOT="${MC_ROOT:-$HOME/mcserver}"
PROPS="$MC_ROOT/server.properties"
STATE_FILE="$MC_ROOT/.fetch-resourcepack-state"
TOKEN_FILE="${GITHUB_TOKEN_FILE:-$MC_ROOT/.github-token}"
WEBHOOK_FILE="$MC_ROOT/scripts/discord-webhook.url"
LOG_FILE="${FETCH_LOG:-$MC_ROOT/backups/ops.log}"
PROMOTE_MARKER="${RESOURCEPACK_PROMOTE_MARKER:-MOBILE_RP_PROMOTE}"

DRY=0; FORCE=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run) DRY=1; shift ;;
    --force) FORCE=1; shift ;;
    -h|--help) sed -n '2,5p' "$0" | sed 's/^# *//'; exit 0 ;;
    *) echo "알 수 없는 인자: $1" >&2; exit 2 ;;
  esac
done

log() {
  local m="[$(date '+%Y-%m-%d %H:%M:%S')] [fetch-resourcepack] $*"
  echo "$m"; echo "$m" >> "$LOG_FILE" 2>/dev/null || true
}
notify() {
  [[ -s "$WEBHOOK_FILE" ]] || return 0
  local url; url=$(<"$WEBHOOK_FILE")
  curl -fsS --max-time 15 -H 'Content-Type: application/json' \
    -d "$(python3 -c 'import json,sys;print(json.dumps({"content":sys.argv[1]}))' "$1")" \
    "$url" >/dev/null 2>&1 || true
}
die() { log "✗ $*"; notify "🔴 **모바일 리소스팩 pull 실패** — $*"; exit 1; }

[[ -f "$PROPS" ]] || die "server.properties 없음: $PROPS"
HDR=(-H 'Accept: application/vnd.github+json' -H 'X-GitHub-Api-Version: 2022-11-28')
if [[ -s "$TOKEN_FILE" ]]; then
  HDR+=(-H "Authorization: Bearer $(<"$TOKEN_FILE")")
fi

API="https://api.github.com/repos/$REPO/releases?per_page=30"
BODY=$(mktemp)
trap 'rm -f "$BODY"' EXIT
CODE=$(curl -sS --max-time 60 -o "$BODY" -w '%{http_code}' "${HDR[@]}" "$API" 2>/dev/null || echo 000)
case "$CODE" in
  200) : ;;
  401) die "GitHub 토큰 인증 실패 (401): $TOKEN_FILE" ;;
  403) die "GitHub API 권한/rate limit (403): $REPO" ;;
  000) die "GitHub API 네트워크/DNS 실패" ;;
  *) die "GitHub API HTTP $CODE: $REPO" ;;
esac

CANDIDATE=$(python3 - "$BODY" "$PROMOTE_MARKER" <<'PY'
import json, sys
path, marker = sys.argv[1:]
data = json.load(open(path, encoding="utf-8"))
for release in data:
    if release.get("draft") or release.get("prerelease"):
        continue
    if marker not in (release.get("body") or ""):
        continue
    for asset in release.get("assets", []):
        if asset.get("name") == "barkan-resourcepack.zip":
            print(release["tag_name"])
            print(asset["browser_download_url"])
            print(asset["size"])
            print("1" if "APPLY_NOW" in (release.get("body") or "") else "0")
            raise SystemExit
PY
)
if [[ -z "$CANDIDATE" ]]; then
  [[ "$DRY" = 1 ]] && log "승격된 모바일 리소스팩 Release 없음"
  exit 0
fi
mapfile -t C < <(printf '%s\n' "$CANDIDATE")
TAG="${C[0]}"; URL="${C[1]}"; EXPECTED_SIZE="${C[2]}"; APPLY="${C[3]}"
LAST=$(cat "$STATE_FILE" 2>/dev/null || true)
if [[ "$LAST" == "$TAG" && "$FORCE" = 0 ]]; then
  [[ "$DRY" = 1 ]] && log "이미 처리한 Release: $TAG"
  exit 0
fi
log "승격 Release: $TAG (apply_now=$APPLY)"
[[ "$DRY" = 1 ]] && { log "dry-run — 다운로드/설정변경/재시작 없음"; exit 0; }

TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
curl -fsSL --max-time 600 --retry 3 --retry-delay 2 "$URL" -o "$TMP/barkan-resourcepack.zip" \
  || die "팩 다운로드 실패: $URL"
GOT_SIZE=$(stat -c %s "$TMP/barkan-resourcepack.zip")
[[ "$GOT_SIZE" = "$EXPECTED_SIZE" ]] || die "팩 크기 불일치 (기대 $EXPECTED_SIZE / 실제 $GOT_SIZE)"
unzip -t "$TMP/barkan-resourcepack.zip" >/dev/null 2>&1 || die "팩 ZIP 손상"
python3 - "$TMP/barkan-resourcepack.zip" <<'PY' || die "팩 구조 검증 실패"
import sys, zipfile
with zipfile.ZipFile(sys.argv[1]) as z:
    names = set(z.namelist())
    assert "pack.mcmeta" in names
    assert any(n.startswith("assets/barkan/") for n in names)
    assert all(not n.startswith("/") and ".." not in n.split("/") for n in names)
PY
SHA=$(sha1sum "$TMP/barkan-resourcepack.zip" | awk '{print $1}')

python3 - "$PROPS" "$URL" "$SHA" <<'PY'
import io, os, sys
props, url, sha = sys.argv[1:]
escaped = url.replace(":", "\\:", 1)
out=[]; seen_url=False; seen_sha=False
for line in io.open(props, encoding="utf-8"):
    if line.startswith("resource-pack="):
        out.append("resource-pack=" + escaped + "\n"); seen_url=True
    elif line.startswith("resource-pack-sha1="):
        out.append("resource-pack-sha1=" + sha + "\n"); seen_sha=True
    else:
        out.append(line)
assert seen_url and seen_sha, "resource-pack 항목 없음"
tmp=props + ".mobile.tmp"
io.open(tmp, "w", encoding="utf-8").write("".join(out))
os.replace(tmp, props)
PY

"$MC_ROOT/scripts/resourcepack-guard.sh" --check || die "공개 URL SHA1 교차검증 실패"
printf '%s\n' "$TAG" > "$STATE_FILE"
log "server.properties 갱신 완료: $SHA"

if [[ "$APPLY" = 1 ]]; then
  log "APPLY_NOW 무시 — prod 재시작 금지 정책으로 설정만 갱신"
else
  log "설정만 갱신 — prod 재시작 안 함"
fi
notify "📦 **모바일 리소스팩 승격 완료** — \`$TAG\`\n설정만 갱신했습니다. prod 재시작은 정책상 하지 않습니다."
