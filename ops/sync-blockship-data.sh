#!/bin/bash
# BlockShip 라이브 JSON → 레포 미러(ops/blockship-data/). 히스토리·diff·리뷰를 만들기 위한 스냅샷.
#
# 왜 있나 — 2026-08-20. npc.json/dialogue.json/quests.json 은 NPC 165명·대사 128셋·퀘스트 전부를
# 정의하는데 **git 밖에 있었다.** 그래서 `선원.quests` 에 한 줄이 잘못 들어가 입항 컷씬이 2주 넘게
# 죽어 있었는데도 "누가 언제 왜"를 알 방법이 없었다. 오프사이트 백업은 복원용이고 diff 를 못 준다.
#
# ★★2026-09-04 정정 — 이 아래 문단은 반대로 적혀 있었다("권위는 라이브, 배포도 라이브에서
#   올라간다"). 실제로는 **배포 소스가 이 미러다**: ops/deploy-blockship.sh 의
#   LOCAL_DATA="$SCRIPTS_REPO/ops/blockship-data" 를 prod 로 scp 하고, dev 라이브에도
#   미러를 덮어쓴다. 즉 편집은 미러에 해야 서버에 닿고, 라이브만 고치면 다음 배포에 덮인다
#   (CLAUDE.md 「작업 원본은 dev 라이브 폴더가 아니라 git 레포 ops/blockship-data/」와 일치).
#   이 스크립트는 라이브가 «앞서간» 경우(서버가 부팅 때 재생성하는 항목)를 미러로 되받는
#   역방향 도구다 — 사본 드리프트 게이트(ops/audit-copies.py ②)를 맞출 때 쓴다.
#   ⚠ 미러에 아직 배포 안 된 편집이 있으면 이걸 그냥 돌리면 그 편집이 사라진다. 먼저 diff 를 볼 것.
#
# 사용:  ops/sync-blockship-data.sh          (미러 갱신 + 변경 요약)
#        ops/sync-blockship-data.sh --check  (갱신 없이 «미러가 낡았나»만 판정, 낡으면 exit 1)
set -u
LIVE="/Users/user/Library/Application Support/feather/player-server/servers/07de2d81-991a-47e2-b62d-06c0d1b5150a/plugins/BlockShip"
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MIRROR="$REPO/ops/blockship-data"
# deploy-blockship.sh 의 DATA_FILES 와 같은 목록이어야 한다(prod 로 올라가는 파일 = 히스토리가 필요한 파일).
FILES=(npc.json dialogue.json titles.json parts.json enhance.json recipes.json materials.json quests.json fish.json item-flavor.json cashshop.json)

CHECK=0; [ "${1:-}" = "--check" ] && CHECK=1
mkdir -p "$MIRROR"
STALE=0; CHANGED=0
for f in "${FILES[@]}"; do
  [ -f "$LIVE/$f" ] || { echo "  - $f 라이브에 없음(스킵)"; continue; }
  if cmp -s "$LIVE/$f" "$MIRROR/$f"; then continue; fi
  STALE=$((STALE+1))
  if [ "$CHECK" -eq 1 ]; then
    echo "  ▲ $f 미러가 라이브와 다르다"
  else
    # 줄 수 변화를 같이 보여준다 — 대량 감소는 사고 신호다(2026-08-01 npc.json 138명→1명 사고)
    OLD=$( [ -f "$MIRROR/$f" ] && wc -l < "$MIRROR/$f" || echo 0 )
    cp "$LIVE/$f" "$MIRROR/$f"
    NEW=$(wc -l < "$MIRROR/$f")
    printf "  ✓ %-18s %6d → %6d 줄\n" "$f" "$OLD" "$NEW"
    CHANGED=$((CHANGED+1))
  fi
done
if [ "$CHECK" -eq 1 ]; then
  [ "$STALE" -eq 0 ] && { echo "  미러 최신"; exit 0; }
  echo "  미러가 낡았다 — ops/sync-blockship-data.sh 실행 후 커밋할 것"; exit 1
fi
[ "$CHANGED" -eq 0 ] && echo "  변경 없음"
exit 0
