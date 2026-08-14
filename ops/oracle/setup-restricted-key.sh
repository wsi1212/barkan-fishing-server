#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# 제한 SSH 키 설치 — 롤백·진단만 가능한 키를 authorized_keys 에 등록한다.
#
# ★prod 에서 실행한다. 맥에서라면:
#     scp ops/oracle/{ssh-restricted-shim.sh,setup-restricted-key.sh} prod:~/mcserver/scripts/
#     ssh prod '~/mcserver/scripts/setup-restricted-key.sh ~/restricted_key.pub'
#
# ## 이 키로 할 수 있는 것 (ssh-restricted-shim.sh 의 화이트리스트)
#     rollback list | dry | yes [to <파일>]      log [N]      ops [N]      status
# ## 할 수 없는 것
#     임의 명령 · 셸 · 파일 쓰기 · sudo · 포트포워딩 · 백업/월드 삭제
#
# ## 왜 기존 oracle-mc.key 를 쓰면 안 되나
#   그 키는 맥에서 배포·백업·전부에 쓰는 만능 키다. 유출·오용이 의심돼 폐기하면
#   맥 접속까지 같이 끊긴다. 별도 키여야 **이것만** 조용히 폐기할 수 있다.
#
# 사용:
#   setup-restricted-key.sh <공개키파일>          등록
#   setup-restricted-key.sh --show                현재 등록된 제한 키 보기
#   setup-restricted-key.sh --revoke              제한 키만 제거 (다른 키는 안 건드림)
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

MC_ROOT="${MC_ROOT:-$HOME/mcserver}"
SHIM="$MC_ROOT/scripts/ssh-restricted-shim.sh"
AUTH="$HOME/.ssh/authorized_keys"
MARK="barkan-restricted"   # 이 주석으로 우리 줄을 찾는다(다른 키를 건드리지 않으려고)

show()   { grep -n "$MARK" "$AUTH" 2>/dev/null || echo "(등록된 제한 키 없음)"; }
revoke() {
  [[ -f "$AUTH" ]] || { echo "authorized_keys 가 없다"; exit 0; }
  cp -f "$AUTH" "$AUTH.bak-$(date -u +%Y%m%d-%H%M%S)"
  grep -v "$MARK" "$AUTH" > "$AUTH.tmp" && mv -f "$AUTH.tmp" "$AUTH"
  chmod 600 "$AUTH"
  echo "제한 키 제거 완료 (백업: $AUTH.bak-*)"
}

case "${1:-}" in
  --show)   show; exit 0 ;;
  --revoke) revoke; exit 0 ;;
  "")       echo "사용: $0 <공개키파일> | --show | --revoke" >&2; exit 2 ;;
esac

PUB="$1"
[[ -f "$PUB" ]] || { echo "공개키 파일이 없다: $PUB" >&2; exit 1; }
[[ -x "$SHIM" ]] || { echo "shim 이 없거나 실행권한이 없다: $SHIM" >&2; exit 1; }

KEY=$(tr -d '\r\n' < "$PUB")
# 개인키를 실수로 넘긴 경우를 막는다 — 그대로 등록하면 아무것도 안 되고, 파일만 샌다.
[[ "$KEY" == ssh-* || "$KEY" == ecdsa-* || "$KEY" == sk-* ]] \
  || { echo "공개키 형식이 아니다 (ssh-ed25519 … 로 시작해야 한다). 개인키를 넘긴 게 아닌지 확인할 것." >&2; exit 1; }

mkdir -p "$HOME/.ssh"; touch "$AUTH"; chmod 700 "$HOME/.ssh"; chmod 600 "$AUTH"

if grep -qF "$KEY" "$AUTH" 2>/dev/null; then
  echo "이미 등록된 키다 — 중복 등록하지 않는다"; show; exit 0
fi

cp -f "$AUTH" "$AUTH.bak-$(date -u +%Y%m%d-%H%M%S)"

# restrict = no-agent-forwarding,no-port-forwarding,no-pty,no-user-rc,no-X11-forwarding 를 한 번에.
# 나중에 OpenSSH 가 옵션을 추가해도 자동으로 막히는 쪽이라 개별 나열보다 안전하다.
printf 'restrict,command="%s" %s %s\n' "$SHIM" "$KEY" "$MARK" >> "$AUTH"
chmod 600 "$AUTH"

echo "등록 완료:"
show
cat <<EOF

확인해 보려면 (클라이언트에서):
  ssh -i <개인키> ubuntu@168.107.8.107 status
  ssh -i <개인키> ubuntu@168.107.8.107 'rollback list'
  ssh -i <개인키> ubuntu@168.107.8.107 'rm -rf /'     ← 거부돼야 정상

되돌리려면: $0 --revoke
EOF
