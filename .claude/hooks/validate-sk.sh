#!/bin/bash
# .sk 파일 컨벤션 검증 훅
# Edit/Write 후 자동 실행 — 위반 시 Claude에게 피드백

INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // .tool_response.filePath // empty')

# .sk 파일만 검증
if [[ ! "$FILE_PATH" =~ \.sk$ ]]; then
  exit 0
fi

if [ ! -f "$FILE_PATH" ]; then
  exit 0
fi

CONTENT=$(cat "$FILE_PATH")
WARNINGS=""

# 검사 1: 한글 명령어에 aliases(영타별칭) 있는지
while IFS= read -r line; do
  LINE_NUM=$(echo "$line" | cut -d: -f1)
  CMD=$(echo "$line" | sed 's/^[0-9]*://' | sed 's/command \(\/[^ ]*\).*/\1/' | xargs)
  # 다음 3줄에 aliases: 가 있는지
  HAS_ALIAS=$(sed -n "$((LINE_NUM+1)),$((LINE_NUM+3))p" "$FILE_PATH" | grep -c "aliases:")
  if [ "$HAS_ALIAS" -eq 0 ]; then
    WARNINGS="$WARNINGS\n[영타별칭 누락] $CMD (line $LINE_NUM)"
  fi
done < <(grep -n "^command /[가-힣]" "$FILE_PATH" 2>/dev/null)

# 검사 2: 인자 있는 명령어에 tab complete 있는지
while IFS= read -r line; do
  LINE_NUM=$(echo "$line" | cut -d: -f1)
  # 명령어 이름 추출 (첫 공백 또는 [ 전까지)
  CMD=$(echo "$line" | sed 's/^[0-9]*://' | sed 's/command *\(\/[^ []*\).*/\1/' | xargs)
  # on tab complete of "CMD" 가 파일에 있는지
  if ! grep -qF "on tab complete of \"$CMD\"" "$FILE_PATH"; then
    WARNINGS="$WARNINGS\n[탭완성 누락] $CMD (line $LINE_NUM)"
  fi
done < <(grep -n "^command /.*\[<" "$FILE_PATH" 2>/dev/null)

# 검사 3: player arg-N 버그 패턴
BAD=$(grep -n "player arg-" "$FILE_PATH" 2>/dev/null | head -3)
if [ -n "$BAD" ]; then
  WARNINGS="$WARNINGS\n[버그패턴] 'player arg-N' 감지 — loop all players 패턴 사용 필요"
fi

# 결과
if [ -n "$WARNINGS" ]; then
  echo -e "=== .sk 컨벤션 위반 ===$WARNINGS" >&2
  exit 2
fi

exit 0
