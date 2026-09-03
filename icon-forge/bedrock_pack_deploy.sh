#!/usr/bin/env bash
# 베드락 커스텀 아이템 팩 배포 — bedrock_pack_build.py 산출물을 서버에 올린다.
#
#   ./bedrock_pack_deploy.sh dev     맥 dev 서버 (재시작은 별도)
#   ./bedrock_pack_deploy.sh prod    오라클 prod (★재시작하지 않는다 — CLAUDE.md 금지)
#
# ★팩과 매핑은 «짝» 이고 «폴더가 다르다».
#     packs/           ← .mcpack (텍스처)
#     custom_mappings/ ← 매핑 JSON   ★여기 아니면 Geyser 가 아예 안 읽는다
#   2026-09-04 실측: 매핑을 packs/ 에 두면 조용히 무시돼 커스텀 아이템이 0개가 된다.
# ★Geyser 는 부팅 때 팩·매핑을 읽는다. 올리기만 하고 재시작하지 않으면 반영되지 않는다.
#   prod 는 06:00 정기 재시작에서 반영된다(에이전트 임의 재시작 금지).
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUT="$HERE/out/bedrock"
PACK="$OUT/barkan_bedrock.mcpack"
MAP="$OUT/barkan_mappings.json"

TARGET="${1:-}"
[[ -f "$PACK" && -f "$MAP" ]] || { echo "❌ 산출물이 없습니다 — 먼저: python3 bedrock_pack_build.py"; exit 1; }

case "$TARGET" in
  dev)
    DEST="/Users/user/Library/Application Support/feather/player-server/servers/07de2d81-991a-47e2-b62d-06c0d1b5150a/plugins/Geyser-Spigot/packs"
    MAPDEST="${DEST%/packs}/custom_mappings"
    mkdir -p "$DEST" "$MAPDEST"
    cp "$PACK" "$DEST/"
    cp "$MAP" "$MAPDEST/"
    rm -f "$DEST/barkan_mappings.json"    # packs/ 의 사본은 혼동만 준다
    ls -la "$DEST" "$MAPDEST"
    echo "✅ dev 반영 — 적용하려면: ~/dev-mc.sh restart"
    ;;
  prod)
    KEY=~/.ssh/oracle-mc.key
    HOST=ubuntu@168.107.8.107
    DEST='~/mcserver/plugins/Geyser-Spigot/packs'
    # 되돌릴 수 있게 기존 파일을 먼저 백업한다(팩만 바꿔 놓고 문제가 나면 이걸로 복구).
    MAPDEST='~/mcserver/plugins/Geyser-Spigot/custom_mappings'
    ssh -i "$KEY" "$HOST" "mkdir -p $DEST $MAPDEST && cd $DEST && \
      for f in barkan_bedrock.mcpack; do \
        [ -f \$f ] && cp -a \$f \$f.bak-\$(date +%Y%m%d-%H%M%S) || true; done; \
      cd $MAPDEST && [ -f barkan_mappings.json ] && \
        cp -a barkan_mappings.json barkan_mappings.json.bak-\$(date +%Y%m%d-%H%M%S) || true"
    scp -i "$KEY" "$PACK" "$HOST:$DEST/"
    scp -i "$KEY" "$MAP" "$HOST:$MAPDEST/"
    ssh -i "$KEY" "$HOST" "rm -f $DEST/barkan_mappings.json; ls -la $DEST $MAPDEST"
    echo "✅ prod 업로드 완료 — ★재시작은 하지 않았습니다(06:00 정기 재시작에서 반영)"
    ;;
  *)
    echo "사용법: $0 <dev|prod>"; exit 2 ;;
esac
