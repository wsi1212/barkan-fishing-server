#!/bin/bash
# 리소스팩 배포: ~/development/barkan-resourcepack → GitHub latest + prod sha1 갱신.
# ※ zip 이름은 반드시 barkan-resourcepack.zip (다운로드 URL이 이 이름을 찾음 — rp.zip 등이면 404!).
set -e
RP="$HOME/development/barkan-resourcepack"
ZIP="/tmp/barkan-resourcepack.zip"
REPO="wsi1212/minecraft-fish-resource-pack"
echo "[1] zip 생성..."
rm -f "$ZIP"
( cd "$RP" && zip -rq "$ZIP" assets pack.mcmeta -x "*.DS_Store" )
echo "    $(wc -c < "$ZIP")b ($(unzip -l "$ZIP" | tail -1 | awk '{print $2}') 파일)"
SHA=$(shasum "$ZIP" | awk '{print $1}')
echo "[2] GitHub 릴리스에 barkan-resourcepack.zip asset만 교체..."
# ※ release delete 금지! 같은 release의 barkan-furniture.zip(CraftEngine RP)이 같이 날아감.
#   release가 없을 때만 생성하고, 평소엔 asset만 --clobber로 덮어쓴다 (다른 asset 보존).
gh release view latest --repo "$REPO" >/dev/null 2>&1 || gh release create latest --repo "$REPO" --title "Latest" --notes "" >/dev/null
gh release upload latest "$ZIP" --repo "$REPO" --clobber >/dev/null
echo "    sha1: $SHA"

# GitHub는 same-name asset 교체 뒤 짧은 시간 동안 이전 CDN 바이트를 돌려줄 수 있다.
# 이때 로컬 ZIP의 SHA만 server.properties에 쓰고 바로 재시작하면 강제 리소스팩
# 다운로드가 전원 실패한다. 공개 URL에서 다시 내려받은 바이트가 정확히 일치할 때만
# 운영 설정을 바꾼다.
PACK_URL="https://github.com/$REPO/releases/download/latest/barkan-resourcepack.zip"
VERIFY="/tmp/barkan-resourcepack-verify-$$.zip"
trap 'rm -f "$VERIFY"' EXIT
echo "[3] GitHub 공개 URL SHA1 반영 대기·검증..."
ready=0
for attempt in $(seq 1 30); do
  rm -f "$VERIFY"
  if curl --fail --location --silent --show-error --retry 2 --retry-delay 2 \
      --connect-timeout 15 --max-time 240 --proto '=https' --tlsv1.2 \
      "$PACK_URL" --output "$VERIFY"; then
    LIVE_SHA=$(shasum "$VERIFY" | awk '{print $1}')
    if [ "$LIVE_SHA" = "$SHA" ]; then
      ready=1
      break
    fi
    echo "    아직 이전 asset 응답 ($LIVE_SHA, ${attempt}/30)"
  else
    echo "    공개 URL 다운로드 실패 (${attempt}/30)"
  fi
  sleep 2
done
[ "$ready" = "1" ] || { echo "❌ 공개 URL SHA1이 새 팩과 일치하지 않아 운영 설정·재시작을 중단합니다." >&2; exit 1; }

# ★prod는 이 GitHub 팩을 쓰지 않는다 (2026-08-08 확인).
#   prod resource-pack = https://barkan.kro.kr/barkan-resourcepack.zip
#     → Caddy가 /var/www/barkan/barkan-resourcepack.zip 을 서빙하고,
#       그 파일은 "메인 팩 + BetterHud build.zip 병합본"이라 이 zip과 내용이 다르다.
#   예전 순서(sed로 SHA1 먼저 박고 나서 검증)는 prod가 서빙하는 파일과 무관한 해시를
#   server.properties에 남겼다. 가드가 재시작은 막아주지만 오염된 SHA1은 그대로 남아
#   디스코드 경보가 계속 울리고, 다음 재시작 때 require-resource-pack 때문에
#   전원이 접속 차단된다. (2026-08-08 실제 발생)
# 그래서 prod가 이미 이 바이트를 서빙하고 있을 때만 SHA1을 건드린다.
echo "[4] prod가 이 팩을 서빙 중인지 먼저 확인..."
PROD_URL=$(ssh -i ~/.ssh/oracle-mc.key -o ConnectTimeout=12 ubuntu@168.107.8.107 \
  "sed -n 's/^resource-pack=//p' ~/mcserver/server.properties | head -n1 | sed 's/\\\\:/:/g'")
PROD_SHA=$(ssh -i ~/.ssh/oracle-mc.key -o ConnectTimeout=12 ubuntu@168.107.8.107 \
  "curl -fsSL --max-time 240 '$PROD_URL' | sha1sum | cut -d' ' -f1")

if [ "$PROD_SHA" = "$SHA" ]; then
  echo "[5] prod server.properties 갱신·원격 재검증..."
  ssh -i ~/.ssh/oracle-mc.key -o ConnectTimeout=12 ubuntu@168.107.8.107 \
    "sed -i 's/^resource-pack-sha1=.*/resource-pack-sha1=$SHA/' ~/mcserver/server.properties && ~/mcserver/scripts/resourcepack-guard.sh --check"
  echo "[6] prod 재시작..."
  ssh -i ~/.ssh/oracle-mc.key -o ConnectTimeout=12 ubuntu@168.107.8.107 \
    'sudo systemctl restart mcserver'
  echo "✅ 공개 URL과 prod SHA1 검증 후 재시작 명령까지 완료했습니다."
else
  cat <<EOF
✅ GitHub 팩 교체 완료 (dev가 쓰는 팩). sha1: $SHA
⏸  prod는 건드리지 않았습니다 — 서빙 경로가 다릅니다.
     prod URL : $PROD_URL
     prod 실제 : $PROD_SHA
     이번 팩   : $SHA
   prod에도 반영하려면 그 파일($PROD_URL 뒤의 /var/www/barkan/…)을 먼저 교체하고
   ~/mcserver/scripts/resourcepack-guard.sh --repair 로 SHA1을 맞춘 뒤 재시작할 것.
   ※prod 팩은 BetterHud build.zip 병합본이라 이 zip을 그대로 올리면 NPC 대화창이 깨집니다.
EOF
fi
