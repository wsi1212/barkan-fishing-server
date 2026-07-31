#!/bin/bash
# BlockShip Java 플러그인 빌드 + 오라클 배포 + 리로드
# 사용법: ./deploy-blockship.sh

set -e

BLOCKSHIP_DIR="$HOME/development/blockship-plugin"
JAR_NAME="BlockShip-1.0.0-SNAPSHOT.jar"
LOCAL_JAR="$BLOCKSHIP_DIR/build/libs/$JAR_NAME"

REMOTE_USER="ubuntu"
REMOTE_HOST="168.107.8.107"
REMOTE_PLUGINS="~/mcserver/plugins"
SSH_KEY="$HOME/.ssh/oracle-mc.key"

# 로컬 BlockShip 데이터 폴더 (dev)
LOCAL_DATA="/Users/user/Library/Application Support/feather/player-server/servers/07de2d81-991a-47e2-b62d-06c0d1b5150a/plugins/BlockShip"
# 검증기(ops/validate-staged.py)가 있는 스크립트 저장소
SCRIPTS_REPO="/Users/user/Library/Application Support/feather/player-server/servers/07de2d81-991a-47e2-b62d-06c0d1b5150a/plugins/Skript/scripts"
# Skript→Java 이관으로 Java가 소유하는 JSON 데이터 (dev→prod 단방향 sync).
#  주의: 이 파일들은 prod에서 직접 편집(/npc등록·/칭호 생성 등)하면 다음 배포에서 덮어쓰여짐.
#        편집은 dev에서 하고 배포할 것.
DATA_FILES=("npc.json" "dialogue.json" "titles.json" "parts.json" "enhance.json" "recipes.json" "item-flavor.json")
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

echo ""
echo "▶ 오라클 서버에 SCP 업로드"
scp -i "$SSH_KEY" -o StrictHostKeyChecking=no \
  "$LOCAL_JAR" \
  "$REMOTE_USER@$REMOTE_HOST:$REMOTE_PLUGINS/"

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

echo ""
echo "▶ 오라클 BlockShip 적용 — 전체 재시작 (★plugman reload 금지: 클래스로더 손상 NoClassDefFoundError)"
echo "  현재 접속자 확인 후 진행 권장. 5초 후 재시작합니다 (Ctrl+C로 취소)..."
sleep 5
ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no \
  "$REMOTE_USER@$REMOTE_HOST" \
  "sudo systemctl restart mcserver && echo '✓ prod 재시작 요청됨 (베타 유저 ~45초 끊김, 부팅 후 자동 복귀)'"

echo ""
echo "✅ 배포 완료"
echo "  - 로컬 패더(dev): plugins/ 복사됨 — jar 교체라 dev도 재시작해야 적용 (plugman 금지)"
echo "  - 오라클(prod): systemctl restart 로 적용 중 (접속자 없을 때 돌리는 게 안전)"
