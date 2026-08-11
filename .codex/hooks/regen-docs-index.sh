#!/bin/bash
# 최상위 설계 문서가 변경되면 docs-index.md를 재생성한다.

INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // .tool_response.filePath // empty')
PROJECT_DIR="/Users/user/Library/Application Support/feather/player-server/servers/07de2d81-991a-47e2-b62d-06c0d1b5150a/plugins/Skript/scripts"

[[ "$FILE_PATH" =~ \.md$ ]] || exit 0
[[ "$(dirname "$FILE_PATH")" == "$PROJECT_DIR" ]] || exit 0
[[ "$(basename "$FILE_PATH")" == "docs-index.md" ]] && exit 0

cd "$PROJECT_DIR" && python3 gen_docs_index.py >/dev/null 2>&1 || true
exit 0
