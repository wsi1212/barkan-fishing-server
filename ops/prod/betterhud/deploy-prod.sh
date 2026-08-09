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
JAR="${1:-}"

say() { echo; echo "── $* ──"; }

say "1) 파일 전송"
# ★COPYFILE_DISABLE=1 필수 — macOS 가 ._ AppleDouble 을 끼워넣는데, assets/ 에 들어가면
#   BetterHud 가 그걸 이미지로 읽으려다 폰트가 깨진다.
COPYFILE_DISABLE=1 tar cz -C "$SRC" \
  $(cd "$SRC" && ls *-hud.yml *-layout.yml *-image.yml *-font.yml 2>/dev/null) assets \
  | $SSH 'rm -rf /tmp/bhdeploy && mkdir -p /tmp/bhdeploy && tar xz -C /tmp/bhdeploy'
[ -n "$JAR" ] && scp -q -i "$HOME/.ssh/oracle-mc.key" "$JAR" ubuntu@168.107.8.107:/tmp/BlockShip-new.jar

say "2) 정지 → 교체 → 기동"
$SSH "set -e
BH=~/mcserver/plugins/BetterHud
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
find \$BH/assets -name '._*' -delete
if [ -f /tmp/BlockShip-new.jar ]; then
  cp ~/mcserver/plugins/BlockShip-1.0.0-SNAPSHOT.jar ~/mcserver/backups/BlockShip-prev.jar
  cp /tmp/BlockShip-new.jar ~/mcserver/plugins/BlockShip-1.0.0-SNAPSHOT.jar
  rm -f /tmp/BlockShip-new.jar
fi
rm -f \$BH/.cache/*.txt \$BH/build.zip
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
$SSH '~/mcserver/scripts/rcon.py "craftengine reload all" >/dev/null 2>&1; sleep 35
      sha1sum ~/mcserver/plugins/CraftEngine/generated/resource_pack.zip | cut -c1-40'

say "6) GitHub 업로드"
rm -f /tmp/barkan-furniture.zip
scp -q -i "$HOME/.ssh/oracle-mc.key" \
  ubuntu@168.107.8.107:'~/mcserver/plugins/CraftEngine/generated/resource_pack.zip' /tmp/barkan-furniture.zip
# ★파일명이 곧 릴리스 자산 이름이다. 다르면 덮어쓰지 않고 새 자산이 생긴다.
gh release upload latest /tmp/barkan-furniture.zip --clobber -R "$REPO"

say "7) 공개 URL 대조 → CE sha1 갱신"
$SSH "set -e
curl -sL '$URL' -o /tmp/pc.zip
PUB=\$(sha1sum /tmp/pc.zip|cut -c1-40); LOC=\$(sha1sum ~/mcserver/plugins/CraftEngine/generated/resource_pack.zip|cut -c1-40)
rm -f /tmp/pc.zip
[ \"\$PUB\" = \"\$LOC\" ] || { echo \"❌ 공개파일(\$PUB) != 서버팩(\$LOC)\"; exit 1; }
echo \"\$PUB\" | grep -qE '^[0-9a-f]{40}\$' || { echo '❌ sha1 형식 이상'; exit 1; }
OLD=\$(grep -oE '[0-9a-f]{40}' ~/mcserver/plugins/CraftEngine/config.yml|head -1)
sed -i \"s|sha1: \\\"\$OLD\\\"|sha1: \\\"\$PUB\\\"|\" ~/mcserver/plugins/CraftEngine/config.yml
[ \"\$(grep -oE '[0-9a-f]{40}' ~/mcserver/plugins/CraftEngine/config.yml|head -1)\" = \"\$PUB\" ] \
  || { echo '❌ CE config 갱신 실패'; exit 1; }
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
      echo "  메인팩 : $(~/mcserver/scripts/resourcepack-guard.sh --check 2>&1|tail -1)"
      echo "  예외   : $(grep -icE exception ~/mcserver/logs/latest.log)"
python3 - <<PY
import zipfile, json
# ★이 대조가 이번 사고의 직접 판정이다. 어긋나면 서버가 보내는 좌표와 클라 글리프 폭이
#   달라져서 "글자가 아이콘 위로 겹치고 새 그림은 [] 로 뜬다".
def fonts(path):
    z=zipfile.ZipFile(path); out={}
    for i in z.infolist():
        if i.filename.startswith("assets/betterhud/font/") and i.filename.endswith(".json"):
            try: raw=z.read(i)
            except zipfile.BadZipFile:
                i.orig_filename=""; raw=z.read(i)
            d=json.loads(raw)
            out[i.filename]=[(p.get("file","space"),p.get("height"),p.get("ascent")) for p in d["providers"]]
    return out
a=fonts("/home/ubuntu/mcserver/plugins/BetterHud/build.zip")
b=fonts("/home/ubuntu/mcserver/plugins/CraftEngine/generated/resource_pack.zip")
bad=[k for k in a if a[k]!=b.get(k)]
print("  폰트 대조:", "OK 전부 일치 (%d개)"%len(a) if not bad else "X 불일치: %s"%bad[:3])
PY'
echo; echo "✅ 배포 완료. 유저는 재접속해야 새 팩을 받는다."
