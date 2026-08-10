#!/bin/bash
# BetterHud 정의/아트를 prod 에 배포하는 전체 체인. ★손으로 나눠 치지 말 것.
#
# ★왜 스크립트인가: 2026-08-09 이 체인을 손으로 돌리다 중간(팩 업로드 직전)에 끊겼다.
#   서버는 새 폰트로 좌표를 보내는데 클라는 옛 팩을 쓰는 상태가 되어
#   "경험치 바가 [] 로 뜨고 글자가 아이콘 위로 겹침"이 났다. 중간 상태 자체가 고장이다.
#   한 단계라도 실패하면 즉시 멈추고(-e), 뭐가 남았는지 알려준다.
#
# 사용법:  ./deploy-prod.sh            # 정의·아트만
#          ./deploy-prod.sh <jar경로>   # BlockShip jar 도 같이
set -euo pipefail

SRC="$(cd "$(dirname "$0")" && pwd)"
SSH="ssh -i $HOME/.ssh/oracle-mc.key ubuntu@168.107.8.107"
REPO="wsi1212/minecraft-fish-resource-pack"
URL="https://github.com/$REPO/releases/download/latest/barkan-furniture.zip"
JAR=""
WITH_DIALOGUE=0
for a in "$@"; do
  case "$a" in
    --with-dialogue) WITH_DIALOGUE=1 ;;   # ★Codex 담당 파일까지 보낸다. 합의된 경우에만.
    *) JAR="$a" ;;
  esac
done
AGGRO_FONT="${AGGRO_FONT:-$HOME/development/barkan-resourcepack/assets/barkan/font/aggro_medium.ttf}"

[ -f "$AGGRO_FONT" ] || { echo "❌ Aggro 폰트를 찾을 수 없다: $AGGRO_FONT" >&2; exit 1; }

say() { echo; echo "── $* ──"; }

say "0) 보내기 전 검사"
# ★어그로체에는 ☀ ☁ ☂ ⚡ ❄ ≋ ☽ 같은 기호가 없다. 이 두 플래그를 끄면 그 글자가
#   MC 기본 폰트로 폴백되는데, 폴백 글리프는 BetterHud 의 위치 인코딩이 없어서
#   셰이더가 못 옮긴다 -> 그 글자만 화면 위 보스바 자리에 찍힌다(2026-08-10 실제 사고).
for k in "merge-default-bitmap" "use-unifont"; do
  grep -qE "^ *$k: *true" "$SRC/npc-dialogue-font.yml" \
    || { echo "❌ npc-dialogue-font.yml 의 $k 가 true 가 아니다 — 기호가 보스바로 샌다"; exit 1; }
done
echo "  폰트 플래그 OK"

say "1) 파일 전송"
# ★★대화창 정의(npc-dialogue-{hud,layout,image}.yml)와 assets/dialogue 는 보내지 않는다.
#   2026-08-10 현재 그쪽은 Codex 가 NPC별·표정별 초상화로 확장해 놓았다(정의 1160개).
#   여기서 같은 파일명을 덮으면 그 작업이 통째로 날아간다. 실제로 그럴 뻔했다.
#   대화창을 다시 이 스크립트로 관리하려면 먼저 양쪽 정의를 합치고 나서 이 목록에 넣을 것.
#   npc-dialogue-font.yml(폰트 설정)은 공용이라 보낸다.
# ★COPYFILE_DISABLE=1 필수 — macOS 가 ._ AppleDouble 을 끼워넣는데, assets/ 에 들어가면
#   BetterHud 가 그걸 이미지로 읽으려다 폰트가 깨진다.
SEND=$(cd "$SRC" && ls status-*.yml place-*.yml npc-dialogue-font.yml 2>/dev/null)
DIRS="assets/status"
if [ "$WITH_DIALOGUE" = 1 ]; then
  SEND="$SEND $(cd "$SRC" && ls npc-dialogue-hud.yml npc-dialogue-layout.yml npc-dialogue-image.yml 2>/dev/null)"
  DIRS="$DIRS assets/dialogue"
  echo "  ★--with-dialogue: 대화창 정의도 보낸다(Codex 담당 파일)"
fi
echo "  보낼 정의: $(echo $SEND | tr '\n' ' ')"
COPYFILE_DISABLE=1 tar cz -C "$SRC" $SEND $DIRS \
  | $SSH 'rm -rf /tmp/bhdeploy && mkdir -p /tmp/bhdeploy && tar xz -C /tmp/bhdeploy'
scp -q -i "$HOME/.ssh/oracle-mc.key" "$AGGRO_FONT" ubuntu@168.107.8.107:/tmp/aggro_medium.ttf
[ -n "$JAR" ] && scp -q -i "$HOME/.ssh/oracle-mc.key" "$JAR" ubuntu@168.107.8.107:/tmp/BlockShip-new.jar

say "2) 정지 → 교체 → 기동"
$SSH "set -e
BH=~/mcserver/plugins/BetterHud
install -m 0644 /tmp/aggro_medium.ttf \$BH/aggro_medium.ttf
mkdir -p \$BH/fonts
install -m 0644 /tmp/aggro_medium.ttf \$BH/fonts/aggro_medium.ttf
cp \$BH/config.yml \$BH/config.yml.bak-font-\$(date +%Y%m%d%H%M%S)
sed -i -E 's|^default-font-name:.*$|default-font-name: aggro_medium.ttf|' \$BH/config.yml
cat > \$BH/font.yml <<'EOF'
scale: 16
height: 8
ascent: 7
merge-default-bitmap: false
use-unifont: false
EOF
~/mcserver/scripts/rcon.py 'say [공지] HUD 업데이트 — 재시작합니다' >/dev/null 2>&1 || true
sleep 2
sudo systemctl stop mcserver || true
for i in \$(seq 1 30); do [ \"\$(systemctl is-active mcserver || true)\" = active ] || break; sleep 2; done
[ \"\$(systemctl is-active mcserver || true)\" = active ] && { echo '정지 실패'; exit 1; }
cp /tmp/bhdeploy/*-hud.yml    \$BH/huds/    2>/dev/null || true
cp /tmp/bhdeploy/*-layout.yml \$BH/layouts/ 2>/dev/null || true
cp /tmp/bhdeploy/*-image.yml  \$BH/images/  2>/dev/null || true
cp /tmp/bhdeploy/*-font.yml   \$BH/texts/   2>/dev/null || true
cp -r /tmp/bhdeploy/assets/* \$BH/assets/
# 안전망: 대화창 정의를 실수로 덮었는지 확인한다(Codex 작업물은 1000개 이상이다)
n=\$(grep -cE '^npc_dialogue' \$BH/huds/npc-dialogue-hud.yml 2>/dev/null || echo 0)
[ \"\$n\" -ge 100 ] || { echo \"❌ npc-dialogue-hud.yml 정의가 \$n 개뿐 — Codex 작업물을 덮었다\"; exit 1; }
echo \"  대화창 정의 \$n 개 보존 확인\"
find \$BH/assets -name '._*' -delete
if [ -f /tmp/BlockShip-new.jar ]; then
  cp ~/mcserver/plugins/BlockShip-1.0.0-SNAPSHOT.jar ~/mcserver/backups/BlockShip-prev.jar
  cp /tmp/BlockShip-new.jar ~/mcserver/plugins/BlockShip-1.0.0-SNAPSHOT.jar
  rm -f /tmp/BlockShip-new.jar
fi
rm -f \$BH/.cache/*.txt \$BH/build.zip
rm -f /tmp/aggro_medium.ttf
sudo systemctl start mcserver"

say "3) 기동 대기 (+ barkan_exp 리스너 리로드까지)"
$SSH 'until ~/mcserver/scripts/rcon.py list >/dev/null 2>&1; do sleep 5; done
      until [ -f ~/mcserver/plugins/BetterHud/build.zip ]; do sleep 3; done
      # 경험치 바 리스너를 쓰면 BlockShip 이 리로드를 한 번 더 건다 — 그게 끝나야 build.zip 이 최종본이다
      for i in $(seq 1 20); do grep -q "barkan_exp 리스너 등록 후" ~/mcserver/logs/latest.log && break; sleep 3; done
      sleep 8; echo "  기동 완료"'

say "4) 26.1 셰이더 다시 뽑기 (★현재 build.zip 에서. 사본 박제 금지)"
$SSH '~/mcserver/scripts/betterhud-26-1-fix.sh' | grep -E 'SHADER|❌' || true

say "5) CraftEngine 팩 재생성"
$SSH 'old=$(sha1sum ~/mcserver/plugins/CraftEngine/generated/resource_pack.zip|cut -c1-40)
      ~/mcserver/scripts/rcon.py "ce reload all" >/dev/null 2>&1; sleep 10
      # CraftEngine은 reload 직후 비동기로 ZIP을 여러 번 다시 쓴다. 첫 SHA1을
      # 바로 업로드하면 공개팩과 서버가 서로 다른 중간 산출물을 쓰게 된다.
      last=""; stable=0; changed=0
      for i in $(seq 1 24); do
        cur=$(sha1sum ~/mcserver/plugins/CraftEngine/generated/resource_pack.zip|cut -c1-40)
        size=$(stat -c %s ~/mcserver/plugins/CraftEngine/generated/resource_pack.zip)
        [ "$cur" != "$old" ] && changed=1
        if [ "$changed" = 1 ] && [ "$cur" = "$last" ] && [ "$size" -gt 1000000 ]; then stable=$((stable+1)); else stable=0; fi
        last="$cur"
        [ "$stable" -ge 3 ] && break
        sleep 10
      done
      [ "$changed" = 1 ] && [ "$stable" -ge 3 ] || { echo "❌ CraftEngine 팩 재생성/안정화되지 않음"; exit 1; }
      echo "$last"'

say "6) GitHub 업로드"
rm -f /tmp/barkan-furniture.zip
scp -q -i "$HOME/.ssh/oracle-mc.key" \
  ubuntu@168.107.8.107:'~/mcserver/plugins/CraftEngine/generated/resource_pack.zip' /tmp/barkan-furniture.zip
# ★파일명이 곧 릴리스 자산 이름이다. 다르면 덮어쓰지 않고 새 자산이 생긴다.
gh release upload latest /tmp/barkan-furniture.zip --clobber -R "$REPO"

say "7) 공개 URL 대조 → CE sha1 갱신"
$SSH "set -e
LOC=\$(sha1sum ~/mcserver/plugins/CraftEngine/generated/resource_pack.zip|cut -c1-40)
# ★GitHub CDN 이 새 자산을 바로 안 준다. 업로드 직후 한 번만 재보면 옛 파일이 잡혀서
#   멀쩡한 배포가 여기서 죽는다(2026-08-10 34MB 올릴 때 실제로 그랬다). 몇 번 기다렸다 다시 본다.
for try in 1 2 3 4 5 6; do
  curl -sL '$URL' -o /tmp/pc.zip
  PUB=\$(sha1sum /tmp/pc.zip|cut -c1-40); rm -f /tmp/pc.zip
  [ \"\$PUB\" = \"\$LOC\" ] && break
  echo \"  (CDN 지연 \$try/6: 공개=\$PUB) 15초 후 재시도\"; sleep 15
done
[ \"\$PUB\" = \"\$LOC\" ] || { echo \"❌ 공개파일(\$PUB) != 서버팩(\$LOC)\"; exit 1; }
echo \"\$PUB\" | grep -qE '^[0-9a-f]{40}\$' || { echo '❌ sha1 형식 이상'; exit 1; }
C=~/mcserver/plugins/CraftEngine/config.yml
OLD=\$(grep -oE '[0-9a-f]{40}' \$C|head -1)
# ★옛 값을 패턴으로 쓰지 말 것. 옛 값이 조금이라도 어긋나면 엉뚱하게 걸려 값이
#   이어붙는다 — 2026-08-10 실제로 '앞 14자리만 새 값' 인 잡종 sha1 이 만들어져
#   가구팩 다운로드가 계속 실패했다. sha1 줄 자체를 통째로 갈아끼운다.
awk -v s=\"\$PUB\" '/^ *sha1: / { sub(/\"[0-9a-fA-F]*\"/, \"\\\"\" s \"\\\"\"); } { print }' \$C > \$C.new
mv \$C.new \$C
[ \"\$(grep -oE '[0-9a-f]{40}' \$C|head -1)\" = \"\$PUB\" ] || { echo '❌ CE config 갱신 실패'; exit 1; }
echo \"  CE설정 \$OLD -> \$PUB\""

say "8) ★마지막 재시작 (없으면 클라가 새 팩을 안 받는다)"
$SSH 'sudo systemctl stop mcserver || true
      for i in $(seq 1 30); do [ "$(systemctl is-active mcserver || true)" = active ] || break; sleep 2; done
      [ "$(systemctl is-active mcserver || true)" = active ] && { echo "정지 실패"; exit 1; }
      sudo systemctl start mcserver
      until ~/mcserver/scripts/rcon.py list >/dev/null 2>&1; do sleep 5; done'

say "9) 검증"
$SSH 'echo "  서버   : $(systemctl is-active mcserver)"
      echo "  CE설정 : $(grep -oE "[0-9a-f]{40}" ~/mcserver/plugins/CraftEngine/config.yml|head -1)"
      echo "  서버팩 : $(sha1sum ~/mcserver/plugins/CraftEngine/generated/resource_pack.zip|cut -c1-40)"
      [ "$(grep -oE "[0-9a-f]{40}" ~/mcserver/plugins/CraftEngine/config.yml|head -1)" = "$(sha1sum ~/mcserver/plugins/CraftEngine/generated/resource_pack.zip|cut -c1-40)" ] || { echo "  ❌ CE설정과 서버팩 불일치"; exit 1; }
      echo "  메인팩 : $(~/mcserver/scripts/resourcepack-guard.sh --check 2>&1|tail -1)"
      echo "  예외   : $(grep -icE exception ~/mcserver/logs/latest.log)"
      BUILD_FONTS=$(unzip -Z1 ~/mcserver/plugins/BetterHud/build.zip | grep -c "^assets/betterhud/font/.*\\.json$")
      PACK_FONTS=$(unzip -Z1 ~/mcserver/plugins/CraftEngine/generated/resource_pack.zip | grep -c "^assets/betterhud/font/.*\\.json$")
      unzip -Z1 ~/mcserver/plugins/CraftEngine/generated/resource_pack.zip | grep -qx "assets/betterhud/font/default.json" \\
        || { echo "  ❌ 배포팩에 BetterHud 기본 폰트가 없음"; exit 1; }
      [ "$PACK_FONTS" -ge "$BUILD_FONTS" ] || { echo "  ❌ 배포팩 폰트 엔트리 부족: build=$BUILD_FONTS pack=$PACK_FONTS"; exit 1; }
      echo "  폰트 대조 : OK 엔트리 확인 (build=$BUILD_FONTS pack=$PACK_FONTS; 보호 ZIP이라 JSON 바이트 대조 생략)"'
say "10) ★재시작 후 sha1 재확인"
# 쓰는 시점에만 검사하면 그 뒤에 값이 망가져도 못 잡는다 — 2026-08-10 잡종 sha1 이
# 남아 가구팩 다운로드가 계속 실패했는데 배포는 성공으로 끝났었다.
$SSH "A=\$(sha1sum ~/mcserver/plugins/CraftEngine/generated/resource_pack.zip|cut -c1-40)
B=\$(grep -oE '[0-9a-f]{40}' ~/mcserver/plugins/CraftEngine/config.yml|head -1)
echo \"  팩 \$A\"; echo \"  설정 \$B\"
[ \"\$A\" = \"\$B\" ] || { echo '❌ 재시작 후 어긋남 — 클라가 가구팩 다운로드에 실패한다'; exit 1; }
echo '  ✅ 일치'"

echo; echo "✅ 배포 완료. 유저는 재접속해야 새 팩을 받는다."
