#!/usr/bin/env bash
# 즉시 배포 뒤 prod staging/ 을 라이브와 같은 상태로 맞춘다.
#
# ## 왜 필요한가 — 조용한 되돌림
# prod 에는 두 갈래 배포가 있다.
#   ① 즉시 배포 : 맥에서 jar 을 plugins/ 에 바로 올리고 재시작   (deploy-blockship / deploy-jar / deploy-all-prod)
#   ② 지연 배포 : staging/ 에 얹어 두면 06:00 nightly-restart.sh 가 적용
# ②의 잔여물이 staging/ 에 남아 있는데 ①을 돌리면, 그날 밤 nightly 가 **낡은 jar 을
# 라이브에 덮어쓴다.** 서버는 정상 기동하고 에러도 없어서 「어제 고친 게 왜 다시 안 되지」
# 로만 드러난다. 2026-08-26 실측: 8/25 자 jar + titles.json 이 staging 에 남은 채였다.
#
# ## 무엇을 하나
#   - staging 의 **같은 이름 jar** 이 있으면 staging-superseded/<시각>/ 로 치운다
#   - 방금 라이브에 올라간 jar 을 staging 에 복사한다 → staging 은 라이브보다 낡을 수 없다
#     (그날 밤 nightly 가 적용해도 같은 바이트라 무해한 no-op 이다)
#   - --with-config 면 staging/BlockShip/ 의 설정도 치운다. 즉시 배포는 JSON 을 라이브에
#     직접 쓰므로, staging 에 남은 JSON 은 정의상 그보다 낡았다.
#
# ## 건드리지 않는 것
#   - `.fetch-staging-state` — 마지막으로 받은 Release 태그. 지우면 fetch-staging.sh 가
#     같은 Release 를 다시 받아 staging 에 도로 얹는다(되돌림 재발). 그대로 둔다.
#   - 다른 이름의 jar (BarkanChess 등) — 남이 의도적으로 올려둔 지연 배포다.
#   - plugins/ 루트 — 여기서는 절대 쓰지 않는다. staging 까지가 이 스크립트의 권한이다.
#
# 사용: ops/sync-prod-staging.sh --jar-name <plugins 안 파일명> [--with-config]
set -euo pipefail

KEY="${PROD_SSH_KEY:-$HOME/.ssh/oracle-mc.key}"
PROD_HOST="${PROD_HOST:-ubuntu@168.107.8.107}"

JAR_NAME=""
WITH_CONFIG=0
while [ $# -gt 0 ]; do
  case "$1" in
    --jar-name) JAR_NAME="${2:-}"; shift 2 ;;
    --with-config) WITH_CONFIG=1; shift ;;
    *) echo "사용법: $0 --jar-name <파일명> [--with-config]" >&2; exit 2 ;;
  esac
done
[ -n "$JAR_NAME" ] || { echo "❌ --jar-name 필요" >&2; exit 2; }
[ -f "$KEY" ] || { echo "❌ SSH 키 없음: $KEY" >&2; exit 1; }

echo "▶ prod staging 동기화 ($JAR_NAME${WITH_CONFIG:+, 설정 포함})"
ssh -o BatchMode=yes -o ConnectTimeout=15 -i "$KEY" "$PROD_HOST" \
  "JAR_NAME='$JAR_NAME' WITH_CONFIG='$WITH_CONFIG' bash -s" <<'REMOTE'
set -euo pipefail
MC="$HOME/mcserver"
STAGING="$MC/staging"
PLUGINS="$MC/plugins"
LIVE="$PLUGINS/$JAR_NAME"
TS=$(TZ=Asia/Seoul date +%Y%m%d-%H%M%S)
SUP="$MC/staging-superseded/$TS"
LOG="$MC/backups/ops.log"
log() { local m="[$(date '+%Y-%m-%d %H:%M:%S')] [sync-staging] $*"; echo "$m"; echo "$m" >> "$LOG" 2>/dev/null || true; }

[ -s "$LIVE" ] || { echo "❌ 라이브 jar 없음: $LIVE"; exit 1; }
mkdir -p "$STAGING"

moved=0
if [ -f "$STAGING/$JAR_NAME" ]; then
  if cmp -s "$STAGING/$JAR_NAME" "$LIVE"; then
    log "staging jar 이 이미 라이브와 동일 — 그대로 둔다"
  else
    mkdir -p "$SUP"; mv -f "$STAGING/$JAR_NAME" "$SUP/"; moved=$((moved+1))
    log "낡은 staging jar 격리: $JAR_NAME → staging-superseded/$TS/"
  fi
fi
if [ "$WITH_CONFIG" = 1 ] && [ -d "$STAGING/BlockShip" ] && [ -n "$(ls -A "$STAGING/BlockShip" 2>/dev/null)" ]; then
  mkdir -p "$SUP"; mv -f "$STAGING/BlockShip" "$SUP/BlockShip"; moved=$((moved+1))
  log "낡은 staging 설정 격리: BlockShip/ → staging-superseded/$TS/"
fi

cp -f "$LIVE" "$STAGING/$JAR_NAME"
live_sha=$(sha1sum "$LIVE" | awk '{print $1}')
stage_sha=$(sha1sum "$STAGING/$JAR_NAME" | awk '{print $1}')
[ "$live_sha" = "$stage_sha" ] || { echo "❌ staging 복사 검증 실패 (live=$live_sha stage=$stage_sha)"; exit 1; }

# 지연 배포용으로 남의 jar 이 대기 중이면 알려만 준다(치우지 않는다).
others=$(find "$STAGING" -maxdepth 1 -name '*.jar' ! -name "$JAR_NAME" -printf '%f ' 2>/dev/null || true)
[ -n "${others// /}" ] && log "⚠ 다른 지연 배포 jar 대기 중(건드리지 않음): $others"

log "완료 — staging == 라이브 ($live_sha), 격리 ${moved}건"
echo "STAGING_SHA1=$stage_sha"
REMOTE
echo "✓ prod staging 동기화 완료"
