#!/usr/bin/env python3
"""NPC 역할 × 마을 행렬 — 어느 마을에 어떤 기능 NPC 가 빠졌는지 찾는다.

prod 박스에서 돌린다:
    scp ops/audit-npc-roles.py ubuntu@<prod>:/tmp/ && ssh ubuntu@<prod> 'python3 /tmp/audit-npc-roles.py'

★마을은 좌표로 «군집화» 한다 — regions.json 은 낚시 구역이라 마을 판정에 못 쓴다
  (바르칸·강·원양 같은 루트 지역이 전부 겹쳐 나온다. 실측 확인).
★역할은 npc.json 의 «True 인 플래그» 가 권위다. 표시이름의 [태그] 는 장식이라
  태그만 있고 플래그가 없는 NPC 가 실제로 있었다(우클릭이 아무 일도 안 한다).
★citizensId 가 0 인 항목을 찾아 준다 — 이름으로는 이어지지만 메타데이터가 끊긴 상태.
"""
import re, json, math, collections, sys

SAVES = '/home/ubuntu/mcserver/plugins/Citizens/saves.yml'
NPCJ  = '/home/ubuntu/mcserver/plugins/BlockShip/npc.json'
LINK  = 150          # 이 거리 안이면 같은 마을로 잇는다(전이적)

def citizens():
    cur, C = None, {}
    for ln in open(SAVES, encoding='utf-8'):
        r = ln.rstrip('\n')
        m = re.match(r"^  '?(\d+)'?:\s*$", r)
        if m:
            cur = m.group(1); C.setdefault(cur, {}); continue
        if not cur: continue
        s = r.strip()
        if s.startswith('name:'):
            C[cur]['name'] = re.sub(r'&.', '', s.split('name:', 1)[1].strip().strip("'\""))
        if s.startswith('textureRaw:'):
            C[cur]['skin'] = True
        for k in ('x', 'y', 'z'):
            if s.startswith(k + ':'):
                try: C[cur][k] = float(s.split(k + ':', 1)[1].strip().strip("'\""))
                except ValueError: pass
    return C

def cluster(C):
    pts = [(c, d) for c, d in C.items() if isinstance(d.get('x'), float)]
    par = {c: c for c, _ in pts}
    def find(a):
        while par[a] != a: par[a] = par[par[a]]; a = par[a]
        return a
    for i, (a, da) in enumerate(pts):
        for b, db in pts[i + 1:]:
            if math.hypot(da['x'] - db['x'], da['z'] - db['z']) <= LINK:
                ra, rb = find(a), find(b)
                if ra != rb: par[ra] = rb
    G = collections.defaultdict(list)
    for c, _ in pts: G[find(c)].append(c)
    return sorted(G.values(), key=len, reverse=True)

def main():
    C = citizens()
    D = json.load(open(NPCJ, encoding='utf-8'))['npcs']
    roles = collections.Counter()
    zero = []
    for k, v in D.items():
        if not isinstance(v, dict): continue
        if str(v.get('citizensId', '')) in ('0', '', 'None'):
            zero.append((k, re.sub(r'&.', '', v.get('name', ''))))
        for f, val in v.items():
            if val is True: roles[f] += 1
    print('NPC %d명 · npc.json %d항목' % (len(C), len(D)))
    print('역할 플래그:', dict(roles.most_common()))
    if zero:
        print('\n★citizensId 가 0/빈값인 항목 %d개 (메타데이터 끊김):' % len(zero))
        for k, nm in zero: print('   %-14s %s' % (k, nm))
    noskin = [(c, d['name']) for c, d in C.items() if 'name' in d and not d.get('skin')]
    if noskin:
        print('\n★스킨(textureRaw) 없는 NPC %d명:' % len(noskin))
        for c, nm in noskin: print('   cid %-5s %s' % (c, nm))

    byname = {}
    for k, v in D.items():
        if isinstance(v, dict):
            byname[re.sub(r'&.', '', v.get('name', k)).replace(' ', '')] = \
                [f for f, x in v.items() if x is True]
    print('\n=== 군집(=마을) 별 역할 ===')
    for cl in cluster(C):
        if len(cl) < 4: continue
        xs = [C[c]['x'] for c in cl]; zs = [C[c]['z'] for c in cl]
        have = collections.Counter()
        for c in cl:
            for f in byname.get(C[c].get('name', '').replace(' ', ''), []):
                have[f] += 1
        print('\n─ %2d명  중심(%5.0f,%5.0f)' % (len(cl), sum(xs) / len(xs), sum(zs) / len(zs)))
        print('   있음:', dict(have.most_common()) or '없음')
        print('   없음:', [f for f in roles if f not in have])
    return 0

if __name__ == '__main__':
    sys.exit(main())
