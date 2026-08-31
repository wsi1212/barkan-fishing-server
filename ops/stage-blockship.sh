#!/usr/bin/env bash
# BlockShip 지연 배포(스테이징) — 오라클 `staging/` 에만 올리고 재시작하지 않는다.
#   → 다음 06:00 KST 데일리 유지보수 때 자동 적용된다(맥이 꺼져 있어도 된다).
#   즉시 적용은 ~/deploy-blockship.sh.
#
# ## 왜 얇은 래퍼인가 (2026-08-31)
# 예전 이 파일은 «gradlew build + scp» 12줄이었다. 그래서 **게이트를 하나도 안 돌았다** —
# 퀘스트 감사·사본 드리프트·빌드 출처·굵은 포맷·NPC 대사 전부 건너뛴 jar 이 staging 에
# 앉아 있다가 06:00 에 **아무 검사 없이 prod 에 적용**됐다. 즉시배포만 게이트를 걸어 두면
# 지연배포가 그대로 우회로가 된다.
#
# ⇒ 검사·빌드·업로드 로직을 복제하지 않고 deploy-blockship.sh 를 스테이징 목적지로 부른다.
#   게이트가 늘거나 바뀌어도 이 경로가 저절로 따라온다.
set -euo pipefail

# ★심볼릭링크를 풀어야 한다 — ~/stage-blockship.sh 로 실행되면 BASH_SOURCE 가 홈을
#   가리켜 REPO 가 /Users 가 된다(2026-08-31 실측: /Users/ops/deploy-blockship.sh not found).
SELF="${BASH_SOURCE[0]}"
while [ -L "$SELF" ]; do
  LINK="$(readlink "$SELF")"
  case "$LINK" in /*) SELF="$LINK" ;; *) SELF="$(dirname "$SELF")/$LINK" ;; esac
done
REPO="$(cd "$(dirname "$SELF")/.." && pwd)"
STAGE_JAR="/home/ubuntu/mcserver/staging/"
STAGE_DATA="/home/ubuntu/mcserver/staging/BlockShip/"

echo "▶ staging 디렉터리 확인"
ssh -o BatchMode=yes -o ConnectTimeout=12 -i "$HOME/.ssh/oracle-mc.key" \
  ubuntu@168.107.8.107 "install -d -m 0755 '$STAGE_JAR' '$STAGE_DATA'"

PROD_JAR_DEST="$STAGE_JAR" PROD_DATA_DEST="$STAGE_DATA" \
  "$REPO/ops/deploy-blockship.sh" --no-restart

echo ""
echo "✅ 스테이징 완료 — 게이트 전부 통과한 jar/JSON 이 staging/ 에 있습니다."
echo "   다음 06:00 KST 데일리 유지보수 때 자동 적용됩니다."
echo "   즉시 적용하려면: ~/deploy-blockship.sh"
