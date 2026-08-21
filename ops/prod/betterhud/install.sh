#!/bin/bash
# NPC 대화창 HUD 정의를 BetterHud 플러그인 폴더에 설치한다.
#
# ★왜 필요한가: BetterHud jar를 교체하거나 폴더를 지우고 다시 받으면 huds/·layouts/·
#   images/·texts/·assets/ 가 기본값으로 초기화되면서 npc_dialogue 정의와 대화창 그림이
#   통째로 사라진다. 2026-08-08 dev에서 실제로 발생했고, 증상은 "대사가 [] 네모로만 보임"
#   이었다 — 정의가 사라져 use-unifont(한글 11172자) 폰트가 생성되지 않았기 때문.
#   그러니 권위는 항상 이 폴더이고, BetterHud를 건드린 뒤에는 반드시 이 스크립트를 돌린다.
#
# 사용법:
#   ./install.sh                 # dev(Mac)에 설치
#   ./install.sh <BetterHud경로>  # 임의 경로(예: prod에서 ~/mcserver/plugins/BetterHud)
#
# 설치 후에는 서버를 재시작해야 한다. BetterHud가 build.zip을 다시 만들고,
# CraftEngine이 그걸 자기 리소스팩에 합쳐서 클라이언트로 보낸다.
# (CraftEngine 팩이 갱신되지 않으면 `ce reload all` 로 재생성)
set -e

SRC="$(cd "$(dirname "$0")" && pwd)"
DEV_BH="/Users/user/Library/Application Support/feather/player-server/servers/07de2d81-991a-47e2-b62d-06c0d1b5150a/plugins/BetterHud"
BH="${1:-$DEV_BH}"
AGGRO_FONT="${AGGRO_FONT:-/Users/user/development/barkan-resourcepack/assets/barkan/font/aggro_medium.ttf}"

[ -d "$BH" ] || { echo "❌ BetterHud 폴더가 없다: $BH" >&2; exit 1; }
[ -f "$AGGRO_FONT" ] || { echo "❌ Aggro 폰트를 찾을 수 없다: $AGGRO_FONT" >&2; exit 1; }

install_one() { # <원본파일> <대상폴더>
  mkdir -p "$2"
  cp "$1" "$2/"
  echo "   → $2/$(basename "$1")"
}

echo "[1] 정의 파일 설치 ($BH)"
# ★대화창 HUD 를 huds-disabled/ 로 빼 둔 박스가 있으면 그 결정을 존중한다.
#   dev(Mac, 힙 2G)는 npc-dialogue-hud.yml(165KB · 초상화 1160벌)을 읽는 순간 기동이 OOM 으로
#   죽는다. 그래서 dev 는 그 파일만 huds-disabled/ 에 둔 상태다. 여기서 무조건 huds/ 에
#   복사하면 dev 가 다시 못 뜬다(2026-08-21 이 스크립트에 buff 를 추가하며 발견).
for set in npc-dialogue status place buff; do
  dest="$BH/huds"
  [ "$set" = "npc-dialogue" ] && [ -f "$BH/huds-disabled/npc-dialogue-hud.yml" ] \
    && dest="$BH/huds-disabled" && echo "   (대화창 HUD 는 이 박스에서 꺼져 있다 → huds-disabled/ 로)"
  [ -f "$SRC/$set-hud.yml" ]    && install_one "$SRC/$set-hud.yml"    "$dest"
  [ -f "$SRC/$set-layout.yml" ] && install_one "$SRC/$set-layout.yml" "$BH/layouts"
  [ -f "$SRC/$set-image.yml" ]  && install_one "$SRC/$set-image.yml"  "$BH/images"
  [ -f "$SRC/$set-font.yml" ]   && install_one "$SRC/$set-font.yml"   "$BH/texts"
done

echo "[1.5] 서버 기본 폰트 설치"
install -m 0644 "$AGGRO_FONT" "$BH/aggro_medium.ttf"
mkdir -p "$BH/fonts"
install -m 0644 "$AGGRO_FONT" "$BH/fonts/aggro_medium.ttf"
sed -i '' -E 's|^default-font-name:.*$|default-font-name: aggro_medium.ttf|' "$BH/config.yml"
cat > "$BH/font.yml" <<'EOF'
scale: 16
height: 8
ascent: 7
merge-default-bitmap: false
use-unifont: false
EOF

# ★HUD 전용 폰트(assets/fonts/aggro_medium_hud.ttf = build_hud_font.py 산출물)도 넣는다.
#   npc-dialogue-font.yml 이 이 파일을 가리키는데 여기서 안 넣고 있었다 — dev 에는 아예
#   없었고(2026-08-21 확인), 그러면 대화창·상태판·위치판·버프판 글자가 통째로 안 나온다.
#   prod 는 deploy-prod.sh 가 assets/fonts/*.ttf 를 넣어 주고 있어서 여태 안 드러났다.
if compgen -G "$SRC/assets/fonts/*.ttf" >/dev/null; then
  mkdir -p "$BH/fonts"
  for f in "$SRC"/assets/fonts/*.ttf; do
    install -m 0644 "$f" "$BH/fonts/$(basename "$f")"
    echo "   → fonts/$(basename "$f")"
  done
fi

echo "[2] 그림 설치"
# 상태 HUD 아트는 gui-forge/build_status_hud.py 산출물이다. 손으로 고치지 말고 다시 구울 것.
for dir in dialogue status; do
  [ -d "$SRC/assets/$dir" ] || continue
  mkdir -p "$BH/assets/$dir"
  # gen/ 아래의 크기별 산출물도 포함한다. 1단계 복사만 하면 YAML이 참조하는
  # dialogue/gen·status/gen 파일이 빠져 BetterHud가 이미지를 조용히 누락한다.
  cp -R "$SRC/assets/$dir/." "$BH/assets/$dir/"
  find "$BH/assets/$dir" -type f -print | sed "s|$BH/assets/$dir/|   → $dir/|"
done

# ★2026-08-08: BetterHud 기본 제공 정의를 전부 지웠다(되돌리지 않음).
#   entity-popup(때리면 뜨는 체력 팝업) / default-hud(데모 바) / default_compass(나침반)
#   과 그것들만 쓰던 layouts·images·texts·assets. 팩에 쓸데없는 폰트·텍스처가 계속
#   구워지고 있었고, 체력 팝업은 트리거 기반이라 default-popup 이 비어도 자동으로 떴다.
#   BetterHud 를 재설치하면 이 파일들이 되살아나므로, 그때 다시 지울 것.
BH_DEFAULTS=(popups/entity-popup.yml huds/default-hud.yml compasses/default_compass.yml
             layouts/entity-layout.yml layouts/default-layout.yml
             images/entity-image.yml images/entity-head-image.yml images/default-image.yml
             texts/entity-font.yml)
echo "[2.5] BetterHud 기본 정의 제거 (재설치 시 되살아남)"
for f in "${BH_DEFAULTS[@]}"; do
  [ -e "$BH/$f" ] && rm -f "$BH/$f" && echo "   x $f"
done
rm -rf "$BH/assets/entity" "$BH/assets/compass"; rm -f "$BH"/assets/*.png

echo "[3] 검증"
missing=0
# npc-dialogue-image.yml 이 참조하는 파일이 실제로 있는지 확인한다.
for f in $(grep -hoE 'file: *(dialogue|status)/[^ ]+\.png' "$SRC"/*-image.yml | awk '{print $2}' | sort -u); do
  [ -f "$BH/assets/$f" ] || { echo "   ❌ 누락: assets/$f"; missing=1; }
done
# HUD 글자 폰트가 실제로 설치돼 있는지 확인한다.
# ★옛날엔 'aggro_medium.ttf' 문자열을 찾았는데, 폰트가 aggro_medium_hud.ttf(기호 7자를
#   추가한 것)로 바뀐 뒤로 이 검사는 항상 실패하고 있었다 — 늘 빨간 검사는 아무도 안 본다.
#   지금은 yml 이 가리키는 파일명을 읽어서 그 파일이 있는지 본다.
HUDFONT=$(grep -E "^ *file: *" "$BH/texts/npc-dialogue-font.yml" | head -1 | sed "s/.*file: *//")
[ -n "$HUDFONT" ] && [ -f "$BH/fonts/$HUDFONT" ] \
  || { echo "   ❌ HUD 폰트 누락: fonts/$HUDFONT (build_hud_font.py 를 돌릴 것)"; missing=1; }
grep -q 'merge-default-bitmap: *false' "$BH/font.yml" \
  || { echo "   ❌ 보스바가 BetterHud 기본 폰트를 계속 사용한다"; missing=1; }
[ -f "$BH/aggro_medium.ttf" ] && [ -f "$BH/fonts/aggro_medium.ttf" ] \
  || { echo "   ❌ Aggro Medium TTF 설치 누락"; missing=1; }
[ "$missing" = "0" ] && echo "   ✅ 참조 그림·Aggro Medium 폰트 설정 정상"

echo
echo "✅ 설치 완료. 이제 서버를 재시작할 것:"
echo "   dev  : ~/dev-mc.sh restart"
echo "   prod : sudo systemctl restart mcserver"
echo "재시작 뒤 build.zip 에 hud_npc_dialogue_text_* 가 400KB 이상(=한글 포함)인지 확인하면 확실하다."

echo
cat <<'NOTE'
────────────────────────────────────────────────────────────────────
★HUD 정의를 바꿨다면(추가·삭제) prod 배포는 이 순서를 지킬 것.
  셰이더 안에 HUD별 좌표표(switch (id))가 구워지는데, 정의가 바뀌면 id 배정이
  바뀐다. 한 단계라도 빠지면 서버는 새 id 로 보내고 클라는 옛 표를 써서
  HUD가 통째로 화면 밖으로 날아간다("[] 네모도 없이 아무것도 안 보임").

★RCON 으로 `betterhud reload` 는 안 먹는다 — 출력도 로그도 없이 exit 0 만 나오고
  실제로는 아무 일도 안 일어난다(`execute as <player> run` 도 마찬가지). 재시작뿐이다.
  돌았는지 판정은 `plugins/BetterHud/build.zip` 의 mtime 으로 할 것.

★가로(x)만 바꿨다면 위 절차 전부 불필요 — 정지→교체→기동이면 끝난다.
  생성 폰트(hud_*_image.json)에는 세로만 ascent 로 구워지고 가로 좌표는 없다.
  가로는 서버가 매번 보내는 네거티브 스페이스 문자로 잡기 때문이다.
  그래서 x만 고치면 팩이 바이트 단위로 그대로다(sha1 동일). 고장이 아니다.

  1) 정지 → 파일 교체 → BetterHud/.cache/*.txt·build.zip 삭제 → 기동
  2) ~/mcserver/scripts/betterhud-26-1-fix.sh      # 26.1 셰이더 다시 뽑기
  3) ce reload all
  4) generated/resource_pack.zip → barkan-furniture.zip 이름으로 gh release upload --clobber
  5) 공개 URL sha1 확인 → CraftEngine/config.yml 의 external sha1 갱신
  6) ★재시작                                       # 없으면 클라가 새 팩을 안 받는다

  검증: build.zip 과 배포팩의 switch (id) 문자열이 같은지 대조.
────────────────────────────────────────────────────────────────────
NOTE
