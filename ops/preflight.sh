#!/usr/bin/env bash
# 배포 게이트를 «배포하지 않고» 전부 돌린다 — 읽기전용 프리플라이트.
#
# ## 왜 있나 (2026-08-31)
# 게이트 10종을 deploy-blockship.sh 안에만 두면 **게이트를 확인하려면 배포를 해야 한다.**
# 그건 게이트 자체를 못 믿게 만든다(고치고 나서 검증하려고 prod 를 재시작할 수는 없다).
# 그래서 같은 검사를 부작용 없이 도는 입구를 따로 둔다. prod 는 «읽기만» 한다.
#
# 배포 스크립트와 검사 목록이 갈라지면 의미가 없으므로, 목록은 deploy-blockship.sh 에서
# 실제로 부르는 것과 같아야 한다 — ops/audit-copies.py 가 그 드리프트를 잡는 것과 같은 정신.
#
# 사용:  ops/preflight.sh            (게이트 전부, prod 대조 포함)
#        ops/preflight.sh --local    (prod 접속 없이 로컬 게이트만)
set -uo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BLOCKSHIP_DIR="${BLOCKSHIP_DIR:-$HOME/development/blockship-plugin}"
MIRROR="$REPO/ops/blockship-data"
DEV_DATA="/Users/user/Library/Application Support/feather/player-server/servers/07de2d81-991a-47e2-b62d-06c0d1b5150a/plugins/BlockShip"
REMOTE="ubuntu@168.107.8.107"
KEY="$HOME/.ssh/oracle-mc.key"
DATA_FILES=(npc.json dialogue.json titles.json parts.json enhance.json recipes.json materials.json quests.json fish.json item-flavor.json)
LOCAL_ONLY=0; [ "${1:-}" = "--local" ] && LOCAL_ONLY=1

PASS=0; FAIL=0
gate() {  # gate <이름> <명령...>
  local name="$1"; shift
  printf '\n▶ %s\n' "$name"
  if "$@" > /tmp/preflight-gate.log 2>&1; then
    tail -3 /tmp/preflight-gate.log | sed 's/^/    /'
    echo "  ✓ 통과"; PASS=$((PASS+1))
  else
    tail -8 /tmp/preflight-gate.log | sed 's/^/    /'
    echo "  ✗ 실패"; FAIL=$((FAIL+1))
  fi
}

echo "═══ 배포 프리플라이트 (부작용 없음) ═══"

gate "① 인스턴스 데이터 제외목록" \
  python3 "$REPO/ops/hooks/guard-instance-data.py" --check-list "${DATA_FILES[@]}"
gate "② 퀘스트 목표 id 대조" \
  python3 "$REPO/ops/audit-quest-goal-ids.py"
gate "③ 사본 드리프트" \
  python3 "$REPO/ops/audit-copies.py"
gate "④ 퀘스트·콘텐츠 진행 가능성" \
  python3 "$BLOCKSHIP_DIR/tools/quest_audit.py" --root "$BLOCKSHIP_DIR" \
    --runtime-dir "$MIRROR" --regions-dir "$DEV_DATA"
gate "⑤ 런타임 굵은 포맷" \
  python3 "$REPO/ops/verify-no-bold-format.py" "$BLOCKSHIP_DIR/src/main"
gate "⑥ 타임존 미지정 시간 API" \
  python3 "$REPO/ops/verify-no-naive-time.py" "$BLOCKSHIP_DIR/src/main"
gate "⑦ NPC·대사 정합성" \
  python3 "$REPO/ops/audit-dialogue.py" --dir "$MIRROR" --quiet

# ⑧ 빌드 출처 — 워크트리를 뜨면 정리까지 한다(부작용 남기지 않는다)
printf '\n▶ ⑧ 빌드 출처 (커밋된 트리인가)\n'
if GUARD="$("$REPO/ops/guard-build-source.sh" "$BLOCKSHIP_DIR" 2>&1 >/tmp/preflight-guard.env)"; then
  printf '%s\n' "$GUARD" | sed 's/^/  /'
  # shellcheck disable=SC1090
  . /tmp/preflight-guard.env
  if [ -n "${BUILD_WORKTREE:-}" ]; then
    git -C "$BLOCKSHIP_DIR" worktree remove --force "$BUILD_WORKTREE" >/dev/null 2>&1
    git -C "$BLOCKSHIP_DIR" worktree prune >/dev/null 2>&1
    echo "  · 프리플라이트가 뜬 임시 워크트리는 정리했다"
  fi
  echo "  ✓ 통과"; PASS=$((PASS+1))
else
  printf '%s\n' "$GUARD" | sed 's/^/  /'
  echo "  ✗ 실패"; FAIL=$((FAIL+1))
fi

if [ "$LOCAL_ONLY" = 1 ]; then
  printf '\n(--local: prod 대조 생략)\n'
else
  # ⑨ staged JSON 검증 — prod 사본을 받아 «올릴 파일 vs 지금 라이브» 를 대조한다(읽기만)
  printf '\n▶ ⑨ staged JSON 검증 (prod 라이브와 대조)\n'
  TMP="$(mktemp -d)"
  BAD=0
  for f in "${DATA_FILES[@]}"; do
    [ -f "$MIRROR/$f" ] || continue
    if ! scp -q -o BatchMode=yes -o ConnectTimeout=10 -i "$KEY" \
         "$REMOTE:~/mcserver/plugins/BlockShip/$f" "$TMP/$f" 2>/dev/null; then
      echo "  · $f prod 에 없음(신규)"; continue
    fi
    if OUT="$(python3 "$REPO/ops/validate-staged.py" "$MIRROR/$f" "$TMP/$f" 2>&1)"; then
      printf '  ✓ %s\n' "$f"
    else
      printf '  ⛔ %s — %s\n' "$f" "$(printf '%s' "$OUT" | head -1)"; BAD=$((BAD+1))
    fi
  done
  rm -rf "$TMP"
  if [ "$BAD" = 0 ]; then echo "  ✓ 통과"; PASS=$((PASS+1)); else echo "  ✗ 실패 $BAD 건"; FAIL=$((FAIL+1)); fi

  # ⑩ prod 가 지금 어느 커밋을 돌고 있나 — 로컬 HEAD 와 대조
  printf '\n▶ ⑩ prod 빌드 스탬프 대조\n'
  WANT="$(git -C "$BLOCKSHIP_DIR" rev-parse HEAD | cut -c1-12)"
  GOT="$(ssh -o BatchMode=yes -o ConnectTimeout=10 -i "$KEY" "$REMOTE" \
    "grep -o '\[Build\] commit=[0-9a-f]*' ~/mcserver/logs/latest.log | tail -1 | cut -d= -f2" 2>/dev/null || true)"
  DIRTY_TAG="$(ssh -o BatchMode=yes -o ConnectTimeout=10 -i "$KEY" "$REMOTE" \
    "grep -o '\[Build\] commit=[0-9a-f]* [a-z★]*' ~/mcserver/logs/latest.log | tail -1 | awk '{print \$NF}'" 2>/dev/null || true)"
  echo "  로컬 HEAD : $WANT"
  echo "  prod 라이브: ${GOT:-(스탬프 없음 — 구 jar)}  ${DIRTY_TAG:-}"
  if [ -z "$GOT" ]; then
    echo "  ⚠ prod 가 스탬프 없는 구 jar 을 돌고 있다"; FAIL=$((FAIL+1))
  elif [ "$GOT" = "$WANT" ]; then
    echo "  ✓ prod 가 로컬 HEAD 와 같은 커밋을 돌고 있다"; PASS=$((PASS+1))
  else
    BEHIND="$(git -C "$BLOCKSHIP_DIR" rev-list --count "$GOT..HEAD" 2>/dev/null || echo '?')"
    echo "  ⚠ 다름 — prod 가 로컬보다 $BEHIND 커밋 뒤처졌다(아직 배포 안 한 작업이 있다는 뜻)"
    PASS=$((PASS+1))   # 미배포 자체는 실패가 아니다. 사실만 알린다.
  fi
fi

printf '\n═══ 통과 %d / 실패 %d ═══\n' "$PASS" "$FAIL"
[ "$FAIL" = 0 ] || exit 1
