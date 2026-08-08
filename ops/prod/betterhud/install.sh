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
# (CraftEngine 팩이 갱신되지 않으면 `craftengine reload all` 로 재생성)
set -e

SRC="$(cd "$(dirname "$0")" && pwd)"
DEV_BH="/Users/user/Library/Application Support/feather/player-server/servers/07de2d81-991a-47e2-b62d-06c0d1b5150a/plugins/BetterHud"
BH="${1:-$DEV_BH}"

[ -d "$BH" ] || { echo "❌ BetterHud 폴더가 없다: $BH" >&2; exit 1; }

install_one() { # <원본파일> <대상폴더>
  mkdir -p "$2"
  cp "$1" "$2/"
  echo "   → $2/$(basename "$1")"
}

echo "[1] 정의 파일 설치 ($BH)"
install_one "$SRC/npc-dialogue-hud.yml"    "$BH/huds"
install_one "$SRC/npc-dialogue-layout.yml" "$BH/layouts"
install_one "$SRC/npc-dialogue-image.yml"  "$BH/images"
install_one "$SRC/npc-dialogue-font.yml"   "$BH/texts"

echo "[2] 대화창 그림 설치"
mkdir -p "$BH/assets/dialogue"
cp "$SRC/assets/dialogue/"*.png "$BH/assets/dialogue/"
ls "$BH/assets/dialogue" | sed 's/^/   → /'

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
for f in $(grep -oE 'file: *dialogue/[^ ]+\.png' "$SRC/npc-dialogue-image.yml" | awk '{print $2}' | sort -u); do
  [ -f "$BH/assets/$f" ] || { echo "   ❌ 누락: assets/$f"; missing=1; }
done
# 한글이 [] 네모로 깨지는 사고의 직접 원인 — unifont 병합 플래그가 살아있는지 본다.
grep -q 'use-unifont: *true' "$BH/texts/npc-dialogue-font.yml" \
  || { echo "   ❌ use-unifont 가 꺼져 있다 — 한글이 전부 네모로 나온다"; missing=1; }
[ "$missing" = "0" ] && echo "   ✅ 참조 그림·unifont 설정 정상"

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

  1) 정지 → 파일 교체 → BetterHud/.cache/*.txt·build.zip 삭제 → 기동
  2) ~/mcserver/scripts/betterhud-26-1-fix.sh      # 26.1 셰이더 다시 뽑기
  3) craftengine reload all
  4) generated/resource_pack.zip → barkan-furniture.zip 이름으로 gh release upload --clobber
  5) 공개 URL sha1 확인 → CraftEngine/config.yml 의 external sha1 갱신
  6) ★재시작                                       # 없으면 클라가 새 팩을 안 받는다

  검증: build.zip 과 배포팩의 switch (id) 문자열이 같은지 대조.
────────────────────────────────────────────────────────────────────
NOTE
