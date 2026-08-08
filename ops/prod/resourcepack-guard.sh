#!/usr/bin/env bash
# 운영 리소스팩 무결성 가드.
#
# GitHub release `latest`의 같은 asset을 --clobber로 교체하면 URL은 그대로인데
# 파일만 바뀐다. server.properties의 SHA1이 이전 파일을 가리킨 채 서버가
# 재시작되면 require-resource-pack=true 환경에서 모든 접속자가 다운로드 실패로
# 차단된다. 서버 기동 직전 실제 공개 URL의 파일을 다시 해시해 이 상태를 막는다.
#
# 사용법:
#   resourcepack-guard.sh --check   # 불일치면 실패, 파일은 수정하지 않음
#   resourcepack-guard.sh --repair  # 불일치면 SHA1만 원자적으로 보정

set -euo pipefail

MODE="${1:---check}"
case "$MODE" in
  --check|--repair) ;;
  *) echo "usage: $0 --check|--repair" >&2; exit 2 ;;
esac

ROOT="${MC_ROOT:-$HOME/mcserver}"
PROPS="$ROOT/server.properties"
WEBHOOK_FILE="${WEBHOOK_FILE:-$ROOT/scripts/discord-webhook.url}"
LABEL="[바르칸 prod]"

notify() {
  [ -s "$WEBHOOK_FILE" ] || return 0
  local url payload
  url=$(cat "$WEBHOOK_FILE")
  payload=$(python3 -c 'import json,sys; print(json.dumps({"content": sys.argv[1]}))' "$LABEL $1")
  curl -fsS -m 10 -H 'Content-Type: application/json' -d "$payload" "$url" >/dev/null 2>&1 || true
}

fail() {
  echo "resourcepack-guard: $1" >&2
  notify "🔴 리소스팩 기동 전 검증 실패: $1"
  exit 1
}

[ -f "$PROPS" ] || fail "server.properties 없음: $PROPS"
url=$(sed -n 's/^resource-pack=//p' "$PROPS" | head -n 1)
expected=$(sed -n 's/^resource-pack-sha1=//p' "$PROPS" | head -n 1 | tr '[:upper:]' '[:lower:]')
url="${url//\\:/:}"

[[ "$url" == https://* ]] || fail "HTTPS resource-pack URL이 아님"
[[ "$expected" =~ ^[0-9a-f]{40}$ ]] || fail "resource-pack-sha1 형식 오류: ${expected:-없음}"

pack=$(mktemp /tmp/barkan-resourcepack-guard.XXXXXX.zip)
trap 'rm -f "$pack"' EXIT
curl --fail --location --silent --show-error --retry 3 --retry-delay 2 \
  --connect-timeout 15 --max-time 240 --proto '=https' --tlsv1.2 \
  "$url" --output "$pack" || fail "공개 리소스팩 다운로드 실패"

actual=$(sha1sum "$pack" | awk '{print $1}')
if [ "$actual" = "$expected" ]; then
  echo "resourcepack-guard: OK $actual"
  exit 0
fi

if [ "$MODE" = "--check" ]; then
  fail "SHA1 불일치 (설정=$expected, 공개파일=$actual)"
fi

next=$(mktemp "${PROPS}.tmp.XXXXXX")
trap 'rm -f "$pack" "$next"' EXIT
awk -v sha="$actual" '
  /^resource-pack-sha1=/ { print "resource-pack-sha1=" sha; found=1; next }
  { print }
  END { if (!found) exit 42 }
' "$PROPS" > "$next" || fail "resource-pack-sha1 항목 갱신 실패"
chmod --reference="$PROPS" "$next"
mv "$next" "$PROPS"
echo "resourcepack-guard: REPAIRED $expected -> $actual"
notify "⚠️ GitHub 공개 리소스팩 SHA1 변경 감지 → 다음 기동용 서버 설정을 자동 보정했습니다. ($expected → $actual)"
