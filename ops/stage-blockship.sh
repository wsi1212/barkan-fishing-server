#!/usr/bin/env bash
# BlockShip 빌드 → 오라클 staging/ 업로드 (재시작 안 함)
#   → 다음 06:00 KST 데일리 재시작 때 자동 적용됨.
#   즉시 적용하려면 ~/deploy-blockship.sh (빌드+배포+즉시 재시작) 사용.
set -e
cd /Users/user/development/blockship-plugin
echo "▶ 빌드..."; ./gradlew build -q
JAR=build/libs/BlockShip-1.0.0-SNAPSHOT.jar
echo "▶ 오라클 staging 업로드..."
scp -i ~/.ssh/oracle-mc.key "$JAR" ubuntu@168.107.8.107:~/mcserver/staging/
echo "✅ 스테이징 완료 — 다음 06:00 KST 재시작 때 자동 적용."
echo "   설정 JSON도 넣으려면: scp ...json ubuntu@168.107.8.107:~/mcserver/staging/BlockShip/"
