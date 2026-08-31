#!/usr/bin/env bash
# 바르칸 전체 prod 배포 진입점.
#
# 이 스크립트가 담당하는 범위:
#   1) BlockShip 빌드
#   2) Java 소유 JSON 검증·동기화
#   3) BlockShip JAR 업로드
#   4) 메인 리소스팩 빌드·업로드·server.properties SHA1 갱신
#   5) BetterHud 정의·아트·폰트 교체
#   6) BetterHud 셰이더 재생성 + CraftEngine 팩 재생성/공개 SHA1 검증
#   7) 서버 재시작 1회 + JAR/JSON/서버 상태 최종 대조
#
# 전체 배포를 요청받았을 때는 하위 스크립트를 따로 실행하지 말고 이 파일만 쓴다.
# BetterHud 전용 수정만 있을 때는 ops/prod/betterhud/deploy-prod.sh 를 쓴다.

set -euo pipefail

# ★심볼릭링크 해석 — ~/<이름>.sh 로 실행되면 $0·BASH_SOURCE 가 홈을 가리켜
#   같은 폴더의 스크립트를 못 찾는다(2026-08-31: 모든 배포가 staging 동기화를 조용히
#   건너뛰고 있었다). 원본 로직은 ops/lib-self.sh.
_self_real() { local s="$1" l; while [ -L "$s" ]; do l="$(readlink "$s")"; case "$l" in /*) s="$l";; *) s="$(dirname "$s")/$l";; esac; done; printf '%s\n' "$s"; }
SELF_DIR="$(cd "$(dirname "$(_self_real "${BASH_SOURCE[0]:-$0}")")" && pwd)"

ROOT="$SELF_DIR"
BLOCKSHIP_DIR="${BLOCKSHIP_DIR:-$HOME/development/blockship-plugin}"
JAR="$BLOCKSHIP_DIR/build/libs/BlockShip-1.0.0-SNAPSHOT.jar"
# Java 소유 JSON의 작업 원본은 dev 런타임 사본이 아니라 git 미러다.
# dev plugins/BlockShip/은 기동 중 Java 정규화로 내용이 달라질 수 있다.
DATA_DIR="$ROOT/blockship-data"
PROD_HOST="ubuntu@168.107.8.107"
KEY="$HOME/.ssh/oracle-mc.key"
LOCK="/tmp/barkan-deploy-all-prod.lock"
DEPLOY_ID="codex-$$-$(date +%Y%m%d%H%M%S)"
REMOTE_STAGE="/home/ubuntu/mcserver/.deploy-staged/$DEPLOY_ID"
REMOTE_STAGE_JAR="$REMOTE_STAGE/BlockShip-1.0.0-SNAPSHOT.jar"
REMOTE_STAGE_DATA="$REMOTE_STAGE/BlockShip"
REMOTE_STAGE_MOTD="$REMOTE_STAGE/motd.properties"
REMOTE_LIVE_JAR="/home/ubuntu/mcserver/plugins/BlockShip-1.0.0-SNAPSHOT.jar"
SERVER_MAY_BE_DOWN=0
MOTD_FILE="$ROOT/prod/motd.properties"

[ -x "$ROOT/deploy-blockship.sh" ] || { echo "❌ deploy-blockship.sh 실행 권한 없음" >&2; exit 1; }
[ -x "$ROOT/rp-deploy.sh" ] || { echo "❌ rp-deploy.sh 실행 권한 없음" >&2; exit 1; }
[ -x "$ROOT/prod/betterhud/deploy-prod.sh" ] || { echo "❌ BetterHud deploy-prod.sh 실행 권한 없음" >&2; exit 1; }
[ -f "$KEY" ] || { echo "❌ SSH 키 없음: $KEY" >&2; exit 1; }
[ -f "$MOTD_FILE" ] || { echo "❌ MOTD 파일 없음: $MOTD_FILE" >&2; exit 1; }

if ! mkdir "$LOCK" 2>/dev/null; then
  old=$(cat "$LOCK/pid" 2>/dev/null || true)
  if [ -n "$old" ] && kill -0 "$old" 2>/dev/null; then
    echo "❌ 다른 전체 prod 배포가 실행 중이다 (pid $old)" >&2
    exit 1
  fi
  rm -rf "$LOCK"
  mkdir "$LOCK"
fi
echo "$$" > "$LOCK/pid"

say() { echo; echo "── $* ──"; }

# JAR은 서버가 살아 있는 동안 라이브 plugins/에 쓰지 않는다. 실패해도
# 임시 산출물만 치우고 현재 서버/JAR은 그대로 두도록 한다.
remote_cleanup() {
  ssh -o BatchMode=yes -o ConnectTimeout=12 -i "$KEY" "$PROD_HOST" \
    "rm -rf '$REMOTE_STAGE'" >/dev/null 2>&1 || true
}
cleanup_all() {
  if [ "$SERVER_MAY_BE_DOWN" = 1 ]; then
    ssh -o BatchMode=yes -o ConnectTimeout=12 -i "$KEY" "$PROD_HOST" \
      'sudo systemctl start mcserver' >/dev/null 2>&1 || true
  fi
  remote_cleanup
  rm -rf "$LOCK"
}
trap cleanup_all EXIT

ssh -o BatchMode=yes -o ConnectTimeout=12 -i "$KEY" "$PROD_HOST" \
  "install -d -m 0755 '$REMOTE_STAGE' '$REMOTE_STAGE_DATA'"

say "1) BlockShip 빌드 + JSON/JAR 업로드 (재시작은 마지막에 한 번)"
PROD_JAR_DEST="$REMOTE_STAGE/" PROD_DATA_DEST="$REMOTE_STAGE_DATA/" \
  "$ROOT/deploy-blockship.sh" --no-restart
[ -s "$JAR" ] || { echo "❌ JAR 빌드 산출물 없음: $JAR" >&2; exit 1; }
EXPECTED_JAR=$(shasum "$JAR" | awk '{print $1}')
echo "  JAR SHA1: $EXPECTED_JAR"

say "2) 메인 리소스팩 배포 (재시작은 마지막에 한 번)"
# rp-deploy.sh 는 --restart 없이도 공개팩·prod server.properties SHA1까지 갱신한다.
# 마지막 BetterHud 체인의 재시작이 두 팩을 함께 적용한다.
"$ROOT/rp-deploy.sh" prod

say "2-b) MOTD 반영 예약"
scp -q -i "$KEY" -o StrictHostKeyChecking=no \
  "$MOTD_FILE" "$PROD_HOST:$REMOTE_STAGE_MOTD"
ssh -o BatchMode=yes -o ConnectTimeout=12 -i "$KEY" "$PROD_HOST" \
  "python3 - '$REMOTE_STAGE_MOTD' <<'PY'
from pathlib import Path
import sys

props = Path('/home/ubuntu/mcserver/server.properties')
motd_file = Path(sys.argv[1])
replacement = motd_file.read_text(encoding='utf-8').rstrip('\n') + '\n'
lines = props.read_text(encoding='utf-8').splitlines(keepends=True)
out = []
seen = False
for line in lines:
    if line.startswith('motd='):
        out.append(replacement)
        seen = True
    else:
        out.append(line)
if not seen:
    out.append(replacement)
props.write_text(''.join(out), encoding='utf-8')
print('MOTD staged')
PY"

say "3) BetterHud + CraftEngine 리소스팩 + 마지막 재시작"
# JSON과 JAR은 1단계에서 모두 임시 경로에 있다. 서버를 멈춘 뒤에만
# 라이브 plugins/로 승격하고 BetterHud 체인의 기동을 통과시킨다.
say "3-a) 서버 정지 후 JAR 라이브 승격"
SERVER_MAY_BE_DOWN=1
ssh -o BatchMode=yes -o ConnectTimeout=12 -i "$KEY" "$PROD_HOST" "set -e
  sudo systemctl stop mcserver
  for i in \$(seq 1 30); do
    [ \"\$(systemctl is-active mcserver || true)\" = active ] || break
    sleep 2
  done
  [ \"\$(systemctl is-active mcserver || true)\" = active ] && { echo '❌ 서버 정지 실패'; exit 1; }
  test -s '$REMOTE_STAGE_JAR'
  for f in npc.json dialogue.json titles.json parts.json enhance.json recipes.json materials.json item-flavor.json; do
    test -s '$REMOTE_STAGE_DATA'/\$f
  done
  if [ -f '$REMOTE_LIVE_JAR' ]; then
    cp '$REMOTE_LIVE_JAR' \"/home/ubuntu/mcserver/backups/BlockShip-prev-\$(date +%Y%m%d%H%M%S).jar\"
  fi
  for f in npc.json dialogue.json titles.json parts.json enhance.json recipes.json materials.json item-flavor.json; do
    mv '$REMOTE_STAGE_DATA'/\$f \"/home/ubuntu/mcserver/plugins/BlockShip/\$f\"
  done
  mv '$REMOTE_STAGE_JAR' '$REMOTE_LIVE_JAR'
  sha1sum '$REMOTE_LIVE_JAR'"

# 위에서 서버를 멈췄으므로 BetterHud 체인의 내부 stop은 no-op이고, 최종
# start가 새 JAR을 읽는다. 이 시점에는 jar-guard의 false positive가 없다.
BETTERHUD_ARGS=()
if [ "${DEPLOY_DIALOGUE:-0}" = 1 ]; then
  BETTERHUD_ARGS+=(--with-dialogue)
  echo "  ★DEPLOY_DIALOGUE=1: 대화창 정의/초상화 assets도 함께 전송"
fi
# 현재 빌드 JAR을 명시적으로 넘긴다. BetterHud 스크립트가 원격의
# 오래된 /tmp/BlockShip-new.jar를 발견해 새로 승격한 JAR을 덮어쓰는 일을 막는다.
# ★bash 3.2(맥 기본) + set -u 에서는 빈 배열 전개 "${arr[@]}" 자체가 unbound 로 죽는다.
# 2026-08-26 실전 배포가 정확히 이 줄에서 끊겼다(JAR 승격 직후 = 서버 정지 상태). +확장으로 회피.
"$ROOT/prod/betterhud/deploy-prod.sh" "$JAR" ${BETTERHUD_ARGS[@]+"${BETTERHUD_ARGS[@]}"}
SERVER_MAY_BE_DOWN=0

say "4) 전체 배포 최종 대조"
remote_jar=$(ssh -o BatchMode=yes -o ConnectTimeout=12 -i "$KEY" "$PROD_HOST" \
  "sha1sum ~/mcserver/plugins/BlockShip-1.0.0-SNAPSHOT.jar | awk '{print \$1}'")
[ "$remote_jar" = "$EXPECTED_JAR" ] || {
  echo "❌ prod JAR SHA1 불일치: 로컬=$EXPECTED_JAR prod=$remote_jar" >&2
  exit 1
}
echo "  JAR SHA1 일치: $remote_jar"

# deploy-blockship.sh 가 실제로 올리는 Java 소유 데이터만 대조한다.
for f in npc.json dialogue.json titles.json parts.json enhance.json recipes.json materials.json item-flavor.json; do
  local_file="$DATA_DIR/$f"
  [ -f "$local_file" ] || { echo "  - $f 로컬 없음(스킵)"; continue; }
  expected=$(shasum "$local_file" | awk '{print $1}')
  actual=$(ssh -o BatchMode=yes -o ConnectTimeout=12 -i "$KEY" "$PROD_HOST" \
    "sha1sum ~/mcserver/plugins/BlockShip/$f | awk '{print \$1}'")
  # NpcManager.save()는 Gson pretty-print 결과를 마지막 개행 없이 저장한다.
  # 따라서 재기동 뒤 dialogue.json은 의미상 동일해도 로컬 미러와 1바이트 차이가 날 수 있다.
  # 이 경우에만 마지막 개행을 제거한 해시로 재확인하고, 그 외 내용 차이는 계속 실패시킨다.
  if [ "$actual" != "$expected" ] && [ "$f" = "dialogue.json" ]; then
    expected_normalized=$(perl -0777 -pe 's/\n\z//' "$local_file" | shasum | awk '{print $1}')
    actual_normalized=$(ssh -o BatchMode=yes -o ConnectTimeout=12 -i "$KEY" "$PROD_HOST" \
      "perl -0777 -pe 's/\\n\\z//' ~/mcserver/plugins/BlockShip/$f | sha1sum | awk '{print \$1}'")
    if [ "$actual_normalized" = "$expected_normalized" ]; then
      echo "  $f 일치 (운영 저장 시 마지막 개행 정규화)"
      continue
    fi
  fi
  # 통발 레시피의 result.lore는 부팅 시 TrapSpecs(Java 단일 진실원)가
  # 현행 지역명으로 정규화한다. lore만 비교에서 제외하고 재료·결과·잠금 등
  # 나머지 레시피 필드는 그대로 검증해 실제 누락·변경을 계속 검출한다.
  if [ "$actual" != "$expected" ] && [ "$f" = "recipes.json" ]; then
    expected_normalized=$(jq -S 'with_entries(if .key == "recipes" then .value |= with_entries(if (.key | test("^TR(01|03|04|05|06|08|09|10|11|13)(D|L|Q)?$")) then .value.result |= del(.lore) else . end) else . end)' \
      "$local_file" | shasum | awk '{print $1}')
    actual_normalized=$(ssh -o BatchMode=yes -o ConnectTimeout=12 -i "$KEY" "$PROD_HOST" \
      "jq -S 'with_entries(if .key == \"recipes\" then .value |= with_entries(if (.key | test(\"^TR(01|03|04|05|06|08|09|10|11|13)(D|L|Q)?$\")) then .value.result |= del(.lore) else . end) else . end)' ~/mcserver/plugins/BlockShip/$f | sha1sum | awk '{print \$1}'")
    if [ "$actual_normalized" = "$expected_normalized" ]; then
      echo "  $f 일치 (통발 result.lore는 Java 정규화)"
      continue
    fi
  fi
  [ "$actual" = "$expected" ] || {
    echo "❌ $f SHA1 불일치: 로컬=$expected prod=$actual" >&2
    exit 1
  }
  echo "  $f 일치"
done

ssh -o BatchMode=yes -o ConnectTimeout=12 -i "$KEY" "$PROD_HOST" \
  'test "$(systemctl is-active mcserver)" = active && test -s ~/mcserver/plugins/CraftEngine/generated/resource_pack.zip'
echo "  서버 active + CraftEngine 팩 존재 확인"

say "5) staging 동기화 (06:00 조용한 되돌림 차단)"
# 여기까지 왔으면 라이브가 최신이다. staging/ 에 남아 있던 낡은 jar·설정은 그날 밤
# nightly-restart.sh 가 그대로 라이브에 덮어써 오늘 배포를 조용히 되돌린다(에러 없음).
# staging 을 라이브와 같게 맞춰 그 경로를 무해하게 만든다. 상세는 sync-prod-staging.sh.
"$ROOT/sync-prod-staging.sh" --jar-name "$(basename "$REMOTE_LIVE_JAR")" --with-config

echo
echo "✅ 전체 prod 배포 완료: Java/JSON/BetterHud/리소스팩/재시작/staging 동기화/최종 해시 검증 통과"
