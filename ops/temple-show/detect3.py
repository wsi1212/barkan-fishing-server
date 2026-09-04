"""월드 전체에서 인공블록 밀도가 가장 높은 청크를 씨앗으로 잡아 flood-fill."""
import sys, json, numpy as np, amulet, logging, collections
from detect import NAT, bn
logging.disable(logging.ERROR)

def run(path, thr=400):
    lv = amulet.load_level(path)
    dims=list(lv.dimensions); D = "minecraft:overworld" if "minecraft:overworld" in dims else dims[0]
    pal = lv.block_palette
    dens={}; ybox={}
    for cx,cz in lv.all_chunk_coords(D):
        try: ch = lv.get_chunk(cx,cz,D)
        except Exception: continue
        man = np.array([not NAT.match(bn(pal[i].namespaced_name)) for i in range(len(pal))], bool)
        tot=0; ymin=10**9; ymax=-10**9
        for cy in list(ch.blocks.sub_chunks):
            a = ch.blocks.get_sub_chunk(cy)
            if a.max() >= len(man): continue
            m = man[a]
            c=int(m.sum())
            if not c: continue
            tot+=c; ys=np.nonzero(m)[1]
            ymin=min(ymin,cy*16+int(ys.min())); ymax=max(ymax,cy*16+int(ys.max()))
        if tot: dens[(cx,cz)]=tot; ybox[(cx,cz)]=(ymin,ymax)
    lv.close()
    if not dens: return {"path":path,"error":"empty"}
    seed = max(dens, key=dens.get)
    comp=set(); seen=set(); stack=[seed]
    while stack:
        k=stack.pop()
        if k in seen: continue
        seen.add(k)
        if dens.get(k,0)<thr: continue
        comp.add(k); x,z=k
        for n in ((x+1,z),(x-1,z),(x,z+1),(x,z-1),(x+1,z+1),(x-1,z-1),(x+1,z-1),(x-1,z+1)):
            if n not in seen: stack.append(n)
    cxs=[c[0] for c in comp]; czs=[c[1] for c in comp]
    ymin=min(ybox[c][0] for c in comp); ymax=max(ybox[c][1] for c in comp)
    bb=(min(cxs)*16, ymin, min(czs)*16, max(cxs)*16+15, ymax, max(czs)*16+15)
    return {"path":path,"seed":seed,"seed_density":dens[seed],"chunks":len(comp),"bbox":bb,
            "size":(bb[3]-bb[0]+1,bb[4]-bb[1]+1,bb[5]-bb[2]+1)}

for p in sys.argv[1:]:
    try: print(json.dumps(run(p)), flush=True)
    except Exception as e: print(json.dumps({"path":p,"error":f"{type(e).__name__}: {e}"}), flush=True)
