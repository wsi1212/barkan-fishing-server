#!/bin/bash
# 이미 빌드된 jar 하나만 prod 에 올린다 — **정지 → 교체 → 기동**을 한 몸으로.
#
# ## 왜 따로 있나
# 평소 배포는 ~/deploy-blockship.sh 다. 그건 **공용 작업 트리를 다시 빌드**하는데,
# 다른 세션이 파일을 고치는 중이면 컴파일이 깨져 배포 자체가 막힌다. 그럴 때
# 격리 worktree(HEAD + 내 커밋)에서 뽑은 jar 을 이 스크립트로 올린다.
#   git worktree add <경로> HEAD && cp -R libs <경로>/ && (cd <경로> && ./gradlew build)
#
# ## 지켜야 할 것
# 라이브 jar 을 덮어쓰고 재시작을 미루면 그 뒤 처음 로드되는 클래스가 전부
# NoClassDefFoundError 가 된다(2026-08-03 prod 사고). 그래서 여기서는 **먼저 멈추고**
# 교체한 뒤 다시 띄운다. 업로드가 실패하면 옛 jar 그대로 다시 띄운다.
# ops/hooks/guard-live-jar.py 의 허용 목록에 이 파일 이름이 들어 있다 — 우회가 아니라
# 훅이 요구하는 「stop→교체→start 를 한 몸으로 처리하는 스크립트」 그 자체다.
#
# ★JSON 데이터는 안 올린다(jar 전용). 데이터까지 보내려면 deploy-blockship.sh 를 쓸 것.
#
# 사용: ops/deploy-jar.sh <jar 경로>
set -euo pipefail

JAR="${1:?사용: $0 <jar 경로>}"
[ -f "$JAR" ] || { echo "❌ jar 없음: $JAR"; exit 1; }

KEY="$HOME/.ssh/oracle-mc.key"
HOST="ubuntu@168.107.8.107"
REMOTE="~/mcserver/plugins/BlockShip-1.0.0-SNAPSHOT.jar"

echo "▶ 접속자 확인"
ssh -i "$KEY" -o StrictHostKeyChecking=no "$HOST" 'python3 ~/mcserver/scripts/rcon.py list | head -1' || true

echo "▶ 정지"
ssh -i "$KEY" -o StrictHostKeyChecking=no "$HOST" 'sudo systemctl stop mcserver'

echo "▶ jar 교체 ($(wc -c < "$JAR")b)"
if ! scp -q -i "$KEY" -o StrictHostKeyChecking=no "$JAR" "$HOST:$REMOTE"; then
    echo "🔴 업로드 실패 — 옛 jar 그대로 다시 띄운다"
    ssh -i "$KEY" -o StrictHostKeyChecking=no "$HOST" 'sudo systemctl start mcserver'
    exit 1
fi

echo "▶ 기동"
ssh -i "$KEY" -o StrictHostKeyChecking=no "$HOST" 'sudo systemctl start mcserver'
echo "✅ 배포 완료 — 부팅 ~50초"
