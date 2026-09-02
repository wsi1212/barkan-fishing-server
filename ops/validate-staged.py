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


def _instance_files():
    """인스턴스 전용 파일 목록을 guard-instance-data.py 에서 가져온다.

    목록을 여기 복제하면 언젠가 한쪽만 늘어난다 — 권위는 훅 파일 하나다.
    prod 에서는 같은 디렉터리(~/mcserver/scripts/), 레포에서는 ops/hooks/ 에 있다.
    못 찾으면 **거부**한다 — 검사가 조용히 사라지는 쪽이 훨씬 위험하다.
    """
    import importlib.util

    here = os.path.dirname(os.path.abspath(__file__))
    for cand in (os.path.join(here, 'guard-instance-data.py'),
                 os.path.join(here, 'hooks', 'guard-instance-data.py')):
        if os.path.exists(cand):
            spec = importlib.util.spec_from_file_location('guard_instance_data', cand)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod.INSTANCE_FILES
    reject('guard-instance-data.py 를 찾을 수 없다 — 인스턴스 데이터 검사 불가, 안전을 위해 거부')





def main():
    if len(sys.argv) < 3:
        reject('사용법: validate-staged.py <staged> <live>')
    staged, live = sys.argv[1], sys.argv[2]

    # ★인스턴스 전용 상태는 애초에 배포 대상이 아니다 — dev 와 prod 가 각자 따로 들고 있는
    #   유저 데이터다. 항목수 검사로는 못 막힌다: dev 쪽이 더 크기만 하면 통과해 버리고,
    #   그러면 남의 서버 유저 상태를 덮는다.
    #   2026-08-25 실사고: dev regions.json 이 prod 를 덮어 개인섬 5개의 지역이 사라졌고,
    #   하루 뒤 소유자가 /섬 을 치는 순간 「지역 없음 → 새 격자로 재발급」 =  섬 초기화.
    #   목록 권위는 ops/hooks/guard-instance-data.py 의 INSTANCE_FILES 다(복제하지 말 것).
    if os.path.basename(staged) in _instance_files():
        reject('인스턴스 전용 데이터(서버별 유저 상태) — 배포 대상 아님')

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
    # ★recipes.json 재료 항목의 필수 키 — 서버 gson 은 «모르는 키를 조용히 버린다».
    #   그래서 kind 를 type 이라고 써도 파싱은 통과하고, 런타임에 ing.kind == null 이 되어
    #   RecipeLoader 의 `"custom".equals(ing.kind)` 판정이 전부 false 가 된다 →
    #   그 재료 칸이 «있지만 인식 안 되는» 상태가 된다. 에러도, 로그도 없다.
    #   2026-09-02 실사고: 생성 스크립트 두 개가 "type" 으로 써서 74개 항목이 그 상태로
    #   prod 에 나갔다(압축자수정·대표재료). 항목수·크기·타입 검사 전부 통과했다.
    #   판정은 «내용»으로 한다 — 파일명으로 하면 이름만 다른 사본이 검사를 빠져나간다.
    if isinstance(snew.get('recipes'), dict):
        need = {'kind', 'typeOrMatId', 'qty'}
        broken = []
        for rid, rec in (snew.get('recipes') or {}).items():
            for i in (rec or {}).get('ingredients') or []:
                miss = need - set(i)
                if miss:
                    broken.append(f"{rid}:{i.get('typeOrMatId') or i.get('displayName')}"
                                  f"(없음 {sorted(miss)})")
        if broken:
            reject(f'재료 항목 필수 키 누락 {len(broken)}건 — 서버가 조용히 무시한다: '
                   f'{broken[:6]}{" …" if len(broken) > 6 else ""}')

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
