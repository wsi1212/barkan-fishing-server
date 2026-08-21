#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""메인 퀘스트 체인을 한 칸씩 진행시키며 «그 시점에 이 NPC가 어떤 대사를 하는가»를
NpcDialogueManager.beginByQuestState 와 같은 규칙으로 재현해, 대사 구멍을 찾는다.

찾는 구멍 3종:
  1) 공백    — 이 NPC와 이미 거래했는데 다음 퀘스트가 남의 퀘스트에 막혀 있어
               «첫날 인사»로 되돌아가는 구간. 처방 = dialogue.json 에 "대기/<다음퀘스트>".
  2) 노드없음 — 분기가 고른 키(인사/<qid>·진행중/<qid>·퀘스트완료/<qid>·첫만남·후일담)가
               데이터에 아예 없어 폴백으로 때우는 경우.
  3) 첫만남재생 — 이미 거래한 NPC가 첫만남 대사를 다시 하는 경우.

사용:  ops/audit-dialogue-gaps.py [BlockShip디렉터리]        (기본=라이브 dev)
       ops/audit-dialogue-gaps.py --check                    (구멍 있으면 exit 1)
"""
import json, sys, os, re, collections

LIVE = os.path.expanduser(
    "~/Library/Application Support/feather/player-server/servers/"
    "07de2d81-991a-47e2-b62d-06c0d1b5150a/plugins/BlockShip")
args = [a for a in sys.argv[1:] if not a.startswith('--')]
CHECK = '--check' in sys.argv
D = args[0] if args else LIVE

q = json.load(open(os.path.join(D, 'quests.json'), encoding='utf-8'))['퀘스트']
npcs = json.load(open(os.path.join(D, 'npc.json'), encoding='utf-8'))['npcs']
dlg = json.load(open(os.path.join(D, 'dialogue.json'), encoding='utf-8'))

fld = lambda qid, f: (q.get(qid) or {}).get(f) or ''
nm = lambda qid: re.sub(r'&.', '', fld(qid, '이름') or qid)

# 메인 체인 = 튜토_선원 → 다음퀘스트 …
chain, cur, seen = [], '튜토_선원', set()
while cur and cur in q and cur not in seen:
    seen.add(cur); chain.append(cur); cur = fld(cur, '다음퀘스트')


def has_progress_later(qid, status):
    s, nxt = set(), qid
    while nxt and nxt not in s:
        s.add(nxt); nxt = fld(nxt, '다음퀘스트')
        if not nxt: return False
        if status.get(nxt): return True
    return False


def first_available(nq, status, level):
    """NpcDialogueManager.firstAvailableQuest 와 같은 판정 — 레벨 게이트 포함.
    (레벨이 모자란 퀘스트는 수락 자체가 막히므로 «인사/<qid>» 후보가 아니다)"""
    for qid in nq:
        if status.get(qid) == '완료': continue
        pre = fld(qid, '선행퀘스트')
        if pre and status.get(pre) != '완료': continue
        try: need = int((q.get(qid) or {}).get('필요레벨') or 1)
        except (TypeError, ValueError): need = 1
        if level and level < need: continue
        if has_progress_later(qid, status): continue
        return qid
    return None


def resolve(npcId, nq, status, level=0):
    """(구멍종류|None, 설명) — Java 분기와 1:1"""
    m = dlg.get(npcId, {})
    ex = lambda k: k in m
    comp = act = None
    for qid in nq:
        st = status.get(qid)
        if st == '완료대기': comp = qid; break
        if st == '진행' and act is None: act = qid
    if comp:
        return (None if ex('퀘스트완료/' + comp) or ex('퀘스트완료') else '노드없음', '퀘스트완료/' + comp)
    if act:
        return (None if ex('진행중/' + act) or ex('진행중') else '노드없음', '진행중/' + act)
    av = first_available(nq, status, level)
    rec = any(status.get(x) in ('진행', '완료대기', '완료') for x in nq)
    if av:
        first = nq[0]
        pre = fld(av, '선행퀘스트')
        if av == first and not rec and (not pre or status.get(pre) != '완료'):
            return (None if ex('첫만남') else '노드없음', '첫만남')
        if rec and ex('첫만남') and av == first and not any(
                status.get(x) in ('진행', '완료대기', '완료') for x in nq):
            return ('첫만남재생', '첫만남')
        return (None if ex('인사/' + av) or ex('인사') else '노드없음', '인사/' + av)
    if all(status.get(x) == '완료' for x in nq):
        return (None if ex('후일담') else '노드없음', '후일담')
    pending = next((x for x in nq if status.get(x) != '완료'), None)
    dealt = any(status.get(x) == '완료' for x in nq)
    if dealt and (ex('대기/' + pending) or ex('대기')):
        return (None, '대기/' + pending)
    return (('공백' if dealt else None), '대기/' + str(pending))


# 사이드 퀘스트(체인 밖) — «완주형» 2회차 시뮬레이션에서 완료로 채운다.
#   히든_* 는 레벨 60 해금이라 스토리 중간에 깼다고 볼 수 없어 제외한다.
SIDE = [k for k in q if k not in set(chain) and not k.startswith('히든_')]


def fill_side(status):
    for _ in range(4):
        for sq in SIDE:
            if status.get(sq): continue
            pre = fld(sq, '선행퀘스트')
            if not pre or status.get(pre) == '완료': status[sq] = '완료'


holes = collections.defaultdict(list)   # (종류,npc,키) -> [체인 index]
for pas in ('기본', '완주형'):
  for i, cq in enumerate(chain):
    status = {c: '완료' for c in chain[:i]}
    status[cq] = '진행'
    if pas == '완주형': fill_side(status)
    try: lvl = int((q.get(cq) or {}).get('필요레벨') or 1)
    except (TypeError, ValueError): lvl = 1
    for npcId, v in npcs.items():
        nq = [x for x in (v.get('quests') or []) if x]
        if not nq: continue
        kind, key = resolve(npcId, nq, status, lvl)
        if kind: holes[(kind, npcId, key, pas)].append(i)

rows = []
for (kind, npcId, key, pas), idxs in holes.items():
    idxs.sort(); start = prev = idxs[0]
    for i in idxs[1:] + [10 ** 9]:
        if i != prev + 1:
            rows.append((kind, npcId, key, start, prev, pas)); start = i
        prev = i
rows.sort(key=lambda r: (r[0], r[3]))

seen_row = set()
for kind, npcId, key, a, b, pas in rows:
    if (kind, npcId, key, a, b) in seen_row: continue   # 두 패스에 같이 걸린 건 한 번만
    seen_row.add((kind, npcId, key, a, b))
    print('[%s/%s] %-10s %-16s %3d퀘  %s ~ %s'
          % (kind, pas, npcId, key, b - a + 1, nm(chain[a]), nm(chain[b])))
print('\n구멍 %d개 / NPC %d명 (메인 체인 %d퀘 × 기본·완주형 2패스)'
      % (len(seen_row), len({r[1] for r in rows}), len(chain)))
if CHECK and rows: sys.exit(1)
