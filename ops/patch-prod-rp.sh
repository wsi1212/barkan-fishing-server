#!/bin/bash
# prod 리소스팩 부분 갱신 — 바뀐 파일만 갈아 끼운다. 재시작은 하지 않는다.
#
# ## 왜 ~/deploy-rp.sh 를 못 쓰나
# deploy-rp.sh 는 GitHub 릴리스로 올린다. 그런데 **prod 는 GitHub 를 안 쓴다** —
# server.properties 의 resource-pack 이 https://barkan.kro.kr/... 이고 그건 박스의
# Caddy 가 /var/www/barkan/ 에서 직접 서빙한다.
#
# ## 통째 교체 vs 패치 (2026-08-11 갱신)
# 예전에는 "서빙 zip 에 BetterHud 가 합쳐 넣은 1300여 파일이 있으니 통째로 덮으면 HUD 가
# 전멸한다"가 이 도구의 존재 이유였다. **그 제약은 사라졌다** — BetterHud 에셋은 이제
# CraftEngine 팩(barkan-furniture.zip)이 실어 보내고, 메인 서빙본의 assets/betterhud/ 는
# **0 개**다(2026-08-11 실측: 서빙본 11014 개, 그중 betterhud 0).
#
# 그래서 지금 두 도구는 이렇게 갈린다 — 둘 다 유효하다:
#   * 통째 재빌드 = ops/build-prod-rp.py  (다이어트까지 적용: betterhud·백업 제외 +
#     아이템 128px 상한 + PNG 재압축. 111MB → 71MB. 새 파일명으로 올리고 sha1 갱신)
#   * 부분 갱신   = 이 스크립트          (경로 몇 개만 빨리 갈아 끼울 때. 다이어트는 안 먹는다
#     — 여기로 올린 파일은 원본 해상도 그대로 들어간다)
#
# ★그래서 이 도구로 아이템 텍스처(assets/minecraft/textures/item/…)를 갈면 128px 상한이
#   적용되지 않아 서빙본만 조금씩 뚱뚱해진다. 아이콘 대량 변경은 build-prod-rp.py 쪽으로.
#
# 사용: ops/patch-prod-rp.sh <라벨> <RP루트 기준 경로> [경로 ...]
#   예: ops/patch-prod-rp.sh gui-plates assets/barkan/textures/gui assets/barkan/font/gui.json
#
# 끝나면 server.properties 의 sha1 까지 갱신된다. **재시작해야 클라가 새 팩을 받는다** —
# jar 배포(deploy-blockship.sh)와 묶어서 재시작 한 번으로 끝내는 걸 권장.
set -euo pipefail

RP="$HOME/development/barkan-resourcepack"
KEY="$HOME/.ssh/oracle-mc.key"
HOST="ubuntu@168.107.8.107"
# ★서빙 파일명을 박아 두지 말 것 — server.properties 의 resource-pack URL 이 권위다.
#   2026-08-11: 다른 세션이 버전 붙인 파일명(...-20260810-2333.zip)으로 갈아탔는데 이 값이
#   옛 이름에 박혀 있어, 몇 시간 동안 **아무도 안 보는 파일에 패치하고 있었다.**
SERVED=$(ssh -i "$HOME/.ssh/oracle-mc.key" -o StrictHostKeyChecking=no ubuntu@168.107.8.107 \
    'grep -oP "(?<=^resource-pack=).*" ~/mcserver/server.properties | sed "s|\\\\||g; s|.*/||"')
SERVED="/var/www/barkan/${SERVED}"
echo "▶ 서빙 파일: $SERVED"

[ $# -ge 2 ] || { echo "사용: $0 <라벨> <경로> [경로 ...]"; exit 1; }
LABEL="$1"; shift

PATCH="/tmp/rp-patch-$$.zip"
trap 'rm -f "$PATCH"' EXIT
echo "▶ 패치 zip 생성 — 대상 $# 건 (첫 항목: $1)"   # 목록을 다 찍으면 로그가 파묻힌다
( cd "$RP" && zip -rq "$PATCH" "$@" -x "*.DS_Store" )
echo "  $(unzip -l "$PATCH" | tail -1 | awk '{print $2}') 파일 · $(wc -c < "$PATCH")b"

echo "▶ 업로드"
scp -q -i "$KEY" -o StrictHostKeyChecking=no "$PATCH" "$HOST:/tmp/rp-patch.zip"

echo "▶ 박스에서 병합 (BetterHud 파일 보존)"
ssh -i "$KEY" -o StrictHostKeyChecking=no "$HOST" "LABEL='$LABEL' SERVED='$SERVED' bash -s" <<'REMOTE'
set -euo pipefail
NEW=/tmp/barkan-new.zip
python3 - "$SERVED" /tmp/rp-patch.zip "$NEW" <<'PY'
import sys, zipfile
served, patch, out = sys.argv[1:4]
with zipfile.ZipFile(patch) as pz:
    names = set(pz.namelist())
    with zipfile.ZipFile(served) as sz, zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as oz:
        kept = 0
        for it in sz.infolist():
            if it.filename in names:
                continue
            oz.writestr(it, sz.read(it.filename)); kept += 1
        for it in pz.infolist():
            oz.writestr(it, pz.read(it.filename))
        print(f"  보존 {kept} + 교체/추가 {len(names)} = {kept + len(names)}")
PY
# ★병합본이 성한지 먼저 확인하고 나서 자리를 바꾼다.
#   패치는 교체·추가만 하므로 **전체 파일 수는 절대 줄 수 없다** — 줄었으면 병합이 깨진 것이다.
#   구 가드는 assets/betterhud/ 개수를 봤는데 그건 이제 서빙본에 0 개라 `0 >= 0` 으로
#   무조건 통과하는 죽은 검사였다(2026-08-11). 전체 개수로 바꿨다.
python3 - "$SERVED" "$NEW" <<'PY'
import sys, zipfile
old, new = sys.argv[1:3]
o = zipfile.ZipFile(old); n = zipfile.ZipFile(new)
print(f"  전체 {len(o.namelist())} → {len(n.namelist())}")
assert len(n.namelist()) >= len(o.namelist()), "파일이 줄었다 — 병합 실패, 중단"
assert n.testzip() is None, "zip 손상"
PY
sudo cp -a "$SERVED" "$SERVED.bak-$(date +%Y%m%d)-$LABEL"
sudo mv "$NEW" "$SERVED"
sudo chown root:root "$SERVED"; sudo chmod 644 "$SERVED"
SHA=$(sha1sum "$SERVED" | awk '{print $1}')
sudo sed -i "s/^resource-pack-sha1=.*/resource-pack-sha1=$SHA/" ~/mcserver/server.properties
echo "  sha1 $SHA · server.properties 갱신"
rm -f /tmp/rp-patch.zip
REMOTE

echo "✅ 리소스팩 패치 완료 — ★재시작해야 클라가 받는다"
