#!/bin/bash
# BlockShip Java 플러그인 빌드 + 오라클 배포 + 재시작
# 사용법: ./deploy-blockship.sh [--no-restart]
#
# --no-restart 는 전체 배포 래퍼가 BetterHud 교체·리소스팩 재생성과 함께
# 마지막에 한 번만 재시작할 때 사용한다. JAR/데이터를 prod plugins/ 에
# 올린 채로 이 옵션만 단독 실행하고 끝내면 안 된다.

set -e

# ★심볼릭링크 해석 — ~/<이름>.sh 로 실행되면 $0·BASH_SOURCE 가 홈을 가리켜
#   같은 폴더의 스크립트를 못 찾는다(2026-08-31: 모든 배포가 staging 동기화를 조용히
#   건너뛰고 있었다). 원본 로직은 ops/lib-self.sh.
_self_real() { local s="$1" l; while [ -L "$s" ]; do l="$(readlink "$s")"; case "$l" in /*) s="$l";; *) s="$(dirname "$s")/$l";; esac; done; printf '%s\n' "$s"; }
SELF_DIR="$(cd "$(dirname "$(_self_real "${BASH_SOURCE[0]:-$0}")")" && pwd)"

RESTART_PROD=1
for arg in "$@"; do
  case "$arg" in
    --no-restart) RESTART_PROD=0 ;;
    *) echo "사용법: $0 [--no-restart]" >&2; exit 2 ;;
  esac
done

BLOCKSHIP_DIR="${BLOCKSHIP_DIR:-$HOME/development/blockship-plugin}"
JAR_NAME="BlockShip-1.0.0-SNAPSHOT.jar"
LOCAL_JAR="$BLOCKSHIP_DIR/build/libs/$JAR_NAME"

REMOTE_USER="ubuntu"
REMOTE_HOST="168.107.8.107"
REMOTE_PLUGINS="~/mcserver/plugins"
SSH_KEY="$HOME/.ssh/oracle-mc.key"
# 전체 배포 래퍼는 JAR을 라이브 plugins/에 바로 쓰지 않고 원격 임시
# 디렉터리에 먼저 올린다. 기본값은 기존 단독 배포 동작을 유지한다.
PROD_JAR_DEST="${PROD_JAR_DEST:-$REMOTE_PLUGINS/}"
REMOTE_LIVE_JAR="/home/ubuntu/mcserver/plugins/$JAR_NAME"
REMOTE_STAGE=""
REMOTE_JAR_SOURCE=""
REMOTE_DATA_STAGE=""
REMOTE_DATA_SOURCE=""
PROD_DATA_DEST="${PROD_DATA_DEST:-/home/ubuntu/mcserver/plugins/BlockShip/}"

if [ "$RESTART_PROD" = 0 ] && { [ "$PROD_JAR_DEST" = "$REMOTE_PLUGINS/" ] || [ "$PROD_DATA_DEST" = "/home/ubuntu/mcserver/plugins/BlockShip/" ]; }; then
  echo "❌ --no-restart 로 라이브 plugins/에 JAR을 올릴 수 없다." >&2
  echo "   전체배포처럼 임시 경로를 지정하거나, 즉시배포(재시작 포함)를 사용하라." >&2
  exit 2
fi

if [ "$RESTART_PROD" = 1 ] && [ "$PROD_DATA_DEST" = "/home/ubuntu/mcserver/plugins/BlockShip/" ]; then
  # 실행 중인 BlockShip이 메모리의 recipes.json을 저장할 수 있으므로,
  # JSON도 JAR과 같은 임시 경로에 올린 뒤 정지 상태에서 승격한다.
  DEPLOY_ID="blockship-$$-$(date +%Y%m%d%H%M%S)"
  REMOTE_STAGE="/home/ubuntu/mcserver/.deploy-staged/$DEPLOY_ID"
  PROD_JAR_DEST="$REMOTE_STAGE/"
  REMOTE_DATA_STAGE="$REMOTE_STAGE/BlockShip"
  PROD_DATA_DEST="$REMOTE_DATA_STAGE/"
  ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no \
    "$REMOTE_USER@$REMOTE_HOST" "install -d -m 0755 '$REMOTE_DATA_STAGE'"
fi

# 검증기(ops/validate-staged.py)가 있는 스크립트 저장소
SCRIPTS_REPO="/Users/user/Library/Application Support/feather/player-server/servers/07de2d81-991a-47e2-b62d-06c0d1b5150a/plugins/Skript/scripts"
# Java 소유 JSON의 작업 원본은 dev 런타임 사본이 아니라 git 미러다.
# dev plugins/BlockShip/은 서버 기동 중 Java가 정규화할 수 있는 런타임 사본이므로,
# 배포 전에 미러에서 다시 채운다.
LOCAL_DATA="$SCRIPTS_REPO/ops/blockship-data"
DEV_DATA="/Users/user/Library/Application Support/feather/player-server/servers/07de2d81-991a-47e2-b62d-06c0d1b5150a/plugins/BlockShip"
# Skript→Java 이관으로 Java가 소유하는 JSON 데이터 (dev→prod 단방향 sync).
#  주의: 이 파일들은 prod에서 직접 편집(/npc등록·/칭호 생성 등)하면 다음 배포에서 덮어쓰여짐.
#        편집은 dev에서 하고 배포할 것.
DATA_FILES=("npc.json" "dialogue.json" "titles.json" "parts.json" "enhance.json" "recipes.json" "materials.json" "quests.json" "fish.json" "item-flavor.json")
# 주의: collectibles.json/regions.json/env-bonuses.json 은 인스턴스 전용이라 sync 제외.
#  ★2026-08-28 정정 — quests.json/fish.json 을 **넣었다**. 여태 빠져 있었는데,
#    ① guard-instance-data.py 의 INSTANCE_FILES(제외 목록의 권위) 에 둘 다 없다 = 콘텐츠다
#    ② prod 실측이 미러와 동일했다(퀘스트 339=339, 어종 470=470) — prod 쪽 저작으로
#       갈라진 적이 없다. 즉 제외는 보호 효과가 없었다.
#    ③ 그런데 이 둘만 빠지면 «반쪽 배포» 가 난다: 2026-08-28 붉은사막→붉은_골짜기 이관에서
#       materials 는 가고 fish/quests 는 안 가서, prod 는 드롭테이블만 옮겨지고 어종은
#       옛 지역에 남아 통발에 잡을 물고기가 없고 도감 퀘스트 8건이 0 으로 세는 상태가 된다.
#    삭제 방향은 validate-staged.py 의 «항목수 감소 거부» 가 계속 막는다.

# ★제외 목록을 주석이 아니라 코드로 지킨다 — 목록 권위는 ops/hooks/guard-instance-data.py.
#   섬·길드·플레이어 상태가 sync 목록에 끼면 상대 서버의 유저 데이터를 지운다(사고 3건).
python3 "$SCRIPTS_REPO/ops/hooks/guard-instance-data.py" --check-list "${DATA_FILES[@]}"

# ★퀘스트 목표의 id 인자가 실제로 발행되는 값인지 대조 — 오타·개명은 «에러 없이» 영구
#   진행불가를 만든다(2026-08-28 메인 3-7 이 mine|iron_ore 로 통째 막혀 있었다).
python3 "$SCRIPTS_REPO/ops/audit-quest-goal-ids.py"

# ★사본 드리프트 — 「같아야 하는 두 벌」이 갈라진 채 배포되면, 게이트가 검사한 파일과
#   실제 올라가는 파일이 다른 물건이 된다(2026-08-31: 레포 fish.json 이 개명 전에 멈춰
#   유령 ERROR 21건 + 진짜 버그 1건을 가렸다).
python3 "$SCRIPTS_REPO/ops/audit-copies.py"

# ★퀘스트·콘텐츠 진행 가능성 전수 검사.
#   2026-08-31 에 ERROR 158 → 0 이 됐다(157건이 낡은 사본을 본 유령이었다). 0 이 기준선이니
#   SKIP_QUEST_AUDIT 같은 우회구를 다시 만들지 말 것 — 우회구가 있으면 부채가 다시 쌓이고
#   그 안에 진짜 버그가 숨는다(튜토09 통발 무지급이 그렇게 숨어 있었다).
echo "▶ 퀘스트·콘텐츠 진행 가능성 전수 검사"
if ! python3 "$BLOCKSHIP_DIR/tools/quest_audit.py" --root "$BLOCKSHIP_DIR" --runtime-dir "$LOCAL_DATA" --regions-dir "$DEV_DATA" > /tmp/quest_audit.log 2>&1; then
  tail -1 /tmp/quest_audit.log
  echo "❌ 퀘스트 감사 실패. 전체 리포트: /tmp/quest_audit.log"
  exit 1
fi
echo "  ✓ 통과"

echo "▶ 런타임 굵은 포맷 전수 검사"
python3 "$BLOCKSHIP_DIR/tools/verify-no-bold-format.py" "$BLOCKSHIP_DIR/src/main"
echo "▶ 타임존 미지정 시간 API 전수 검사"
python3 "$BLOCKSHIP_DIR/tools/verify-no-naive-time.py" "$BLOCKSHIP_DIR/src/main"

# ★NPC·대사 정합성 — 역할·퀘스트가 붙어 있는데 대사가 없으면 클릭 시 '...' 만 뜨고
#   에러도 로그도 없이 죽는다. 봇이 NPC 우클릭을 못 찍어 사람 검증으로 안 걸린다.
echo "▶ NPC·대사 정합성 감사"
AUDIT="$SCRIPTS_REPO/ops/audit-dialogue.py"
if [ -f "$AUDIT" ]; then
  if ! python3 "$AUDIT" --dir "$LOCAL_DATA" --quiet; then
    echo "❌ NPC·대사 감사에서 ERROR가 나왔습니다. prod 배포를 중단합니다."
    echo "   전체 리포트: python3 \"$AUDIT\" --full"
    exit 1
  fi
  echo "  ✓ ERROR 0건"
fi

# ★prod 로 나갈 jar 은 «커밋된 트리»에서 빌드한다 — 규칙이 문서에만 있어서 두 방향으로
#   사고가 났다: 미커밋이 실려 나가거나(2026-08-11), 낡은 체크아웃에서 빌드돼 커밋된
#   기능이 빠지거나(2026-08-31, jar mtime 은 최신인데 내용은 며칠 전).
#   더러우면 이 게이트가 HEAD 워크트리를 «자동으로» 떠서 그걸 빌드한다.
echo "▶ 빌드 출처 검증 (커밋된 트리인가)"
SOURCE_REPO="$BLOCKSHIP_DIR"   # 워크트리를 떠도 «원본 저장소»는 여기다(정리에 필요)
# ★명령치환을 eval 에 «직접» 먹이지 말 것 — guard 는 실패 메시지를 stderr 로 내므로
#   실패 시 stdout 이 비고, `eval ""` 은 0 을 반환한다. 그러면 `|| exit 1` 이 영원히
#   발동하지 않아 게이트가 «아무 소리 없이» 우회된다(2026-09-01 실측: 미푸시 7커밋에
#   ❌ 를 찍고도 빌드까지 진행했다. 거기서 멈춘 것도 BLOCKSHIP_DIR="" → cd "" 가 no-op 라
#   ./gradlew 를 못 찾은 «우연»이었을 뿐 — 플러그인 폴더 안에서 실행했다면 그대로 업로드됐다).
#   ⇒ 출력을 변수에 받아 종료코드를 별도로 확인한 뒤에 eval 한다.
GUARD_ENV="$("$SCRIPTS_REPO/ops/guard-build-source.sh" "$BLOCKSHIP_DIR")" || {
  echo "❌ 빌드 출처 게이트에서 막혔습니다. prod 배포를 중단합니다."
  exit 1
}
BUILD_DIR=""
eval "$GUARD_ENV"
# guard 가 0 을 냈는데도 BUILD_DIR 이 비면(출력 형식 변경·잘림) 빈 cd 로 «현재 디렉터리»를
#   빌드하게 된다 — 게이트가 통째로 무의미해지므로 여기서 죽인다.
if [ -z "${BUILD_DIR:-}" ]; then
  echo "❌ 빌드 출처 게이트가 BUILD_DIR 을 내놓지 않았습니다(출력: ${GUARD_ENV:-<비어있음>})."
  exit 1
fi
BLOCKSHIP_DIR="$BUILD_DIR"
LOCAL_JAR="$BLOCKSHIP_DIR/build/libs/$JAR_NAME"
if [ -n "${BUILD_WORKTREE:-}" ]; then
  # shellcheck disable=SC2064
  trap "git -C '$SOURCE_REPO' worktree remove --force '$BUILD_WORKTREE' >/dev/null 2>&1; git -C '$SOURCE_REPO' worktree prune >/dev/null 2>&1" EXIT
fi

echo "▶ BlockShip 빌드"
cd "$BLOCKSHIP_DIR"
./gradlew build

if [ ! -f "$LOCAL_JAR" ]; then
  echo "❌ jar 빌드 실패: $LOCAL_JAR 없음"
  exit 1
fi

echo ""
echo "▶ 로컬 마크 서버에도 배포 (dev)"
cp "$LOCAL_JAR" "/Users/user/Library/Application Support/feather/player-server/servers/07de2d81-991a-47e2-b62d-06c0d1b5150a/plugins/"
echo "  ✓ 로컬 패더 plugins/ 에 복사됨"
for f in "${DATA_FILES[@]}"; do
  if [ -f "$LOCAL_DATA/$f" ]; then
    cp "$LOCAL_DATA/$f" "$DEV_DATA/$f"
  fi
done
echo "  ✓ dev BlockShip 데이터 미러 갱신"
# ★jar만 복사하고 dev를 안 재시작하면 dev도 lazy-load CNFE 지뢰가 된다(prod와 같은 원리).
#   dev가 돌고 있으면 즉시 재시작해서 중간 상태를 남기지 않는다.
if pgrep -f "paper-1\.21\..*\.jar" >/dev/null 2>&1; then
  echo "  · dev 가동 중 → 재시작 (jar만 갈아두면 CNFE 지뢰)"
  ~/dev-mc.sh restart || echo "  ⚠ dev 재시작 실패 — 수동으로 ~/dev-mc.sh restart 할 것"
else
  echo "  · dev 미가동 → 다음 기동 때 적용됨"
fi

echo ""
echo "▶ 오라클에 JSON 데이터 업로드 (Java 소유 이관 데이터)"
# 실행 중인 서버가 라이브 JSON을 덮어쓰지 못하게 임시 경로에 전송한다.
ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no \
  "$REMOTE_USER@$REMOTE_HOST" "install -d -m 0755 '$PROD_DATA_DEST'"
# ★2026-08-01 사고 후 게이트: 부분/구버전 JSON이 prod 라이브를 덮는 걸 막는다.
#   (그날 staging 경로로 NPC 1명짜리 npc.json이 138명짜리를 덮어 NPC/대화/퀘스트가 죽었다.
#    이 즉시배포 경로도 같은 구멍이 있었으므로 동일 검증기를 통과시킨다.)
VALIDATOR="$SCRIPTS_REPO/ops/validate-staged.py"
REJECTED=0
for f in "${DATA_FILES[@]}"; do
  if [ -f "$LOCAL_DATA/$f" ]; then
    if [ -x "$VALIDATOR" ]; then
      TMPLIVE=$(mktemp)
      scp -q -i "$SSH_KEY" -o StrictHostKeyChecking=no \
        "$REMOTE_USER@$REMOTE_HOST:$REMOTE_PLUGINS/BlockShip/$f" "$TMPLIVE" 2>/dev/null || : > "$TMPLIVE"
      if [ -s "$TMPLIVE" ] && ! REASON=$(python3 "$VALIDATOR" "$LOCAL_DATA/$f" "$TMPLIVE" 2>&1); then
        echo "  ⛔ $f 거부 — $REASON"
        echo "     (의도한 삭제면 $LOCAL_DATA/$f.allow-shrink 를 만들고 다시 실행)"
        REJECTED=$((REJECTED+1)); rm -f "$TMPLIVE"; continue
      fi
      rm -f "$TMPLIVE"
    fi
    scp -i "$SSH_KEY" -o StrictHostKeyChecking=no \
      "$LOCAL_DATA/$f" \
      "$REMOTE_USER@$REMOTE_HOST:$PROD_DATA_DEST" \
      && echo "  ✓ $f"
  else
    echo "  - $f 없음(스킵)"
  fi
done
if [ "$REJECTED" -gt 0 ]; then
  echo ""
  echo "❌ JSON ${REJECTED}건이 검증에서 거부됐습니다. jar 배포/재시작을 중단합니다."
  echo "   prod 데이터를 잃지 않으려면 로컬 파일을 먼저 바로잡으세요."
  exit 1
fi

# ★jar 업로드는 반드시 JSON 검증 통과 **후**에. 2026-08-03 사고: 예전엔 jar을 이 지점보다
#   먼저 scp하고 그 뒤 JSON 게이트에서 exit 1 → 라이브 jar만 갈린 채 재시작이 안 돼서
#   lazy-load NoClassDefFoundError가 터진다(/칭호·계단앉기 등 전방위 고장). 순서를 바꿔 원천 차단한다.
echo ""
if [ -x "$SCRIPTS_REPO/ops/sync-blockship-data.sh" ]; then
  echo ""
  echo "▶ 레포 미러 갱신 (ops/blockship-data/)"
  "$SCRIPTS_REPO/ops/sync-blockship-data.sh" || true
fi

echo "▶ 오라클 서버에 jar SCP 업로드 (JSON 검증 통과 후)"
echo "  목적지: $PROD_JAR_DEST"

if ! scp -i "$SSH_KEY" -o StrictHostKeyChecking=no \
  "$LOCAL_JAR" \
  "$REMOTE_USER@$REMOTE_HOST:$PROD_JAR_DEST"; then
  if [ "$RESTART_PROD" = 1 ]; then
    echo "🔴 JAR 업로드 실패 — 기존 JAR로 prod를 다시 기동한다" >&2
    ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no \
      "$REMOTE_USER@$REMOTE_HOST" 'sudo systemctl start mcserver' || true
  fi
  exit 1
fi
REMOTE_JAR_SOURCE="${PROD_JAR_DEST%/}/$JAR_NAME"

echo ""
if [ "$RESTART_PROD" = 0 ]; then
  echo "⏸ prod 재시작 생략 — 전체 배포 래퍼가 임시 JAR을 라이브로 승격한 뒤 재시작할 것"
else
  echo "▶ 오라클 BlockShip 적용 — 정지 후 원자 승격, 기동 (★plugman reload 금지: 클래스로더 손상 NoClassDefFoundError)"
  if ! ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no \
    "$REMOTE_USER@$REMOTE_HOST" \
    "set -e
     sudo systemctl stop mcserver
     test -s '$REMOTE_JAR_SOURCE'
     for f in npc.json dialogue.json titles.json parts.json enhance.json recipes.json materials.json item-flavor.json; do
       test -s '$PROD_DATA_DEST'\$f
     done
     if [ -f '$REMOTE_LIVE_JAR' ]; then
       cp '$REMOTE_LIVE_JAR' \"/home/ubuntu/mcserver/backups/BlockShip-prev-\$(date +%Y%m%d%H%M%S).jar\"
     fi
     for f in npc.json dialogue.json titles.json parts.json enhance.json recipes.json materials.json item-flavor.json; do
       mv '$PROD_DATA_DEST'\$f \"/home/ubuntu/mcserver/plugins/BlockShip/\$f\"
     done
     mv '$REMOTE_JAR_SOURCE' '$REMOTE_LIVE_JAR'
     sudo systemctl start mcserver
     echo '✓ prod 기동 요청됨 (베타 유저 ~45초 끊김, 부팅 후 자동 복귀)'"; then
    echo ""
    echo "🔴 BlockShip 교체/기동 실패 — prod 기동 상태를 확인해야 한다." >&2
    echo "   확인: ssh -i $SSH_KEY $REMOTE_USER@$REMOTE_HOST 'sudo systemctl status mcserver'" >&2
    ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no \
      "$REMOTE_USER@$REMOTE_HOST" 'sudo systemctl start mcserver' || true
    exit 1
  fi
  [ -z "$REMOTE_STAGE" ] || ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no \
    "$REMOTE_USER@$REMOTE_HOST" "rm -rf '$REMOTE_STAGE'" || true
fi

# 즉시 배포는 staging/ 을 라이브와 같은 상태로 맞춘다 — 남아 있는 낡은 jar/설정이
# 그날 밤 06:00 nightly 에 라이브를 덮어써 조용히 되돌리는 것을 막는다.
# --no-restart 는 아직 JAR 을 승격하지 않았으므로 래퍼(deploy-all-prod.sh)가 맡는다.
if [ "$RESTART_PROD" = 1 ]; then
  "$SELF_DIR/sync-prod-staging.sh" --jar-name "$JAR_NAME" --with-config \
    || echo "⚠ staging 동기화 실패 — 06:00 되돌림 위험. ops/sync-prod-staging.sh 를 직접 돌릴 것" >&2
fi

# ★루프 닫기 — prod 가 «진짜 그 커밋»을 실었는지 부팅 로그의 빌드 스탬프로 확인한다.
#   jar sha1 대조만으로는 「내가 올린 파일이 그대로 있다」까지만 알 수 있고, 그게 어느
#   커밋인지는 모른다. 2026-08-31 에 prod jar 은 mtime 최신·sha1 일치였는데 내용이
#   며칠 전이었다(다른 세션이 낡은 체크아웃에서 빌드). 스탬프가 그 구멍을 막는다.
if [ "$RESTART_PROD" = 1 ] && [ -n "${BUILD_COMMIT:-}" ] && [ "$BUILD_COMMIT" != "unknown" ]; then
  echo ""
  echo "▶ prod 빌드 스탬프 대조 (부팅 대기)"
  WANT="${BUILD_COMMIT:0:12}"
  GOT=""
  # ★재시작 직후에는 latest.log 가 아직 «이전 세션»의 것이다. 그 로그에도 [Build] 줄과
  #   「For help, type」이 둘 다 들어 있으므로, 무엇을 «기다림 조건»으로 삼아도 옛 로그가
  #   즉시 만족시켜 버린다 — 정상 배포를 실패로 오탐한다(2026-08-31 두 번 겪었다).
  #   ⇒ 조건을 바꾸지 말고 **원하는 값이 나올 때까지 폴링**한다. 타임아웃까지 안 나오면
  #     그게 진짜 실패다(승격 안 됨 / staging 잔존 / 다른 세션이 덮음).
  for _ in $(seq 1 60); do
    GOT="$(ssh -o BatchMode=yes -o ConnectTimeout=8 -i "$SSH_KEY" "$REMOTE_USER@$REMOTE_HOST" \
      "grep -o '\[Build\] commit=[0-9a-f]*' ~/mcserver/logs/latest.log | tail -1 | cut -d= -f2" 2>/dev/null || true)"
    [ "$GOT" = "$WANT" ] && break
    sleep 5
  done
  if [ -z "$GOT" ]; then
    echo "  ⚠ 스탬프를 못 읽었다 — 아직 부팅 중이거나 스탬프 없는 구 jar 이다"
  elif [ "$GOT" = "$WANT" ]; then
    echo "  ✓ prod 가 commit $WANT 을 돌고 있다 (배포한 것과 일치)"
  else
    echo "  ❌ prod 가 commit $GOT 을 돌고 있다 — 배포한 것은 $WANT 다!"
    echo "     jar 이 승격되지 않았거나(staging 잔존) 다른 세션이 덮었다."
    echo "     확인: ops/rollback-jar.sh 목록 / ssh ... 'ls -la ~/mcserver/staging'"
    exit 1
  fi
fi

echo ""
echo "✅ 배포 완료"
echo "  - 로컬 패더(dev): plugins/ 복사 + (가동중이면) 자동 재시작 완료"
if [ "$RESTART_PROD" = 0 ]; then
  echo "  - 오라클(prod): JAR/JSON 업로드 완료, JAR 승격·재시작은 아직 안 함"
else
  echo "  - 오라클(prod): 정지→JAR 교체→기동 완료 (접속자 없을 때 돌리는 게 안전)"
fi
