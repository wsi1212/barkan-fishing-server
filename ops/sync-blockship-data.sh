#!/bin/bash
# BlockShip 라이브 JSON → 레포 미러(ops/blockship-data/). 히스토리·diff·리뷰를 만들기 위한 스냅샷.
#
# 왜 있나 — 2026-08-20. npc.json/dialogue.json/quests.json 은 NPC 165명·대사 128셋·퀘스트 전부를
# 정의하는데 **git 밖에 있었다.** 그래서 `선원.quests` 에 한 줄이 잘못 들어가 입항 컷씬이 2주 넘게
# 죽어 있었는데도 "누가 언제 왜"를 알 방법이 없었다. 오프사이트 백업은 복원용이고 diff 를 못 준다.
#
# ★권위는 여전히 라이브 파일이다(plugins/BlockShip/*.json). 이건 읽기 전용 미러다 —
#   미러를 고쳐도 서버엔 반영되지 않고, 다음 sync 에 덮인다. 배포도 라이브에서 올라간다.
#
# 사용:  ops/sync-blockship-data.sh          (미러 갱신 + 변경 요약)
#        ops/sync-blockship-data.sh --check  (갱신 없이 «미러가 낡았나»만 판정, 낡으면 exit 1)
set -u
LIVE="/Users/user/Library/Application Support/feather/player-server/servers/07de2d81-991a-47e2-b62d-06c0d1b5150a/plugins/BlockShip"
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MIRROR="$REPO/ops/blockship-data"
# deploy-blockship.sh 의 DATA_FILES 와 같은 목록이어야 한다(prod 로 올라가는 파일 = 히스토리가 필요한 파일).
FILES=(npc.json dialogue.json titles.json parts.json enhance.json recipes.json materials.json quests.json item-flavor.json)

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
