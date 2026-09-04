"""플레이어 위치에서 시작해 «사람이 지은 블록» 밀도가 높은 청크를 flood-fill 해 빌드 범위를 잡는다."""
import sys, json, numpy as np, amulet, logging, collections
from detect import NAT, bn
logging.disable(logging.ERROR)

def run(path, px, pz, win=24, thr=150):
    lv = amulet.load_level(path)
    dims=list(lv.dimensions); D = "minecraft:overworld" if "minecraft:overworld" in dims else dims[0]
    pal = lv.block_palette
    pcx, pcz = px//16, pz//16
    dens = {}; ybox = {}; names = collections.Counter()
    for cx in range(pcx-win, pcx+win+1):
        for cz in range(pcz-win, pcz+win+1):
            try: ch = lv.get_chunk(cx,cz,D)
            except Exception: continue
            man = np.array([not NAT.match(bn(pal[i].namespaced_name)) for i in range(len(pal))], bool)
            tot=0; ymin=10**9; ymax=-10**9
            for cy in list(ch.blocks.sub_chunks):
                a = ch.blocks.get_sub_chunk(cy)
                if a.max() >= len(man): continue
                m = man[a]
                c = int(m.sum())
                if not c: continue
                tot += c
                ys = np.nonzero(m)[1]
                ymin = min(ymin, cy*16+int(ys.min())); ymax = max(ymax, cy*16+int(ys.max()))
                for i,n in zip(*np.unique(a[m], return_counts=True)): names[bn(pal[int(i)].namespaced_name)] += int(n)
            if tot:
                dens[(cx,cz)] = tot; ybox[(cx,cz)] = (ymin,ymax)
    # flood fill
    seen=set(); stack=[]
    for d in range(0,6):
        for dx in range(-d,d+1):
            for dz in range(-d,d+1):
                k=(pcx+dx,pcz+dz)
                if dens.get(k,0)>=thr: stack.append(k)
        if stack: break
    comp=set()
    while stack:
        k=stack.pop()
        if k in seen: continue
        seen.add(k)
        if dens.get(k,0) < thr: continue
        comp.add(k)
        x,z=k
        for n in ((x+1,z),(x-1,z),(x,z+1),(x,z-1),(x+1,z+1),(x-1,z-1),(x+1,z-1),(x-1,z+1)):
            if n not in seen: stack.append(n)
    lv.close()
    if not comp: return {"path":path,"error":"no cluster","top":names.most_common(8)}
    cxs=[c[0] for c in comp]; czs=[c[1] for c in comp]
    ymin=min(ybox[c][0] for c in comp); ymax=max(ybox[c][1] for c in comp)
    bbox=(min(cxs)*16, ymin, min(czs)*16, max(cxs)*16+15, ymax, max(czs)*16+15)
    return {"path":path,"chunks":len(comp),"bbox":bbox,
            "size":(bbox[3]-bbox[0]+1,bbox[4]-bbox[1]+1,bbox[5]-bbox[2]+1),
            "top":names.most_common(6)}

if __name__=="__main__":
    for spec in sys.argv[1:]:
        p,x,z = spec.split(",")
        try: print(json.dumps(run(p,int(x),int(z))), flush=True)
        except Exception as e: print(json.dumps({"path":p,"error":f"{type(e).__name__}: {e}"}), flush=True)
