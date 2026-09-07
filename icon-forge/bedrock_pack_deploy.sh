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
#
# ★★prod 라이브 폴더에 직접 넣지 않는다 — staging/geyser/ 로 올린다.
#   Geyser 는 부팅 때 읽은 uuid·버전·해시·크기를 클라에 «알려주고», 실제 바이트는
#   그때그때 «디스크에서» 흘려보낸다. 그래서 가동 중에 파일을 갈아 끼우면
#     · 캐시가 있는 유저 → 서버가 옛 버전이라 말하니 재다운로드 안 함(업데이트 안 된 것처럼 보임)
#     · 캐시가 없는 유저 → 알린 해시와 받은 바이트가 어긋나 팩이 깨짐 → «아이템 전부 투명»
#   2026-09-04 에 실제로 이걸로 베드락이 하루 반나절 깨졌다. 재시작 직전 교체가 유일하게
#   안전한 시점이라, nightly-restart.sh 의 ①-3 단계가 staging/geyser/ 를 적용한다.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUT="$HERE/out/bedrock"
PACK="$OUT/barkan_bedrock.mcpack"
MAP="$OUT/barkan_mappings.json"
# ★블록 산출물 3종은 bedrock_block_build.py 가 만든다. 예전엔 이 스크립트가 팩·아이템매핑
#   둘만 날라서, 채집·작물 3D 모델이 «dev 에서 손으로 복사한 사람 화면에서만» 보였다.
#   prod 에는 한 번도 간 적이 없다(2026-09-07 실측: prod 에 bedrock-blocks.json·
#   barkan_blocks.json 둘 다 없음 → 베드락에서 채집물이 바닐라 밀·흰들국화로 폴백).
BLOCKMAP="$OUT/barkan_blocks.json"      # → Geyser custom_mappings/
BLOCKDATA="$OUT/bedrock-blocks.json"    # → plugins/BlockShip/ (자바가 읽어 blockstate 를 보낸다)

TARGET="${1:-}"
[[ -f "$PACK" && -f "$MAP" ]] || { echo "❌ 산출물이 없습니다 — 먼저: python3 bedrock_pack_build.py"; exit 1; }

# ★순서 함정: bedrock_pack_build.py 는 팩을 «처음부터 다시» 만든다(stage 를 rmtree).
#   그래서 아이템 빌더를 나중에 돌리면 블록 지오메트리가 통째로 날아간다.
#   팩 안에 블록 지오메트리(models/blocks/)가 있는지로 그 사고를 잡는다.
#   ★blocks.json 을 찾으면 안 된다 — Geyser 커스텀 블록은 블록 «정의» 를 서버가 등록하고
#     팩에는 지오메트리·텍스처만 들어간다(애드온식 blocks.json 이 아니다).
#   ★`grep -q` 를 쓰지 말 것 — 첫 일치에서 파이프를 닫아 unzip 이 SIGPIPE 로 죽고,
#     이 스크립트의 `set -o pipefail` 이 그걸 실패로 읽어 «있는데 없다» 고 판정한다.
if [ "$(unzip -l "$PACK" 2>/dev/null | grep -c "models/blocks/" || true)" = "0" ]; then
  echo "❌ 팩에 커스텀 블록이 없습니다 — 아이템 빌더를 나중에 돌려 지워졌을 수 있습니다."
  echo "   순서: python3 bedrock_pack_build.py  →  python3 bedrock_block_build.py"
  exit 1
fi
[[ -f "$BLOCKMAP" && -f "$BLOCKDATA" ]] || { echo "❌ 블록 산출물이 없습니다 — python3 bedrock_block_build.py"; exit 1; }

case "$TARGET" in
  dev)
    DEST="/Users/user/Library/Application Support/feather/player-server/servers/07de2d81-991a-47e2-b62d-06c0d1b5150a/plugins/Geyser-Spigot/packs"
    MAPDEST="${DEST%/packs}/custom_mappings"
    mkdir -p "$DEST" "$MAPDEST"
    BSDEST="${DEST%/Geyser-Spigot/packs}/BlockShip"
    cp "$PACK" "$DEST/"
    cp "$MAP" "$MAPDEST/"
    cp "$BLOCKMAP" "$MAPDEST/"
    mkdir -p "$BSDEST" && cp "$BLOCKDATA" "$BSDEST/"
    rm -f "$DEST/barkan_mappings.json"    # packs/ 의 사본은 혼동만 준다
    ls -la "$DEST" "$MAPDEST" "$BSDEST/bedrock-blocks.json"
    echo "✅ dev 반영 — 적용하려면: ~/dev-mc.sh restart"
    ;;
  prod)
    KEY=~/.ssh/oracle-mc.key
    HOST=ubuntu@168.107.8.107
    STAGE='~/mcserver/staging/geyser'
    # ★라이브(packs/·custom_mappings/)에 쓰지 않는다 — 위 주석 참조.
    #   nightly-restart.sh ①-3 이 재시작 직전에 옮겨 끼운다(팩 무결성 게이트 포함).
    BSSTAGE='~/mcserver/staging/BlockShip'
    ssh -i "$KEY" "$HOST" "mkdir -p $STAGE $BSSTAGE"
    scp -i "$KEY" "$PACK"     "$HOST:$STAGE/"
    scp -i "$KEY" "$MAP"      "$HOST:$STAGE/"
    # nightly-restart.sh 의 geyser 적용부는 *.mcpack → packs/, *.json → custom_mappings/ 로 나른다.
    scp -i "$KEY" "$BLOCKMAP" "$HOST:$STAGE/"
    # bedrock-blocks.json 은 Geyser 가 아니라 «우리 플러그인» 이 읽는다 → staging/BlockShip/.
    scp -i "$KEY" "$BLOCKDATA" "$HOST:$BSSTAGE/"
    ssh -i "$KEY" "$HOST" "ls -la $STAGE $BSSTAGE"
    SZ=$(stat -f%z "$PACK" 2>/dev/null || stat -c%s "$PACK")
    echo "✅ prod 스테이징 완료 (${SZ} bytes) — 06:00 KST 정기 재시작에서 반영됩니다"
    if [ "$SZ" -gt 6500000 ]; then
      echo "⚠️  팩이 6.5MB 를 넘습니다. 15MB 는 베드락 접속 자체를 깼고 6.0MB 는 정상이었습니다"
      echo "    (그 사이 임계는 미측정) — dev 에서 실제 접속 확인 후 두고 갈 것."
    fi
    ;;
  *)
    echo "사용법: $0 <dev|prod>"; exit 2 ;;
esac
