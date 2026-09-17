#!/usr/bin/env python3
"""피아노 bake 자가검증 — 구운 모델을 월드 좌표로 «역복원»해 원본 큐브와 대조한다.

bake_piano.py 의 출력만 보고 눈으로 판단하면 놓친다(2026-09-16: 뒷면 소실·막대 누락·
철심 이동을 유저가 먼저 발견). 여기서 세 가지를 수치로 잡는다.
  ① 부피 대조   — 원본 큐브 AABB 합집합 vs 복원 AABB 합집합 (누락/초과)
  ② 면 대조     — 6방향별 면 개수 (회전 리맵 누락이면 방향이 쏠린다)
  ③ 형상 왜곡   — 얇은 큐브(막대/철심)의 치수 변화 (AABB 근사로 굵어졌는가)
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

# ---------- 원본 ----------
orig = []
with zipfile.ZipFile(JARP) as z:
    for n in sorted(x for x in z.namelist() if x.endswith(".mcfunction")):
        s = z.read(n).decode("utf-8", "replace")
        for m in re.finditer(r'block_state:\{Name:"minecraft:([a-z_]+)"(?:,Properties:\{([^}]*)\})?\},'
                             r'transformation:\[([^\]]+)\]', s):
            name, props, tr = m.group(1), m.group(2) or "", m.group(3)
            v = [float(x.rstrip('f')) for x in tr.split(',')]
            ty = v[7]
            if ((name == "quartz_block" and abs(ty-WHITE_Y) < Y_TOL) or
                (name == "polished_blackstone_slab" and abs(ty-BLACK_Y) < Y_TOL)): continue
            state = name if not props else name+"["+props.replace('"','').replace(":","=")+"]"
            for elements, _tm in parts_for_state(state):
                for e in elements:
                    fr, to = e["from"], e["to"]
                    pts = [mat_apply(v, ((fr[0] if a==0 else to[0])/16, (fr[1] if b==0 else to[1])/16,
                                         (fr[2] if c==0 else to[2])/16))
                           for a in (0,1) for b in (0,1) for c in (0,1)]
                    lo = [min(p[i] for p in pts) for i in range(3)]
                    hi = [max(p[i] for p in pts) for i in range(3)]
                    orig.append((lo, hi, len(e.get("faces", {})), name))

# ---------- 복원 ----------
desc = json.load(open(os.path.join(BS, "piano-body.json")))
def qrot(q, p):
    x,y,z,w = q
    # v' = v + 2w(q×v) + 2q×(q×v)
    cx = y*p[2]-z*p[1]; cy = z*p[0]-x*p[2]; cz = x*p[1]-y*p[0]
    c2x = y*cz-z*cy;    c2y = z*cx-x*cz;    c2z = x*cy-y*cx
    return (p[0]+2*(w*cx+c2x), p[1]+2*(w*cy+c2y), p[2]+2*(w*cz+c2z))

recon = []; face_dirs = {}
for b in desc["bodies"]:
    mdl = json.load(open(os.path.join(RP, "assets/barkan/models/piano", b["model"].split("/")[-1] + ".json")))
    for e in mdl["elements"]:
        for f in e.get("faces", {}): face_dirs[f] = face_dirs.get(f, 0) + 1
        pts = []
        for a in (0,1):
            for c in (0,1):
                for d in (0,1):
                    m = ((e["from"][0] if a==0 else e["to"][0]) - 8) / 16 * b["k"],
                    mm = (((e["from"][0] if a==0 else e["to"][0])-8)/16*b["k"],
                          ((e["from"][1] if c==0 else e["to"][1])-8)/16*b["k"],
                          ((e["from"][2] if d==0 else e["to"][2])-8)/16*b["k"])
                    r = qrot(b["rot"], mm)
                    pts.append((r[0]+b["pos"][0], r[1]+b["pos"][1], r[2]+b["pos"][2]))
        lo = [min(p[i] for p in pts) for i in range(3)]
        hi = [max(p[i] for p in pts) for i in range(3)]
        recon.append((lo, hi, len(e.get("faces", {}))))

# ---------- 리포트 ----------
def bbox(lst):
    return ([min(x[0][i] for x in lst) for i in range(3)], [max(x[1][i] for x in lst) for i in range(3)])
ol, oh = bbox(orig); rl, rh = bbox(recon)
print("원본 큐브 %d개 / 복원 요소 %d개  (자투리 %d개는 굽지 않음)" % (len(orig), len(recon), len(desc["keep"])))
print("원본 bbox  lo=%s hi=%s" % ([round(x,3) for x in ol], [round(x,3) for x in oh]))
print("복원 bbox  lo=%s hi=%s" % ([round(x,3) for x in rl], [round(x,3) for x in rh]))
print("bbox 오차  lo=%s hi=%s" % ([round(rl[i]-ol[i],3) for i in range(3)], [round(rh[i]-oh[i],3) for i in range(3)]))
print()
print("면 방향 분포(복원):", dict(sorted(face_dirs.items())))
of = {}
for _,_,nf,_ in orig: of[nf] = of.get(nf,0)+1
print("원본 요소당 면 개수 분포:", dict(sorted(of.items())))
print()
# 얇은 큐브 왜곡
thin_o = [(lo,hi) for lo,hi,_,_ in orig if sorted([hi[i]-lo[i] for i in range(3)])[1] < 0.06]
thin_r = [(lo,hi) for lo,hi,_ in recon if sorted([hi[i]-lo[i] for i in range(3)])[1] < 0.06]
print("얇은 큐브(철심·막대) 원본 %d개 → 복원 %d개  %s" %
      (len(thin_o), len(thin_r), "★상당수가 굵어졌다" if len(thin_r) < len(thin_o)*0.8 else "유지"))

# ---------- ④ 큐브 단위 매칭: 원본 하나하나가 복원본에 있는가 ----------
print()
used = [False]*len(recon)
miss, shifted = [], []
for lo, hi, _nf, name in orig:
    ctr = [(lo[i]+hi[i])/2 for i in range(3)]
    dim = [hi[i]-lo[i] for i in range(3)]
    best, bd = -1, 1e9
    for j, (rlo, rhi, _) in enumerate(recon):
        if used[j]: continue
        rc = [(rlo[i]+rhi[i])/2 for i in range(3)]
        d = sum((rc[i]-ctr[i])**2 for i in range(3))
        if d < bd: bd, best = d, j
    if best < 0 or bd > 0.02**2:
        miss.append((name, [round(x,3) for x in ctr], [round(x,3) for x in dim]))
    else:
        used[best] = True
        rlo, rhi, _ = recon[best]
        rd = [rhi[i]-rlo[i] for i in range(3)]
        err = max(abs(rd[i]-dim[i]) for i in range(3))
        if err > 0.02: shifted.append((name, [round(x,3) for x in dim], [round(x,3) for x in rd]))
print("원본 %d개 중 복원에서 못 찾음 = %d개 (자투리 %d 포함)" % (len(orig), len(miss), len(desc["keep"])))
print("치수가 틀어진 것 = %d개" % len(shifted))
if miss:
    from collections import Counter
    print("  누락 재질:", Counter(m[0] for m in miss).most_common(6))
    big = sorted(miss, key=lambda m: -(m[2][0]*m[2][1]*m[2][2]))[:6]
    print("  누락 중 큰 것(부피순):")
    for n,c,d in big: print("    %-26s 중심 %s 치수 %s" % (n, c, d))
if shifted[:4]:
    print("  치수 왜곡 예:", shifted[:4])
