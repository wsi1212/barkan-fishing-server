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

ROOT="$(cd "$(dirname "$0")" && pwd)"
BLOCKSHIP_DIR="${BLOCKSHIP_DIR:-$HOME/development/blockship-plugin}"
JAR="$BLOCKSHIP_DIR/build/libs/BlockShip-1.0.0-SNAPSHOT.jar"
DATA_DIR="/Users/user/Library/Application Support/feather/player-server/servers/07de2d81-991a-47e2-b62d-06c0d1b5150a/plugins/BlockShip"
PROD_HOST="ubuntu@168.107.8.107"
KEY="$HOME/.ssh/oracle-mc.key"
LOCK="/tmp/barkan-deploy-all-prod.lock"

[ -x "$ROOT/deploy-blockship.sh" ] || { echo "❌ deploy-blockship.sh 실행 권한 없음" >&2; exit 1; }
[ -x "$ROOT/rp-deploy.sh" ] || { echo "❌ rp-deploy.sh 실행 권한 없음" >&2; exit 1; }
[ -x "$ROOT/prod/betterhud/deploy-prod.sh" ] || { echo "❌ BetterHud deploy-prod.sh 실행 권한 없음" >&2; exit 1; }
[ -f "$KEY" ] || { echo "❌ SSH 키 없음: $KEY" >&2; exit 1; }

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
cleanup() { rm -rf "$LOCK"; }
trap cleanup EXIT

say() { echo; echo "── $* ──"; }

say "1) BlockShip 빌드 + JSON/JAR 업로드 (재시작은 마지막에 한 번)"
"$ROOT/deploy-blockship.sh" --no-restart
[ -s "$JAR" ] || { echo "❌ JAR 빌드 산출물 없음: $JAR" >&2; exit 1; }
EXPECTED_JAR=$(shasum "$JAR" | awk '{print $1}')
echo "  JAR SHA1: $EXPECTED_JAR"

say "2) 메인 리소스팩 배포 (재시작은 마지막에 한 번)"
# rp-deploy.sh 는 --restart 없이도 공개팩·prod server.properties SHA1까지 갱신한다.
# 마지막 BetterHud 체인의 재시작이 두 팩을 함께 적용한다.
"$ROOT/rp-deploy.sh" prod

say "3) BetterHud + CraftEngine 리소스팩 + 마지막 재시작"
# JAR/JSON은 2단계에서 이미 prod에 올라갔다. BetterHud 체인이 서버를 멈춘 뒤
# 새 JAR까지 읽어 기동하므로 재시작은 여기서 한 번만 일어난다.
"$ROOT/prod/betterhud/deploy-prod.sh"

say "4) 전체 배포 최종 대조"
remote_jar=$(ssh -o BatchMode=yes -o ConnectTimeout=12 -i "$KEY" "$PROD_HOST" \
  "sha1sum ~/mcserver/plugins/BlockShip-1.0.0-SNAPSHOT.jar | awk '{print \$1}'")
[ "$remote_jar" = "$EXPECTED_JAR" ] || {
  echo "❌ prod JAR SHA1 불일치: 로컬=$EXPECTED_JAR prod=$remote_jar" >&2
  exit 1
}
echo "  JAR SHA1 일치: $remote_jar"

# deploy-blockship.sh 가 실제로 올리는 Java 소유 데이터만 대조한다.
for f in npc.json dialogue.json titles.json parts.json enhance.json recipes.json item-flavor.json; do
  local_file="$DATA_DIR/$f"
  [ -f "$local_file" ] || { echo "  - $f 로컬 없음(스킵)"; continue; }
  expected=$(shasum "$local_file" | awk '{print $1}')
  actual=$(ssh -o BatchMode=yes -o ConnectTimeout=12 -i "$KEY" "$PROD_HOST" \
    "sha1sum ~/mcserver/plugins/BlockShip/$f | awk '{print \$1}'")
  [ "$actual" = "$expected" ] || {
    echo "❌ $f SHA1 불일치: 로컬=$expected prod=$actual" >&2
    exit 1
  }
  echo "  $f 일치"
done

ssh -o BatchMode=yes -o ConnectTimeout=12 -i "$KEY" "$PROD_HOST" \
  'test "$(systemctl is-active mcserver)" = active && test -s ~/mcserver/plugins/CraftEngine/generated/resource_pack.zip'
echo "  서버 active + CraftEngine 팩 존재 확인"
echo
echo "✅ 전체 prod 배포 완료: Java/JSON/BetterHud/리소스팩/재시작/최종 해시 검증 통과"
