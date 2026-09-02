#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# BetterHud 정의·자산을 prod 스테이징에 올린다 (재시작 없음)
#
#   ./stage-prod.sh                  변경분만 스테이징 → 06:00 데일리 유지보수에 자동 적용
#   ./stage-prod.sh --dry-run        무엇이 올라갈지만 보여준다(전송 없음)
#   ./stage-prod.sh --with-dialogue  대화창 «정의» yml 까지 올린다(아래 ★ 참고)
#
# deploy-prod.sh 와의 차이: 저쪽은 지금 당장 배포하며 재시작을 두 번 한다. 이쪽은
# 파일만 올려두고 아무것도 건드리지 않는다. 적용은 prod 의 apply-betterhud-staging.sh
# 가 06:00 재시작 창에서 «재시작 전 교체 → 재시작 → 팩 재생성 → 공개배치 → sha1 →
# 마무리 재시작» 순으로 처리한다. 그래서 낮에 올려두면 맥이 꺼져 있어도 반영된다.
#
# ★대화창 정의(npc-dialogue-{hud,layout,image}.yml)는 기본적으로 안 올린다.
#   NPC별 초상화 1160벌이 들어 있어서, 낡은 로컬 사본이 올라가면 라이브가 통째로
#   되돌아간다. 실제로 그 파일들을 덮을 뻔한 적이 있어 deploy-prod.sh 도 같은 가드를
#   갖고 있다. 정말 정의를 바꿨을 때만 --with-dialogue 로 명시할 것.
#   (초상화 «그림»만 바꿨다면 정의는 안 바뀌므로 플래그가 필요 없다.)
#
# ★변경분만 보낸다 — assets/dialogue 만 21MB/1457개다. 전체를 매번 올리면 느리고,
#   apply 쪽에서 «무엇이 바뀌었는지» 판단할 근거도 사라진다.
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

SRC="$(cd "$(dirname "$0")" && pwd)"
KEY="${KEY:-$HOME/.ssh/oracle-mc.key}"
PROD="${PROD:-ubuntu@168.107.8.107}"
SSHC=(ssh -o ConnectTimeout=20 -i "$KEY" "$PROD")
REMOTE_BH='~/mcserver/plugins/BetterHud'
REMOTE_STAGE='~/mcserver/staging/betterhud'

DRY=0; WITH_DIALOGUE=0
for a in "$@"; do
  case "$a" in
    --dry-run) DRY=1 ;;
    --with-dialogue) WITH_DIALOGUE=1 ;;
    -h|--help) sed -n '2,26p' "$0" | sed 's/^# \?//'; exit 0 ;;
    *) echo "알 수 없는 인자: $a" >&2; exit 2 ;;
  esac
done

say() { echo; echo "── $* ──"; }
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT

say "0) 보내기 전 검사"
# 폰트 yml 이 가리키는 TTF 가 실제로 있는지. 없으면 BetterHud 가 폰트를 못 구워
# 판 글자가 통째로 사라진다(2026-08-21 dev 가 이 상태였고 검증 grep 이 옛 파일명을
# 보고 있어 아무도 못 봤다).
while read -r f; do
  [ -n "$f" ] || continue
  [ -f "$SRC/assets/fonts/$f" ] || { echo "❌ assets/fonts/$f 가 없다 — build_hud_font.py 를 먼저 돌릴 것" >&2; exit 1; }
done < <(grep -E '^ *file: *' "$SRC/npc-dialogue-font.yml" | sed 's/.*file: *//')
grep -qE '^ *use-unifont: *false' "$SRC/npc-dialogue-font.yml" \
  || { echo "❌ use-unifont 가 true 다 — 한글이 유니폰트로 바뀐다" >&2; exit 1; }
echo "  폰트 정의 OK"

# prod 에 적용기가 깔려 있나. 없으면 올려도 06:00 에 아무 일도 안 일어난다(조용한 고장).
"${SSHC[@]}" 'test -x ~/mcserver/scripts/apply-betterhud-staging.sh' \
  || { echo "❌ prod 에 apply-betterhud-staging.sh 가 없다 — 먼저 배포할 것:
   scp -i $KEY $SRC/../apply-betterhud-staging.sh $PROD:~/mcserver/scripts/ && ssh ... chmod +x" >&2; exit 1; }
echo "  prod 적용기 존재 확인"

say "1) 로컬 ↔ prod 해시 대조"
DEFS=$(cd "$SRC" && ls status-*.yml place-*.yml buff-*.yml npc-dialogue-font.yml 2>/dev/null || true)
if [ "$WITH_DIALOGUE" = 1 ]; then
  DEFS="$DEFS $(cd "$SRC" && ls npc-dialogue-hud.yml npc-dialogue-layout.yml npc-dialogue-image.yml 2>/dev/null || true)"
fi
( cd "$SRC" && find assets/status assets/fonts assets/dialogue -type f ! -name '._*' ! -name '.DS_Store' 2>/dev/null \
    | sort > "$TMP/assetlist" )
# 공백 있는 파일명은 목록 기반 전송에서 조용히 깨진다 — 있으면 멈춘다.
if grep -q ' ' "$TMP/assetlist"; then echo "❌ 파일명에 공백이 있다:"; grep ' ' "$TMP/assetlist"; exit 1; fi
( cd "$SRC" && shasum -a 1 $DEFS $(cat "$TMP/assetlist") 2>/dev/null ) \
  | awk '{print $1" "$2}' | sort -k2 > "$TMP/local.txt"

"${SSHC[@]}" "cd $REMOTE_BH && { sha1sum huds/*.yml layouts/*.yml images/*.yml texts/*.yml 2>/dev/null;
  find assets/status assets/fonts assets/dialogue -type f 2>/dev/null | xargs -r sha1sum 2>/dev/null; }" \
  | sed -E 's#^([0-9a-f]{40})  (huds|layouts|images|texts)/#\1  #' \
  | awk '{print $1" "$2}' | sort -k2 > "$TMP/prod.txt"

awk 'NR==FNR{p[$2]=$1;next} p[$2]!=$1 {print $2}' "$TMP/prod.txt" "$TMP/local.txt" | sort > "$TMP/changed"
CNT=$(grep -c . "$TMP/changed" || true)
echo "  로컬 $(grep -c . "$TMP/local.txt")개 / prod $(grep -c . "$TMP/prod.txt")개 → 변경 ${CNT}개"

if [ "$CNT" = 0 ]; then echo; echo "✅ prod 와 동일하다 — 올릴 것이 없다."; exit 0; fi

# 정의 yml 이 섞였는지(=좌표표·글리프가 바뀌는 변경) 표시. apply 쪽도 같은 판정을 해서
# 필요하면 셰이더 좌표표를 다시 뽑는다.
DEFCHG=$(grep -E '^(npc-dialogue-(hud|layout|image)|status-|place-|buff-).*\.yml$' "$TMP/changed" || true)
sed 's/^/   /' "$TMP/changed" | head -25
[ "$CNT" -gt 25 ] && echo "   … 외 $((CNT-25))개"
[ -n "$DEFCHG" ] && { echo; echo "  ★정의 변경 포함 — 적용 시 셰이더 좌표표도 다시 뽑힌다:"; printf '   %s\n' $DEFCHG; }

if [ "$DRY" = 1 ]; then echo; echo "(dry-run — 전송 없음)"; exit 0; fi

say "2) 스테이징 전송 (재시작·적용 안 함)"
# ★COPYFILE_DISABLE=1 필수 — macOS 가 ._ AppleDouble 을 끼워넣고, 그게 assets/ 에
#   들어가면 BetterHud 가 이미지로 읽으려다 폰트가 깨진다.
# --no-xattrs: macOS 가 붙이는 com.apple.provenance 확장속성이 GNU tar 쪽에서
#   "Ignoring unknown extended header keyword" 경고를 파일마다 한 줄씩 뱉는다(무해하지만
#   1000개 파일이면 진짜 오류가 그 속에 묻힌다).
COPYFILE_DISABLE=1 tar cz --no-xattrs -C "$SRC" -T "$TMP/changed" \
  | "${SSHC[@]}" "rm -rf $REMOTE_STAGE && mkdir -p $REMOTE_STAGE && tar xz -C $REMOTE_STAGE"
"${SSHC[@]}" "find $REMOTE_STAGE -name '._*' -delete 2>/dev/null; find $REMOTE_STAGE -type f | wc -l | sed 's/^/  올라간 파일 /'"

git -C "$SRC" rev-parse --short HEAD 2>/dev/null | sed 's/^/  소스 커밋 /' || true
echo
echo "✅ 스테이징 완료. 06:00 KST 데일리 유지보수에서 자동 적용된다."
echo "   지금 당장 반영하려면(재시작 2회):  $SRC/deploy-prod.sh --with-dialogue"
echo "   대기 상태 확인:  ssh … 'ls ~/mcserver/staging/betterhud'"
