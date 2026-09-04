import sys, json
import numpy as np, amulet, logging
logging.disable(logging.ERROR)

SKIP = {"air","cave_air","void_air","water","flowing_water","bubble_column",
        "seagrass","tall_seagrass","kelp","kelp_plant"}
def base(n): return n.split(":")[-1]

def scan(path):
    lv = amulet.load_level(path)
    dims = list(lv.dimensions)
    dim = "minecraft:overworld" if "minecraft:overworld" in dims else dims[0]
    pal = lv.block_palette
    bbox=None; nch=0; nerr=0
    for cx, cz in lv.all_chunk_coords(dim):
        try:
            ch = lv.get_chunk(cx, cz, dim)
        except Exception:
            nerr+=1; continue
        nch+=1
        solid = np.array([base(pal[i].namespaced_name) not in SKIP for i in range(len(pal))], bool)
        for cy in list(ch.blocks.sub_chunks):
            arr = ch.blocks.get_sub_chunk(cy)
            if arr.max() >= len(solid): continue
            m = solid[arr]
            if not m.any(): continue
            xs, ys, zs = np.nonzero(m)
            b = (cx*16+int(xs.min()), cy*16+int(ys.min()), cz*16+int(zs.min()),
                 cx*16+int(xs.max()), cy*16+int(ys.max()), cz*16+int(zs.max()))
            bbox = b if bbox is None else (min(bbox[0],b[0]),min(bbox[1],b[1]),min(bbox[2],b[2]),
                                           max(bbox[3],b[3]),max(bbox[4],b[4]),max(bbox[5],b[5]))
    v = str(lv.level_wrapper.version); lv.close()
    out={"path":path,"dim":dim,"version":v,"chunks":nch,"err_chunks":nerr,"bbox":bbox}
    if bbox: out["size"]=(bbox[3]-bbox[0]+1,bbox[4]-bbox[1]+1,bbox[5]-bbox[2]+1)
    return out

for p in sys.argv[1:]:
    try: print(json.dumps(scan(p)), flush=True)
    except Exception as e: print(json.dumps({"path":p,"error":f"{type(e).__name__}: {e}"}), flush=True)
