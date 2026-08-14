#!/bin/bash
# 최상위 설계 문서가 변경되면 docs-index.md를 재생성한다.
#
# 경로는 하드코딩하지 않는다 — 이 스크립트의 위치에서 리포 루트를 역산한다
# (.codex/hooks/ 에 있으므로 두 단계 위). 맥의 Skript/scripts 경로든 다른
# 머신의 클론이든 그대로 돈다. 훅은 비차단(항상 exit 0)이라 경로가 틀려도
# 아무 경고 없이 조용히 죽으므로, 애초에 틀릴 수 없게 만든다.

INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // .tool_response.filePath // empty')

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

[[ "$FILE_PATH" =~ \.md$ ]] || exit 0
[[ "$(dirname "$FILE_PATH")" == "$PROJECT_DIR" ]] || exit 0
[[ "$(basename "$FILE_PATH")" == "docs-index.md" ]] && exit 0

cd "$PROJECT_DIR" && python3 gen_docs_index.py >/dev/null 2>&1 || true
exit 0
