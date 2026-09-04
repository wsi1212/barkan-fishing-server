"""전시월드 후보를 flatroom 의 «아직 region 파일이 없는» 좌표에 오프라인으로 굽는다.
서버는 아무 일도 하지 않는다 — 파일만 떨어뜨리면 다음에 그 청크를 열 때 로드된다."""
import json, os, shutil, sys, time, numpy as np, amulet, logging
from amulet.api.block import Block
import tlib
from manifest import CAND
logging.disable(logging.ERROR)

DEST = "build/flatroom_patch2"
TPL  = "../flatroom/level.dat"
DIM  = "minecraft:overworld"
GROUND = [("bedrock", -64, 1), ("dirt", -63, 2), ("grass_block", -61, 1)]
JOBS = [("07", 6700, 100, 5000), ("13", 6700, 100, 5300)]   # id, x, y, z (콘텐츠 최소모서리)

def extract(cid):
    cand = {c[0]: c for c in CAND}[cid]
    _, ko, src, kind, path, _pp, extra = cand
    if kind == "schem":
        vol, uni = tlib.parse_schematic(path)
    else:
        bb = json.load(open("boxes.json"))[cid]
        vol, uni = tlib.world_volume(path, tuple(bb))
    vol, local = tlib.normalize(vol, uni, extra)
    vol, _ = tlib.trim(vol, 0)
    return ko, src, vol, local

def main():
    t0 = time.time()
    items = []
    for cid, x, y, z in JOBS:
        ko, src, vol, local = extract(cid)
        ax, az = (x // 16) * 16, (z // 16) * 16
        px, pz = x - ax, z - az
        W, H, L = vol.shape
        pad = np.zeros((W + px, H, L + pz), vol.dtype)
        pad[px:, :, pz:] = vol
        items.append(dict(id=cid, ko=ko, src=src, vol=pad, local=local, ax=ax, ay=y, az=az,
                          x=x, z=z, w=W, h=H, l=L))
        print(f"[{cid}] {ko:14s} {W}x{H}x{L} → x {x}..{x+W-1} / y {y}..{y+H-1} / z {z}..{z+L-1}", flush=True)

    if os.path.exists(DEST): shutil.rmtree(DEST)
    for d in ("region", "entities", "poi", "data"): os.makedirs(f"{DEST}/{d}")
    shutil.copy(TPL, f"{DEST}/level.dat")
    lv = amulet.load_level(DEST)
    air = lv.block_palette.get_add_block(Block("universal_minecraft", "air"))
    for it in items:
        cw = -(-it["vol"].shape[0] // 16) * 16
        cl = -(-it["vol"].shape[2] // 16) * 16
        for name, y, h in GROUND:                      # 평지 지반 재현(바닥 구멍 방지)
            b = lv.block_palette.get_add_block(Block("universal_minecraft", name))
            tlib.paste(lv, DIM, np.full((cw, h, cl), b, np.int32), (it["ax"], y, it["az"]), air)
        v2, a2 = tlib.to_level(it["vol"], it["local"], lv)
        tlib.paste(lv, DIM, v2, (it["ax"], it["ay"], it["az"]), a2)
        it.pop("vol"); it.pop("local")
    lv.save(); lv.close()
    print("region:", sorted(os.listdir(f"{DEST}/region")))
    json.dump(items, open("patch2.json", "w"), ensure_ascii=False, indent=1)
    print(f"{time.time()-t0:.0f}s")

main()
