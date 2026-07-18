#!/bin/bash
# docs-index 자동 갱신 훅 — 프로젝트 최상위 .md 편집 시 gen_docs_index.py 재실행
# PostToolUse(Edit|Write)에서 실행. 비차단(항상 exit 0).

INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // .tool_response.filePath // empty')

# .md 파일만
[[ "$FILE_PATH" =~ \.md$ ]] || exit 0
# 프로젝트 최상위 직속 파일만 (하위 .claude/*.md·메모리 등 제외 — gen은 top-level만 스캔)
[[ "$(dirname "$FILE_PATH")" == "$CLAUDE_PROJECT_DIR" ]] || exit 0
# 인덱스 자체 편집은 무시 (재생성 불필요)
[[ "$(basename "$FILE_PATH")" == "docs-index.md" ]] && exit 0

cd "$CLAUDE_PROJECT_DIR" && python3 gen_docs_index.py >/dev/null 2>&1 || true
exit 0
