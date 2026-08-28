#!/usr/bin/env python3
"""megstudy와 <b>같은 잣대</b>로 우리 .bbmodel을 잰다.

★.bbmodel은 소스 포맷이라 rotation이 자유각 [x,y,z] 리스트다(리소스팩의 컴파일된
  vanilla JSON은 ±22.5/±45만 허용). 같은 지표를 뽑되 이 차이는 감안해서 읽어야 한다.
"""
import json, sys, collections

def dims_ang(el):
    a,b = el.get('from',[0,0,0]), el.get('to',[0,0,0])
    d = sorted(abs(b[i]-a[i]) for i in range(3))
    r = el.get('rotation') or [0,0,0]
    if isinstance(r, dict): ang = abs(float(r.get('angle',0) or 0))
    else: ang = max(abs(float(v)) for v in r) if r else 0.0
    return d, ang

def bone_count(o):
    n=0
    for x in o:
        if isinstance(x,dict): n += 1 + bone_count(x.get('children',[]))
    return n

def owner_map(o, parent=None, out=None):
    """큐브 uuid → 소속 본 이름"""
    out = {} if out is None else out
    for x in o:
        if isinstance(x,dict):
            nm = x.get('name','?')
            for c in x.get('children',[]):
                if isinstance(c,str): out[c]=nm
            owner_map(x.get('children',[]), nm, out)
        elif isinstance(x,str) and parent:
            out[x]=parent
    return out

for path in sys.argv[1:]:
    d=json.load(open(path))
    els=[e for e in d.get('elements',[]) if e.get('type','cube')=='cube']
    if not els: continue
    own=owner_map(d.get('outliner',[]))
    m=[dims_ang(e) for e in els]
    n=len(m)
    rot=[x for x in m if x[1]>0.01]
    thin=[x for x in m if x[0][0]<=2.0]
    vols=[x[0][0]*x[0][1]*x[0][2] for x in m]
    mean=sum(vols)/n
    cv=(sum((v-mean)**2 for v in vols)/n)**0.5/max(1e-6,mean)
    per=collections.Counter(own.get(e.get('uuid'),'?') for e in els)
    bones=bone_count(d.get('outliner',[]))
    name=path.split('/')[-1].replace('.bbmodel','')
    print('%-14s %4d %5d %7.2f %6.1f %6.1f %8.2f %10d' % (
        name, bones, n, n/max(1,bones), 100*len(rot)/n, 100*len(thin)/n, cv,
        max(per.values()) if per else 0))
    if rot:
        print('    회전각:', sorted({round(x[1],1) for x in rot})[:8])
