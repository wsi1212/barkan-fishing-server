#!/usr/bin/env python3
"""스테이징 JSON이 라이브 파일을 덮어도 되는지 판정한다.

    validate-staged.py <staged_file> <live_file>
    exit 0 = 적용해도 안전 / exit 1 = 거부(사유를 stdout에 한 줄)

왜 필요한가 (2026-08-01 사고):
  누군가 npc.json을 "새로 추가할 NPC 1명만" 담아 staging에 올렸고, 06:00 데일리
  유지보수가 그걸 그대로 prod에 통째 복사했다. 결과: NPC 138명 -> 1명,
  dialogue 100세트 -> 53세트, 퀘스트 235개 -> 214개. 게다가 그 파일은
  quests 필드를 배열이 아닌 문자열로 써서 Gson 파싱까지 실패, NPC 대화/상점이
  전부 죽었다. 아무도 막지 않았고 리포트에도 "🚀 설정 1개 갱신"으로만 찍혔다.

판정 규칙 (레지스트리 JSON은 커지기만 하지 줄지 않는다는 전제):
  1) JSON으로 파싱되지 않으면 거부
  2) 최상위 컨테이너 항목 수가 라이브보다 '하나라도' 줄면 거부
     (70% 같은 느슨한 문턱은 quests.json 235->214처럼 조용한 퇴행을 놓친다 — 실측)
  3) 파일 크기가 라이브의 70% 미만이면 거부 (포맷 변경 여지는 남김)
  4) 양쪽에 공통으로 있는 항목에서 같은 필드의 '타입'이 바뀌면 거부
     (list -> str 같은 스키마 파손. 이번 사고의 직접 원인)
라이브 파일이 없으면(신규 파일) 통과. .json이 아니면 통과.
의도적으로 항목을 지우는 배포라면 스테이징에 <파일명>.allow-shrink 를 같이 올린다.
"""
import collections
import json
import os
import sys

SHRINK_OK = 0.70


def container(obj):
    """레지스트리 본체로 볼 만한 최대 컨테이너와 그 길이."""
    if isinstance(obj, list):
        return obj, len(obj)
    if isinstance(obj, dict):
        best, n = obj, len(obj)
        for v in obj.values():
            if isinstance(v, (dict, list)) and len(v) > n:
                best, n = v, len(v)
        return best, n
    return obj, 0


def reject(msg):
    print(msg)
    sys.exit(1)


def main():
    if len(sys.argv) < 3:
        reject('사용법: validate-staged.py <staged> <live>')
    staged, live = sys.argv[1], sys.argv[2]
    if not staged.endswith('.json'):
        sys.exit(0)                                    # jar/기타는 이 검사 대상 아님
    # ★중복 키를 먼저 잡는다 — 파이썬 json 은 중복을 조용히 덮어쓰지만 서버의 gson 은
    #   JsonSyntaxException("duplicate key") 으로 **파일 전체를 거부**한다. 그래서 여기서
    #   통과시키면 prod 에서 그 데이터가 통째로 안 읽힌다.
    #   2026-08-11 실제 사고: parts.json 에 초보자 4종이 두 번 들어가 prod 가
    #   "Loaded 0 parts (0 types)" 로 떴다 — 장비 시스템 전체 정지.
    dups = []

    def dup_hook(pairs):
        counts = collections.Counter(k for k, _ in pairs)
        dups.extend(k for k, n in counts.items() if n > 1)
        return dict(pairs)

    try:
        with open(staged, encoding='utf-8') as f:
            snew = json.loads(f.read(), object_pairs_hook=dup_hook)
    except Exception as e:                             # noqa: BLE001
        reject(f'JSON 파싱 실패: {e}')
    if dups:
        uniq = sorted(set(dups))
        reject(f'중복 키 {len(uniq)}건 — 서버 gson 이 파일 전체를 거부한다: '
               f'{uniq[:8]}{" …" if len(uniq) > 8 else ""}')
    if not os.path.exists(live):
        sys.exit(0)                                    # 신규 파일은 통과
    try:
        with open(live, encoding='utf-8') as f:
            sold = json.load(f)
    except Exception:                                  # noqa: BLE001
        sys.exit(0)                                    # 라이브가 이미 깨졌으면 덮어쓰기 허용

    cnew, nnew = container(snew)
    cold, nold = container(sold)
    allow_shrink = os.path.exists(staged + '.allow-shrink')
    if nold and nnew < nold and not allow_shrink:
        reject(f'항목이 {nold}개 → {nnew}개로 감소 '
               f'(부분 파일을 통째로 덮으려는 것 아닌가? 의도한 삭제면 '
               f'{os.path.basename(staged)}.allow-shrink 를 같이 올릴 것)')

    znew, zold = os.path.getsize(staged), os.path.getsize(live)
    if zold and znew < zold * SHRINK_OK and not allow_shrink:
        reject(f'크기가 {zold}B → {znew}B로 급감')

    if isinstance(cnew, dict) and isinstance(cold, dict):
        for key in list(set(cnew) & set(cold))[:200]:
            a, b = cnew[key], cold[key]
            if isinstance(a, dict) and isinstance(b, dict):
                for fld in set(a) & set(b):
                    if type(a[fld]) is not type(b[fld]):  # noqa: E721
                        reject(f'스키마 파손: {key}.{fld} 타입이 '
                               f'{type(b[fld]).__name__} → {type(a[fld]).__name__}')
    sys.exit(0)


if __name__ == '__main__':
    main()
