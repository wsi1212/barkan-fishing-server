#!/usr/bin/env bash
# 이 폴더에서만 9Router 경유로 claude 실행 (한도 다 찼을 때 안전망).
# 평소엔 그냥 `claude` 쓰면 됨 — 이 스크립트는 필요할 때만 사용.
# 9Router가 안 떠있으면 자동으로 백그라운드(tray)로 띄운 뒤 진행한다.
set -euo pipefail
cd "$(dirname "$0")"

if ! curl -s -o /dev/null -m 2 http://localhost:20128/v1/models; then
  echo "9Router가 안 떠있어서 백그라운드로 띄웁니다..."
  env npm_config_registry=https://registry.npmjs.org/ npx -y 9router@latest --tray >/dev/null 2>&1 &
  disown
  for i in $(seq 1 20); do
    curl -s -o /dev/null -m 2 http://localhost:20128/v1/models && break
    sleep 1
  done
fi

source .claude/.env.9router
export ANTHROPIC_MODEL="fish"
# groq/gpt-oss-120b는 tools 128개 제한이 있어서, 이 스크립트에서는 minecraft-ai-builder(건축/스크린샷, 90개+)는 끄고
# codegraph(9개 안팎, 유용함)만 살려서 내장 도구+codegraph만 사용
exec claude --model fish --strict-mcp-config --mcp-config '{"mcpServers":{"codegraph":{"command":"/Users/user/.local/bin/codegraph","args":["serve","--mcp","-p","/Users/user/development/blockship-plugin"]}}}' "$@"
