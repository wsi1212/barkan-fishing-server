#!/usr/bin/env bash
# prod 로 나갈 jar 이 «커밋된 트리»에서 빌드되는지 강제한다.
#
# ## 왜 있나 (2026-08-31)
# 「prod 는 커밋된 소스에서 빌드한다」는 규칙이 CLAUDE.md 와 메모리에만 있었고, 지키는 건
# 사람 손이었다. 실제로 두 방향 모두 사고가 났다:
#
#  ① **미커밋이 실려 나간다** — 2026-08-11, 커밋 안 된 작업 트리에서 빌드된 jar 이 올라가
#     접속/퇴장 메시지·HUD·설정GUI·휴지통·디스코드 명령이 통째로 사라졌다.
#  ② **커밋된 게 빠진다** — 2026-08-31, 다른 세션이 «낡은 체크아웃»에서 빌드해 prod jar 의
#     mtime 은 최신인데 통발·미끼·심해작살·팁 4개 기능이 라이브에 없었다. mtime 으로는
#     판별 불가라 jar 을 내려받아 javap 으로 중첩클래스를 뒤져야 알았다.
#
# 그래서 사람의 주의력이 아니라 게이트로 만든다. 세 가지를 본다:
#   1) 작업 트리가 더러우면 → **HEAD 워크트리를 자동으로 떠서** 그걸 빌드하게 한다
#      (지금까지는 세션마다 손으로 `git worktree add` 했다. 그 수고가 규칙을 안 지키는 이유였다.)
#   2) HEAD 가 upstream 보다 뒤처졌으면 → 거부. 남이 푸시한 커밋이 prod 에서 되돌아간다.
#   3) 빌드 스탬프(jar 안 build-stamp.properties)의 commit 이 HEAD 와 같은지 → 배포 후 대조용.
#
# 사용:  eval "$(ops/guard-build-source.sh <소스트리>)"
#        → BUILD_DIR / BUILD_COMMIT / BUILD_WORKTREE(임시면 경로) 를 내보낸다.
#        호출자는 끝나고 BUILD_WORKTREE 가 비어있지 않으면 정리해야 한다.
# 탈출구: ALLOW_DIRTY_BUILD=1 (더러운 트리를 그대로 빌드 — 긴급용, prod 에 쓰지 말 것)
#         ALLOW_BEHIND_UPSTREAM=1 (뒤처진 HEAD 를 그대로 빌드)
set -uo pipefail

SRC="${1:?사용: guard-build-source.sh <소스트리>}"
say() { printf '%s\n' "$1" >&2; }

if ! git -C "$SRC" rev-parse --git-dir >/dev/null 2>&1; then
  say "⚠️  $SRC 는 git 트리가 아니다 — 빌드 출처를 보증할 수 없다"
  printf 'BUILD_DIR=%q\nBUILD_COMMIT=unknown\nBUILD_WORKTREE=\n' "$SRC"
  exit 0
fi

HEAD_SHA="$(git -C "$SRC" rev-parse HEAD)"
DIRTY="$(git -C "$SRC" status --porcelain)"

# ── 2) upstream 보다 뒤처졌는가 ────────────────────────────────────────
UPSTREAM="$(git -C "$SRC" rev-parse --abbrev-ref '@{upstream}' 2>/dev/null || true)"
if [ -n "$UPSTREAM" ]; then
  BEHIND="$(git -C "$SRC" rev-list --count "HEAD..$UPSTREAM" 2>/dev/null || echo 0)"
  if [ "${BEHIND:-0}" -gt 0 ]; then
    if [ -n "${ALLOW_BEHIND_UPSTREAM:-}" ]; then
      say "⚠️  HEAD 가 $UPSTREAM 보다 $BEHIND 커밋 뒤처졌다 — ALLOW_BEHIND_UPSTREAM=1 로 통과"
    else
      say ""
      say "❌ HEAD 가 $UPSTREAM 보다 $BEHIND 커밋 뒤처졌습니다."
      say "   이대로 배포하면 남이 푸시한 커밋이 **prod 에서 되돌아갑니다.**"
      say "   먼저:  git -C \"$SRC\" pull --no-rebase   (충돌 나면 해소 후 빌드 확인)"
      say "   정말 의도한 것이면 ALLOW_BEHIND_UPSTREAM=1"
      exit 1
    fi
  fi
fi

# ── 1) 더러우면 HEAD 워크트리를 떠서 거기서 빌드 ──────────────────────
if [ -z "$DIRTY" ]; then
  say "  ✓ 빌드 출처: 커밋된 트리 ${HEAD_SHA:0:12} (미커밋 0)"
  printf 'BUILD_DIR=%q\nBUILD_COMMIT=%q\nBUILD_WORKTREE=\n' "$SRC" "$HEAD_SHA"
  exit 0
fi

N_DIRTY="$(printf '%s\n' "$DIRTY" | wc -l | tr -d ' ')"
if [ -n "${ALLOW_DIRTY_BUILD:-}" ]; then
  say "  ⚠️  미커밋 $N_DIRTY 개를 실어서 빌드한다 (ALLOW_DIRTY_BUILD=1) — prod 에서는 재현 불가능해진다"
  printf 'BUILD_DIR=%q\nBUILD_COMMIT=%q-dirty\nBUILD_WORKTREE=\n' "$SRC" "$HEAD_SHA"
  exit 0
fi

WT="$(mktemp -d "${TMPDIR:-/tmp}/bs-head-XXXXXX")"
rmdir "$WT"
if ! git -C "$SRC" worktree add --detach --quiet "$WT" HEAD 2>/dev/null; then
  say "❌ HEAD 워크트리 생성 실패: $WT"
  exit 1
fi
say "  ✓ 미커밋 $N_DIRTY 개가 있어 **HEAD 워크트리에서 빌드**한다 (${HEAD_SHA:0:12})"
say "     제외된 파일:"
printf '%s\n' "$DIRTY" | sed 's/^/       /' >&2
say "     ★이 파일들은 prod 에 안 나갑니다. 나가야 하는 것이면 커밋하고 다시 실행하세요."
printf 'BUILD_DIR=%q\nBUILD_COMMIT=%q\nBUILD_WORKTREE=%q\n' "$WT" "$HEAD_SHA" "$WT"
