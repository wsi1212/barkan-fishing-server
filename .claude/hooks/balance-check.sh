#!/bin/bash
# 밸런스 관련 변경 감지 훅
# .sk 또는 balance.md 수정 시:
# 1) 변경된 스탯/밸런스 키워드 감지
# 2) 해당 스탯을 읽는 곳 (소비처) + 부여하는 곳 (공급처) 모두 제시
# 3) balance.md 기준 적절성 검토 요청

INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // .tool_response.filePath // empty')

# .sk 또는 balance.md만 검증
if [[ ! "$FILE_PATH" =~ \.sk$ ]] && [[ ! "$FILE_PATH" =~ balance\.md$ ]]; then
  exit 0
fi

if [ ! -f "$FILE_PATH" ]; then
  exit 0
fi

SCRIPT_DIR=$(dirname "$FILE_PATH")
# balance.md가 다른 디렉토리에 있을 수 있으므로 보정
if [[ "$FILE_PATH" =~ balance\.md$ ]]; then
  SCRIPT_DIR=$(dirname "$FILE_PATH")
fi

HINTS=""

# ===== 스탯 키워드 =====
# 소비처 키워드 (스탯을 읽어서 효과를 적용하는 곳 — 변수/함수명 패턴)
CONSUME_KEYWORDS="물고기난이도|물고기크기난이도|미니게임파라미터|강화스탯적용|존폭|zoneWidth|barWidth|spotMoveInterval|fractionalPos|낚싯대보너스|_net|escapeBase|escapeInc|도망확률감소|크리티컬확률|크리티컬데미지|등급시프트|경험치보너스|크기보너스|더블찬스|트리플찬스|판매보너스|내구보존"

# 공급처 키워드 (스탯을 부여/저장하는 곳)
SUPPLY_KEYWORDS="강화테이블|부품::|축복::|도핑데이터|낚싯대강화난이도|낚싯대강화크기|낚싯대강화등급업|낚싯대강화크리확률|낚싯대강화경험치|낚싯대강화더블|낚싯대강화트리플|낚싯대강화판매|낚싯대강화내구|플레이어축복"

# 스탯 이름 키워드 (변수/데이터 패턴만 — UI 텍스트 오탐 방지)
# 앞뒤에 코드 맥락이 있는 패턴: {_난이도}, 난이도:, "난이도" 등
STAT_KEYWORDS="난이도:|도망감소:|크리배율:|등급업:|경험치:|크기:|크리확률:|더블찬스:|트리플찬스:|내구보존:|판매보너스:|_난이도|_도망감소|_크리배율|_등급업|_경험치보너스|_크기보너스|_크리확률|_더블찬스|_트리플찬스|_내구보존|_판매보너스"

# ===== 변경 내용 추출 =====
DIFF=""
if command -v git &>/dev/null; then
  DIFF=$(cd "$SCRIPT_DIR" && git diff -- "$FILE_PATH" 2>/dev/null | grep "^+" | grep -v "^+++" | head -80)
fi

if [ -z "$DIFF" ]; then
  DIFF=$(cat "$FILE_PATH")
fi

# ===== 매칭 =====
STAT_MATCH=$(echo "$DIFF" | grep -oE "$STAT_KEYWORDS" | sort -u | tr '\n' ', ' | sed 's/,$//')
CONSUME_MATCH=$(echo "$DIFF" | grep -oE "$CONSUME_KEYWORDS" | sort -u | tr '\n' ', ' | sed 's/,$//')
SUPPLY_MATCH=$(echo "$DIFF" | grep -oE "$SUPPLY_KEYWORDS" | sort -u | tr '\n' ', ' | sed 's/,$//')

# 아무것도 안 걸리면 종료
if [ -z "$STAT_MATCH" ] && [ -z "$CONSUME_MATCH" ] && [ -z "$SUPPLY_MATCH" ]; then
  exit 0
fi

# ===== 영향받는 파일 찾기 =====
# 소비처 파일 (이 스탯을 읽어서 효과를 적용하는 파일)
CONSUMER_FILES=""
# 공급처 파일 (이 스탯을 부여/생성하는 파일)
SUPPLIER_FILES=""

ALL_KEYWORDS="$STAT_MATCH"
for KEYWORD in $(echo "$ALL_KEYWORDS" | tr ',' ' '); do
  KEYWORD=$(echo "$KEYWORD" | xargs)
  if [ -z "$KEYWORD" ]; then
    continue
  fi
  # 소비처: 스탯을 변수로 읽는 파일
  MATCHES=$(grep -rl "{_${KEYWORD}}" "$SCRIPT_DIR"/*.sk 2>/dev/null | grep -v "$FILE_PATH" | xargs -I{} basename {} 2>/dev/null | sort -u)
  if [ -n "$MATCHES" ]; then
    CONSUMER_FILES="$CONSUMER_FILES $MATCHES"
  fi
  # 공급처: 스탯을 데이터로 정의하는 파일 (부품, 강화, 축복, 도핑)
  MATCHES=$(grep -rl "\"$KEYWORD:" "$SCRIPT_DIR"/*.sk 2>/dev/null | grep -v "$FILE_PATH" | xargs -I{} basename {} 2>/dev/null | sort -u)
  if [ -n "$MATCHES" ]; then
    SUPPLIER_FILES="$SUPPLIER_FILES $MATCHES"
  fi
  # 글로벌 변수로 저장하는 파일
  MATCHES=$(grep -rl "{낚싯대강화${KEYWORD}" "$SCRIPT_DIR"/*.sk 2>/dev/null | grep -v "$FILE_PATH" | xargs -I{} basename {} 2>/dev/null | sort -u)
  if [ -n "$MATCHES" ]; then
    SUPPLIER_FILES="$SUPPLIER_FILES $MATCHES"
  fi
done

CONSUMER_FILES=$(echo "$CONSUMER_FILES" | tr ' ' '\n' | sort -u | grep -v "^$" | tr '\n' ', ' | sed 's/,$//')
SUPPLIER_FILES=$(echo "$SUPPLIER_FILES" | tr ' ' '\n' | sort -u | grep -v "^$" | tr '\n' ', ' | sed 's/,$//')

# ===== 힌트 구성 =====
HINTS="[밸런스 변경 감지] 영향 스탯: $STAT_MATCH"

if [ -n "$CONSUME_MATCH" ]; then
  HINTS="$HINTS | 변경된 소비 로직: $CONSUME_MATCH"
fi
if [ -n "$SUPPLY_MATCH" ]; then
  HINTS="$HINTS | 변경된 공급 데이터: $SUPPLY_MATCH"
fi
if [ -n "$CONSUMER_FILES" ]; then
  HINTS="$HINTS | 소비처(읽는곳): $CONSUMER_FILES"
fi
if [ -n "$SUPPLIER_FILES" ]; then
  HINTS="$HINTS | 공급처(부여하는곳): $SUPPLIER_FILES"
fi

HINTS="$HINTS | 검토사항: (1) balance.md 수치와 일치하는지 (2) 공급처(부품/강화/축복/도핑)에서 이 스탯을 올바르게 부여하는지 (3) 소비처(낚시/스탯GUI/판매 등)에서 올바르게 읽는지 (4) 이름 변경/삭제 시 잔재가 남아있지 않은지"

ESCAPED=$(echo "$HINTS" | sed 's/"/\\"/g' | tr '\n' ' ')
echo "{\"hookSpecificOutput\":{\"hookEventName\":\"PostToolUse\",\"additionalContext\":\"$ESCAPED\"}}"
exit 0
