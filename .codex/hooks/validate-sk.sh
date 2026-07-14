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
ERRORS=""
WARNINGS=""

# 검사 1: 한글 명령어에 aliases(영타별칭) 있는지 (OP 명령어 제외)
while IFS= read -r line; do
  LINE_NUM=$(echo "$line" | cut -d: -f1)
  CMD=$(echo "$line" | sed 's/^[0-9]*://' | sed 's/command \(\/[^ ]*\).*/\1/' | xargs)
  # 다음 5줄에 permission: op 가 있으면 OP 명령어 → 영타별칭 불필요
  IS_OP=$(sed -n "$((LINE_NUM+1)),$((LINE_NUM+5))p" "$FILE_PATH" | grep -c "permission: op")
  if [ "$IS_OP" -gt 0 ]; then
    continue
  fi
  # 다음 3줄에 aliases: 가 있는지
  HAS_ALIAS=$(sed -n "$((LINE_NUM+1)),$((LINE_NUM+3))p" "$FILE_PATH" | grep -c "aliases:")
  if [ "$HAS_ALIAS" -eq 0 ]; then
    ERRORS="$ERRORS\n[영타별칭 누락] $CMD (line $LINE_NUM)"
  fi
done < <(grep -n "^command /[가-힣]" "$FILE_PATH" 2>/dev/null)

# 검사 2: 인자 있는 명령어에 tab complete 있는지 (OP 명령어 제외)
while IFS= read -r line; do
  LINE_NUM=$(echo "$line" | cut -d: -f1)
  CMD=$(echo "$line" | sed 's/^[0-9]*://' | sed 's/command *\(\/[^ []*\).*/\1/' | xargs)
  # OP 명령어면 스킵
  IS_OP=$(sed -n "$((LINE_NUM+1)),$((LINE_NUM+5))p" "$FILE_PATH" | grep -c "permission: op")
  if [ "$IS_OP" -gt 0 ]; then
    continue
  fi
  # on tab complete of "CMD" 가 파일에 있는지
  if ! grep -qF "on tab complete of \"$CMD\"" "$FILE_PATH"; then
    ERRORS="$ERRORS\n[탭완성 누락] $CMD (line $LINE_NUM)"
  fi
done < <(grep -n "^command /.*\[<" "$FILE_PATH" 2>/dev/null)

# 검사 3: player arg-N 버그 패턴 (Skript에서 이름으로 플레이어 못 가져옴)
BAD=$(grep -n "player arg-" "$FILE_PATH" 2>/dev/null | head -3)
if [ -n "$BAD" ]; then
  ERRORS="$ERRORS\n[버그] 'player arg-N' — loop all players로 이름 매칭 필요"
fi

# 검사 4: play sound ... with volume X with pitch Y (with 중복 → and pitch Y)
BAD=$(grep -n "with volume.*with pitch" "$FILE_PATH" 2>/dev/null | head -3)
if [ -n "$BAD" ]; then
  ERRORS="$ERRORS\n[버그] 'with volume X with pitch Y' → 'with volume X and pitch Y'로 수정 필요"
fi

# 검사 4b: else if ... contains "X" or ... contains "Y" (Skript 파싱 실패 → 분리 필요)
BAD=$(grep -n 'else if.*contains.*or.*contains' "$FILE_PATH" 2>/dev/null | head -3)
if [ -n "$BAD" ]; then
  ERRORS="$ERRORS\n[버그] 'else if A contains X or B contains Y' — Skript에서 파싱 실패, 별도 else if로 분리 필요\n$BAD"
fi

# 검사 5: on inventory close 블록 안에서 player's current inventory 사용 (닫힌 뒤라 읽을 수 없음)
# on inventory close 행 번호 ~ 다음 빈 행(또는 다음 on/command) 사이에 player's current inventory가 있는지 확인
while IFS= read -r line; do
  CLOSE_LINE=$(echo "$line" | cut -d: -f1)
  # 블록 끝 찾기: 다음 on/command 또는 파일 끝
  NEXT_BLOCK=$(tail -n "+$((CLOSE_LINE+1))" "$FILE_PATH" | grep -n "^on \|^command " | head -1 | cut -d: -f1)
  if [ -n "$NEXT_BLOCK" ]; then
    END_LINE=$((CLOSE_LINE + NEXT_BLOCK - 1))
  else
    END_LINE=$(wc -l < "$FILE_PATH")
  fi
  BAD=$(sed -n "${CLOSE_LINE},${END_LINE}p" "$FILE_PATH" | grep -n "player's current inventory" | head -3)
  if [ -n "$BAD" ]; then
    WARNINGS="$WARNINGS\n[주의] on inventory close 블록(line $CLOSE_LINE) 안에서 'player's current inventory' 사용 — event-inventory 사용 권장"
  fi
done < <(grep -n "^on inventory close" "$FILE_PATH" 2>/dev/null)

# 검사 6: loop 중첩에서 loop-value 사용 (내부 루프는 loop-value-2 필요)
# loop X times + loop {list::*} 패턴
if grep -qP "loop .* times:" "$FILE_PATH" 2>/dev/null; then
  if grep -qP "loop \{.*::\*\}" "$FILE_PATH" 2>/dev/null; then
    # 중첩 루프가 있고 loop-value만 사용하면 경고
    INNER_LV=$(grep -n "loop-value[^-]" "$FILE_PATH" 2>/dev/null | grep -v "loop-value-2" | head -3)
    if [ -n "$INNER_LV" ]; then
      WARNINGS="$WARNINGS\n[주의] 중첩 루프에서 'loop-value' 감지 — 내부 루프는 'loop-value-2' 필요할 수 있음 (확인 필요)"
    fi
  fi
fi

# 검사 7: all players' names (작동 안 함 → names of all players)
BAD=$(grep -n "all players' names" "$FILE_PATH" 2>/dev/null | head -3)
if [ -n "$BAD" ]; then
  ERRORS="$ERRORS\n[버그] 'all players' names' → 'names of all players'로 수정 필요"
fi

# 검사 8: function 안에서 player 키워드 사용 (함수 파라미터 사용해야 함)
# "player can hold" 패턴을 function 안에서 사용하면 위험
while IFS= read -r line; do
  LINE_NUM=$(echo "$line" | cut -d: -f1)
  # 이 라인이 function 블록 안인지 체크 (위로 function 선언 찾기)
  FUNC_LINE=$(head -n "$LINE_NUM" "$FILE_PATH" | grep -n "^function " | tail -1 | cut -d: -f1)
  if [ -n "$FUNC_LINE" ]; then
    WARNINGS="$WARNINGS\n[주의] function 안에서 'player can hold' 사용 (line $LINE_NUM) — 함수 파라미터 사용 권장"
  fi
done < <(grep -n "player can hold" "$FILE_PATH" 2>/dev/null | head -3)

# 검사 9: if tab arg 조건문 (작동 안 함, 직접 set tab completions 사용)
BAD=$(grep -n "if tab arg" "$FILE_PATH" 2>/dev/null | head -3)
if [ -n "$BAD" ]; then
  ERRORS="$ERRORS\n[버그] 'if tab arg' 조건 — 작동하지 않음, 직접 set tab completions 사용 필요"
fi

# 검사 10: clicked item 사용 (Skript 2.13.2에서 작동 안 함 → event-item 사용)
BAD=$(grep -n "clicked item" "$FILE_PATH" 2>/dev/null | head -3)
if [ -n "$BAD" ]; then
  ERRORS="$ERRORS\n[버그] 'clicked item' — Skript 2.13.2에서 미지원, 'event-item' 사용 필요"
fi

# 검사 11: replace ... in loop-value (loop-value는 읽기 전용, 로컬 변수에 복사 후 replace)
BAD=$(grep -n "replace.*in loop-value" "$FILE_PATH" 2>/dev/null | head -3)
if [ -n "$BAD" ]; then
  ERRORS="$ERRORS\n[버그] 'replace in loop-value' — loop-value는 읽기 전용, 로컬 변수에 복사 후 replace 필요"
fi

# 결과
if [ -n "$ERRORS" ]; then
  # 에러 → 차단 (exit 2)
  MSG="=== .sk 컨벤션 위반 (차단) ===$ERRORS"
  if [ -n "$WARNINGS" ]; then
    MSG="$MSG\n\n=== 경고 (참고) ===$WARNINGS"
  fi
  echo -e "$MSG" >&2
  exit 2
fi

if [ -n "$WARNINGS" ]; then
  # 경고만 → 통과하되 피드백 (exit 0 + JSON)
  ESCAPED=$(echo -e "$WARNINGS" | sed 's/"/\\"/g' | tr '\n' ' ')
  echo "{\"hookSpecificOutput\":{\"hookEventName\":\"PostToolUse\",\"additionalContext\":\"[.sk 경고] $ESCAPED\"}}"
  exit 0
fi

exit 0
