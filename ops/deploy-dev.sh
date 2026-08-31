#!/bin/bash
# dev 원클릭 배포: BlockShip 빌드 → dev plugins 복사 → dev 서버 자동 재시작.
set -e
PLUGIN=/Users/user/development/blockship-plugin
SRV="/Users/user/Library/Application Support/feather/player-server/servers/07de2d81-991a-47e2-b62d-06c0d1b5150a"
echo "[1/3] 빌드..."
( cd "$PLUGIN" && ./gradlew build -q --offline )
echo "[2/3] jar 배포..."
cp "$PLUGIN/build/libs/BlockShip-1.0.0-SNAPSHOT.jar" "$SRV/plugins/"
echo "[3/3] dev 서버 재시작..."
/Users/user/dev-mc.sh restart
echo "✅ dev 배포 완료"
