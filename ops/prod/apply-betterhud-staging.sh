#!/usr/bin/env bash
# =====================================================================
# BetterHud 정의·자산 스테이징 적용기 (prod 온박스)
#
#   apply-betterhud-staging.sh --pre    재시작 «전»: staging/betterhud → 활성 경로
#   apply-betterhud-staging.sh --post   재시작 «후»: 팩 갱신 → 공개 배치 → sha1 → 재시작
#   apply-betterhud-staging.sh --status  대기 중인지만 판정(출력 없음, 0=대기 있음)
#
# 왜 이게 필요한가 —
#   BetterHud 자산(대화창 초상화 등)은 CraftEngine 생성 팩에 병합되어 클라로 간다.
#   그래서 «파일만 바꾸면» 끝이 아니고 재시작(build.zip 재생성) → 팩 재생성 →
#   공개 팩 교체 → CE config sha1 갱신 → 재시작이 한 묶음이다. 이 체인이 맥의
#   deploy-prod.sh 안에만 있어서 **재시작을 지금 감수하지 않으면 배포가 불가능**했다.
#   (jar 처럼 staging 에 올려두고 06:00 에 적용되는 경로가 없었다.)
#
#   막혀 있던 지점은 «공개 팩 교체»였다: 예전엔 GitHub Release 자산이라 업로드에
#   contents:write 가 필요한데 prod 토큰은 read 전용이고 gh CLI 도 없다. 그래서
#   2026-09-02 에 CE 팩을 **Caddy 자체 서빙**(barkan.kr/barkan-furniture.zip)으로
#   옮겼다 — 이제 prod 는 파일 복사 + sha1 갱신만 하면 되고 외부 권한이 필요 없다.
#
# ★순서가 안전의 전부다:
#   공개 파일 · config sha1 · CE 메모리(마지막 기동 시점의 config) **세 값이 일치**해야
#   클라가 팩을 받는다. 그래서 「공개 배치 → config 기록 → 재시작」 순이며, 재시작 뒤
#   로컬 팩이 다시 구워져 sha1 이 달라져도 그건 클라에 무해하다(경고만 남긴다).
#   반대로 config 만 먼저 갱신하고 재시작을 미루면 CE 는 옛 sha1 을 계속 보내면서
#   공개 파일은 새것이 되어 **전원 다운로드 실패**한다.
# =====================================================================
set -uo pipefail

DIR=${DIR:-$HOME/mcserver/scripts}
MC=${MC_ROOT:-$HOME/mcserver}
STAGING=${STAGING:-$MC/staging}
STAGE="$STAGING/betterhud"
BH="$MC/plugins/BetterHud"
CE="$MC/plugins/CraftEngine"
PACK="$CE/generated/resource_pack.zip"
CFG="$CE/config.yml"
WEBROOT=${WEBROOT:-/var/www/barkan}
PUBFILE=${PUBFILE:-barkan-furniture.zip}
PUBURL=${PUBURL:-https://barkan.kr/$PUBFILE}
MARKER="$MC/.betterhud-staging-applied"
BAKROOT="$MC/backups/betterhud-prev"
WEBHOOK_FILE=${WEBHOOK_FILE:-$DIR/discord-webhook.url}
LOG_FILE=${LOG_FILE:-$MC/backups/ops.log}
LABEL="[바르칸 prod]"
DRYRUN=${DRY:-0}

log() { local m="$(date -u +%Y-%m-%dT%H:%M:%SZ) [bh-staging] $*"; echo "$m"
        echo "$m" >> "$LOG_FILE" 2>/dev/null || true; }
notify() { [ -s "$WEBHOOK_FILE" ] || return 0; local u p; u=$(cat "$WEBHOOK_FILE")
  p=$(python3 -c "import json,sys;print(json.dumps({'content':sys.argv[1]}))" "$1")
  curl -sf -m 15 -H 'Content-Type: application/json' -d "$p" "$u" >/dev/null 2>&1 || true; }
rcon() { "$DIR/rcon.py" "$1" >/dev/null 2>&1; }
sha1of() { sha1sum "$1" | cut -c1-40; }

# 정의 파일이 «부분»인지 본다. 대화창 정의는 NPC별 초상화 1160벌이라 정상값이 1000+ 다.
# 100 개짜리 파일이 올라오면 그건 누군가의 낡은 사본이고, 덮으면 초상화가 통째로 죽는다.
def_count() { grep -cE '^npc_dialogue' "$1" 2>/dev/null || echo 0; }

pre() {
  [ -d "$STAGE" ] && [ -n "$(ls -A "$STAGE" 2>/dev/null)" ] || exit 3

  local defs_changed=0 rejected=""
  # --- 게이트 ① 정의 yml 이 올라왔으면 부분 파일인지 검사 ---
  local f n
  for f in npc-dialogue-hud.yml npc-dialogue-layout.yml npc-dialogue-image.yml; do
    [ -f "$STAGE/$f" ] || continue
    defs_changed=1
    n=$(def_count "$STAGE/$f")
    if [ "$n" -lt 100 ]; then
      rejected+="$f(정의 ${n}개) "
    fi
  done
  # --- 게이트 ② 폰트 yml 이 참조하는 ttf 가 실제로 있나 ---
  if [ -f "$STAGE/npc-dialogue-font.yml" ]; then
    while read -r ttf; do
      [ -n "$ttf" ] || continue
      [ -f "$STAGE/assets/fonts/$ttf" ] || [ -f "$BH/fonts/$ttf" ] || rejected+="폰트누락($ttf) "
    done < <(grep -E '^ *file: *' "$STAGE/npc-dialogue-font.yml" | sed 's/.*file: *//')
  fi
  if [ -n "$rejected" ]; then
    local rej="$STAGING-rejected/betterhud-$(TZ=Asia/Seoul date +%Y%m%d-%H%M%S)"
    mkdir -p "$rej"; cp -a "$STAGE"/. "$rej"/ 2>/dev/null || true; rm -rf "$STAGE"
    log "거부: $rejected"
    notify "$LABEL 🔴 **BetterHud 스테이징 거부** — $rejected
부분 파일이 라이브를 덮으려 했습니다. \`staging-rejected/\` 로 격리했습니다."
    echo "🔴 BetterHud 스테이징 거부: $rejected"
    exit 1
  fi

  local files; files=$(cd "$STAGE" && find . -type f ! -name '.*' | sed 's|^\./||' | sort)
  local cnt; cnt=$(printf '%s\n' "$files" | grep -c . || true)
  if [ "$DRYRUN" = "1" ]; then
    log "DRY: would apply $cnt files (defs_changed=$defs_changed)"
    echo "🎨 BetterHud 자산 ${cnt}개 (DRY)"
    return 0
  fi

  # --- 백업: 덮어쓸 파일의 «현재» 모습만 (롤백용) ---
  local bak="$BAKROOT/$(TZ=Asia/Seoul date +%Y%m%d-%H%M%S)"
  mkdir -p "$bak"
  local rel dst
  while read -r rel; do
    [ -n "$rel" ] || continue
    case "$rel" in
      assets/*) dst="$BH/$rel" ;;
      *-hud.yml) dst="$BH/huds/$rel" ;;
      *-layout.yml) dst="$BH/layouts/$rel" ;;
      *-image.yml) dst="$BH/images/$rel" ;;
      *-font.yml) dst="$BH/texts/$rel" ;;
      *) dst="" ;;
    esac
    [ -n "$dst" ] && [ -f "$dst" ] && { mkdir -p "$bak/$(dirname "$rel")"; cp -f "$dst" "$bak/$rel"; }
  done <<< "$files"

  # --- 적용 ---
  cp -f "$STAGE"/*-hud.yml    "$BH/huds/"    2>/dev/null || true
  cp -f "$STAGE"/*-layout.yml "$BH/layouts/" 2>/dev/null || true
  cp -f "$STAGE"/*-image.yml  "$BH/images/"  2>/dev/null || true
  cp -f "$STAGE"/*-font.yml   "$BH/texts/"   2>/dev/null || true
  [ -d "$STAGE/assets" ] && cp -a "$STAGE/assets/." "$BH/assets/"
  # ★macOS 가 끼워넣는 AppleDouble. assets/ 에 남으면 BetterHud 가 이미지로 읽으려다 폰트가 깨진다.
  find "$BH/assets" -name '._*' -delete 2>/dev/null || true

  # --- 적용 후 재검증(복사가 실제로 라이브를 부분 파일로 만들지 않았나) ---
  n=$(def_count "$BH/huds/npc-dialogue-hud.yml")
  if [ "$n" -lt 100 ]; then
    log "치명: 적용 후 대화창 정의가 ${n}개 — 백업에서 되돌린다 ($bak)"
    cp -a "$bak"/. "$BH"/ 2>/dev/null || true
    notify "$LABEL 🔴 **BetterHud 적용 실패** — 적용 후 대화창 정의가 ${n}개뿐이라 되돌렸습니다.
백업: \`$bak\`"
    echo "🔴 BetterHud 적용 실패(정의 ${n}개) — 롤백함"
    exit 1
  fi

  # ★캐시·build.zip 을 지워야 재기동 때 새 자산으로 다시 굽는다. 안 지우면 파일은
  #   갈렸는데 구운 결과는 옛것이라 «아무것도 안 바뀐» 것처럼 보인다.
  rm -f "$BH"/.cache/*.txt "$BH/build.zip"

  printf 'defs_changed=%s\ncount=%s\nbackup=%s\nfiles=%s\n' \
    "$defs_changed" "$cnt" "$bak" "$(printf '%s' "$files" | tr '\n' ',')" > "$MARKER"
  rm -rf "$STAGE"
  log "적용 $cnt 개 (정의변경=$defs_changed) 백업=$bak"
  echo "🎨 BetterHud 자산 ${cnt}개 적용(재시작 후 팩 갱신)"
}

wait_boot() {
  local i
  for i in $(seq 1 60); do
    systemctl is-active --quiet mcserver && "$DIR/rcon.py" list >/dev/null 2>&1 && return 0
    sleep 5
  done
  return 1
}

post() {
  [ -f "$MARKER" ] || exit 3
  local defs_changed; defs_changed=$(grep -oP '(?<=^defs_changed=).*' "$MARKER" || echo 0)

  if [ "$DRYRUN" = "1" ]; then log "DRY: would refresh pack + publish"; return 0; fi

  wait_boot || { log "부팅 확인 실패 — 팩 갱신 중단"
    notify "$LABEL 🔴 **BetterHud 팩 갱신 중단** — 재시작 후 RCON 무응답."; return 1; }
  local i
  for i in $(seq 1 40); do [ -f "$BH/build.zip" ] && break; sleep 3; done
  [ -f "$BH/build.zip" ] || { log "build.zip 이 안 생겼다"; notify "$LABEL 🔴 BetterHud build.zip 미생성"; return 1; }
  # 경험치 바 리스너 등록으로 BetterHud 가 한 번 더 리로드한다 — 그게 끝나야 최종본이다
  for i in $(seq 1 20); do grep -q "barkan_exp 리스너 등록 후" "$MC/logs/latest.log" && break; sleep 3; done
  sleep 8

  # ★정의를 바꿨으면 셰이더의 HUD 좌표표가 바뀐다 — 사본을 그대로 두면 HUD 가 화면 밖으로 날아간다
  if [ "$defs_changed" = "1" ]; then
    "$DIR/betterhud-26-1-fix.sh" 2>&1 | grep -E 'SHADER|✅|❌' || true
  fi

  # --- 팩 안정화 대기 (CE 는 reload 후 비동기로 zip 을 여러 번 다시 쓴다) ---
  rcon "ce reload all"; sleep 10
  local last="" stable=0 cur size
  for i in $(seq 1 24); do
    cur=$(sha1of "$PACK"); size=$(stat -c %s "$PACK")
    if [ "$cur" = "$last" ] && [ "$size" -gt 1000000 ]; then stable=$((stable+1)); else stable=0; fi
    last="$cur"; [ "$stable" -ge 3 ] && break; sleep 10
  done
  [ "$stable" -ge 3 ] || { log "팩이 안정화되지 않음"; notify "$LABEL 🔴 BetterHud: CE 팩이 안정화되지 않았습니다."; return 1; }
  local X="$last"
  log "팩 sha1=$X"

  # --- 공개 배치 (원자적으로: 임시파일에 쓰고 mv) ---
  sudo cp -f "$PACK" "$WEBROOT/.$PUBFILE.tmp"
  sudo chmod 644 "$WEBROOT/.$PUBFILE.tmp"
  sudo mv -f "$WEBROOT/.$PUBFILE.tmp" "$WEBROOT/$PUBFILE"

  local PUB=""
  for i in 1 2 3; do
    curl -fsSL --max-time 300 "$PUBURL" -o /tmp/bhpub.zip 2>/dev/null \
      && PUB=$(sha1of /tmp/bhpub.zip) && rm -f /tmp/bhpub.zip
    [ "$PUB" = "$X" ] && break
    log "공개 URL 불일치(공개=$PUB) 10초 후 재시도"; sleep 10
  done
  [ "$PUB" = "$X" ] || { log "공개 파일이 팩과 다르다 (공개=$PUB 팩=$X)"
    notify "$LABEL 🔴 **BetterHud 팩 공개 실패** — 공개파일(\`$PUB\`) != 서버팩(\`$X\`). CE 설정은 건드리지 않았습니다."; return 1; }

  # --- CE config sha1 갱신 (sha1 줄 자체를 통째로 갈아끼운다 — 부분치환은 잡종 sha1 을 만든다) ---
  cp -f "$CFG" "$CFG.bak-bhstaging-$(TZ=Asia/Seoul date +%Y%m%d-%H%M%S)"
  awk -v s="$X" '/^ *sha1: / { sub(/"[0-9a-fA-F]*"/, "\"" s "\"") } { print }' "$CFG" > "$CFG.new"
  mv -f "$CFG.new" "$CFG"
  [ "$(grep -oE '[0-9a-f]{40}' "$CFG" | head -1)" = "$X" ] || {
    log "CE config 갱신 실패"; notify "$LABEL 🔴 BetterHud: CE config sha1 갱신 실패"; return 1; }

  # --- ★마지막 재시작: 이게 있어야 CE 메모리가 새 sha1 을 들고 클라에 보낸다 ---
  local n; n=$("$DIR/rcon.py" list 2>/dev/null | grep -oE 'are [0-9]+' | grep -oE '[0-9]+' | head -1)
  [ "${n:-0}" -gt 0 ] 2>/dev/null && rcon "say [서버] HUD 자산 적용 마무리로 잠시 재시작합니다."
  sleep 2
  sudo systemctl restart mcserver
  wait_boot || { log "2차 재시작 후 부팅 확인 실패"
    notify "$LABEL 🔴 **BetterHud 마무리 재시작 후 RCON 무응답** — \`tail -50 ~/mcserver/logs/latest.log\`"; return 1; }

  # --- 최종 검증 ---
  local warn=""
  local cfg_sha; cfg_sha=$(grep -oE '[0-9a-f]{40}' "$CFG" | head -1)
  curl -fsSL --max-time 300 "$PUBURL" -o /tmp/bhpub2.zip 2>/dev/null || true
  local pub2=""; [ -f /tmp/bhpub2.zip ] && pub2=$(sha1of /tmp/bhpub2.zip) && rm -f /tmp/bhpub2.zip
  [ "$pub2" = "$cfg_sha" ] || { log "치명: 공개($pub2) != 설정($cfg_sha)"
    notify "$LABEL 🔴 **BetterHud: 재시작 후 공개팩≠설정sha1** — 클라가 가구팩 다운로드에 실패합니다.
공개 \`$pub2\` / 설정 \`$cfg_sha\`"; return 1; }
  # 로컬 팩이 재기동으로 다시 구워져 달라질 수 있다. 클라에는 무해하므로 경고만.
  local now_pack; now_pack=$(sha1of "$PACK")
  [ "$now_pack" = "$cfg_sha" ] || warn="⚠️ 재시작 후 로컬 팩이 다시 구워짐(공개본은 정상, 다음 배포에서 정렬)"

  rm -f "$MARKER"
  log "완료 sha1=$cfg_sha $warn"
  notify "$LABEL 🎨 **BetterHud 자산 배포 완료** (스테이징 → 06:00 자동 적용)
가구팩 \`${cfg_sha:0:12}\` · 공개 URL 검증 통과 · 재시작 후 정상
$warn"
}

case "${1:---status}" in
  --pre) pre ;;
  --post)
    echo "❌ prod 재시작 금지 정책: BetterHud post 적용(재시작 포함)은 영구 비활성화되었습니다." >&2
    exit 2
    ;;
  --status) [ -d "$STAGE" ] && [ -n "$(ls -A "$STAGE" 2>/dev/null)" ] || [ -f "$MARKER" ] ;;
  *) echo "usage: $0 --pre|--post|--status" >&2; exit 2 ;;
esac
