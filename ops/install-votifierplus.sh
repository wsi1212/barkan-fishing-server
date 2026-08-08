#!/usr/bin/env bash
# VotifierPlus를 검증된 고정 버전으로 설치한다.
#
# 기본(--dev): BlockShip 빌드 성공 후 dev를 정지하고 두 jar를 원자 교체한 뒤 한 번만 기동·검증.
# --stage-prod: prod 라이브 plugins/를 건드리지 않고 staging/에만 올린다.
#              실제 적용은 다음 정기 재시작이 담당하며, 그 전/재시작 시 리소스팩 SHA1 가드가 검증한다.
set -euo pipefail

VERSION="1.4.3"
JAR_NAME="VotifierPlus-${VERSION}.jar"
URL="https://nexus.bencodez.com/repository/maven-public/com/bencodez/votifierplus/${VERSION}/votifierplus-${VERSION}.jar"
SHA256="42015fc6fc45f9b865d6c3caa669b621902dbcbcaeaa7d98cfeec8a0dee388d0"
DEV_ROOT="/Users/user/Library/Application Support/feather/player-server/servers/07de2d81-991a-47e2-b62d-06c0d1b5150a"
BLOCKSHIP_ROOT="$HOME/development/blockship-plugin"
BLOCKSHIP_JAR="$BLOCKSHIP_ROOT/build/libs/BlockShip-1.0.0-SNAPSHOT.jar"
SSH_KEY="$HOME/.ssh/oracle-mc.key"
REMOTE="ubuntu@168.107.8.107"

mode="${1:---dev}"
case "$mode" in
  --dev|--stage-prod) ;;
  *) echo "사용법: $0 [--dev|--stage-prod]" >&2; exit 2 ;;
esac

work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
candidate="$work/$JAR_NAME"

if [ "$mode" = "--dev" ]; then
  echo "[1/6] BlockShip 빌드…"
  (cd "$BLOCKSHIP_ROOT" && ./gradlew build -q)
  [ -s "$BLOCKSHIP_JAR" ] || { echo "❌ BlockShip 빌드 산출물 없음" >&2; exit 1; }

  echo "[2/6] VotifierPlus ${VERSION} 다운로드…"
  curl --fail --location --silent --show-error --retry 3 --retry-delay 2 \
    --connect-timeout 15 --max-time 240 --proto '=https' --tlsv1.2 \
    "$URL" --output "$candidate"

  echo "[3/6] SHA-256·플러그인 구조 검증…"
  actual=$(shasum -a 256 "$candidate" | awk '{print $1}')
  [ "$actual" = "$SHA256" ] || { echo "❌ SHA-256 불일치: $actual" >&2; exit 1; }
  jar tf "$candidate" | grep -qx 'plugin.yml' || { echo "❌ Bukkit plugin.yml이 없는 jar" >&2; exit 1; }
  unzip -p "$candidate" plugin.yml | grep -q '^name: VotifierPlus$' || { echo "❌ VotifierPlus jar가 아님" >&2; exit 1; }

  target_dir="$DEV_ROOT/plugins"
  target="$target_dir/$JAR_NAME"
  echo "[4/6] dev 정상 정지 후 jar 2개 원자 교체…"
  "$HOME/dev-mc.sh" stop
  install -d "$target_dir"
  install -m 0644 "$candidate" "$target_dir/.${JAR_NAME}.new"
  mv -f "$target_dir/.${JAR_NAME}.new" "$target"
  install -m 0644 "$BLOCKSHIP_JAR" "$target_dir/.BlockShip-1.0.0-SNAPSHOT.jar.new"
  mv -f "$target_dir/.BlockShip-1.0.0-SNAPSHOT.jar.new" "$target_dir/BlockShip-1.0.0-SNAPSHOT.jar"

  echo "[5/6] dev 전체 기동…"
  "$HOME/dev-mc.sh" start

  echo "[6/6] VotifierPlus·BlockShip 로드 로그 검증…"
  log="$DEV_ROOT/logs/dev-script.log"
  grep -q 'VotifierPlus' "$log" || { echo "❌ VotifierPlus 로드 로그를 찾지 못함: $log" >&2; exit 1; }
  grep -q '\[MineList\] 추천 보상 수신 준비 완료' "$log" || {
    echo "❌ BlockShip 추천 보상 연결 로그를 찾지 못함: $log" >&2; exit 1;
  }
  echo "✅ dev 설치·전체 재시작·연결 검증 완료"
  exit 0
fi

echo "[1/5] VotifierPlus ${VERSION} 다운로드…"
curl --fail --location --silent --show-error --retry 3 --retry-delay 2 \
  --connect-timeout 15 --max-time 240 --proto '=https' --tlsv1.2 \
  "$URL" --output "$candidate"
echo "[2/5] SHA-256·플러그인 구조 검증…"
actual=$(shasum -a 256 "$candidate" | awk '{print $1}')
[ "$actual" = "$SHA256" ] || { echo "❌ SHA-256 불일치: $actual" >&2; exit 1; }
jar tf "$candidate" | grep -qx 'plugin.yml' || { echo "❌ Bukkit plugin.yml이 없는 jar" >&2; exit 1; }
unzip -p "$candidate" plugin.yml | grep -q '^name: VotifierPlus$' || { echo "❌ VotifierPlus jar가 아님" >&2; exit 1; }

echo "[3/5] prod 리소스팩 공개 SHA1 사전 검증…"
ssh -i "$SSH_KEY" -o ConnectTimeout=12 "$REMOTE" '~/mcserver/scripts/resourcepack-guard.sh --check'
echo "[4/5] prod staging에만 업로드 (라이브 plugins/ 미변경)…"
ssh -i "$SSH_KEY" -o ConnectTimeout=12 "$REMOTE" 'mkdir -p ~/mcserver/staging'
scp -i "$SSH_KEY" -o ConnectTimeout=12 "$candidate" "$REMOTE:~/mcserver/staging/$JAR_NAME"
echo "[5/5] staging SHA-256 재검증…"
remote_sha=$(ssh -i "$SSH_KEY" -o ConnectTimeout=12 "$REMOTE" "sha256sum ~/mcserver/staging/$JAR_NAME" | awk '{print $1}')
[ "$remote_sha" = "$SHA256" ] || { echo "❌ prod staging SHA-256 불일치: $remote_sha" >&2; exit 1; }
echo "✅ prod는 staging에만 준비됨 — 다음 정기 재시작의 리소스팩 가드 통과 뒤 적용됩니다."
