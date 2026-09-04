"""신전 시그니처 블록(prismarine/sea_lantern/conduit) 밀도로 위치를 찾는다."""
import sys, json, re, numpy as np, amulet, logging, collections
logging.disable(logging.ERROR)
SIG = re.compile(r"(prismarine|sea_lantern|conduit)")
def run(path):
    lv=amulet.load_level(path); dims=list(lv.dimensions)
    D="minecraft:overworld" if "minecraft:overworld" in dims else dims[0]
    pal=lv.block_palette; dens=collections.Counter(); yb={}
    for cx,cz in lv.all_chunk_coords(D):
        try: ch=lv.get_chunk(cx,cz,D)
        except Exception: continue
        sig=np.array([bool(SIG.search(pal[i].namespaced_name)) for i in range(len(pal))],bool)
        t=0; ymin=10**9; ymax=-10**9
        for cy in list(ch.blocks.sub_chunks):
            a=ch.blocks.get_sub_chunk(cy)
            if a.max()>=len(sig): continue
            m=sig[a]
            if not m.any(): continue
            t+=int(m.sum()); ys=np.nonzero(m)[1]
            ymin=min(ymin,cy*16+int(ys.min())); ymax=max(ymax,cy*16+int(ys.max()))
        if t: dens[(cx,cz)]=t; yb[(cx,cz)]=(ymin,ymax)
    lv.close()
    if not dens: return {"path":path,"error":"시그니처 없음"}
    seed=max(dens,key=dens.get)
    comp=set(); seen=set(); stack=[seed]; thr=max(30, dens[seed]//40)
    while stack:
        k=stack.pop()
        if k in seen: continue
        seen.add(k)
        if dens.get(k,0)<thr: continue
        comp.add(k); x,z=k
        for n in ((x+1,z),(x-1,z),(x,z+1),(x,z-1),(x+1,z+1),(x-1,z-1),(x+1,z-1),(x-1,z+1)):
            if n not in seen: stack.append(n)
    cxs=[c[0] for c in comp]; czs=[c[1] for c in comp]
    bb=(min(cxs)*16, min(yb[c][0] for c in comp), min(czs)*16,
        max(cxs)*16+15, max(yb[c][1] for c in comp), max(czs)*16+15)
    return {"path":path,"seed":seed,"peak":dens[seed],"thr":thr,"chunks":len(comp),"bbox":bb,
            "size":(bb[3]-bb[0]+1,bb[4]-bb[1]+1,bb[5]-bb[2]+1),"top":dens.most_common(5)}
for p in sys.argv[1:]:
    try: print(json.dumps(run(p)),flush=True)
    except Exception as e: print(json.dumps({"path":p,"error":f"{type(e).__name__}: {e}"}),flush=True)
