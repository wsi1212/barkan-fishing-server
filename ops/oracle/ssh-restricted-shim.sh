#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# 제한 SSH 키의 유일한 진입점 — 화이트리스트에 있는 것만 실행한다.
#
# authorized_keys 에 command="..." 로 묶인 키는 접속자가 무엇을 치든 **이 스크립트만**
# 실행되고, 원래 치려던 명령은 $SSH_ORIGINAL_COMMAND 로 들어온다. 그걸 여기서 검사한다.
#
# ## 왜 이게 필요한가
# 에이전트(또는 폰)에게 장애 대응 권한을 주고 싶은데, 평범한 SSH 키를 주면 그 키로
# 무엇이든 할 수 있다 — 월드 삭제, 백업 삭제, 인스턴스 조작까지. 키가 새면 서버가 끝난다.
# 그래서 **"고장을 되돌리고 상태를 보는 것"만** 열어 둔다. 이 목록에 없으면 전부 거부다.
#
# ## 허용 (이것뿐)
#   rollback list | dry | yes | yes to <파일명>   → rollback-jar.sh 위임
#   log [N]                                       → latest.log 끝 N줄 (기본 100, 최대 500)
#   status                                        → systemd 상태 + 접속자 수 + 디스크
#   ops [N]                                       → 운영 로그(backups/ops.log) 끝 N줄
#
# ## 일부러 뺀 것
#   임의 셸 · 파일 쓰기 · 재시작 단독 실행 · 백업 삭제 · staging 조작 · sudo.
#   재시작이 필요하면 rollback yes 안에 포함돼 있다(그게 되돌리는 행위의 일부라서).
#   ★"편의상" 여기에 명령을 더하지 말 것 — 더할 때마다 키의 폭발 반경이 커진다.
#     새 명령이 필요하면 그 작업 전용 스크립트를 만들고 그것만 화이트리스트에 넣는다.
#
# ## 설치
#   setup-restricted-key.sh 참조 (authorized_keys 한 줄을 만들어 준다)
# ─────────────────────────────────────────────────────────────────────────────
set -uo pipefail

MC_ROOT="${MC_ROOT:-$HOME/mcserver}"
DIR="$MC_ROOT/scripts"
LOG_FILE="$MC_ROOT/backups/ops.log"

CMD="${SSH_ORIGINAL_COMMAND:-}"

audit() {
  # ★모든 시도를 남긴다 — 거부된 것도. 키가 샜을 때 이 기록이 유일한 단서다.
  # ★${SSH_CLIENT:-} 로 받는다. sshd 는 항상 넣어 주지만 set -u 라 없으면 감사 로그를
  #   쓰다가 죽는다 — 거부 경로에서 죽으면 거부 사실 자체가 안 남는다(로컬 테스트로 발견).
  local from="${SSH_CLIENT:-unknown}"
  local m="[$(date '+%Y-%m-%d %H:%M:%S')] [restricted-ssh] from=${from%% *} $*"
  echo "$m" >> "$LOG_FILE" 2>/dev/null || true
}
deny() {
  audit "거부: '$CMD' ($1)"
  echo "거부됨: $1" >&2
  echo "쓸 수 있는 것: rollback list|dry|yes [to <파일>] · log [N] · status · ops [N]" >&2
  exit 126
}

[[ -n "$CMD" ]] || deny "이 키로는 대화형 셸을 열 수 없다"

# 인자를 안전하게 쪼갠다. eval 을 쓰지 않는다 — 그러면 화이트리스트가 무의미해진다.
read -r -a ARG <<<"$CMD"
SUB="${ARG[0]:-}"

# 숫자 인자 검사 (로그 줄 수) — 범위를 넘기면 로그로 디스크·대역을 태울 수 있다
num_or() {
  local v="${1:-}" def="$2" max="$3"
  [[ "$v" =~ ^[0-9]+$ ]] || { echo "$def"; return; }
  (( v > max )) && { echo "$max"; return; }
  (( v < 1 )) && { echo "$def"; return; }
  echo "$v"
}

case "$SUB" in
  rollback)
    # rollback-jar.sh 는 자기 인자를 스스로 검사한다(list|dry|yes|to). 여기서는
    # **위임만** 하고, 알 수 없는 것은 그쪽이 거부한다. 다만 인자 개수는 제한한다.
    (( ${#ARG[@]} > 4 )) && deny "rollback 인자가 너무 많다"
    [[ -x "$DIR/rollback-jar.sh" ]] || deny "rollback-jar.sh 가 없다"
    audit "허용: $CMD"
    exec "$DIR/rollback-jar.sh" "${ARG[@]:1}"
    ;;
  log)
    N=$(num_or "${ARG[1]:-}" 100 500)
    audit "허용: log $N"
    exec tail -n "$N" "$MC_ROOT/logs/latest.log"
    ;;
  ops)
    N=$(num_or "${ARG[1]:-}" 100 500)
    audit "허용: ops $N"
    exec tail -n "$N" "$LOG_FILE"
    ;;
  status)
    audit "허용: status"
    echo "── systemd ──"
    systemctl is-active mcserver 2>/dev/null || true
    systemctl show mcserver -p ActiveEnterTimestamp --value 2>/dev/null || true
    echo "── 접속자 ──"
    "$DIR/rcon.py" list 2>/dev/null || echo "(rcon 무응답)"
    echo "── 디스크 ──"
    df -h "$MC_ROOT" | tail -1
    echo "── 라이브 jar ──"
    ls -l "$MC_ROOT"/plugins/BlockShip-*.jar 2>/dev/null || echo "(없음)"
    sha256sum "$MC_ROOT"/plugins/BlockShip-*.jar 2>/dev/null || true
    echo "── staging ──"
    ls -l "$MC_ROOT"/staging/ 2>/dev/null || echo "(비어있음)"
    exit 0
    ;;
  *)
    deny "허용되지 않은 명령"
    ;;
esac
