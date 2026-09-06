#!/usr/bin/env bash
# 베드락 «소리» 팩 배포 — bedrock_sound_pack_build.py 산출물.
#
#   ./bedrock_sound_pack_deploy.sh dev       맥 dev — Geyser 인밴드(packs/) 전송
#   ./bedrock_sound_pack_deploy.sh dev-url    맥 dev — 원격 URL 전송(prod 와 같은 방식)
#
# 두 모드는 «배타적» 이다. 같은 팩을 packs/ 와 URL 로 동시에 내보내면 uuid 가 겹쳐
# Geyser 가 한쪽을 버린다 → 각 모드가 반대쪽 흔적을 스스로 지운다.
#   dev     : 새 변수가 «팩 하나» 뿐이라 소리가 나는지부터 깔끔하게 본다. 단 인밴드 총량이
#             17.7MB(아이콘 7.3 + 소리 10.3 + Geyser 통합팩 0.1)가 되어 접속이 깨질 수 있다.
#   dev-url : 크기 제약이 사라지고 prod 와 같은 경로를 시험한다. 대신 폰이 맥의 HTTP 호스트
#             (~/casino-rp-host, 포트 8801)에 닿아야 하고 http:// 라 베드락이 거부할 수도 있다.
#
# ★가동 중 교체 금지 — Geyser 는 부팅 때 읽은 uuid·버전·해시·크기를 클라에 «알려주고»
#   실제 바이트는 그때그때 디스크에서 흘려보낸다. 도는 중에 갈면 캐시 있는 유저는
#   「업데이트가 안 됐다」, 캐시 없는 유저는 「전부 깨짐」이 된다. 그래서 dev 도 정지 후 교체한다.
#
# ★prod 는 이 스크립트로 나가지 않는다 (아래 prod 분기가 거부한다).
#   소리 팩은 9~10MB 라 Geyser 인밴드(packs/) 전송에 태우면 안 된다 — 15MB 팩이 베드락
#   접속 자체를 깬 전례가 있고 7.2MB 는 정상이었다(그 사이 임계는 미측정). prod 경로는
#     ① /var/www/barkan/ 에 파일 배치 (Caddy 가 이미 그 폴더를 파일서버로 서빙한다)
#     ② Geyser config.yml  resource-pack-urls: ["https://barkan.kr/barkan-bedrock-sounds.mcpack"]
#        ★barkan.kr 직접 — barkan.kro.kr 은 308 리다이렉트로 잡혀 있고 베드락 클라는 리다이렉트에 예민하다
#     ③ 웹 파일 교체도 «재시작 직전» 이어야 한다 → nightly-restart.sh ①-3 에 단계 추가 필요
#   ③이 아직 없으므로 prod 는 dev 실기기 확인 뒤에 손댄다.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PACK="$HERE/out/bedrock/barkan_bedrock_sounds.mcpack"
[[ -f "$PACK" ]] || { echo "❌ 산출물이 없습니다 — 먼저: python3 bedrock_sound_pack_build.py"; exit 1; }

case "${1:-}" in
  dev|dev-url)
    MODE="$1"
    SRV="/Users/user/Library/Application Support/feather/player-server/servers/07de2d81-991a-47e2-b62d-06c0d1b5150a"
    DEST="$SRV/plugins/Geyser-Spigot/packs"
    CFG="$SRV/plugins/Geyser-Spigot/config.yml"
    HOSTDIR="$HOME/casino-rp-host"
    mkdir -p "$DEST"

    # ★가동 중 교체 금지(위 주석) + config 는 부팅 때만 읽힌다 → 정지 후 손댄다.
    if pgrep -f 'paper-.*\.jar' >/dev/null; then
      echo "▶ dev 정지 (가동 중 팩 교체 금지)"
      ~/dev-mc.sh stop || true
      for _ in $(seq 1 30); do pgrep -f 'paper-.*\.jar' >/dev/null || break; sleep 1; done
      RESTART=1
    else
      RESTART=0
    fi

    if [[ "$MODE" == "dev" ]]; then
      cp "$PACK" "$DEST/"
      python3 - "$CFG" '[]' <<'PYEDIT'
import re, sys
p, val = sys.argv[1], sys.argv[2]
s = open(p, encoding="utf-8").read()
s2 = re.sub(r"^(\s*resource-pack-urls:).*$", lambda m: m.group(1) + " " + val, s, count=1, flags=re.M)
open(p, "w", encoding="utf-8").write(s2)
print("resource-pack-urls =", val)
PYEDIT
      echo "▶ 인밴드 모드 — packs/ 에 배치, URL 목록 비움"
    else
      IP="$(ipconfig getifaddr en0 || true)"
      [[ -n "$IP" ]] || { echo "❌ en0 LAN IP 를 못 읽었습니다"; exit 1; }
      mkdir -p "$HOSTDIR"
      cp "$PACK" "$HOSTDIR/"
      rm -f "$DEST/barkan_bedrock_sounds.mcpack"      # ★uuid 중복 방지
      URL="http://$IP:8801/barkan_bedrock_sounds.mcpack"
      python3 - "$CFG" "[\"$URL\"]" <<'PYEDIT'
import re, sys
p, val = sys.argv[1], sys.argv[2]
s = open(p, encoding="utf-8").read()
s2 = re.sub(r"^(\s*resource-pack-urls:).*$", lambda m: m.group(1) + " " + val, s, count=1, flags=re.M)
open(p, "w", encoding="utf-8").write(s2)
print("resource-pack-urls =", val)
PYEDIT
      if ! lsof -nP -iTCP:8801 -sTCP:LISTEN >/dev/null 2>&1; then
        echo "⚠️  8801 HTTP 호스트가 꺼져 있습니다 — 먼저 띄울 것:"
        echo "    (cd $HOSTDIR && nohup python3 -m http.server 8801 >/dev/null 2>&1 &)"
      fi
      echo "▶ 원격 URL 모드 — $URL"
    fi

    ls -la "$DEST"
    if [[ "$RESTART" == 1 ]]; then
      echo "▶ dev 기동 (~83초 걸린다 — 타임아웃은 실패가 아니다)"
      ~/dev-mc.sh start || true
    else
      echo "✅ dev 반영 — 적용하려면: ~/dev-mc.sh start"
    fi
    ;;
  prod)
    echo "❌ prod 는 이 스크립트로 나가지 않는다 — 파일 상단 주석의 3단계를 볼 것."
    exit 2 ;;
  *)
    echo "사용법: $0 <dev|dev-url>"; exit 2 ;;
esac
