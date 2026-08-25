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
# 사용: ops/deploy-jar.sh <jar 경로> [--dev] [--name <plugins 안 파일명>]
#   --dev            prod 대신 dev(맥)에 올린다. 정지·기동은 ~/dev-mc.sh 가 맡는다.
#   --name <파일명>   BlockShip 이 아닌 플러그인(예: BarkanChess-1.0.0.jar)을 올릴 때.
# ★별도 레포 플러그인(BarkanChess 등)도 이걸 쓴다 — --name 을 생략하면 원격 파일명은 로컬 jar 의 basename.
#   BarkanChess 는 반드시 tools/gate.sh 를 먼저 통과시킬 것(역컴파일 복원본이라 빌드 성공 ≠ 정상).
set -euo pipefail

JAR="${1:?사용: $0 <jar 경로> [--dev] [--name <파일명>]}"
shift
[ -f "$JAR" ] || { echo "❌ jar 없음: $JAR"; exit 1; }

TARGET=prod
NAME="BlockShip-1.0.0-SNAPSHOT.jar"
NAME_SET=0
while [ $# -gt 0 ]; do
    case "$1" in
        --dev)  TARGET=dev; shift ;;
        --name) NAME="${2:?--name 뒤에 파일명}"; NAME_SET=1; shift 2 ;;
        *)      echo "❌ 모르는 인자: $1"; exit 1 ;;
    esac
done

# --name 을 명시하지 않은 별도 플러그인은 로컬 산출물 이름을 그대로 사용한다.
# BlockShip 기본 산출물명은 기존 기본값과 동일하므로 기존 호출은 변하지 않는다.
if [ "$NAME_SET" = 0 ]; then
    NAME="$(basename "$JAR")"
fi

KEY="$HOME/.ssh/oracle-mc.key"
HOST="ubuntu@168.107.8.107"
REMOTE="~/mcserver/plugins/$NAME"
DEV_PLUGINS="/Users/user/Library/Application Support/feather/player-server/servers/07de2d81-991a-47e2-b62d-06c0d1b5150a/plugins"

if [ "$TARGET" = dev ]; then
    [ -f "$DEV_PLUGINS/$NAME" ] || { echo "❌ dev 에 그 이름의 jar 이 없다: $NAME (이름 확인)"; exit 1; }
    echo "▶ dev 정지"
    ~/dev-mc.sh stop || true
    echo "▶ jar 교체 ($(wc -c < "$JAR")b) → $NAME"
    cp "$JAR" "$DEV_PLUGINS/$NAME"
    echo "▶ dev 기동 (기동 ~83초, 타임아웃 떠도 실패 아님)"
    ~/dev-mc.sh start || true
    echo "✅ dev 배포 완료"
    exit 0
fi

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

# staging/ 에 남은 같은 이름의 낡은 jar 이 그날 밤 06:00 nightly 에 이걸 덮어쓰지
# 못하게 라이브와 같은 상태로 맞춘다. JSON 은 이 스크립트가 안 올리므로 손대지 않는다.
"$(dirname "$0")/sync-prod-staging.sh" --jar-name "$NAME" \
  || echo "⚠ staging 동기화 실패 — 06:00 되돌림 위험. ops/sync-prod-staging.sh 를 직접 돌릴 것" >&2

echo "✅ 배포 완료 — 부팅 ~50초"
