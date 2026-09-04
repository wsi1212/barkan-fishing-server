"""후보 해저신전들을 하나의 전시월드(temple_show)에 격자로 굽는다."""
import json, os, sys, time, numpy as np, amulet, logging
from amulet.api.block import Block
import tlib
from manifest import CAND
logging.disable(logging.ERROR)

OUT = sys.argv[1] if len(sys.argv) > 1 else "build/temple_show"
DIM = "minecraft:overworld"
GAP, ROW_MAX, FLOOR, YMAX = 24, 800, 64, 318
def align(v, a=16): return (v // a) * a

def extract(kind, path, bb, extra):
    """소스를 열어 (정규화된 볼륨, 로컬팔레트) 를 만들고 소스를 닫는다."""
    if kind == "schem":
        vol, uni = tlib.parse_schematic(path)
    else:
        vol, uni = tlib.world_volume(path, tuple(bb))
    vol, local = tlib.normalize(vol, uni, extra)
    vol, _ = tlib.trim(vol, 0)
    return vol, local

def main():
    boxes = json.load(open("boxes.json")) if os.path.exists("boxes.json") else {}
    plots = []
    x = z = row_depth = 0
    t0 = time.time()
    for cid, ko, src, kind, path, ppos, extra in CAND:
        t = time.time()
        bb = boxes.get(cid)
        if kind == "world" and not bb:
            print(f"[{cid}] SKIP: 범위 미검출"); continue
        vol, local = extract(kind, path, bb, extra)
        if vol is None:
            print(f"[{cid}] SKIP: 내용 없음"); continue
        W, H, L = vol.shape
        if x != 0 and x + W > ROW_MAX:
            z = align(z + row_depth + GAP); x = 0; row_depth = 0
        ox, oz = align(x), align(z)
        oy = min(FLOOR, YMAX - H)
        lv = amulet.load_level(OUT)                       # 소스는 이미 닫힌 상태
        vol2, air = tlib.to_level(vol, local, lv)
        tlib.paste(lv, DIM, vol2, (ox, oy, oz), air)
        tlib.platform(lv, DIM, ox, oz, W, L, oy - 1)
        lv.save(); lv.close()
        plots.append({"id": cid, "ko": ko, "src": src, "kind": kind,
                      "x": ox, "y": oy, "z": oz, "w": W, "h": H, "l": L,
                      "cx": ox + W // 2, "cz": oz + L // 2})
        print(f"[{cid}] {ko:14s} {W:4d}x{H:4d}x{L:4d} @ ({ox},{oy},{oz})  {time.time()-t:.1f}s", flush=True)
        x = align(ox + W + GAP); row_depth = max(row_depth, L)
    lv = amulet.load_level(OUT)
    sp = lv.block_palette.get_add_block(Block("universal_minecraft", "sea_lantern"))
    air = lv.block_palette.get_add_block(Block("universal_minecraft", "air"))
    tlib.paste(lv, DIM, np.full((16, 1, 16), sp, np.int32), (-32, FLOOR - 1, -32), air)
    lv.save(); lv.close()
    json.dump(plots, open("plots.json", "w"), ensure_ascii=False, indent=1)
    print(f"완료 {len(plots)}개 / {time.time()-t0:.0f}s")

main()
