"""17번(아르타잔의 성역) 을 «안 잘리게» 통째로 떠서 flatroom 5000/100/5000 에 놓을
region 파일을 오프라인으로 굽는다. 서버는 아무 일도 하지 않는다(파일만 떨어뜨림)."""
import json, os, shutil, sys, time, numpy as np, amulet, logging
from amulet.api.block import Block
import tlib
from manifest import FAKE_SEA
logging.disable(logging.ERROR)

SRC   = "ex/17/world"
BBOX  = (464, 58, 496, 911, 182, 1071)      # 신전 복합체 전체 + 산호 여백
DEST  = "build/flatroom_patch"
TPL   = "../flatroom/level.dat"             # prod flatroom 의 level.dat (평지 제너레이터)
DIM   = "minecraft:overworld"
AT    = (5000, 100, 5000)                   # 콘텐츠 최소모서리 / 바닥 y
GROUND = [("bedrock", -64, 1), ("dirt", -63, 2), ("grass_block", -61, 1)]

def main():
    t0 = time.time()
    print("1/4 소스 추출", BBOX, flush=True)
    vol, uni = tlib.world_volume(SRC, BBOX)
    vol, local = tlib.normalize(vol, uni, FAKE_SEA)
    W, H, L = vol.shape
    print(f"    {W}x{H}x{L}, 팔레트 {len(local)}, 비어있지않은 블록 {int((vol!=0).sum()):,}", flush=True)

    ax, az = (AT[0] // 16) * 16, (AT[2] // 16) * 16        # 청크 정렬 원점
    px, pz = AT[0] - ax, AT[2] - az                        # 서/북 패딩
    pad = np.zeros((W + px, H, L + pz), vol.dtype)
    pad[px:, :, pz:] = vol
    del vol
    W2, L2 = pad.shape[0], pad.shape[2]
    cw = -(-W2 // 16) * 16; cl = -(-L2 // 16) * 16         # 청크 단위로 올림

    if os.path.exists(DEST): shutil.rmtree(DEST)
    for d in ("region", "entities", "poi", "data"): os.makedirs(f"{DEST}/{d}")
    shutil.copy(TPL, f"{DEST}/level.dat")

    print("2/4 대상 월드 열기 + 평지 지반", flush=True)
    lv = amulet.load_level(DEST)
    air = lv.block_palette.get_add_block(Block("universal_minecraft", "air"))
    for name, y, h in GROUND:                              # flatroom 지반을 그대로 재현(구멍 방지)
        b = lv.block_palette.get_add_block(Block("universal_minecraft", name))
        tlib.paste(lv, DIM, np.full((cw, h, cl), b, np.int32), (ax, y, az), air)
    print("3/4 신전 붙여넣기", flush=True)
    vol2, air2 = tlib.to_level(pad, local, lv)
    del pad
    tlib.paste(lv, DIM, vol2, (ax, AT[1], az), air2)
    del vol2
    print("4/4 저장", flush=True)
    lv.save(); lv.close()
    files = sorted(os.listdir(f"{DEST}/region"))
    print("region:", files)
    print(f"콘텐츠 범위 x {AT[0]}..{AT[0]+W-1} / y {AT[1]}..{AT[1]+H-1} / z {AT[2]}..{AT[2]+L-1}")
    json.dump({"x0":AT[0],"y0":AT[1],"z0":AT[2],"w":W,"h":H,"l":L,
               "chunk_x":[ax//16,(ax+cw)//16-1],"chunk_z":[az//16,(az+cl)//16-1]},
              open("patch17.json","w"), indent=1)
    print(f"{time.time()-t0:.0f}s")

main()
