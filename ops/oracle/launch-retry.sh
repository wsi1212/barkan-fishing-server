#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# A1.Flex 용량 사냥 — "Out of host capacity" 를 뚫을 때까지 계속 시도
#
# 춘천(ap-chuncheon-1)의 Always Free ARM 자리는 귀하다. 기존 박스도
# ~/oracle-auto-retry/resize-retry.sh 를 오래 돌려서 4/24 를 얻었다.
# 그건 "resize" 재시도였고, 새 테넌시에 필요한 건 "launch" 재시도다.
#
# ★설정 오류로 며칠을 헛돌지 않게, 용량 부족만 재시도하고
#   인증·OCID 오류는 즉시 죽는다.
#
# 사용법:
#   launch-retry.sh --discover          # 필요한 OCID들을 찾아서 보여준다 (먼저 이거)
#   launch-retry.sh --dry-run           # 설정 검증 + 실행될 명령만 출력
#   launch-retry.sh                     # 사냥 시작
#
# 설정: 아래 값을 채우거나 환경변수로 넘긴다. --discover 가 대부분 알려준다.
# ─────────────────────────────────────────────────────────────────────────────
set -uo pipefail

OCI_PROFILE="${OCI_PROFILE:-DEFAULT}"
COMPARTMENT="${COMPARTMENT:-}"          # 보통 테넌시 루트 OCID (ocid1.tenancy...)
SUBNET="${SUBNET:-}"                    # 퍼블릭 서브넷 OCID
IMAGE="${IMAGE:-}"                      # Ubuntu 24.04 aarch64 이미지 OCID
AD="${AD:-}"                            # 춘천은 AD 1개 (ap-chuncheon-1-AD-1)
SSH_PUB="${SSH_PUB:-$HOME/.ssh/oracle-new.pub}"
NAME="${NAME:-mc-prod-new}"
OCPUS="${OCPUS:-4}"                     # ★Always Free 상한 = 4 OCPU / 24GB (합계)
MEM_GB="${MEM_GB:-24}"                  #   초과하면 트라이얼 종료 후 정지·회수된다
BOOT_GB="${BOOT_GB:-200}"               # Always Free 블록스토리지 합계 200GB
INTERVAL="${INTERVAL:-90}"              # 재시도 간격(초). 너무 짧으면 429 를 맞는다
MAX_HOURS="${MAX_HOURS:-720}"           # 30일 상한 (무한루프 방지)
WEBHOOK_FILE="${WEBHOOK_FILE:-$HOME/mcserver/scripts/discord-webhook.url}"
LOG_FILE="${LOG_FILE:-$HOME/launch-retry.log}"

MODE=run
while [[ $# -gt 0 ]]; do
  case "$1" in
    --discover) MODE=discover; shift ;;
    --dry-run)  MODE=dry; shift ;;
    -h|--help)  sed -n '2,20p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "알 수 없는 인자: $1" >&2; exit 2 ;;
  esac
done

log() { local m="[$(date '+%m-%d %H:%M:%S')] $*"; echo "$m"; echo "$m" >> "$LOG_FILE" 2>/dev/null||true; }
notify() {
  [[ -f "$WEBHOOK_FILE" ]] || return 0
  local u; u=$(<"$WEBHOOK_FILE"); [[ -n "$u" ]] || return 0
  curl -fsS --max-time 15 -H 'Content-Type: application/json' \
    -d "$(python3 -c 'import json,sys;print(json.dumps({"content":sys.argv[1]}))' "$1")" "$u" >/dev/null 2>&1||true
}

command -v oci >/dev/null || { echo "oci CLI 없음. 설치: bash -c \"\$(curl -L https://raw.githubusercontent.com/oracle/oci-cli/master/scripts/install/install.sh)\"" >&2; exit 2; }

# ── --discover : 필요한 OCID 를 찾아준다 ────────────────────────────────────
if [[ "$MODE" == discover ]]; then
  echo "▶ 테넌시 / 리전"
  TEN=$(oci --profile "$OCI_PROFILE" iam compartment list --all --query 'data[0]."compartment-id"' --raw-output 2>/dev/null) \
    || { echo "  ✗ oci 호출 실패 — ~/.oci/config 와 API 키를 먼저 설정할 것"; exit 1; }
  echo "  COMPARTMENT=$TEN   (테넌시 루트)"
  echo
  echo "▶ 가용 도메인"
  oci --profile "$OCI_PROFILE" iam availability-domain list --compartment-id "$TEN" \
      --query 'data[].name' --raw-output 2>/dev/null | sed 's/^/  AD=/'
  echo
  echo "▶ Ubuntu 24.04 aarch64 이미지 (가장 최신 하나)"
  oci --profile "$OCI_PROFILE" compute image list --compartment-id "$TEN" \
      --operating-system "Canonical Ubuntu" --operating-system-version "24.04" \
      --shape VM.Standard.A1.Flex --sort-by TIMECREATED --limit 1 \
      --query 'data[0].{IMAGE:id,name:"display-name"}' 2>/dev/null | sed 's/^/  /'
  echo
  echo "▶ 서브넷 (VCN 이 없으면 콘솔에서 'VCN 마법사'로 먼저 만들 것)"
  oci --profile "$OCI_PROFILE" network subnet list --compartment-id "$TEN" \
      --query 'data[].{SUBNET:id,name:"display-name",public:"prohibit-public-ip-on-vnic"}' 2>/dev/null | sed 's/^/  /'
  echo
  echo "위 값들을 환경변수로 넘기거나 이 스크립트 상단에 채운 뒤 --dry-run 으로 확인."
  exit 0
fi

# ── 설정 검증 ───────────────────────────────────────────────────────────────
MISSING=()
for v in COMPARTMENT SUBNET IMAGE AD; do [[ -n "${!v}" ]] || MISSING+=("$v"); done
[[ ${#MISSING[@]} -eq 0 ]] || { echo "✗ 설정 누락: ${MISSING[*]}  (--discover 로 찾을 수 있다)" >&2; exit 2; }
[[ -f "$SSH_PUB" ]] || { echo "✗ SSH 공개키 없음: $SSH_PUB" >&2
                         echo "  만들기: ssh-keygen -t ed25519 -f ${SSH_PUB%.pub} -C mc-prod" >&2; exit 2; }

LAUNCH=(oci --profile "$OCI_PROFILE" compute instance launch
  --availability-domain "$AD" --compartment-id "$COMPARTMENT"
  --shape VM.Standard.A1.Flex
  --shape-config "{\"ocpus\":$OCPUS,\"memoryInGBs\":$MEM_GB}"
  --image-id "$IMAGE" --subnet-id "$SUBNET"
  --display-name "$NAME" --assign-public-ip true
  --boot-volume-size-in-gbs "$BOOT_GB"
  --ssh-authorized-keys-file "$SSH_PUB"
  --wait-for-state RUNNING)

if [[ "$MODE" == dry ]]; then
  echo "▶ 실행될 명령:"; printf '  %q' "${LAUNCH[@]}"; echo
  echo
  echo "▶ 사양 확인: ${OCPUS} OCPU / ${MEM_GB}GB / 부트 ${BOOT_GB}GB"
  [[ "$OCPUS" -le 4 && "$MEM_GB" -le 24 ]] \
    && echo "  ✓ Always Free 상한 내 — 트라이얼 종료 후에도 무료로 유지된다" \
    || echo "  ⚠ Always Free 상한(4 OCPU/24GB) 초과 — 트라이얼이 끝나면 정지·회수된다"
  exit 0
fi

# ── 사냥 ────────────────────────────────────────────────────────────────────
log "═══ A1.Flex 사냥 시작 — ${OCPUS}코어/${MEM_GB}GB · ${AD} · ${INTERVAL}초 간격 ═══"
notify "🎯 **A1 용량 사냥 시작** — ${OCPUS} OCPU / ${MEM_GB}GB @ \`${AD}\`"
START=$(date +%s); N=0; BACKOFF=0

while :; do
  N=$((N + 1))
  ELAPSED_H=$(( ($(date +%s) - START) / 3600 ))
  [[ $ELAPSED_H -ge $MAX_HOURS ]] && { log "상한 ${MAX_HOURS}시간 도달 — 중단"; notify "⏹ 용량 사냥 중단 (${MAX_HOURS}h 초과)"; exit 1; }

  OUT=$("${LAUNCH[@]}" 2>&1); RC=$?
  if [[ $RC -eq 0 ]]; then
    IP=$(echo "$OUT" | python3 -c "
import json,sys
try:
    d=json.load(sys.stdin); print(d.get('data',{}).get('id',''))
except Exception: pass" 2>/dev/null)
    log "✅ 인스턴스 생성 성공! (시도 $N, ${ELAPSED_H}h)"
    log "$OUT"
    notify "🎉 **A1 인스턴스 확보!** 시도 ${N}회 / ${ELAPSED_H}시간
OCID: \`${IP:-출력 참조}\`
다음: 퍼블릭 IP 확인 → MIGRATION.md 순서대로"
    exit 0
  fi

  # 용량 부족만 재시도한다. 나머지는 설정 문제이므로 즉시 죽는다.
  if grep -qiE 'out of host capacity|outofcapacity|capacity' <<<"$OUT"; then
    BACKOFF=0
    (( N % 20 == 1 )) && log "용량 없음 (시도 $N, ${ELAPSED_H}h 경과) — 계속 시도"
  elif grep -qiE 'too ?many ?requests|429|rate.?limit' <<<"$OUT"; then
    BACKOFF=$(( BACKOFF < 5 ? BACKOFF + 1 : 5 ))
    log "레이트 리밋 — ${BACKOFF}배 백오프"
  elif grep -qiE 'limit.?exceeded|quota|service limit' <<<"$OUT"; then
    log "✗ 한도 초과 — Always Free 상한(4 OCPU/24GB)을 이미 다 쓰고 있는지 확인"
    log "$OUT"; notify "🔴 용량 사냥 중단 — 서비스 한도 초과"; exit 1
  else
    log "✗ 용량 문제가 아니다 — 설정을 고칠 것 (며칠 헛돌지 않게 여기서 멈춘다)"
    log "$OUT"; notify "🔴 용량 사냥 중단 — 설정 오류
\`\`\`$(echo "$OUT" | head -c 600)\`\`\`"; exit 1
  fi

  # 지터를 넣는다 — 정확히 같은 주기로 때리는 클라이언트가 많으면 서로 부딪힌다
  SLEEP=$(( INTERVAL * (BACKOFF > 0 ? BACKOFF : 1) + RANDOM % 30 ))
  sleep "$SLEEP"
done
