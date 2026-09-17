#!/usr/bin/env python3
"""피아노 bake 코너 단위 자가검증 — AABB 가 아니라 «8개 꼭짓점»을 대조한다.

v1(verify_piano.py) 은 AABB 만 봐서 «방향이 틀린 박스»를 통과시켰다(2026-09-16:
누락 0/왜곡 0 이라고 보고했는데 유저가 막대·뚜껑 이상을 발견). 같은 AABB 를 갖는
서로 다른 방향의 박스가 존재하므로 AABB 비교는 필요조건일 뿐이다.
"""
import json, os, re, sys, math, zipfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from vanilla_model import parts_for_state

BS = os.path.expanduser("~/Library/Application Support/feather/player-server/servers/"
                        "07de2d81-991a-47e2-b62d-06c0d1b5150a/plugins/BlockShip")
RP = os.path.expanduser("~/development/barkan-resourcepack")
JARP = os.path.expanduser("~/Library/Application Support/feather/player-server/servers/"
                          "07de2d81-991a-47e2-b62d-06c0d1b5150a/plugins/BarkanPiano-1.21.11.jar")
WHITE_Y, BLACK_Y, Y_TOL = 1.0899, 1.1384, 0.08

def mat_apply(v, p):
    return (v[0]*p[0]+v[1]*p[1]+v[2]*p[2]+v[3],
            v[4]*p[0]+v[5]*p[1]+v[6]*p[2]+v[7],
            v[8]*p[0]+v[9]*p[1]+v[10]*p[2]+v[11])
def corners(fr, to, M=None):
    out=[]
    for a in (0,1):
        for b in (0,1):
            for c in (0,1):
                p=((fr[0] if a==0 else to[0]), (fr[1] if b==0 else to[1]), (fr[2] if c==0 else to[2]))
                out.append(mat_apply(M,p) if M else p)
    return out

orig=[]
with zipfile.ZipFile(JARP) as z:
    for n in sorted(x for x in z.namelist() if x.endswith(".mcfunction")):
        s=z.read(n).decode("utf-8","replace")
        for m in re.finditer(r'block_state:\{Name:"minecraft:([a-z_]+)"(?:,Properties:\{([^}]*)\})?\},'
                             r'transformation:\[([^\]]+)\]', s):
            name,props,tr=m.group(1),m.group(2) or "",m.group(3)
            v=[float(x.rstrip('f')) for x in tr.split(',')]
            ty=v[7]
            if ((name=="quartz_block" and abs(ty-WHITE_Y)<Y_TOL) or
                (name=="polished_blackstone_slab" and abs(ty-BLACK_Y)<Y_TOL)): continue
            state=name if not props else name+"["+props.replace('"','').replace(":","=")+"]"
            for elements,_ in parts_for_state(state):
                for e in elements:
                    fr=[x/16 for x in e["from"]]; to=[x/16 for x in e["to"]]
                    orig.append((corners(fr,to,v), name))

desc=json.load(open(os.path.join(BS,"piano-body.json")))
def qrot(q,p):
    x,y,z,w=q
    cx=y*p[2]-z*p[1]; cy=z*p[0]-x*p[2]; cz=x*p[1]-y*p[0]
    c2x=y*cz-z*cy; c2y=z*cx-x*cz; c2z=x*cy-y*cx
    return (p[0]+2*(w*cx+c2x), p[1]+2*(w*cy+c2y), p[2]+2*(w*cz+c2z))
recon=[]
for b in desc["bodies"]:
    mdl=json.load(open(os.path.join(RP,"assets/barkan/models/piano",b["model"].split("/")[-1]+".json")))
    for e in mdl["elements"]:
        cs=[]
        for p in corners(e["from"],e["to"]):
            mm=tuple((p[i]-8)/16*b["k"] for i in range(3))
            r=qrot(b["rot"],mm)
            cs.append(tuple(r[i]+b["pos"][i] for i in range(3)))
        recon.append(cs)

# 중심으로 매칭 후, 꼭짓점 집합 간 최대 편차(Hausdorff)
def ctr(cs): return [sum(c[i] for c in cs)/8 for i in range(3)]
used=[False]*len(recon); errs=[]; unmatched=[]
for cs,name in orig:
    oc=ctr(cs); best=-1; bd=1e9
    for j,rs in enumerate(recon):
        if used[j]: continue
        rc=ctr(rs); d=sum((rc[i]-oc[i])**2 for i in range(3))
        if d<bd: bd,best=d,j
    if best<0: unmatched.append(name); continue
    used[best]=True; rs=recon[best]
    h=0.0
    for p in cs: h=max(h, min(math.dist(p,q) for q in rs))
    for q in rs: h=max(h, min(math.dist(p,q) for p in cs))
    errs.append((h,name))
errs.sort(reverse=True)
tot=len(errs)
print("대조 %d개 (미매칭 %d)" % (tot, len(unmatched)))
for th in (0.001,0.01,0.05,0.1,0.3):
    print("  꼭짓점 오차 ≤ %-6.3f 블록 : %4d개 (%5.1f%%)" % (th, sum(1 for e,_ in errs if e<=th), 100*sum(1 for e,_ in errs if e<=th)/tot))
print("  최대 오차 = %.4f 블록" % errs[0][0])
print("\n오차 큰 것 top10 (블록):")
for e,n in errs[:10]: print("   %.4f  %s" % (e,n))
