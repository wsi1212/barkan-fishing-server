#!/bin/bash
# BlockShip Java 플러그인 빌드 + 오라클 배포 + 재시작
# 사용법: ./deploy-blockship.sh [--no-restart]
#
# --no-restart 는 전체 배포 래퍼가 BetterHud 교체·리소스팩 재생성과 함께
# 마지막에 한 번만 재시작할 때 사용한다. JAR/데이터를 prod plugins/ 에
# 올린 채로 이 옵션만 단독 실행하고 끝내면 안 된다.

set -e

RESTART_PROD=1
for arg in "$@"; do
  case "$arg" in
    --no-restart) RESTART_PROD=0 ;;
    *) echo "사용법: $0 [--no-restart]" >&2; exit 2 ;;
  esac
done

BLOCKSHIP_DIR="${BLOCKSHIP_DIR:-$HOME/development/blockship-plugin}"
JAR_NAME="BlockShip-1.0.0-SNAPSHOT.jar"
LOCAL_JAR="$BLOCKSHIP_DIR/build/libs/$JAR_NAME"

REMOTE_USER="ubuntu"
REMOTE_HOST="168.107.8.107"
REMOTE_PLUGINS="~/mcserver/plugins"
SSH_KEY="$HOME/.ssh/oracle-mc.key"
# 전체 배포 래퍼는 JAR을 라이브 plugins/에 바로 쓰지 않고 원격 임시
# 디렉터리에 먼저 올린다. 기본값은 기존 단독 배포 동작을 유지한다.
PROD_JAR_DEST="${PROD_JAR_DEST:-$REMOTE_PLUGINS/}"
REMOTE_LIVE_JAR="/home/ubuntu/mcserver/plugins/$JAR_NAME"
REMOTE_STAGE=""
REMOTE_JAR_SOURCE=""

if [ "$RESTART_PROD" = 0 ] && [ "$PROD_JAR_DEST" = "$REMOTE_PLUGINS/" ]; then
  echo "❌ --no-restart 로 라이브 plugins/에 JAR을 올릴 수 없다." >&2
  echo "   전체배포처럼 임시 경로를 지정하거나, 즉시배포(재시작 포함)를 사용하라." >&2
  exit 2
fi

# 로컬 BlockShip 데이터 폴더 (dev)
LOCAL_DATA="/Users/user/Library/Application Support/feather/player-server/servers/07de2d81-991a-47e2-b62d-06c0d1b5150a/plugins/BlockShip"
# 검증기(ops/validate-staged.py)가 있는 스크립트 저장소
SCRIPTS_REPO="/Users/user/Library/Application Support/feather/player-server/servers/07de2d81-991a-47e2-b62d-06c0d1b5150a/plugins/Skript/scripts"
# Skript→Java 이관으로 Java가 소유하는 JSON 데이터 (dev→prod 단방향 sync).
#  주의: 이 파일들은 prod에서 직접 편집(/npc등록·/칭호 생성 등)하면 다음 배포에서 덮어쓰여짐.
#        편집은 dev에서 하고 배포할 것.
DATA_FILES=("npc.json" "dialogue.json" "titles.json" "parts.json" "enhance.json" "recipes.json" "materials.json" "item-flavor.json")
# 주의: collectibles.json/quests.json/regions.json/env-bonuses.json 은 월드/배치별이라 sync 제외(수동 관리)

echo "▶ BlockShip 빌드"
cd "$BLOCKSHIP_DIR"
./gradlew build

if [ ! -f "$LOCAL_JAR" ]; then
  echo "❌ jar 빌드 실패: $LOCAL_JAR 없음"
  exit 1
fi

echo ""
echo "▶ 로컬 마크 서버에도 배포 (dev)"
cp "$LOCAL_JAR" "/Users/user/Library/Application Support/feather/player-server/servers/07de2d81-991a-47e2-b62d-06c0d1b5150a/plugins/"
echo "  ✓ 로컬 패더 plugins/ 에 복사됨"
# ★jar만 복사하고 dev를 안 재시작하면 dev도 lazy-load CNFE 지뢰가 된다(prod와 같은 원리).
#   dev가 돌고 있으면 즉시 재시작해서 중간 상태를 남기지 않는다.
if pgrep -f "paper-1\.21\..*\.jar" >/dev/null 2>&1; then
  echo "  · dev 가동 중 → 재시작 (jar만 갈아두면 CNFE 지뢰)"
  ~/dev-mc.sh restart || echo "  ⚠ dev 재시작 실패 — 수동으로 ~/dev-mc.sh restart 할 것"
else
  echo "  · dev 미가동 → 다음 기동 때 적용됨"
fi

echo ""
echo "▶ 오라클에 JSON 데이터 업로드 (Java 소유 이관 데이터)"
# ★2026-08-01 사고 후 게이트: 부분/구버전 JSON이 prod 라이브를 덮는 걸 막는다.
#   (그날 staging 경로로 NPC 1명짜리 npc.json이 138명짜리를 덮어 NPC/대화/퀘스트가 죽었다.
#    이 즉시배포 경로도 같은 구멍이 있었으므로 동일 검증기를 통과시킨다.)
VALIDATOR="$SCRIPTS_REPO/ops/validate-staged.py"
REJECTED=0
for f in "${DATA_FILES[@]}"; do
  if [ -f "$LOCAL_DATA/$f" ]; then
    if [ -x "$VALIDATOR" ]; then
      TMPLIVE=$(mktemp)
      scp -q -i "$SSH_KEY" -o StrictHostKeyChecking=no \
        "$REMOTE_USER@$REMOTE_HOST:$REMOTE_PLUGINS/BlockShip/$f" "$TMPLIVE" 2>/dev/null || : > "$TMPLIVE"
      if [ -s "$TMPLIVE" ] && ! REASON=$(python3 "$VALIDATOR" "$LOCAL_DATA/$f" "$TMPLIVE" 2>&1); then
        echo "  ⛔ $f 거부 — $REASON"
        echo "     (의도한 삭제면 $LOCAL_DATA/$f.allow-shrink 를 만들고 다시 실행)"
        REJECTED=$((REJECTED+1)); rm -f "$TMPLIVE"; continue
      fi
      rm -f "$TMPLIVE"
    fi
    scp -i "$SSH_KEY" -o StrictHostKeyChecking=no \
      "$LOCAL_DATA/$f" \
      "$REMOTE_USER@$REMOTE_HOST:$REMOTE_PLUGINS/BlockShip/" \
      && echo "  ✓ $f"
  else
    echo "  - $f 없음(스킵)"
  fi
done
if [ "$REJECTED" -gt 0 ]; then
  echo ""
  echo "❌ JSON ${REJECTED}건이 검증에서 거부됐습니다. jar 배포/재시작을 중단합니다."
  echo "   prod 데이터를 잃지 않으려면 로컬 파일을 먼저 바로잡으세요."
  exit 1
fi

# ★jar 업로드는 반드시 JSON 검증 통과 **후**에. 2026-08-03 사고: 예전엔 jar을 이 지점보다
#   먼저 scp하고 그 뒤 JSON 게이트에서 exit 1 → 라이브 jar만 갈린 채 재시작이 안 돼서
#   lazy-load NoClassDefFoundError가 터진다(/칭호·계단앉기 등 전방위 고장). 순서를 바꿔 원천 차단한다.
echo ""
echo "▶ 오라클 서버에 jar SCP 업로드 (JSON 검증 통과 후)"
echo "  목적지: $PROD_JAR_DEST"
if [ "$RESTART_PROD" = 1 ]; then
  # 즉시배포도 먼저 임시 경로에 올린다. SCP가 끊겨도 라이브 JAR이
  # 부분 파일로 바뀌지 않게 한 뒤, 정지 상태에서 mv로 승격한다.
  if [ "$PROD_JAR_DEST" = "$REMOTE_PLUGINS/" ]; then
    DEPLOY_ID="blockship-$$-$(date +%Y%m%d%H%M%S)"
    REMOTE_STAGE="/home/ubuntu/mcserver/.deploy-staged/$DEPLOY_ID"
    PROD_JAR_DEST="$REMOTE_STAGE/"
    ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no \
      "$REMOTE_USER@$REMOTE_HOST" "install -d -m 0755 '$REMOTE_STAGE'"
  fi
fi

if ! scp -i "$SSH_KEY" -o StrictHostKeyChecking=no \
  "$LOCAL_JAR" \
  "$REMOTE_USER@$REMOTE_HOST:$PROD_JAR_DEST"; then
  if [ "$RESTART_PROD" = 1 ]; then
    echo "🔴 JAR 업로드 실패 — 기존 JAR로 prod를 다시 기동한다" >&2
    ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no \
      "$REMOTE_USER@$REMOTE_HOST" 'sudo systemctl start mcserver' || true
  fi
  exit 1
fi
REMOTE_JAR_SOURCE="${PROD_JAR_DEST%/}/$JAR_NAME"

echo ""
if [ "$RESTART_PROD" = 0 ]; then
  echo "⏸ prod 재시작 생략 — 전체 배포 래퍼가 임시 JAR을 라이브로 승격한 뒤 재시작할 것"
else
  echo "▶ 오라클 BlockShip 적용 — 정지 후 원자 승격, 기동 (★plugman reload 금지: 클래스로더 손상 NoClassDefFoundError)"
  if ! ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no \
    "$REMOTE_USER@$REMOTE_HOST" \
    "set -e
     sudo systemctl stop mcserver
     test -s '$REMOTE_JAR_SOURCE'
     if [ -f '$REMOTE_LIVE_JAR' ]; then
       cp '$REMOTE_LIVE_JAR' \"/home/ubuntu/mcserver/backups/BlockShip-prev-\$(date +%Y%m%d%H%M%S).jar\"
     fi
     mv '$REMOTE_JAR_SOURCE' '$REMOTE_LIVE_JAR'
     sudo systemctl start mcserver
     echo '✓ prod 기동 요청됨 (베타 유저 ~45초 끊김, 부팅 후 자동 복귀)'"; then
    echo ""
    echo "🔴 BlockShip 교체/기동 실패 — prod 기동 상태를 확인해야 한다." >&2
    echo "   확인: ssh -i $SSH_KEY $REMOTE_USER@$REMOTE_HOST 'sudo systemctl status mcserver'" >&2
    ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no \
      "$REMOTE_USER@$REMOTE_HOST" 'sudo systemctl start mcserver' || true
    exit 1
  fi
  [ -z "$REMOTE_STAGE" ] || ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no \
    "$REMOTE_USER@$REMOTE_HOST" "rm -rf '$REMOTE_STAGE'" || true
fi

echo ""
echo "✅ 배포 완료"
echo "  - 로컬 패더(dev): plugins/ 복사 + (가동중이면) 자동 재시작 완료"
if [ "$RESTART_PROD" = 0 ]; then
  echo "  - 오라클(prod): JAR/JSON 업로드 완료, JAR 승격·재시작은 아직 안 함"
else
  echo "  - 오라클(prod): 정지→JAR 교체→기동 완료 (접속자 없을 때 돌리는 게 안전)"
fi
