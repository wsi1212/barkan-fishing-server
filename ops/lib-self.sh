# 심볼릭링크를 풀어 «스크립트 실체의 경로»를 준다. source 해서 쓴다.
#
# ## 왜 있나 (2026-08-31)
# 홈 진입점 4개를 ops/ 실체를 가리키는 심볼릭링크로 바꾼 뒤, `dirname "$0"` 과
# `dirname "${BASH_SOURCE[0]}"` 이 전부 **홈**을 가리키게 됐다. 그래서
# `~/deploy-blockship.sh` 로 배포하면 `$(dirname "$0")/sync-prod-staging.sh` 가
# `/Users/user/sync-prod-staging.sh` 를 찾아 없다고 실패했고 — **모든 배포가
# staging 동기화를 조용히 건너뛰었다**(06:00 데일리가 라이브를 낡은 jar 로 되돌릴 위험).
# 경고 한 줄만 찍고 배포는 계속되니 눈에 안 띄었다.
#
# 사용:
#   . "$(dirname "${BASH_SOURCE[0]}")/lib-self.sh" 2>/dev/null || true   # ← 이러면 안 된다(같은 함정)
#   ⇒ 각 스크립트는 아래 self_dir 을 «인라인»으로 갖는다. 이 파일은 그 원본이다.
self_real() {  # self_real <BASH_SOURCE[0] 또는 $0>
  local s="$1" link
  while [ -L "$s" ]; do
    link="$(readlink "$s")"
    case "$link" in /*) s="$link" ;; *) s="$(dirname "$s")/$link" ;; esac
  done
  printf '%s\n' "$s"
}
self_dir() { cd "$(dirname "$(self_real "$1")")" && pwd; }
