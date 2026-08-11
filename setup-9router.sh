#!/usr/bin/env bash
# 9Router를 이 낚시 프로젝트에서만 "한도 초과 시 안전망"으로 쓰기 위한 설치 스크립트.
# .claude/settings.local.json은 이미 git에 커밋돼 있어 API 키를 넣지 않는다.
# 대신 .claude/.env.9router (gitignore됨)에 키를 저장하고,
# claude-fish.sh 래퍼로 이 폴더에서만 그 env를 적용해 claude를 실행한다.
set -euo pipefail
cd "$(dirname "$0")"

ENV_FILE=".claude/.env.9router"
WRAPPER="claude-fish.sh"
# 이 맥의 ~/.npmrc가 BizBen 사내 CodeArtifact로 고정돼 있어(만료 토큰=401),
# 공개 npm 패키지 설치도 실패한다. ~/.npmrc가 홈 상위경로에 있어 --userconfig로도
# "project config"로 다시 읽혀서 무시됨 → env var로 registry를 강제 지정해 우회한다.
# (~/.npmrc 자체는 전혀 건드리지 않음)

case "${1:-}" in
  start)
    echo "9Router 대시보드를 엽니다 (http://localhost:20128)"
    echo "Providers 메뉴에서 무료 provider(Kiro AI 등)를 연결한 뒤,"
    echo "발급된 API 키를 복사해서: ./setup-9router.sh apply <API_KEY> 실행하세요."
    env npm_config_registry=https://registry.npmjs.org/ npx -y 9router@latest
    ;;

  tray)
    echo "9Router를 백그라운드(트레이 모드)로 띄웁니다. 대시보드는 계속 http://localhost:20128"
    env npm_config_registry=https://registry.npmjs.org/ npx -y 9router@latest --tray &
    disown
    echo "PID: $! (끄려면: pkill -f 9router)"
    ;;

  apply)
    KEY="${2:-}"
    MODEL="${3:-fish}"
    if [ -z "$KEY" ]; then
      echo "사용법: ./setup-9router.sh apply <9router에서 복사한 API_KEY> [콤보이름(기본값: fish)]"
      exit 1
    fi

    mkdir -p .claude
    cat > "$ENV_FILE" <<EOF
export ANTHROPIC_BASE_URL="http://localhost:20128/v1"
export ANTHROPIC_AUTH_TOKEN="$KEY"
export CLAUDE_CODE_ENABLE_GATEWAY_MODEL_DISCOVERY=1
EOF
    chmod 600 "$ENV_FILE"

    grep -qxF "$ENV_FILE" .gitignore 2>/dev/null || echo "$ENV_FILE" >> .gitignore

    cat > "$WRAPPER" <<EOF
#!/usr/bin/env bash
# 이 폴더에서만 9Router 경유로 claude 실행 (한도 다 찼을 때 안전망).
# 평소엔 그냥 \`claude\` 쓰면 됨 — 이 스크립트는 필요할 때만 사용.
# 9Router가 안 떠있으면 자동으로 백그라운드(tray)로 띄운 뒤 진행한다.
set -euo pipefail
cd "\$(dirname "\$0")"

if ! curl -s -o /dev/null -m 2 http://localhost:20128/v1/models; then
  echo "9Router가 안 떠있어서 백그라운드로 띄웁니다..."
  env npm_config_registry=https://registry.npmjs.org/ npx -y 9router@latest --tray >/dev/null 2>&1 &
  disown
  for i in \$(seq 1 20); do
    curl -s -o /dev/null -m 2 http://localhost:20128/v1/models && break
    sleep 1
  done
fi

source .claude/.env.9router
export ANTHROPIC_MODEL="$MODEL"
exec claude --model "$MODEL" "\$@"
EOF
    chmod +x "$WRAPPER"

    echo "완료. 앞으로 한도 다 찼을 때만 이 폴더에서:"
    echo "  ./claude-fish.sh"
    echo "로 실행하면 9Router(무료 폴백)를 거쳐서 계속 작업할 수 있습니다."
    echo "평소엔 그냥 claude 명령어 쓰세요 (원래 Anthropic API 그대로 사용)."
    ;;

  *)
    echo "사용법:"
    echo "  1단계) ./setup-9router.sh start          — 9Router 실행(포그라운드) + 대시보드에서 무료 provider 연결"
    echo "  2단계) ./setup-9router.sh apply <API_KEY> — 이 프로젝트 전용 래퍼(claude-fish.sh) 생성"
    echo "  평소)  ./setup-9router.sh tray            — 9Router 백그라운드 상시 실행 (claude-fish.sh 쓰기 전에 먼저 켜둘 것)"
    exit 1
    ;;
esac
