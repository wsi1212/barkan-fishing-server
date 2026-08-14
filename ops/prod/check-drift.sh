#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# 저장소 ↔ prod 스크립트 드리프트 검사
#
#   ops/prod/check-drift.sh          표로 출력, 다른 게 있으면 종료코드 1
#   ops/prod/check-drift.sh --quiet  다른 것만 출력
#
# 왜 필요한가 — 2026-08-14 실측 사고:
#   클라우드 세션이 즉시 배포(APPLY_NOW)를 저장소에 구현했는데 prod 사본은 낡은 채였다.
#   워크플로는 Release 본문에 마커를 박고 있었지만 prod 의 fetch-staging.sh 는 그 낱말을
#   모르므로 **에러 하나 없이** 06:00 배포로 되돌아갔다. "즉시 배포했다"고 믿은 jar 이
#   5시간 넘게 staging 에 앉아 있었다. 같은 계열의 함정이 이미 하나 있다 —
#   jar 만 올리고 재시작을 안 하는 것(CLAUDE.md). 공통점은 **고장이 조용하다**는 것이다.
#
#   그래서 배포 후 이 스크립트로 "올라갔는지"를 눈으로 확인한다. 특히 서로 물린 것들
#   (fetch-staging ↔ nightly-restart 의 --now)은 **함께** 올라가야 하고, 하나만 올리면
#   구 nightly 가 --now 를 모른 채 데일리 전체(무조건 재시작 + 리포트)를 돌 수 있다.
#
# 판정은 **내용 해시**다. mtime 은 못 믿는다(scp -p, 편집기 touch 로 흔들린다).
# ─────────────────────────────────────────────────────────────────────────────
set -uo pipefail

KEY="${KEY:-$HOME/.ssh/oracle-mc.key}"
PROD="${PROD:-ubuntu@168.107.8.107}"
QUIET=0
[[ "${1:-}" == "--quiet" ]] && QUIET=1

REPO_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT

ssh -o ConnectTimeout=20 -i "$KEY" "$PROD" \
  'cd ~/mcserver/scripts && shasum -a 256 *.sh *.py 2>/dev/null' > "$TMP/prod.txt" \
  || { echo "prod 해시 조회 실패 (SSH 확인)" >&2; exit 2; }

# 저장소 쪽 — **레포 전체**의 .sh/.py 를 basename 으로 색인.
# ★처음엔 ops/ 만 훑었는데 그게 버그였다: 같은 스크립트가 `oracle-ops-scripts/` 에도
#   미러로 있었고(텔레메트리 작업 때 만든 관행), 그걸 못 봐서 "prod 에만 있다"고 오판해
#   ops/prod/ 에 **세 번째 사본**을 만들었다(2026-08-15). 사본이 늘면 한쪽만 고쳐지는
#   날이 오고, 그게 바로 이 스크립트가 막으려는 고장이다. 그래서 전체를 훑고,
#   basename 이 겹치면 "모호"로 올려 사람이 보게 한다.
find "$REPO_ROOT" \
     -path '*/.git' -prune -o \
     -path '*/.claude/worktrees' -prune -o \
     -path '*/node_modules' -prune -o \
     -path '*/site-packages' -prune -o \
     -path '*/venv' -prune -o -path '*/.venv' -prune -o \
     -type f \( -name '*.sh' -o -name '*.py' \) -print0 \
  | xargs -0 shasum -a 256 > "$TMP/repo.txt"

QUIET=$QUIET python3 - "$TMP/prod.txt" "$TMP/repo.txt" "$REPO_ROOT" <<'PY'
import os, sys, collections
prod_f, repo_f, root = sys.argv[1], sys.argv[2], sys.argv[3]
quiet = os.environ.get("QUIET") == "1"

def load(p):
    out = []
    for ln in open(p, encoding="utf-8"):
        ln = ln.rstrip("\n")
        if "  " not in ln: continue
        h, path = ln.split("  ", 1)
        out.append((h, path.strip()))
    return out

prod = {os.path.basename(p): h for h, p in load(prod_f)}
repo = collections.defaultdict(list)
for h, p in load(repo_f):
    repo[os.path.basename(p)].append((h, os.path.relpath(p, root)))

same, diff, ambig = [], [], []
for name, h in sorted(prod.items()):
    cands = repo.get(name)
    if not cands:
        continue
    if len(cands) > 1:
        ambig.append((name, [c[1] for c in cands])); continue
    rh, rp = cands[0]
    (same if rh == h else diff).append((name, rp))

only_prod = sorted(n for n in prod if n not in repo)
only_repo = sorted(n for n in repo if n not in prod)

if diff:
    print("★ 저장소와 prod 가 다르다 — 배포 필요")
    for n, p in diff: print(f"   {n:26} ({p})")
if ambig:
    print("★ basename 중복 — 어느 것이 prod 로 갔는지 판정 불가")
    for n, ps in ambig: print(f"   {n:26} {ps}")
if only_prod:
    print("★ prod 에만 있다 — git 에 없으므로 박스가 죽으면 소실된다")
    for n in only_prod: print(f"   {n}")
if not quiet:
    if same:
        print(f"일치 {len(same)}건: " + ", ".join(n for n, _ in same))
    # ★"저장소에만" 은 목록으로 찍지 않는다. 맥 전용 도구·픽셀아트 스크립트·벤더링된
    #   파이썬 패키지까지 다 걸려서 783건이 나오고(실측), 그 노이즈가 위의 진짜 경고를
    #   화면 밖으로 밀어낸다. 개수만 남긴다 — 이 스크립트가 답할 질문은
    #   "prod 에 있는 것이 저장소와 같은가" 이지 "저장소에 무엇이 더 있나" 가 아니다.
    if only_repo:
        print(f"(저장소에만 있는 것 {len(only_repo)}건 — 맥 전용 도구 등, 정상)")

bad = bool(diff or ambig or only_prod)
print("\n판정:", "★조치 필요" if bad else "드리프트 없음")
sys.exit(1 if bad else 0)
PY
